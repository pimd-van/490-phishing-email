#!/usr/bin/env python3
"""Build gold.csv: one answer-key row per email, taken from the best label available.

Priority: fold labels (rules v1.13 frozen, every row reviewed by Opus) > round-1 labels.
Rows flagged for possible material involving minors are kept in the file with excluded=1;
the RAG and LLM programs skip them.

Run from the project root:
    python part2/labels/build_gold.py
"""
import csv, json, glob, os

HERE = os.path.dirname(os.path.abspath(__file__))
csv.field_size_limit(10**9)


def main():
    split = json.load(open(os.path.join(HERE, "split.json")))
    folds = json.load(open(os.path.join(HERE, "test_folds.json")))["fold_of"]
    excluded = {r["id"] for r in csv.DictReader(open(os.path.join(HERE, "human_review_possible_minors.csv"), encoding="utf-8-sig"))}
    # One row of part2_handoff.csv is the spill-over of meajor_test_22699, whose body hit the 32,767-character
    # spreadsheet cell limit; its "id" is email text. Real handoff = 6,972 emails (as in the Part 1 README).
    malformed = {rid for rid in split if not rid.startswith("meajor_test_")}
    excluded |= malformed
    gold = {}
    for r in csv.DictReader(open(os.path.join(HERE, "labels_round1.csv"), encoding="utf-8-sig")):
        gold[r["id"]] = {"chunk_ids": r["chunk_ids_final"], "fit": r["fit_final"], "language": r["language"],
                         "gold_source": "round1", "rules_version": r["rules_version_used"]}
    for path in sorted(glob.glob(os.path.join(HERE, "labels_fold*.csv"))):
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            gold[r["id"]] = {"chunk_ids": r["chunk_ids_final"], "fit": r["fit_final"], "language": r["language"],
                             "gold_source": f"fold{r['fold']}", "rules_version": r["rules_version"]}
    out = os.path.join(HERE, "gold.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "split", "fold", "gold_source", "rules_version", "chunk_ids", "fit", "language", "excluded"])
        for rid in sorted(gold):
            g = gold[rid]
            w.writerow([rid, split.get(rid, ""), folds.get(rid, ""), g["gold_source"], g["rules_version"],
                        g["chunk_ids"], g["fit"], g["language"], int(rid in excluded)])
    n_fold = sum(1 for g in gold.values() if g["gold_source"].startswith("fold"))
    print(f"gold.csv: {len(gold)} rows ({n_fold} from fold labels, {len(gold) - n_fold} from round 1, "
          f"{len(excluded)} excluded: {len(excluded) - len(malformed)} possible-minors + {len(malformed)} malformed)")


if __name__ == "__main__":
    main()
