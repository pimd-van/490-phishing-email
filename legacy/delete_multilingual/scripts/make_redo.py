"""Rebuild Part 1 (text-only MeAJOR benchmark) and export the Linear SVM handoff.

Outputs (in --out):
  svm_handoff.csv             test emails that LinearSVC predicts as phishing,
                              same columns as legacy/legacy_logistic_regression/part2/part2_handoff.csv but with
                              svm_result + SVM TF-IDF contributions in xai
  test_metrics.csv            held-out test metrics for every model
  svm_vs_lr_rows.csv          rows where LinearSVC and the LR handoff disagree
  comparison_summary.json     counts for the SVM vs LR comparison
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import LinearSVC
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_text import clean_text, metrics, predict_knn_in_blocks

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--lr-handoff", required=True, help="existing legacy/legacy_logistic_regression/part2/part2_handoff.csv")
ap.add_argument("--out", required=True)
args = ap.parse_args()
out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

# ---- identical preprocessing to benchmark_text.py ----
df = pd.read_csv(args.input, low_memory=False)
labels = pd.to_numeric(df["label"], errors="coerce")
keep = labels.isin([0, 1])
df, labels = df.loc[keep].copy(), labels.loc[keep].astype(int)
subject = df["subject"].map(clean_text)
body = df["body"].map(clean_text)
text = (subject + " " + body).str.strip()
valid = text.ne("")
dedupe_key = subject + "\n" + body
df, text, labels = df.loc[valid], text.loc[valid], labels.loc[valid]
dedupe = ~dedupe_key.loc[valid].duplicated(keep="first")
df = df.loc[dedupe].reset_index(drop=True)
text, labels = text.loc[dedupe].reset_index(drop=True), labels.loc[dedupe].reset_index(drop=True)

x_train, x_tmp, y_train, y_tmp = train_test_split(text, labels, test_size=0.30, random_state=42, stratify=labels)
x_val, x_test, y_val, y_test = train_test_split(x_tmp, y_tmp, test_size=0.50, random_state=42, stratify=y_tmp)
vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)
X_train, X_val, X_test = vec.fit_transform(x_train), vec.transform(x_val), vec.transform(x_test)
print("split", len(x_train), len(x_val), len(x_test), flush=True)

models = {
    "MultinomialNB": MultinomialNB(),
    "LogisticRegression": LogisticRegression(),
    "KNN_cosine_k5": KNeighborsClassifier(n_neighbors=5, metric="cosine", algorithm="brute", n_jobs=1),
    "XGBoost": XGBClassifier(n_estimators=100, random_state=42, n_jobs=12, tree_method="hist", eval_metric="logloss"),
    "RandomForest_default": RandomForestClassifier(random_state=42, n_jobs=12),
    "DecisionTree": DecisionTreeClassifier(random_state=42),
    "LinearSVC": LinearSVC(),
}
rows, preds = [], {}
for name, m in models.items():
    m.fit(X_train, y_train)
    p_val = predict_knn_in_blocks(m, X_val) if name.startswith("KNN") else m.predict(X_val)
    p_test = predict_knn_in_blocks(m, X_test) if name.startswith("KNN") else m.predict(X_test)
    preds[name] = p_test
    v, t = metrics(y_val, p_val), metrics(y_test, p_test)
    rows.append({"model": name, **{f"val_{k}": v[k] for k in ("accuracy", "precision", "recall", "f1")},
                 **{f"test_{k}": t[k] for k in ("accuracy", "precision", "recall", "f1", "tn", "fp", "fn", "tp")}})
    print(name, round(v["f1"] * 100, 2), round(t["f1"] * 100, 2), flush=True)
pd.DataFrame(rows).sort_values("val_f1", ascending=False).to_csv(out / "test_metrics.csv", index=False)

# ---- SVM handoff ----
svm = models["LinearSVC"]
coef, intercept = svm.coef_[0], float(svm.intercept_[0])
terms = np.array(vec.get_feature_names_out())
scores = svm.decision_function(X_test)
ps = preds["LinearSVC"]
test_idx = x_test.index.to_numpy()          # index in cleaned/deduped data
cols = [c for c in df.columns if c != "label"]
records = []
for pos in np.flatnonzero(ps == 1):
    i = test_idx[pos]
    row = X_test[pos]
    contrib = row.multiply(coef).tocsr()
    idx, val = contrib.indices, contrib.data
    order = np.argsort(val)
    pos_terms = [{"term": terms[idx[j]], "contribution_margin": float(val[j])} for j in order[::-1][:5] if val[j] > 0]
    neg_terms = [{"term": terms[idx[j]], "contribution_margin": float(val[j])} for j in order[:5] if val[j] < 0]
    rec = {"id": f"meajor_test_{i}", "test_row": int(pos)}
    rec.update({c: df.at[i, c] for c in cols})
    rec["svm_result"] = json.dumps({"prediction": 1, "decision_score": float(scores[pos])})
    rec["xai"] = json.dumps({"method": "linear_svc_tfidf_contributions", "unit": "svm_margin",
                             "intercept_margin": intercept, "top_positive_terms": pos_terms,
                             "top_negative_terms": neg_terms})
    records.append(rec)
pd.DataFrame(records).to_csv(out / "svm_handoff.csv", index=False, encoding="utf-8-sig")
print("svm_handoff rows", len(records), flush=True)

# ---- compare with the existing LR handoff ----
lr_hand = pd.read_csv(args.lr_handoff, encoding="utf-8-sig", dtype=str, keep_default_na=False)
lr_hand = lr_hand[lr_hand["id"].str.match(r"^meajor_test_\d+$")]
lr_ids = set(lr_hand["id"])
svm_ids = {r["id"] for r in records}
y = y_test.to_numpy()
id_of_pos = {f"meajor_test_{test_idx[p]}": p for p in range(len(test_idx))}
diff = []
for kind, ids in (("lr_only", lr_ids - svm_ids), ("svm_only", svm_ids - lr_ids)):
    for rid in sorted(ids, key=lambda s: int(s.rsplit("_", 1)[1])):
        p = id_of_pos[rid]
        diff.append({"id": rid, "test_row": p, "in": kind, "true_label": int(y[p]),
                     "svm_decision_score": float(scores[p])})
pd.DataFrame(diff).to_csv(out / "svm_vs_lr_rows.csv", index=False)
def lab(kind, v): return sum(1 for d in diff if d["in"] == kind and d["true_label"] == v)
summary = {
    "test_rows": len(x_test), "true_phishing_in_test": int(y.sum()),
    "lr_handoff_rows": len(lr_ids), "svm_handoff_rows": len(svm_ids),
    "same_rows": len(lr_ids & svm_ids),
    "lr_only": {"rows": len(lr_ids - svm_ids), "true_phishing": lab("lr_only", 1), "true_legit": lab("lr_only", 0)},
    "svm_only": {"rows": len(svm_ids - lr_ids), "true_phishing": lab("svm_only", 1), "true_legit": lab("svm_only", 0)},
}
(out / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
