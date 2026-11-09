"""Build the English SVM master and its proportional 10% labeling sample."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

PART1 = Path(__file__).resolve().parents[1]
LANGUAGE_TAGS = {"en", "en;en", "en;en;en"}
csv.field_size_limit(1 << 30)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def by_key(rows, key):
    result = {row[key]: row for row in rows}
    if "" in result or len(result) != len(rows):
        raise ValueError(f"Missing or duplicate {key}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part1", type=Path, default=PART1)
    parser.add_argument("--output-dir", type=Path, default=PART1.parent / "dataset")
    args = parser.parse_args()
    part1 = args.part1

    fields, handoff = read_csv(part1 / "dataset/svm_handoff.csv")
    _, assignment_rows = read_csv(part1 / "clustering/assignments.csv")
    _, explanation_rows = read_csv(part1 / "xai/shap_lime_explanations.csv")
    _, manifest = read_csv(part1 / "benchmark/split_manifest.csv")
    ids = by_key(handoff, "id").keys()
    assignments = by_key(assignment_rows, "id")
    explanations = by_key(explanation_rows, "id")
    truth = by_key([row for row in manifest if row["split"] == "test"], "source_row")
    if not ids or ids != assignments.keys() or ids != explanations.keys():
        raise ValueError("Handoff, assignments, and explanations must have the same IDs")
    by_key(handoff, "source_row")

    groups = defaultdict(list)
    master = []
    for row in handoff:
        key = row["id"]
        assignment, explanation = assignments[key], explanations[key]
        test = truth[row["source_row"]]
        if (
            row["language"] not in LANGUAGE_TAGS
            or row["language"] != test["language"]
            or row["test_row"] != test["split_row"]
            or row["test_row"] != explanation["test_row"]
            or row["subject"] != explanation["subject"]
            or test["label"] not in {"0", "1"}
            or any(not value.strip() for value in (row["xai"], explanation["shap"], explanation["lime"]))
        ):
            raise ValueError(f"Invalid or mismatched data for {key}")

        score = float(assignment["silhouette"])
        if not math.isfinite(score) or not -1 <= score <= 1:
            raise ValueError(f"Invalid silhouette for {key}")
        record = {
            **row, "label": test["label"], "shap": explanation["shap"], "lime": explanation["lime"],
            "cluster_id": assignment["cluster_id"], "silhouette": assignment["silhouette"],
        }
        master.append(record)
        groups[int(record["cluster_id"])].append((score, record))

    results = json.loads((part1 / "clustering/silhouette_k02_k60.json").read_text(encoding="utf-8"))
    selected = results["best_every_cluster"]
    sizes, quotas = selected["sizes"], selected["quotas"]
    order = sorted(range(len(sizes)), key=lambda index: -sizes[index])
    sample_size = round(len(master) * 0.10)
    if (
        results["rows"] != len(master)
        or results["sample_rows"] != sample_size
        or sum(quotas) != sample_size
        or len(sizes) != len(quotas)
        or set(groups) != set(range(1, len(order) + 1))
    ):
        raise ValueError("Clustering results do not match the master and the 10% target")

    sample = []
    for cluster_id, index in enumerate(order, 1):
        ranked = sorted(groups[cluster_id], key=lambda item: -item[0])
        quota = quotas[index]
        if len(ranked) != sizes[index] or not 1 <= quota <= len(ranked):
            raise ValueError(f"Unexpected size or quota for cluster {cluster_id}")
        # Keep the original percentile and rounding rules from cluster_english.py.
        percentiles = np.linspace(100, 0, quota) if quota > 1 else np.array([50.0])
        ranks = np.floor((1 - percentiles / 100) * (len(ranked) - 1) + 0.5).astype(int)
        for rank, percentile in zip(ranks, percentiles):
            _, row = ranked[rank]
            sample.append({
                **{name: value for name, value in row.items() if name != "label"},
                "silhouette_percentile": f"{percentile:.8f}",
            })
    if len(by_key(sample, "id")) != sample_size:
        raise ValueError("Expected a unique proportional 10% sample")

    master_fields = [*fields, "label", "shap", "lime", "cluster_id", "silhouette"]
    sample_fields = [name for name in master_fields if name != "label"] + ["silhouette_percentile"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "MeaJoR.csv", master_fields, master)
    write_csv(args.output_dir / "sample_10per.csv", sample_fields, sample)
    print(f"Wrote {len(master)} master rows and {len(sample)} sample rows from {len(groups)} clusters")


if __name__ == "__main__":
    main()

