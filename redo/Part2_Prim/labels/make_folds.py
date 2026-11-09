#!/usr/bin/env python3
"""Split the test rows into 10 stratified folds of about 600 rows each.

Strata: round-1 fit (good/partial/none) x group of the first chunk (BRD, MED, SPM, ...; NONE when empty)
x language (en / other). Rows flagged for possible material involving minors are left out.
Within each stratum, rows are shuffled with a fixed seed and dealt round-robin to the folds, starting
from the fold that currently has the fewest rows, so every fold gets the same mix (differences of at
most one row per stratum).

Usage: python3 make_folds.py --labels labels_round1.csv --split split.json --exclude human_review_possible_minors.csv --out test_folds.json
"""
import argparse, csv, json, random, collections

SEED = 20261101
N_FOLDS = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--exclude", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    csv.field_size_limit(10**9)
    split = json.load(open(a.split))
    excluded = {r["id"] for r in csv.DictReader(open(a.exclude, encoding="utf-8-sig"))}
    rows = [r for r in csv.DictReader(open(a.labels, encoding="utf-8-sig"))
            if split.get(r["id"]) == "test" and r["id"] not in excluded]
    strata = collections.defaultdict(list)
    for r in rows:
        ids = [c for c in r["chunk_ids_final"].split(";") if c]
        group = ids[0].split("-")[0] if ids else "NONE"
        lang = "en" if r["language"] == "en" else "other"
        strata[(r["fit_final"], group, lang)].append(r["id"])
    rng = random.Random(SEED)
    sizes = [0] * N_FOLDS
    fold_of = {}
    # largest strata first, ids sorted before shuffling so the result does not depend on file order
    for key in sorted(strata, key=lambda k: (-len(strata[k]), k)):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        order = sorted(range(N_FOLDS), key=lambda f: (sizes[f], f))
        for i, rid in enumerate(ids):
            f = order[i % N_FOLDS]
            fold_of[rid] = f + 1
            sizes[f] += 1
    out = {"seed": SEED, "n_folds": N_FOLDS, "source_labels": a.labels,
           "strata": "fit_final x first-chunk group x language(en/other)",
           "excluded_ids": sorted(excluded & set(split)), "fold_sizes": {str(i + 1): s for i, s in enumerate(sizes)},
           "fold_of": dict(sorted(fold_of.items()))}
    json.dump(out, open(a.out, "w"), indent=1)
    print("rows:", len(rows), "excluded:", len(excluded), "fold sizes:", sizes)


if __name__ == "__main__":
    main()
