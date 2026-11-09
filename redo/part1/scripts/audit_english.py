"""Verify English-only outputs against their source, split, margins and sampling rules."""

import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark_english import EXPECTED_MD5, LANGUAGE_TAGS, handoff_id, md5sum, prepare, sha256, split
from cluster_english import LEVELS, METHODS, allocate
from embed_english import email_text, load_legacy

csv.field_size_limit(1 << 30)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def checked_terms(payload, key):
    for direction, sign in (("top_positive_terms", 1), ("top_negative_terms", -1)):
        terms = payload[direction]
        values = [sign * term[key] for term in terms]
        check(len(terms) <= 5 and values == sorted(values, reverse=True)
              and all(math.isfinite(v) and v > 0 for v in values), f"Invalid {direction}")


def verify_benchmark(out, source):
    path = out / "benchmark"
    summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    data, reconstructed = prepare(source)
    check(md5sum(source) == EXPECTED_MD5, "Official MeAJOR MD5 differs")
    check(all(summary[key] == value for key, value in reconstructed.items()), "Source filter audit differs")
    check(summary["rows_by_accepted_tag"] == dict(zip(LANGUAGE_TAGS, (82175, 21250, 218))),
          "Unexpected raw count for accepted tags")
    parts, _, _ = split(data)
    manifest = read_csv(path / "split_manifest.csv")
    offsets = 0
    for name, frame in zip(("train", "validation", "test"), parts):
        actual = manifest[offsets:offsets + len(frame)]
        source_fields = frame[["source_row", "language", "label"]].itertuples(index=False, name=None)
        check(len(actual) == len(frame) == summary["split_rows"][name], f"Invalid {name} row count")
        for pos, (entry, expected) in enumerate(zip(actual, source_fields)):
            check(entry["split"] == name and int(entry["split_row"]) == pos
                  and (int(entry["source_row"]), entry["language"], int(entry["label"])) == expected,
                  f"Split manifest differs at {name} row {pos}")
            check(bool(entry["svm_test_margin"]) == (name == "test"), "Margin outside test")
        offsets += len(frame)
    check(offsets == len(manifest) == len({row["source_row"] for row in manifest}),
          "Duplicate or unexpected rows in split")
    validation, test = [read_csv(path / f"{kind}_metrics.csv") for kind in ("validation", "test")]
    expected_models = {"LinearSVC", "MultinomialNB", "LogisticRegression", "KNN_cosine_k5",
                       "XGBoost", "RandomForest_default", "DecisionTree"}
    check(len(validation) == len(test) == 7 and {r["model"] for r in validation} == expected_models
          and {r["model"] for r in test} == expected_models, "Benchmark model sets differ")
    winner = max(validation, key=lambda row: tuple(float(row[field]) for field in ("f1", "precision", "recall")))
    check(summary["best_model"] == winner["model"], "Validation winner differs")
    test_rows = [row for row in manifest if row["split"] == "test"]
    check(all(math.isfinite(float(row["svm_test_margin"])) for row in test_rows), "Nonfinite SVM margin")
    svm_test = next(row for row in test if row["model"] == "LinearSVC")
    confusion = Counter((int(row["label"]), float(row["svm_test_margin"]) > 0) for row in test_rows)
    for key, pair in {"tn": (0, False), "fp": (0, True), "fn": (1, False), "tp": (1, True)}.items():
        check(int(svm_test[key]) == confusion[pair], f"SVM test {key} differs from split manifest")
    return summary, test_rows, parts[2]


def verify_handoff(out, summary, test_rows, test):
    handoff = read_csv(out / "dataset" / "svm_handoff.csv")
    xai = read_csv(out / "xai" / "shap_lime_explanations.csv")
    positives = [row for row in test_rows if float(row["svm_test_margin"]) > 0]
    check(len(positives) == len(handoff) == len(xai) == summary["handoff_rows"], "Handoff and XAI counts differ")
    for expected, row, explanation in zip(positives, handoff, xai):
        pos = int(expected["split_row"])
        source = test.iloc[pos]
        result = json.loads(row["svm_result"])
        contribution = json.loads(row["xai"])
        shap = json.loads(explanation["shap"])
        lime = json.loads(explanation["lime"])
        margin = float(expected["svm_test_margin"])
        check(row["id"] == explanation["id"] == handoff_id(int(expected["source_row"]))
              and row["source_row"] == expected["source_row"]
              and row["test_row"] == explanation["test_row"] == str(pos), "Handoff ID or position differs")
        check(row["subject"] == source["subject"] == explanation["subject"]
              and row["body"] == source["body"] and row["language"] == source["language"],
              f"Cleaned content or language differs for {row['id']}")
        check(result["prediction"] == 1 and result["decision_score"] == margin
              and math.isclose(shap["model_output_margin"], margin, rel_tol=0, abs_tol=1e-8),
              f"Margin differs for {row['id']}")
        check(shap["unit"] == contribution["unit"] == "svm_margin"
              and lime["unit"] == "local_svm_margin_surrogate_weight" and lime["num_samples"] == 500
              and lime["random_seed"] == 42 + int(row["source_row"]), f"XAI settings differ for {row['id']}")
        check(math.isfinite(contribution["intercept_margin"]) and math.isfinite(shap["base_value_margin"]),
              f"Nonfinite baseline for {row['id']}")
        for payload, key in ((contribution, "contribution_margin"), (shap, "value_margin"), (lime, "weight")):
            checked_terms(payload, key)
    return handoff


