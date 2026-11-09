"""Compute SHAP and LIME in a separate CSV without changing Part 2 inputs.

This script reconstructs the frozen Part 1 split/model, checks every
predicted-phishing ID, and writes `xai/shap_lime_explanations.csv`. It only reads
the Part 2 handoff; interrupted runs resume from an ignored JSONL checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from shap.maskers import Independent
from lime.lime_text import LimeTextExplainer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD5 = "aa8f59e96787cbd696c0b650e5400dc9"
HANDOFF = ROOT / "part2" / "part2_handoff.csv"
OUTPUT = ROOT / "xai" / "shap_lime_explanations.csv"
CHECKPOINT = ROOT / "results" / "shap_lime_checkpoint.jsonl"
ID_PATTERN = re.compile(r"meajor_test_(\d+)")
LIME_SAMPLES = 500
TOP_TERMS = 5


def load_source(path: Path) -> pd.DataFrame:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != SOURCE_MD5:
        raise ValueError(f"Unexpected MeAJOR CSV MD5: {digest.hexdigest()}")
    data = pd.read_csv(path, low_memory=False)
    data = data[data["label"].isin([0, 1])].copy()
    for column in ("subject", "body"):
        data[column] = (
            data[column].fillna("").astype(str)
            .str.replace(r"\[([A-Z_]{2,})\]", r" token_\1 ", regex=True)
            .str.lower()
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )
    data["text"] = (data["subject"] + " " + data["body"]).str.strip()
    return data[data["text"].ne("")].drop_duplicates("text").reset_index(drop=True)


def read_handoff() -> list[dict[str, str]]:
    with HANDOFF.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = [row for row in reader if ID_PATTERN.fullmatch(row.get("id") or "")]
    if len(rows) != 6972 or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Expected 6,972 unique predicted-phishing handoff IDs")
    return rows


def load_checkpoint(path: Path) -> dict[str, dict]:
    records = {}
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    record = json.loads(line)
                    records[record["id"]] = record
    return records


def ranked_terms(values: np.ndarray, names: np.ndarray, present: np.ndarray) -> dict:
    indexes = present[np.argsort(values[present])]
    positive = [i for i in indexes[::-1] if values[i] > 0][:TOP_TERMS]
    negative = [i for i in indexes if values[i] < 0][:TOP_TERMS]
    return {
        "top_positive_terms": [
            {"term": str(names[i]), "value_log_odds": float(values[i])} for i in positive
        ],
        "top_negative_terms": [
            {"term": str(names[i]), "value_log_odds": float(values[i])} for i in negative
        ],
    }


def explain_row(row_id: str, text: str, x, names, model, vectorizer, shap_explainer) -> dict:
    shap_values = np.asarray(shap_explainer.shap_values(x)).reshape(-1)
    base = float(shap_explainer.expected_value)
    log_odds = float(model.decision_function(x)[0])
    error = abs(base + float(shap_values.sum()) - log_odds)
    if error > 1e-6:
        raise ValueError(f"SHAP additivity failed for {row_id}: {error}")
    shap_result = {
        "method": "shap.LinearExplainer",
        "unit": "log_odds",
        "base_value_log_odds": base,
        "model_output_log_odds": log_odds,
        "shown_terms": "present_tfidf_features_only",
        **ranked_terms(shap_values, names, x.indices),
    }

    def predict_proba(texts):
        return model.predict_proba(vectorizer.transform(texts))

    seed = 42 + int(ID_PATTERN.fullmatch(row_id).group(1))
    lime_explainer = LimeTextExplainer(
        class_names=["benign", "phishing"], random_state=seed
    )
    explanation = lime_explainer.explain_instance(
        text, predict_proba, labels=(1,), num_features=TOP_TERMS * 2,
        num_samples=LIME_SAMPLES,
    )
    weights = explanation.as_list(label=1)
    lime_result = {
        "method": "lime.lime_text.LimeTextExplainer",
        "unit": "local_probability_surrogate_weight",
        "num_samples": LIME_SAMPLES,
        "random_seed": seed,
        "surrogate_r2": float(explanation.score[1] if isinstance(explanation.score, dict) else explanation.score),
        "surrogate_estimate": float(np.asarray(explanation.local_pred).ravel()[0]),
        "top_positive_terms": [
            {"term": term, "weight": float(weight)}
            for term, weight in weights if weight > 0
        ][:TOP_TERMS],
        "top_negative_terms": [
            {"term": term, "weight": float(weight)}
            for term, weight in weights if weight < 0
        ][:TOP_TERMS],
    }
    return {"id": row_id, "shap": shap_result, "lime": lime_result}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "meajor_cleaned_preprocessed.csv")
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--limit", type=int, help="Explain at most this many handoff rows")
    parser.add_argument("--only-id", help="Explain this one handoff ID")
    parser.add_argument("--start", type=int, default=0, help="First handoff row index for a partial run")
    parser.add_argument("--end", type=int, help="Exclusive end handoff row index for a partial run")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    print("Loading and verifying MeAJOR source...", flush=True)
    source = load_source(args.source)
    if len(source) != 104515:
        raise ValueError(f"Unexpected cleaned data size: {len(source)}")
    y = source["label"].astype(int).to_numpy()
    train, rest = train_test_split(
        np.arange(len(source)), test_size=0.30, random_state=42, stratify=y
    )
    _, test = train_test_split(
        rest, test_size=0.50, random_state=42, stratify=y[rest]
    )
    vectorizer = TfidfVectorizer(
        max_features=5000, ngram_range=(1, 2), sublinear_tf=True, dtype=np.float64
    )
    x_train = vectorizer.fit_transform(source.loc[train, "text"])
    print("Fitting the original TF-IDF Logistic Regression...", flush=True)
    model = LogisticRegression().fit(x_train, y[train])
    x_test = vectorizer.transform(source.loc[test, "text"])
    test_positions = {int(index): position for position, index in enumerate(test)}
    rows = read_handoff()
    predicted = set(test[model.predict(x_test) == 1])
    handoff_ids = {int(ID_PATTERN.fullmatch(row["id"]).group(1)) for row in rows}
    if predicted != handoff_ids:
        raise ValueError("Reconstructed model does not match the handoff prediction set")
    print(f"Verified {len(rows)} unchanged predicted-phishing IDs", flush=True)
    background_index = np.random.default_rng(42).choice(x_train.shape[0], 200, replace=False)
    shap_explainer = shap.LinearExplainer(
        model, Independent(x_train[background_index], max_samples=200)
    )
    names = vectorizer.get_feature_names_out()
    records = load_checkpoint(args.checkpoint)
    targets = [
        row for i, row in enumerate(rows)
        if i >= args.start and (args.end is None or i < args.end)
        and (not args.only_id or row["id"] == args.only_id)
    ]
    if args.limit is not None:
        targets = targets[: args.limit]
    if not targets:
        raise ValueError("No matching handoff row")
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with args.checkpoint.open("a", encoding="utf-8") as stream:
        for count, row in enumerate(targets, start=1):
            row_id = row["id"]
            if row_id in records:
                continue
            index = int(ID_PATTERN.fullmatch(row_id).group(1))
            position = test_positions[index]
            result = explain_row(
                row_id, source.at[index, "text"], x_test[position], names,
                model, vectorizer, shap_explainer,
            )
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            stream.flush()
            records[row_id] = result
            if count % 100 == 0 or args.only_id:
                print(f"Explained {count}/{len(targets)} target rows", flush=True)

    if args.limit is not None or args.only_id or args.start or args.end is not None:
        print(f"Checkpoint contains {len(records)} explanations", flush=True)
        if args.only_id:
            print(json.dumps(records[targets[0]["id"]], ensure_ascii=False, indent=2))
        return
    if set(records) != {row["id"] for row in rows}:
        raise ValueError("Checkpoint does not cover every handoff ID")
    output_rows = [
        {
            "id": row["id"],
            "test_row": row["test_row"],
            "subject": row["subject"],
            "shap": json.dumps(records[row["id"]]["shap"], ensure_ascii=False),
            "lime": json.dumps(records[row["id"]]["lime"], ensure_ascii=False),
        }
        for row in rows
    ]
    write_csv(OUTPUT, ["id", "test_row", "subject", "shap", "lime"], output_rows)
    print(f"Wrote {len(output_rows)} SHAP/LIME explanations to {OUTPUT}")


if __name__ == "__main__":
    main()
