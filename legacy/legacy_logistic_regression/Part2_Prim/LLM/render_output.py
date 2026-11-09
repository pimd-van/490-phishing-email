"""Turn one model's answers into the user-facing output (reason, prevention guideline, sources).

Run from the project root:
    python part2/LLM/render_output.py --model llama3.1:8b --condition rag
    python part2/LLM/render_output.py --model llama3.1:8b --condition rag --hide-chunk-ids    # production view

Writes output_LLM.jsonl (one display object per email) and output_LLM.csv (id, output) next to the result file.
The guideline and source parts come from the model's chunk IDs and sources.json, so source names and links are
never written by the model. confidence and feature_detection belong to Part 1 and are left as null here.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
from part2.vector_database.main_vector_database import resolve_path, read_commented_json, load_settings  # noqa: E402
from part2.LLM.evaluate_LLM import latest_records  # noqa: E402

CONFIG_FILE = Path(__file__).resolve().parent / "config_LLM.json"
GENERAL_NOTE = "No guidance in the knowledge base matches this email specifically; these are general safety steps."


def render(rec: dict, sources: dict, show_ids: bool) -> dict:
    p = rec.get("parsed") or {}
    ok = bool(p.get("format_ok"))
    used = (p.get("chunk_ids_used") or []) if ok else []
    steps = []
    for act in (p.get("actions") or []) if ok else []:
        text = act["action"]
        cid = act.get("chunk_id") or ""
        steps.append(f"{text} [{cid}]" if show_ids and cid else text)
    cited = list(dict.fromkeys([cid for cid in used] + [a.get("chunk_id") for a in (p.get("actions") or []) if a.get("chunk_id")]))
    src, seen = [], set()
    for cid in cited:
        s = sources.get(cid)
        if s and s["url"] not in seen:
            seen.add(s["url"])
            src.append({"title": s["title"], "publisher": s["publisher"], "url": s["url"],
                        **({"chunk_ids": [cid]} if show_ids else {})})
        elif s and show_ids:
            next(x for x in src if x["url"] == s["url"])["chunk_ids"].append(cid)
    return {
        "confidence": None, "feature_detection": None,  # filled by Part 1
        "reason": p.get("reason", "") if ok else "",
        "prevention_guideline": steps,
        "general_guidance_only": bool(ok and not used),
        "note": GENERAL_NOTE if ok and not used else ("" if ok else "The model answer could not be read."),
        "source_guideline": src,
        "chunk_ids": used if show_ids else None,
        "model": rec["model"], "condition": rec["condition"], "prompt_version": rec["prompt_version"],
    }


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--model", required=True)
    a.add_argument("--condition", default="rag")
    a.add_argument("--prompt-version", default=None)
    a.add_argument("--hide-chunk-ids", action="store_true", help="production view: no [ID] after each step")
    a.add_argument("--result")
    args = a.parse_args()
    c = read_commented_json(CONFIG_FILE)
    pv = args.prompt_version or c["prompt_version"]
    v = load_settings(c["vector_config"])
    sources = {s["chunk_id"]: s for s in json.loads(resolve_path(v["sources_file"]).read_text(encoding="utf-8"))}
    path = resolve_path(args.result or c["result_file"])
    recs = [r for r in latest_records(path, None)
            if r["model"] == args.model and r["condition"] == args.condition and r["prompt_version"] == pv]
    if not recs:
        raise SystemExit("No matching answers")
    show = not args.hide_chunk_ids
    outs = [(r["id"], render(r, sources, show)) for r in sorted(recs, key=lambda r: r["id"])]
    with open(path.with_name("output_LLM.jsonl"), "w", encoding="utf-8") as f:
        for rid, o in outs:
            f.write(json.dumps({"id": rid, **o}, ensure_ascii=False) + "\n")
    with open(path.with_name("output_LLM.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["id", "output"])
        for rid, o in outs:
            w.writerow([rid, json.dumps(o, ensure_ascii=False)])
    print(f"{len(outs)} emails -> {path.with_name('output_LLM.jsonl')} and output_LLM.csv (chunk IDs {'shown' if show else 'hidden'})")


if __name__ == "__main__":
    main()