def verify_embeddings(out, handoff, source, legacy_handoff, legacy_vectors):
    cluster = out / "clustering"
    provenance = read_csv(cluster / "embedding_provenance.csv")
    meta = json.loads((cluster / "embedding_metadata.json").read_text(encoding="utf-8"))
    check(meta["prior_handoff_sha256"] == sha256(legacy_handoff)
          and meta["prior_vectors_sha256"] == sha256(legacy_vectors)
          and meta["handoff_sha256"] == sha256(out / "dataset" / "svm_handoff.csv"), "Embedding input hash differs")
    legacy = load_legacy(legacy_handoff, legacy_vectors)
    check([row["id"] for row in provenance] == [row["id"] for row in handoff], "Provenance IDs/order differ")
    raw = pd.read_csv(source, usecols=["subject", "body"], low_memory=False).fillna("")
    cache = cluster / "vectors.npz"
    vectors = None
    if cache.is_file():
        with np.load(cache) as data:
            check(data["ids"].tolist() == [row["id"] for row in handoff], "Vector cache IDs/order differ")
            vectors = data["embeddings"]
        check(vectors.shape == (len(handoff), 1024) and vectors.dtype == np.float32
              and np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5),
              "Invalid normalized float32 embedding cache")
    counts = Counter()
    for index, (row, entry) in enumerate(zip(handoff, provenance)):
        prior = legacy.get(email_text(raw.iloc[int(row["source_row"])]))
        origin, old_id = ("new", "") if prior is None else ("reused", prior[0])
        check((entry["embedding_origin"], entry["prior_id"]) == (origin, old_id),
              f"Embedding match differs for {row['id']}")
        if prior is not None and vectors is not None:
            check(np.array_equal(vectors[index], prior[1]), f"Reused vector values differ for {row['id']}")
        counts[origin] += 1
    check(counts["reused"] == meta["reused_rows"] and counts["new"] == meta["new_rows"]
          and sum(counts.values()) == meta["rows"], "Embedding counts differ")
    return dict(counts), vectors is not None


def verify_sample(out, handoff):
    root = out / "clustering"
    report = json.loads((root / "silhouette_k02_k60.json").read_text(encoding="utf-8"))
    selected = report["best_every_cluster"]
    assignments = read_csv(root / "assignments.csv")
    sample = read_csv(out / "dataset" / "rag_label_sample_10pct.csv")
    quotas = read_csv(out / "dataset" / "rag_sample_cluster_quotas.csv")
    check([row["id"] for row in assignments] == [row["id"] for row in handoff], "Assignment IDs/order differ")
    n = (len(handoff) + 5) // 10
    check(len(sample) == n == report["sample_rows"] == len({row["id"] for row in sample})
          and report["silhouette_evaluation_rows"] == report["rows"] == len(handoff), "Sample size differs")
    candidates = report["results"]
    check(len(candidates) == 118
          and {(row["method"], row["k"]) for row in candidates} == {(m, k) for m in METHODS for k in LEVELS},
          "Missing clustering candidates")
    for candidate in candidates:
        sizes = np.array(candidate["sizes"])
        check(len(sizes) == candidate["k"] and sizes.sum() == len(handoff)
              and allocate(sizes, n).tolist() == candidate["quotas"], "Incorrect clustering quotas")
    covered = [row for row in candidates if min(row["quotas"]) > 0]
    check(selected == max(covered, key=lambda row: row["silhouette"]), "Covered cut selection differs")
    check(len(quotas) == selected["k"] and sum(int(row["total_rows"]) for row in quotas) == len(handoff),
          "Cluster size differs")
    check(math.isclose(np.mean([float(row["silhouette"]) for row in assignments]),
                       selected["silhouette"], rel_tol=0, abs_tol=1e-7), "Mean silhouette differs")
    order = np.argsort(-np.array(selected["sizes"]), kind="stable")
    expected_sample = []
    for cluster_id, (group, quota) in enumerate(zip(order, quotas), 1):
        members = [(float(row["silhouette"]), original) for row, original in zip(assignments, handoff)
                   if row["cluster_id"] == str(cluster_id)]
        check(len(members) == int(quota["total_rows"]) == selected["sizes"][group]
              and int(quota["cluster_id"]) == cluster_id, "Numeric cluster ID or size differs")
        check(math.isclose(np.mean([score for score, _ in members]), float(quota["mean_silhouette"]),
                           rel_tol=0, abs_tol=1e-8), "Cluster mean silhouette differs")
        count = selected["quotas"][group]
        check(count == int(quota["sample_rows"]) > 0, "Cluster coverage differs")
        ranked = sorted(members, key=lambda item: -item[0])
        targets = np.linspace(100, 0, count) if count > 1 else np.array([50.0])
        for pct in targets:
            rank = math.floor((1 - pct / 100) * (len(members) - 1) + 0.5)
            score, original = ranked[rank]
            expected_sample.append({
                **original, "cluster_id": str(cluster_id), "silhouette_percentile": f"{pct:.8f}",
                "silhouette": f"{score:.8f}",
            })
    check(expected_sample == sample, "Sample rows differ from the within-cluster percentile ranks")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prior-handoff", type=Path, required=True)
    parser.add_argument("--prior-vectors", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary, test_rows, test = verify_benchmark(args.out, args.source)
    handoff = verify_handoff(args.out, summary, test_rows, test)
    counts, verified_vectors = verify_embeddings(args.out, handoff, args.source, args.prior_handoff, args.prior_vectors)
    selected = verify_sample(args.out, handoff)
    audit = {
        "status": "passed",
        "source_md5": EXPECTED_MD5,
        "benchmark_rows": summary["clean_rows"],
        "handoff_predictions_and_xai_rows_verified": len(handoff),
        "embedding_origin_rows_verified": counts,
        "reused_vectors_verified_bitwise": verified_vectors,
        "clustering_candidates_verified": 118,
        "cluster_method": selected["method"],
        "cluster_count": selected["k"],
        "sample_rows_verified": sum(selected["quotas"]),
    }
    (args.out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
