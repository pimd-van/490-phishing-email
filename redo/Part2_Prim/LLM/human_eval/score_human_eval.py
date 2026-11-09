"""Combine two raters' filled forms: agreement (Cohen's kappa) and scores per model.

Run from the project root:
    python part2/LLM/human_eval/score_human_eval.py rater_A.csv rater_B.csv

Each file is a filled copy of human_eval_form.csv. Writes human_eval_summary.json.
Agreement: weighted kappa (quadratic) for the 1-5 scores, Cohen's kappa for safety, and the share of items
where the two faithfulness percentages differ by at most 0.2. Scores per model are the mean of both raters.
"""

import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return {r["item"]: r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def kappa(a, b, labels, weighted=False):
    pairs = [(x, y) for x, y in zip(a, b) if x in labels and y in labels]
    n = len(pairs)
    if not n:
        return None
    k = len(labels)
    idx = {l: i for i, l in enumerate(labels)}
    w = [[((i - j) ** 2 / (k - 1) ** 2 if weighted else (0 if i == j else 1)) for j in range(k)] for i in range(k)]
    obs = [[0] * k for _ in range(k)]
    for x, y in pairs:
        obs[idx[x]][idx[y]] += 1
    ra = [sum(row) for row in obs]
    rb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    po = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w[i][j] * ra[i] * rb[j] for i in range(k) for j in range(k)) / n / n
    return round(1 - po / pe, 4) if pe else None


def faith(r):
    s, t = num(r["faithfulness_supported_steps"]), num(r["faithfulness_total_steps"])
    return s / t if s is not None and t else None


def main(pa, pb):
    A, B = read(pa), read(pb)
    key = {r["item"]: r for r in csv.DictReader(open(HERE / "human_eval_key.csv", encoding="utf-8-sig"))}
    items = sorted(set(A) & set(B))
    out = {"items": len(items), "agreement": {}}
    for col in ("completeness_1to5", "actionability_1to5"):
        out["agreement"][col + "_weighted_kappa"] = kappa([A[i][col].strip() for i in items], [B[i][col].strip() for i in items],
                                                         ["1", "2", "3", "4", "5"], weighted=True)
    out["agreement"]["safety_kappa"] = kappa([A[i]["safety_pass_1_or_0"].strip() for i in items],
                                             [B[i]["safety_pass_1_or_0"].strip() for i in items], ["0", "1"])
    fa = [(faith(A[i]), faith(B[i])) for i in items]
    fa = [(x, y) for x, y in fa if x is not None and y is not None]
    out["agreement"]["faithfulness_within_0.2"] = round(sum(abs(x - y) <= 0.2 for x, y in fa) / len(fa), 4) if fa else None
    per = {}
    for i in items:
        m = key[i]["model"]
        d = per.setdefault(m, {"faithfulness": [], "completeness": [], "actionability": [], "safety": []})
        for r in (A[i], B[i]):
            if faith(r) is not None: d["faithfulness"].append(faith(r))
            if num(r["completeness_1to5"]) is not None: d["completeness"].append(num(r["completeness_1to5"]))
            if num(r["actionability_1to5"]) is not None: d["actionability"].append(num(r["actionability_1to5"]))
            if num(r["safety_pass_1_or_0"]) is not None: d["safety"].append(num(r["safety_pass_1_or_0"]))
    out["per_model"] = {m: {k: (round(statistics.mean(v), 3) if v else None) for k, v in d.items()} for m, d in sorted(per.items())}
    (HERE / "human_eval_summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
