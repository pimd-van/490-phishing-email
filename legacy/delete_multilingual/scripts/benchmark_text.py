"""Reproducible text-only MeAJOR benchmark; intended to run on VM 490-18."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import LinearSVC
from xgboost import XGBClassifier
import xgboost

EXPECTED_MD5 = "aa8f59e96787cbd696c0b650e5400dc9"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def clean_text(value: object) -> str:
    s = "" if pd.isna(value) else str(value)
    s = re.sub(r"\[([A-Z][A-Z0-9_]{1,})\]", lambda m: " token_" + m.group(1).lower() + " ", s)
    return re.sub(r"\s+", " ", s.lower()).strip()


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": accuracy_score(y, pred),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "fnr": fn / (fn + tp) if fn + tp else 0.0,
    }


def predict_knn_in_blocks(model, X, block_rows=256):
    """Keep KNN's pairwise distance matrix bounded to at most 256 query rows."""
    outputs = []
    for start in range(0, X.shape[0], block_rows):
        neighbors = model.kneighbors(X[start:start + block_rows], return_distance=False)
        for row in neighbors:
            outputs.append(np.bincount(model._y[row].astype(int), minlength=2).argmax())
    return np.asarray(outputs, dtype=int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to official MeAJOR cleaned CSV")
    ap.add_argument("--out", default="results/slide_text_benchmark")
    ap.add_argument("--allow-md5-mismatch", action="store_true")
    args = ap.parse_args()
    source = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    md5 = md5sum(source)
    if md5 != EXPECTED_MD5 and not args.allow_md5_mismatch:
        raise SystemExit(f"Source MD5 {md5} != expected {EXPECTED_MD5}; inspect source before proceeding")
    df = pd.read_csv(source, low_memory=False)
    low_cols = {c.lower(): c for c in df.columns}
    label_col = low_cols.get("label")
    subject_col = low_cols.get("subject")
    body_col = low_cols.get("body") or low_cols.get("content")
    if not label_col or not body_col:
        raise SystemExit(f"Expected label and body/content columns; found {list(df.columns)}")
    labels = pd.to_numeric(df[label_col], errors="coerce")
    keep = labels.isin([0, 1])
    df, labels = df.loc[keep].copy(), labels.loc[keep].astype(int)
    subject = df[subject_col].map(clean_text) if subject_col else pd.Series("", index=df.index)
    body = df[body_col].map(clean_text)
    text = (subject + " " + body).str.strip()
    valid = text.ne("")
    dedupe_key = subject + "\n" + body
    df = df.loc[valid]
    text = text.loc[valid]
    labels = labels.loc[valid]
    dedupe = ~dedupe_key.loc[valid].duplicated(keep="first")
    text, labels = text.loc[dedupe].reset_index(drop=True), labels.loc[dedupe].reset_index(drop=True)
    # Identical seed/stratification as the project recheck: 70/15/15.
    x_train, x_tmp, y_train, y_tmp = train_test_split(text, labels, test_size=0.30, random_state=42, stratify=labels)
    x_val, x_test, y_val, y_test = train_test_split(x_tmp, y_tmp, test_size=0.50, random_state=42, stratify=y_tmp)
    vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)
    X_train = vec.fit_transform(x_train)
    X_val = vec.transform(x_val)
    X_test = vec.transform(x_test)
    models = {
        "MultinomialNB": MultinomialNB(),
        "LogisticRegression": LogisticRegression(),
        "KNN_cosine_k5": KNeighborsClassifier(n_neighbors=5, metric="cosine", algorithm="brute", n_jobs=1),
        "XGBoost": XGBClassifier(n_estimators=100, random_state=42, n_jobs=12, tree_method="hist", eval_metric="logloss"),
        "RandomForest_default": RandomForestClassifier(random_state=42, n_jobs=12),
        "DecisionTree": DecisionTreeClassifier(random_state=42),
        "LinearSVC": LinearSVC(),
    }
    rows, fitted = [], {}
    for name, model in models.items():
        start = time.perf_counter()
        model.fit(X_train, y_train)
        val_pred = predict_knn_in_blocks(model, X_val) if name == "KNN_cosine_k5" else model.predict(X_val)
        row = {"model": name, **metrics(y_val, val_pred), "fit_val_seconds": time.perf_counter() - start}
        rows.append(row)
        fitted[name] = model
        pd.DataFrame(rows).to_csv(out / "validation_metrics.partial.csv", index=False)
        (out / "progress.json").write_text(json.dumps({
            "completed_models": [r["model"] for r in rows],
            "next_model": list(models)[len(rows)] if len(rows) < len(models) else None,
            "last_validation": row,
        }, indent=2), encoding="utf-8")
        print(json.dumps({"validation": row}), flush=True)
    table = pd.DataFrame(rows).sort_values(["f1", "precision", "recall"], ascending=False)
    winner = str(table.iloc[0]["model"])
    selected_pred = (predict_knn_in_blocks(fitted[winner], X_test) if winner == "KNN_cosine_k5"
                     else fitted[winner].predict(X_test))
    test_result = metrics(y_test, selected_pred)
    lr_test_verification = None
    if winner != "LogisticRegression":
        lr_test_verification = metrics(y_test, fitted["LogisticRegression"].predict(X_test))
    table.to_csv(out / "validation_metrics.csv", index=False)
    details = {
        "source": str(source.resolve()), "source_md5": md5, "source_sha256": sha256(source),
        "expected_md5": EXPECTED_MD5, "clean_rows": len(text),
        "split_rows": {"train": len(x_train), "validation": len(x_val), "test": len(x_test)},
        "class_counts": {
            "cleaned": labels.value_counts().sort_index().astype(int).to_dict(),
            "train": y_train.value_counts().sort_index().astype(int).to_dict(),
            "validation": y_val.value_counts().sort_index().astype(int).to_dict(),
            "test": y_test.value_counts().sort_index().astype(int).to_dict(),
        },
        "split_seed": 42, "split": "stratified 70/15/15", "text_features": "subject + body",
        "tfidf": {"max_features": 5000, "ngram_range": [1, 2], "sublinear_tf": True},
        "selection_kpi": "validation F1", "tie_break": ["precision", "recall"],
        "best_model": winner, "heldout_test_metrics": test_result,
        "logistic_regression_test_verification_if_not_winner": lr_test_verification,
        "sklearn_version": sklearn.__version__, "xgboost_version": xgboost.__version__,
        "host": socket.gethostname(), "platform": platform.platform(), "cpu_count": os.cpu_count(),
        "total_seconds": time.perf_counter() - t0,
        "model_settings": {
            "MultinomialNB": "sklearn defaults", "LogisticRegression": "sklearn defaults",
            "KNN_cosine_k5": "5 nearest neighbors, cosine distance, brute force, single worker",
            "XGBoost": "100 trees, seed 42, histogram, n_jobs=12, logloss",
            "RandomForest_default": "sklearn defaults except seed 42 and n_jobs=12",
            "DecisionTree": "sklearn defaults except seed 42", "LinearSVC": "sklearn defaults",
        },
    }
    (out / "summary.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    table.to_csv(out / "validation_metrics.csv", index=False)
    (out / "progress.json").write_text(json.dumps({"status": "complete", "best_model": winner}, indent=2), encoding="utf-8")
    print(json.dumps({"complete": details}, indent=2), flush=True)


if __name__ == "__main__":
    main()
