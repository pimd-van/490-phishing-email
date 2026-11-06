"""Run the original text-only benchmark with an exact MeAJOR language filter."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
import xgboost

# Share the historical cleaning, metric and bounded KNN implementations.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from benchmark_text import EXPECTED_MD5, clean_text, md5sum, metrics, predict_knn_in_blocks, sha256

LANGUAGE_TAGS = ("en", "en;en", "en;en;en")
SEED = 42


def prepare(source):
    digest = md5sum(source)
    if digest != EXPECTED_MD5:
        raise ValueError(f"Unexpected MeAJOR source MD5: {digest}")
    raw = pd.read_csv(source, low_memory=False)
    english = raw.loc[raw["language"].isin(LANGUAGE_TAGS)].copy()
    labels = pd.to_numeric(english.pop("label"), errors="coerce")
    data = english.loc[labels.isin([0, 1])].copy()
    valid_labels = len(data)
    for field in ("subject", "body"):
        data[field] = data[field].map(clean_text)
    data["text"] = (data["subject"] + " " + data["body"]).str.strip()
    data = data.loc[data["text"].ne("")]
    nonempty = len(data)
    data = data.drop_duplicates(["subject", "body"], keep="first").copy()
    data.insert(0, "source_row", data.index)
    data["label"] = labels.loc[data.index].astype(int)
    summary = {
        "source_file": source.name,
        "source_md5": digest,
        "source_sha256": sha256(source),
        "source_rows": len(raw),
        "exact_language_tags": list(LANGUAGE_TAGS),
        "rows_by_accepted_tag": {tag: int(english["language"].eq(tag).sum()) for tag in LANGUAGE_TAGS},
        "rejected_language_rows": len(raw) - len(english),
        "english_rows": len(english),
        "invalid_label_rows": len(english) - valid_labels,
        "empty_text_rows": valid_labels - nonempty,
        "duplicate_cleaned_subject_body_rows": nonempty - len(data),
        "clean_rows": len(data),
        "clean_rows_by_tag": {tag: int(data["language"].eq(tag).sum()) for tag in LANGUAGE_TAGS},
    }
    return data.reset_index(drop=True), summary


def split(data):
    train, rest = train_test_split(
        data, test_size=0.30, random_state=SEED, stratify=data["label"]
    )
    validation, test = train_test_split(
        rest, test_size=0.50, random_state=SEED, stratify=rest["label"]
    )
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)
    matrices = (
        vectorizer.fit_transform(train["text"]),
        vectorizer.transform(validation["text"]),
        vectorizer.transform(test["text"]),
    )
    return (train, validation, test), vectorizer, matrices


def handoff_id(source_row):
    return f"meajor_en_v1_test_{source_row}"


def write_handoff(out, model, vectorizer, test, x_test, prediction):
    coef = model.coef_[0]
    terms = vectorizer.get_feature_names_out()
    margins = model.decision_function(x_test)
    records = []
    for pos in np.flatnonzero(prediction == 1):
        row = test.iloc[pos]
        contrib = x_test[pos].multiply(coef).tocsr()
        order = np.argsort(contrib.data)
        positive = [
            {"term": terms[contrib.indices[j]], "contribution_margin": float(contrib.data[j])}
            for j in order[::-1][:5] if contrib.data[j] > 0
        ]
        negative = [
            {"term": terms[contrib.indices[j]], "contribution_margin": float(contrib.data[j])}
            for j in order[:5] if contrib.data[j] < 0
        ]
        record = {"id": handoff_id(row["source_row"]), "test_row": int(pos)}
        record.update(row.drop(["label", "text"]).to_dict())
        record["svm_result"] = json.dumps({"prediction": 1, "decision_score": float(margins[pos])})
        record["xai"] = json.dumps({
            "method": "linear_svc_tfidf_contributions", "unit": "svm_margin",
            "intercept_margin": float(model.intercept_[0]),
            "top_positive_terms": positive, "top_negative_terms": negative,
        })
        records.append(record)
    target = out / "dataset" / "svm_handoff.csv"
    temp = target.with_suffix(".tmp")
    pd.DataFrame(records).to_csv(temp, index=False, encoding="utf-8-sig")
    temp.replace(target)
    print(f"Exported {len(records)} SVM handoff rows", flush=True)
    return margins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out
    for name in ("benchmark", "dataset"):
        (out / name).mkdir(parents=True, exist_ok=True)
    data, summary = prepare(args.source)
    print(json.dumps(summary), flush=True)
    parts, vectorizer, matrices = split(data)
    train, validation, test = parts
    x_train, x_val, x_test = matrices
    models = {
        "LinearSVC": LinearSVC(),
        "MultinomialNB": MultinomialNB(),
        "LogisticRegression": LogisticRegression(),
        "KNN_cosine_k5": KNeighborsClassifier(n_neighbors=5, metric="cosine", algorithm="brute", n_jobs=1),
        "XGBoost": xgboost.XGBClassifier(n_estimators=100, random_state=SEED, n_jobs=12,
                                         tree_method="hist", eval_metric="logloss"),
        "RandomForest_default": RandomForestClassifier(random_state=SEED, n_jobs=12),
        "DecisionTree": DecisionTreeClassifier(random_state=SEED),
    }
    val_results, test_results = [], []
    svm_margins = None
    for name, model in models.items():
        model.fit(x_train, train["label"])
        predict = (lambda matrix: predict_knn_in_blocks(model, matrix)) if name == "KNN_cosine_k5" else model.predict
        val_pred, test_pred = predict(x_val), predict(x_test)
        val_results.append({"model": name, **metrics(validation["label"], val_pred)})
        test_results.append({"model": name, **metrics(test["label"], test_pred)})
        print(name, "validation F1", val_results[-1]["f1"], "test F1", test_results[-1]["f1"], flush=True)
        if name == "LinearSVC":
            svm_margins = write_handoff(out, model, vectorizer, test, x_test, test_pred)
            manifest_parts = []
            for key, frame in zip(("train", "validation", "test"), parts):
                manifest = frame[["source_row", "language", "label"]].copy()
                manifest["split"] = key
                manifest["split_row"] = np.arange(len(frame))
                manifest["svm_test_margin"] = svm_margins if key == "test" else None
                manifest_parts.append(manifest)
            pd.concat(manifest_parts).to_csv(out / "benchmark" / "split_manifest.csv", index=False)

    ranked = pd.DataFrame(val_results).sort_values(["f1", "precision", "recall"], ascending=False)
    ranked.to_csv(out / "benchmark" / "validation_metrics.csv", index=False)
    pd.DataFrame(test_results).set_index("model").loc[ranked["model"]].to_csv(
        out / "benchmark" / "test_metrics.csv"
    )
    summary.update({
        "split": "stratified 70/15/15",
        "split_seed": SEED,
        "split_rows": dict(zip(("train", "validation", "test"), map(len, parts))),
        "class_counts": {
            key: frame["label"].value_counts().sort_index().to_dict()
            for key, frame in zip(("train", "validation", "test"), parts)
        },
        "tfidf": {"fit_on": "train", "max_features": 5000, "ngram_range": [1, 2], "sublinear_tf": True},
        "selection_kpi": "validation F1",
        "tie_break": ["precision", "recall"],
        "best_model": ranked.iloc[0]["model"],
        "handoff_model": "LinearSVC",
        "handoff_rows": int(np.count_nonzero(svm_margins > 0)),
        "sklearn_version": sklearn.__version__,
        "xgboost_version": xgboost.__version__,
    })
    (out / "benchmark" / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
