"""Automatic scores for the Local LLM answers (metrics M1, M2 and M5 of the evaluation plan).

Run from the project root after main_LLM.py:
    python part2/LLM/evaluate_LLM.py
    python part2/LLM/evaluate_LLM.py --result part2/LLM/result_LLM.jsonl --set fold1

Per (model, condition, prompt_version):
  M1 citation precision / recall / F1   chunk_ids_used vs the gold chunk IDs (rows with gold chunks)
     first-chunk accuracy               first ID used == first gold ID
  M2 abstention accuracy                gold fit=none rows answered with [] (no_specific_guidance)
     false abstention                   rows with gold chunks answered with []
  M5 format rate, invalid-ID rate, latency (median, p90), output tokens per second, error count
An answer that cannot be parsed counts as citing nothing (it scores 0 on M1 and is not an abstention).
95% bootstrap confidence intervals (1,000 resamples of emails, fixed seed) for F1 and abstention.
Pairwise McNemar tests (first-chunk correct or not) between models within each condition and prompt.
Writes summary_LLM.json and scored_LLM.csv next to the result file. M3 and M4 need human / judge scores.
"""

from __future__ import annotations

import argparse
import collections
import csv
import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
from part2.vector_database.main_vector_database import resolve_path, read_commented_json  # noqa: E402

CONFIG_FILE = Path(__file__).resolve().parent / "config_LLM.json"


def latest_records(path: Path, eval_set: str | None) -> list[dict]:
    """Keep the last successful record per (model, condition, prompt_version, id)."""
    best = {}
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if eval_set and r.get("set") != eval_set:
            continue
        key = (r["model"], r["condition"], r["prompt_version"], r["id"])
        if key not in best or not r.get("error"):
            best[key] = r
    return list(best.values())


def score_row(r: dict) -> dict:
    p = r.get("parsed") or {}
    used = (p.get("chunk_ids_used") or []) if p.get("format_ok") else []
    gold = r["gold_chunk_ids"]
    s = {"format_ok": int(bool(p.get("format_ok"))), "error": int(bool(r.get("error"))),
         "n_used": len(used), "invalid_ids": len(p.get("invalid_ids") or []) if p else 0}
    if gold:
        tp = len(set(used) & set(gold))
        prec = tp / len(set(used)) if used else 0.0
        rec = tp / len(set(gold))
        s.update({"has_gold": 1, "precision": prec, "recall": rec,
                  "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
                  "first_correct": int(bool(used) and used[0] == gold[0]),
                  "false_abstain": int(bool(p.get("format_ok")) and not used)})
    else:
        s.update({"has_gold": 0, "abstain_correct": int(bool(p.get("format_ok")) and not used)})
    tok, dur = r.get("output_tokens"), r.get("eval_duration_s")
    s["latency_s"] = r.get("latency_s")
    s["tokens_per_s"] = tok / dur if tok and dur else None
    return s


def boot_ci(values: list[float], seed=20261102, n=1000):
    if not values:
        return [None, None]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(n))
    return [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)]


def mcnemar(a: list[int], b: list[int]) -> dict:
    b01 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    b10 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    if b01 + b10 == 0:
        return {"only_a_correct": 0, "only_b_correct": 0, "p_value": 1.0}
    chi = (abs(b01 - b10) - 1) ** 2 / (b01 + b10)
    return {"only_a_correct": b01, "only_b_correct": b10, "p_value": round(math.erfc(math.sqrt(chi / 2)), 4)}


