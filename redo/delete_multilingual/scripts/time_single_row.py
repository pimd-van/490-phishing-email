"""Time single-row prediction for LinearSVC and LogisticRegression.

Rebuilds exactly the Part 1 pipeline from benchmark_text.py (same cleaning,
dedupe, 70/15/15 stratified split seed 42, TF-IDF 5000 1-2gram sublinear),
fits both models on train, then times predicting one test email at a time.
"""
import json, sys, time, statistics
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_text import clean_text  # same cleaning as the benchmark

src = Path(sys.argv[1])
df = pd.read_csv(src, low_memory=False)
low = {c.lower(): c for c in df.columns}
label_col, subject_col = low.get("label"), low.get("subject")
body_col = low.get("body") or low.get("content")
labels = pd.to_numeric(df[label_col], errors="coerce")
keep = labels.isin([0, 1])
df, labels = df.loc[keep].copy(), labels.loc[keep].astype(int)
raw_subject = df[subject_col] if subject_col else pd.Series("", index=df.index)
raw_body = df[body_col]
subject = raw_subject.map(clean_text)
body = raw_body.map(clean_text)
text = (subject + " " + body).str.strip()
valid = text.ne("")
dedupe_key = subject + "\n" + body
raw = pd.DataFrame({"subject": raw_subject, "body": raw_body}).loc[valid]
text, labels = text.loc[valid], labels.loc[valid]
dedupe = ~dedupe_key.loc[valid].duplicated(keep="first")
raw = raw.loc[dedupe].reset_index(drop=True)
text, labels = text.loc[dedupe].reset_index(drop=True), labels.loc[dedupe].reset_index(drop=True)

x_train, x_tmp, y_train, y_tmp = train_test_split(text, labels, test_size=0.30, random_state=42, stratify=labels)
x_val, x_test, y_val, y_test = train_test_split(x_tmp, y_tmp, test_size=0.50, random_state=42, stratify=y_tmp)
print("split", len(x_train), len(x_val), len(x_test), flush=True)

vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)
X_train = vec.fit_transform(x_train)
X_test = vec.transform(x_test)

models = {"LinearSVC": LinearSVC(), "LogisticRegression": LogisticRegression()}
for m in models.values():
    m.fit(X_train, y_train)
for name, m in models.items():
    print(name, "test F1", round(f1_score(y_test, m.predict(X_test)) * 100, 2), flush=True)

# Single-row timing on N test emails, starting from raw subject/body text.
N = 2000
idx = x_test.index[:N]
out = {}
for name, m in models.items():
    t_clean, t_vec, t_pred, t_total = [], [], [], []
    for i in idx:
        s, b = raw.at[i, "subject"], raw.at[i, "body"]
        a = time.perf_counter()
        t = (clean_text(s) + " " + clean_text(b)).strip()
        c = time.perf_counter()
        x = vec.transform([t])
        d = time.perf_counter()
        m.predict(x)
        e = time.perf_counter()
        t_clean.append(c - a); t_vec.append(d - c); t_pred.append(e - d); t_total.append(e - a)
    ms = lambda v: {"median_ms": round(statistics.median(v) * 1000, 3),
                    "mean_ms": round(statistics.mean(v) * 1000, 3),
                    "p95_ms": round(float(np.percentile(v, 95)) * 1000, 3)}
    out[name] = {"clean": ms(t_clean), "tfidf_transform": ms(t_vec), "predict": ms(t_pred), "total": ms(t_total)}

# One example row.
i0 = idx[0]
x0 = vec.transform([text.at[i0]])
example = {"row_index_in_cleaned": int(i0), "true_label": int(labels.at[i0]),
           "subject": str(raw.at[i0, "subject"])[:120]}
example["LinearSVC"] = {"prediction": int(models["LinearSVC"].predict(x0)[0]),
                        "decision_score": round(float(models["LinearSVC"].decision_function(x0)[0]), 4)}
example["LogisticRegression"] = {"prediction": int(models["LogisticRegression"].predict(x0)[0]),
                                 "probability_phishing": round(float(models["LogisticRegression"].predict_proba(x0)[0, 1]), 4)}
print(json.dumps({"rows_timed": len(idx), "timing": out, "example": example}, indent=2, ensure_ascii=False))
