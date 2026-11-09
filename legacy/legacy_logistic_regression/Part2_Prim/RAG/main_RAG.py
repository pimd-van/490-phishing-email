"""Retrieve the closest guidance chunks for each email and score them against the gold labels.

Run from the project root (build the vector database first):
    python part2/RAG/main_RAG.py                         # set and files from config_RAG.json
    python part2/RAG/main_RAG.py --set fold1             # override the evaluation set
    python part2/RAG/main_RAG.py --vector-config part2/vector_database/config_vector_database_bge_large.json

Input: model_input.jsonl (the same capped email text the labels were made from) and gold.csv.
Output: result_RAG.json (one record per email) and summary_RAG.json (scores).
Input files are never modified.

Scores (rows whose gold fit is "none" have no gold chunk; they are retrieved but not scored):
  Recall@k  gold chunks found in the top k / number of gold chunks
  nDCG@k    graded: first gold chunk = 2, other gold chunks = 1
  MRR       1 / rank of the first gold chunk (0 if not in the top k)
  Hit@1     top result is the first gold chunk
Baseline: always return the k chunks that are most frequent in the gold of the scored rows.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from part2.vector_database.main_vector_database import load_settings, resolve_path, read_commented_json, load_model  # noqa: E402

RAG_DIR = Path(__file__).resolve().parent
CONFIG_FILE = RAG_DIR / "config_RAG.json"
SETS = ("dev", "test", "fold1", "fold2", "fold3", "fold4", "fold5", "fold6", "fold7", "fold8", "fold9", "fold10",
        "calibration_100", "pilot_200", "all")
csv.field_size_limit(10**9)


def load_rag_settings(path=None) -> dict:
    s = read_commented_json(Path(path) if path else CONFIG_FILE)
    if not isinstance(s.get("action_plan_query"), str):
        raise ValueError("action_plan_query must be text (\"\" for none)")
    for key, minimum in (("top_k", 1), ("max_email_chars", 0), ("max_urls", 0)):
        if not isinstance(s.get(key), int) or s[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")
    if s.get("eval_set") not in SETS:
        raise ValueError(f"eval_set must be one of {', '.join(SETS)}")
    return s


def split_ids(text: str) -> list[str]:
    return [c.strip() for c in (text or "").split(";") if c.strip()]


def load_gold(path) -> dict:
    gold = {}
    for r in csv.DictReader(open(resolve_path(path), encoding="utf-8-sig")):
        r["chunk_list"] = split_ids(r["chunk_ids"])
        gold[r["id"]] = r
    return gold


def in_set(g: dict, name: str) -> bool:
    if g.get("excluded") == "1":
        return False
    if name == "all":
        return True
    if name.startswith("fold"):
        return g.get("split") == "test" and g.get("fold") == name[4:]
    return g.get("split") == name


def map_gold(ids: list[str], mapping: dict) -> list[str]:
    out = []
    for c in ids:
        m = mapping.get(c, c)
        if m not in out:
            out.append(m)
    return out


def email_text(rec: dict, max_chars: int, max_urls: int) -> str:
    parts = [rec.get("subject") or "", rec.get("body") or ""]
    text = "\n\n".join(p.strip() for p in parts if p and p.strip())
    if max_chars:
        text = text[:max_chars]
    urls = (rec.get("urls") or [])[:max_urls]
    if urls:
        text += "\n\nLinks: " + " ".join(urls)
    return text


def score(ranked: list[str], gold: list[str], k: int) -> dict:
    top = ranked[:k]
    gains = {c: (2 if i == 0 else 1) for i, c in enumerate(gold)}
    dcg = sum(gains.get(c, 0) / math.log2(i + 2) for i, c in enumerate(top))
    ideal = sorted(gains.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    rank = top.index(gold[0]) + 1 if gold[0] in top else 0
    return {"recall": len(set(gold) & set(top)) / len(set(gold)), "ndcg": dcg / idcg if idcg else 0.0,
            "rr": 1 / rank if rank else 0.0, "hit1": int(bool(top) and top[0] == gold[0]), "first_rank": rank}


def summarise(rows: list[dict], key: str) -> dict:
    groups = collections.defaultdict(list)
    for r in rows:
        groups["all"].append(r)
        groups[f"fit={r['fit']}"].append(r)
        groups[f"lang={'en' if r['language'] == 'en' else 'other'}"].append(r)
        groups[f"first={r['required_chunk'][0]}"].append(r)
    out = {}
    for g, items in sorted(groups.items()):
        n = len(items)
        out[g] = {"n": n, **{m: round(sum(x[key][m] for x in items) / n, 4) for m in ("recall", "ndcg", "rr", "hit1")}}
    return out


def run(rag_config=None, vector_config=None, eval_set=None, out=None) -> dict:
    import chromadb

    s = load_rag_settings(rag_config)
    if eval_set:
        if eval_set not in SETS:
            raise ValueError(f"--set must be one of {', '.join(SETS)}")
        s["eval_set"] = eval_set
    v = load_settings(vector_config or s.get("vector_config"))
    k = s["top_k"]
    mapping = {}
    if v.get("gold_id_map"):
        mapping = json.loads(resolve_path(v["gold_id_map"]).read_text(encoding="utf-8"))["map_20_to_17"]

    client = chromadb.PersistentClient(path=str(resolve_path(v["database_dir"])))
    collection = client.get_collection(v["collection_name"])
    if collection.metadata.get("embedding_model") != v["embedding_model"]:
        raise ValueError("The Chroma collection uses a different embedding model; rebuild it first")
    if collection.count() == 0:
        raise ValueError("The Chroma collection is empty; build it first")

    gold = load_gold(s["gold_file"])
    records = [json.loads(line) for line in open(resolve_path(s["input_file"]), encoding="utf-8")]
    records = [r for r in records if r["id"] in gold and in_set(gold[r["id"]], s["eval_set"])]
    if not records:
        raise ValueError(f"No rows in set {s['eval_set']}")

    model = load_model(v)
    texts = [f"{v['query_prefix']}{s['action_plan_query']}{email_text(r, s['max_email_chars'], s['max_urls'])}" for r in records]
    vectors = model.encode(texts, batch_size=v["embedding_batch_size"], normalize_embeddings=True,
                           show_progress_bar=len(texts) > 50).tolist()
    n_results = min(k, collection.count())

    results, scored = [], []
    for rec, text, vec in zip(records, texts, vectors):
        res = collection.query(query_embeddings=[vec], n_results=n_results, include=["distances"])
        ids = res["ids"][0]
        sims = [round(1 - d, 4) for d in res["distances"][0]]
        g = gold[rec["id"]]
        gold_ids = map_gold(g["chunk_list"], mapping)
        item = {"query_id": rec["id"], "set": s["eval_set"], "fit": g["fit"], "language": g["language"],
                "gold_source": g["gold_source"], "required_chunk": gold_ids,
                "top_retrieved_chunk": ids, "similarity": sims, "input": text}
        if gold_ids:
            item["score"] = score(ids, gold_ids, k)
            item["score_chunk"] = round(100 * item["score"]["recall"], 2)  # the friend's field, now recall@k in %
            scored.append(item)
        results.append(item)

    # baseline: the k most frequent gold chunks, same list for every email
    freq = collections.Counter(c for r in scored for c in r["required_chunk"])
    baseline_list = [c for c, _ in freq.most_common(k)]
    for r in scored:
        r["baseline_score"] = score(baseline_list, r["required_chunk"], k)

    summary = {
        "eval_set": s["eval_set"], "rows": len(results), "scored_rows": len(scored),
        "skipped_fit_none": len(results) - len(scored), "top_k": k,
        "embedding_model": v["embedding_model"], "collection": v["collection_name"],
        "query_prefix": v["query_prefix"], "action_plan_query": s["action_plan_query"],
        "max_seq_length": v.get("max_seq_length"), "gold_mapped_to": "17-chunk KB" if mapping else "20-chunk KB",
        "gold_sources": dict(collections.Counter(r["gold_source"] for r in results)),
        "metrics": summarise(scored, "score"),
        "baseline": {"chunks": baseline_list, "metrics": summarise(scored, "baseline_score")["all"]},
    }
    out_path = resolve_path(out) if out else resolve_path(s["result_file"])
    summary_path = out_path.with_name(out_path.stem.replace("result_", "summary_") + ".json")
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(out_path)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary["_files"] = [str(out_path), str(summary_path)]
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="RAG config (default config_RAG.json)")
    p.add_argument("--vector-config", help="vector database config (default: vector_config in config_RAG.json)")
    p.add_argument("--set", dest="eval_set", help=f"evaluation set: {', '.join(SETS)}")
    p.add_argument("--out", help="result file (default: result_file in config_RAG.json)")
    a = p.parse_args()
    try:
        summary = run(a.config, a.vector_config, a.eval_set, a.out)
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        raise SystemExit(f"Cannot run retrieval: {error}") from error
    m = summary["metrics"]["all"]
    b = summary["baseline"]["metrics"]
    k = summary["top_k"]
    print(f"set {summary['eval_set']}: {summary['rows']} rows, {summary['scored_rows']} scored, "
          f"{summary['skipped_fit_none']} fit=none not scored")
    print(f"{'':10}{'Recall@' + str(k):>10}{'nDCG@' + str(k):>9}{'MRR':>7}{'Hit@1':>7}")
    print(f"{'RAG':10}{m['recall']:>10.3f}{m['ndcg']:>9.3f}{m['rr']:>7.3f}{m['hit1']:>7.3f}")
    print(f"{'baseline':10}{b['recall']:>10.3f}{b['ndcg']:>9.3f}{b['rr']:>7.3f}{b['hit1']:>7.3f}  ({', '.join(summary['baseline']['chunks'])})")
    print("files:", *summary["_files"])


if __name__ == "__main__":
    main()
