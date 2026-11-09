"""Rebuild the LinearSVC text model and explain each row of the frozen SVM handoff."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import shap
from joblib import Parallel, delayed, parallel_config
from lime.lime_base import LimeBase
from lime.lime_text import IndexedString
from sklearn.svm import LinearSVC

from benchmark_english import SEED, handoff_id, prepare, split

ROOT = Path(__file__).resolve().parents[1]
LIME_SAMPLES = 500
csv.field_size_limit(1 << 30)


def rebuild(source):
    data, _ = prepare(source)
    (train, _, test), vectorizer, (x_train, _, x_test) = split(data)
    model = LinearSVC().fit(x_train, train["label"])
    background = np.random.default_rng(SEED).choice(x_train.shape[0], 200, replace=False)
    explainer = shap.LinearExplainer(
        (model.coef_[0], model.intercept_[0]),
        shap.maskers.Independent(x_train[background], max_samples=200),
    )
    return model, vectorizer, explainer, test, x_test


def ranked(terms, value_key):
    return {
        "top_positive_terms": [
            {"term": term, value_key: float(value)} for term, value in terms if value > 0
        ][:5],
        "top_negative_terms": [
            {"term": term, value_key: float(value)} for term, value in terms if value < 0
        ][:5],
    }


def lime_margin(text, model, vectorizer, seed):
    # Use LIME's text deletion neighborhood and weighted local regression.
    # The single response column is the continuous SVM decision score.
    rng = np.random.RandomState(seed)
    tokens = IndexedString(text)
    count = tokens.num_words()
    if not count:
        return {
            "surrogate_r2": None,
            "surrogate_estimate_margin": None,
            "top_positive_terms": [],
            "top_negative_terms": [],
            "status": "no_words_to_perturb",
        }
    active = np.ones((LIME_SAMPLES, count), dtype=np.int8)
    variants = [text]
    sizes = rng.randint(1, count + 1, LIME_SAMPLES - 1)
    for i, size in enumerate(sizes, start=1):
        removed = rng.choice(count, size, replace=False)
        active[i, removed] = 0
        variants.append(tokens.inverse_removing(removed))
    # Cosine distance to the all-ones mask, scaled to 0–100 as in text LIME.
    distances = (1 - np.sqrt(active.sum(axis=1) / count)) * 100
    margins = model.decision_function(vectorizer.transform(variants))
    base = LimeBase(lambda d: np.exp(-0.5 * (d / 25) ** 2), random_state=rng)
    _, weights, r2, prediction = base.explain_instance_with_data(
        active, margins[:, None], distances, 0, 10, feature_selection="auto"
    )
    return {
        "surrogate_r2": float(r2),
        "surrogate_estimate_margin": float(prediction[0]),
        **ranked([(tokens.word(i), w) for i, w in weights], "weight"),
    }


def explain(row, text, x, model, vectorizer, explainer, names):
    margin = float(model.decision_function(x)[0])
    values = np.asarray(explainer.shap_values(x)).ravel()
    baseline = float(explainer.expected_value)
    if abs(baseline + values.sum() - margin) > 1e-8:
        raise ValueError(f"SHAP additivity failed for {row['id']}")
    order = x.indices[np.argsort(-np.abs(values[x.indices]))]
    shap_result = {
        "method": "shap.LinearExplainer",
        "unit": "svm_margin",
        "base_value_margin": baseline,
        "model_output_margin": margin,
        "shown_terms": "present_tfidf_features_only",
        **ranked([(names[i], values[i]) for i in order], "value_margin"),
    }
    seed = SEED + int(row["id"].rsplit("_", 1)[1])
    lime_result = {
        "method": "LIME text deletion with LimeBase",
        "unit": "local_svm_margin_surrogate_weight",
        "num_samples": LIME_SAMPLES,
        "random_seed": seed,
        **lime_margin(text, model, vectorizer, seed),
    }
    return {
        "id": row["id"],
        "test_row": row["test_row"],
        "subject": row["subject"],
        "shap": json.dumps(shap_result, ensure_ascii=False, allow_nan=False),
        "lime": json.dumps(lime_result, ensure_ascii=False, allow_nan=False),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--handoff", type=Path, default=ROOT / "dataset" / "svm_handoff.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "xai" / "shap_lime_explanations.csv")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()

    with args.handoff.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    model, vectorizer, explainer, test, x_test = rebuild(args.source)
    margins = model.decision_function(x_test)
    positions = np.flatnonzero(model.predict(x_test) == 1)
    expected = [handoff_id(test.iloc[pos]["source_row"]) for pos in positions]
    if [row["id"] for row in rows] != expected:
        raise ValueError("Reconstructed predictions do not match the handoff IDs/order")
    for row, pos in zip(rows, positions):
        result = json.loads(row["svm_result"])
        source_row = test.iloc[pos]
        if (
            int(row["test_row"]) != pos
            or row["subject"] != source_row["subject"]
            or row["body"] != source_row["body"]
            or row["language"] != source_row["language"]
            or int(row["source_row"]) != source_row["source_row"]
            or result["prediction"] != 1
            or not np.isclose(result["decision_score"], margins[pos], rtol=0, atol=1e-8)
        ):
            raise ValueError(f"Reconstructed score, text or position differs for {row['id']}")
    print(f"Verified all {len(rows)} frozen handoff predictions", flush=True)

    names = vectorizer.get_feature_names_out()
    with parallel_config(backend="loky", inner_max_num_threads=1):
        results = Parallel(n_jobs=args.jobs, return_as="generator", verbose=10)(
            delayed(explain)(row, test.iloc[pos]["text"], x_test[pos], model, vectorizer, explainer, names)
            for row, pos in zip(rows, positions)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["id", "test_row", "subject", "shap", "lime"], lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(results)
        temporary.replace(args.output)


if __name__ == "__main__":
    main()