def pct(values, q):
    v = sorted(x for x in values if x is not None)
    return round(v[min(len(v) - 1, int(q * len(v)))], 2) if v else None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--result", help="result_LLM.jsonl (default: result_file in config_LLM.json)")
    p.add_argument("--set", dest="eval_set", help="only records of this set")
    a = p.parse_args()
    c = read_commented_json(CONFIG_FILE)
    path = resolve_path(a.result or c["result_file"])
    recs = latest_records(path, a.eval_set)
    if not recs:
        raise SystemExit(f"No records in {path}")

    groups = collections.defaultdict(list)
    scored_rows = []
    for r in recs:
        s = score_row(r)
        groups[(r["model"], r["condition"], r["prompt_version"])].append((r, s))
        scored_rows.append({"id": r["id"], "model": r["model"], "condition": r["condition"],
                            "prompt_version": r["prompt_version"], "gold_fit": r["gold_fit"],
                            "gold": ";".join(r["gold_chunk_ids"]), "given": ";".join(r["given_chunk_ids"]),
                            "used": ";".join(((r.get("parsed") or {}).get("chunk_ids_used")) or []),
                            **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}})

    summary = {"result_file": str(path), "set": a.eval_set or "all", "groups": {}, "mcnemar_first_chunk": {}}
    for key, items in sorted(groups.items()):
        S = [s for _, s in items]
        g = [s for s in S if s["has_gold"]]
        nn = [s for s in S if not s["has_gold"]]
        f1 = [s["f1"] for s in g]
        ab = [s["abstain_correct"] for s in nn]
        tps = [s["tokens_per_s"] for s in S if s["tokens_per_s"]]
        summary["groups"][" | ".join(key)] = {
            "model": key[0], "condition": key[1], "prompt_version": key[2], "answers": len(S),
            "errors": sum(s["error"] for s in S),
            "format_rate": round(sum(s["format_ok"] for s in S) / len(S), 4),
            "invalid_id_rate": round(sum(1 for s in S if s["invalid_ids"]) / len(S), 4),
            "rows_with_gold": len(g),
            "citation_precision": round(statistics.mean(s["precision"] for s in g), 4) if g else None,
            "citation_recall": round(statistics.mean(s["recall"] for s in g), 4) if g else None,
            "citation_f1": round(statistics.mean(f1), 4) if g else None, "citation_f1_ci95": boot_ci(f1),
            "first_chunk_accuracy": round(statistics.mean(s["first_correct"] for s in g), 4) if g else None,
            "false_abstention_rate": round(statistics.mean(s["false_abstain"] for s in g), 4) if g else None,
            "rows_fit_none": len(nn),
            "abstention_accuracy": round(statistics.mean(ab), 4) if nn else None, "abstention_ci95": boot_ci(ab),
            "latency_median_s": pct([s["latency_s"] for s in S], 0.5), "latency_p90_s": pct([s["latency_s"] for s in S], 0.9),
            "output_tokens_per_s_median": round(statistics.median(tps), 1) if tps else None,
        }
    # McNemar between models, same condition and prompt, on emails both answered
    by_cp = collections.defaultdict(dict)
    for (model, cond, pv), items in groups.items():
        by_cp[(cond, pv)][model] = {r["id"]: s["first_correct"] for r, s in items if s["has_gold"]}
    for (cond, pv), mm in by_cp.items():
        for m1, m2 in itertools.combinations(sorted(mm), 2):
            ids = sorted(set(mm[m1]) & set(mm[m2]))
            summary["mcnemar_first_chunk"][f"{cond} | {pv} | {m1} vs {m2}"] = {
                "emails": len(ids), **mcnemar([mm[m1][i] for i in ids], [mm[m2][i] for i in ids])}

    out_sum = path.with_name("summary_LLM.json")
    out_sum.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_csv = path.with_name("scored_LLM.csv")
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        fields = list(dict.fromkeys(k for row in scored_rows for k in row))
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(scored_rows)

    hdr = f"{'model':16}{'cond':8}{'prompt':8}{'n':>5}{'fmt':>6}{'F1':>7}{'1st':>7}{'abst':>7}{'p50 s':>7}"
    print(hdr)
    for g in summary["groups"].values():
        fmt = lambda x: f"{x:.3f}" if isinstance(x, float) else "  -  "
        print(f"{g['model'][:15]:16}{g['condition']:8}{g['prompt_version'][:7]:8}{g['answers']:>5}{fmt(g['format_rate']):>6}"
              f"{fmt(g['citation_f1']):>7}{fmt(g['first_chunk_accuracy']):>7}{fmt(g['abstention_accuracy']):>7}"
              f"{(g['latency_median_s'] or 0):>7.1f}")
    print("files:", out_sum, out_csv)


if __name__ == "__main__":
    main()
