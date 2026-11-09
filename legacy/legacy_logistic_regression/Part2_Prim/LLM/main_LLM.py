"""Generate structured action plans with local Ollama models under three conditions.

Run from the project root (run main_RAG.py on the same set first):
    python part2/LLM/main_LLM.py --dry-run                 # print one prompt per condition, call nothing
    python part2/LLM/main_LLM.py --limit 5                 # speed test: 5 emails x models x conditions
    python part2/LLM/main_LLM.py                           # full run from config_LLM.json
    python part2/LLM/main_LLM.py --prompt-version simple --conditions rag

Conditions (what the model is given besides the email):
  rag     the top-k chunks retrieved by main_RAG.py
  oracle  the gold chunks plus retrieved non-gold chunks as distractors, shuffled, k in total and always
          at least 2 distractors (so 6-7 chunks when the gold has 4-5); for gold fit=none rows: k retrieved
          chunks, none of them correct
  no_rag  no chunk text, only the list of all chunk IDs and titles

The model must answer in JSON (see the prompts in config_LLM.json). Every answer is appended to
result_LLM.jsonl at once, so an interrupted run resumes where it stopped; rerunning skips finished
(model, condition, prompt_version, id) combinations. Input files are never modified.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.dont_write_bytecode = True
PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from part2.vector_database.main_vector_database import load_settings, resolve_path, read_commented_json  # noqa: E402
from part2.RAG.main_RAG import load_gold, in_set, email_text, SETS  # noqa: E402

LLM_DIR = Path(__file__).resolve().parent
CONFIG_FILE = LLM_DIR / "config_LLM.json"
CONDITIONS = ("rag", "oracle", "no_rag")


def load_config(path=None) -> dict:
    c = read_commented_json(Path(path) if path else CONFIG_FILE)
    if not c.get("models") or not all(isinstance(m, str) and m for m in c["models"]):
        raise ValueError("models must be a non-empty list of Ollama model names")
    if not isinstance(c.get("prompts"), dict) or c.get("prompt_version") not in c["prompts"]:
        raise ValueError("prompt_version must be a key of prompts")
    if any(x not in CONDITIONS for x in c.get("conditions", [])):
        raise ValueError(f"conditions must be from {CONDITIONS}")
    if c.get("eval_set") not in SETS:
        raise ValueError(f"eval_set must be one of {SETS}")
    for name in ("request_timeout_seconds", "top_k"):
        if not isinstance(c.get(name), int) or c[name] <= 0:
            raise ValueError(f"{name} must be a positive integer")
    return c


# ---------- inputs ----------

def load_chunks(vector_config) -> dict:
    """chunk_id -> {"text", "header"} from the Chroma collection (the same text the retriever indexed)."""
    import chromadb
    v = load_settings(vector_config)
    col = chromadb.PersistentClient(path=str(resolve_path(v["database_dir"]))).get_collection(v["collection_name"])
    got = col.get(include=["documents", "metadatas"])
    return {i: {"text": d, "header": (m or {}).get("header", "")} for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}


def load_rows(c: dict, eval_set: str, limit: int | None) -> list[dict]:
    gold = load_gold(c["gold_file"])
    rows = []
    for line in open(resolve_path(c["input_file"]), encoding="utf-8"):
        rec = json.loads(line)
        g = gold.get(rec["id"])
        if g and in_set(g, eval_set):
            rec["_gold"] = g["chunk_list"]
            rec["_fit"] = g["fit"]
            rows.append(rec)
    rows.sort(key=lambda r: r["id"])
    return rows[:limit] if limit else rows


def given_chunks(condition: str, row: dict, retrieved: dict, k: int, all_ids: list[str]) -> list[str]:
    if condition == "no_rag":
        return []
    ranked = retrieved[row["id"]]
    if condition == "rag":
        return ranked[:k]
    gold = [c for c in row["_gold"] if c in all_ids]
    distractors = [c for c in ranked + all_ids if c not in gold]
    # k chunks in total, but always at least 2 distractors so that copying every given ID is never a perfect answer
    picked = gold + [c for c in dict.fromkeys(distractors)][: max(2, k - len(gold))]
    random.Random(f"{row['id']}-oracle").shuffle(picked)
    return picked


def build_user_message(row: dict, condition: str, given: list[str], chunks: dict, c: dict) -> str:
    email = email_text(row, c.get("max_email_chars", 0), c.get("max_urls", 3))
    parts = ["EMAIL", email, ""]
    if condition == "no_rag":
        parts.append("GUIDANCE TOPICS (IDs and titles only; no guidance text is provided)")
        parts += [f"[{cid}] {chunks[cid]['header']}" for cid in sorted(chunks)]
    else:
        parts.append("RETRIEVED GUIDANCE")
        parts += [f"[{cid}] {chunks[cid]['text']}" for cid in given]
    return "\n".join(parts)


# ---------- model call ----------

def call_ollama(c: dict, model: str, system: str, user: str) -> dict:
    payload = {"model": model, "stream": False, "options": c["generation"],
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if c.get("json_mode", True):
        payload["format"] = "json"
    if c.get("think") is not None:
        payload["think"] = c["think"]
    req = Request(c["ollama_url"].rstrip("/") + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=c["request_timeout_seconds"]) as response:
        return json.load(response)


def models_info(c: dict, models: list[str]) -> dict:
    try:
        with urlopen(c["ollama_url"].rstrip("/") + "/api/tags", timeout=30) as r:
            tags = json.load(r).get("models", [])
    except (HTTPError, URLError, OSError) as e:
        return {"error": str(e)}
    keep = {t["name"]: {"digest": t.get("digest"), "size": t.get("size"), "details": t.get("details")} for t in tags}
    return {m: keep.get(m, "not installed") for m in models}


def parse_answer(text: str, valid_ids: set) -> dict:
    """Parse the JSON answer; never raises. format_ok is true only for a well-formed answer."""
    out = {"format_ok": False, "chunk_ids_used": [], "no_specific_guidance": None, "reason": "", "actions": [],
           "invalid_ids": [], "parse_error": ""}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text or "", re.S)
        try:
            obj = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            obj = None
    if not isinstance(obj, dict):
        out["parse_error"] = "not a JSON object"
        return out
    ids = obj.get("chunk_ids_used")
    acts = obj.get("actions")
    ok = isinstance(ids, list) and all(isinstance(x, str) for x in ids) and isinstance(acts, list) \
        and isinstance(obj.get("reason"), str) and isinstance(obj.get("no_specific_guidance"), bool)
    ids = [x.strip().strip("[]") for x in ids] if isinstance(ids, list) else []
    ids = [x for x in dict.fromkeys(ids) if x]
    actions = []
    for a in acts if isinstance(acts, list) else []:
        if isinstance(a, dict) and isinstance(a.get("action"), str):
            cid = a.get("chunk_id")
            actions.append({"action": a["action"].strip(), "chunk_id": (cid or "").strip().strip("[]") if isinstance(cid, str) else ""})
        else:
            ok = False
    out.update({"format_ok": bool(ok), "chunk_ids_used": ids, "no_specific_guidance": obj.get("no_specific_guidance"),
                "reason": obj.get("reason") if isinstance(obj.get("reason"), str) else "", "actions": actions,
                "invalid_ids": [x for x in ids if x not in valid_ids]})
    if not ok:
        out["parse_error"] = "missing or wrong-typed field"
    return out


# ---------- main loop ----------

def done_keys(path: Path) -> set:
    keys = set()
    if path.exists():
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # a line cut by a crash; that combination runs again
            if not r.get("error"):
                keys.add((r["model"], r["condition"], r["prompt_version"], r["id"]))
    return keys


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config")
    p.add_argument("--models", nargs="+", help="override models")
    p.add_argument("--conditions", nargs="+", choices=CONDITIONS)
    p.add_argument("--prompt-version", help="key of prompts in the config (e.g. full, simple)")
    p.add_argument("--set", dest="eval_set", choices=SETS)
    p.add_argument("--limit", type=int, help="first N emails of the set (sorted by id)")
    p.add_argument("--dry-run", action="store_true", help="print the prompts for the first email and stop")
    a = p.parse_args()

    c = load_config(a.config)
    models = a.models or c["models"]
    conditions = a.conditions or c["conditions"]
    pv = a.prompt_version or c["prompt_version"]
    if pv not in c["prompts"]:
        raise SystemExit(f"prompt version {pv} not in config")
    eval_set = a.eval_set or c["eval_set"]
    system = c["prompts"][pv]

    rows = load_rows(c, eval_set, a.limit)
    if not rows:
        raise SystemExit(f"No rows in set {eval_set}")
    chunks = load_chunks(c["vector_config"])
    all_ids = sorted(chunks)
    retrieved = {}
    if any(x in ("rag", "oracle") for x in conditions):
        rag = json.loads(resolve_path(c["rag_result_file"]).read_text(encoding="utf-8"))
        retrieved = {r["query_id"]: r["top_retrieved_chunk"] for r in rag}
        missing = [r["id"] for r in rows if r["id"] not in retrieved]
        if missing:
            raise SystemExit(f"{len(missing)} emails have no retrieval result in {c['rag_result_file']}; "
                             f"run main_RAG.py --set {eval_set} first")

    if a.dry_run:
        for cond in conditions:
            g = given_chunks(cond, rows[0], retrieved, c["top_k"], all_ids)
            print(f"===== condition {cond} | prompt {pv} | id {rows[0]['id']} =====\n--- system ---\n{system}\n--- user ---")
            print(build_user_message(rows[0], cond, g, chunks, c)[:3000], "\n")
        return

    out_path = resolve_path(c["result_file"])
    info_path = out_path.with_name("models_info.json")
    info_path.write_text(json.dumps({"checked_at": time.strftime("%Y-%m-%d %H:%M:%S"), "models": models_info(c, models),
                                     "generation": c["generation"]}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    skip = done_keys(out_path)
    total = len(models) * len(conditions) * len(rows)
    n = 0
    with open(out_path, "a", encoding="utf-8") as out:
        for model in models:
            for cond in conditions:
                todo = [r for r in rows if (model, cond, pv, r["id"]) not in skip]
                print(f"{model} | {cond} | {pv}: {len(rows) - len(todo)} done, {len(todo)} to run", flush=True)
                for row in todo:
                    given = given_chunks(cond, row, retrieved, c["top_k"], all_ids)
                    user = build_user_message(row, cond, given, chunks, c)
                    rec = {"id": row["id"], "set": eval_set, "model": model, "condition": cond, "prompt_version": pv,
                           "given_chunk_ids": given, "gold_chunk_ids": row["_gold"], "gold_fit": row["_fit"]}
                    t0 = time.time()
                    try:
                        resp = call_ollama(c, model, system, user)
                        raw = (resp.get("message") or {}).get("content", "")
                        rec.update({"raw": raw, "latency_s": round(time.time() - t0, 2),
                                    "prompt_tokens": resp.get("prompt_eval_count"), "output_tokens": resp.get("eval_count"),
                                    "eval_duration_s": round((resp.get("eval_duration") or 0) / 1e9, 2),
                                    "done_reason": resp.get("done_reason"), "error": ""})
                        valid = set(all_ids) if cond == "no_rag" else set(given)
                        rec["parsed"] = parse_answer(raw, valid)
                    except (HTTPError, URLError, OSError, ValueError) as e:
                        rec.update({"raw": "", "latency_s": round(time.time() - t0, 2), "error": str(e), "parsed": None})
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    out.flush()
                    n += 1
                    if n % 25 == 0:
                        print(f"  {n}/{total} answers this run", flush=True)
    print(f"Wrote to {out_path}; model details in {info_path}")


if __name__ == "__main__":
    main()
