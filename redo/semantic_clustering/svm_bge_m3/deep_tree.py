"""Add a deeper level (default 60 sub-clusters) to the existing Ward hierarchy.

Reuses vectors.npz, linkage_ward.npy and assignment.npz from svm_clustering.py
(no re-embedding). Writes deep_tree.json with:
  levels      cluster counts per level, e.g. [8, 20, 60]
  nodes       every sub-cluster at the deepest level with parent ids, keywords,
              exemplars, LLM label and its member email ids
  merges      the last (K-1) Ward merges above the deepest cut, for the dendrogram
  cuts        Ward heights that separate each level
"""
import argparse, csv, json, sys
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import cut_tree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svm_clustering import read_rows, clean_for_terms, ollama_label, SEED  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--k", type=int, default=60)
ap.add_argument("--llm", default="qwen2.5:7b")
a = ap.parse_args()
out = Path(a.out)
rows = read_rows(a.input)
with np.load(out / "vectors.npz") as z:
    vecs = z["embeddings"]
Z = np.load(out / "linkage_ward.npy")
with np.load(out / "assignment.npz") as z:
    par, cl = z["parent"], z["cluster"]
N, K = len(rows), a.k

raw = cut_tree(Z, n_clusters=K)[:, 0]
for g in set(raw):  # nesting check against the 20-cluster level
    assert len(set(cl[raw == g])) == 1
# Number sub-clusters in the order of their 20-level cluster, then by size.
keys = sorted(set(raw), key=lambda g: (cl[raw == g][0], -(raw == g).sum()))
sub = np.array([{g: i + 1 for i, g in enumerate(keys)}[g] for g in raw])
np.save(out / f"assignment_k{K}.npy", sub)

# c-TF-IDF keywords per sub-cluster (same recipe as svm_clustering.stage_profile)
from sklearn.feature_extraction.text import CountVectorizer
docs = [clean_for_terms(r["subject"] + " " + r["body"]) for r in rows]
cv = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=5, max_df=0.5,
                     token_pattern=r"(?u)\b[a-z฀-๿][a-z฀-๿]{2,}\b")
X = cv.fit_transform(docs)
terms = np.array(cv.get_feature_names_out())
tf = np.vstack([np.asarray(X[sub == k].sum(axis=0)).ravel() for k in range(1, K + 1)]).astype(float)
tf /= tf.sum(axis=1, keepdims=True)
idf = np.log(1 + (X.sum() / K) / np.asarray(X.sum(axis=0)).ravel())
score = tf * idf

nodes = []
for k in range(1, K + 1):
    m = np.flatnonzero(sub == k)
    cen = vecs[m].mean(0); cen /= np.linalg.norm(cen)
    sims = vecs[m] @ cen
    ex = m[np.argsort(-sims)[:5]]
    nodes.append({
        "sub_id": k, "cluster_id": int(cl[m[0]]), "parent_id": int(par[m[0]]), "emails": int(len(m)),
        "keywords": terms[np.argsort(-score[k - 1])[:10]].tolist(),
        "cohesion_mean_cosine": round(float(sims.mean()), 3),
        "exemplars": [{"id": rows[i]["id"], "subject": rows[i]["subject"][:140],
                       "body_start": " ".join(rows[i]["body"].split())[:300]} for i in ex],
        "members": [rows[i]["id"] for i in m[np.argsort(-sims)]],  # most typical first
    })
if a.llm:
    for n in nodes:
        exs = [f"Subject: {e['subject']}\nBody: {e['body_start']}" for e in n["exemplars"]]
        try:
            n["llm_label"], n["llm_description"] = ollama_label(n["keywords"], exs, a.llm)
        except Exception as e:
            n["llm_label"], n["llm_description"] = "", f"(label failed: {e})"
        print("label", n["sub_id"], n["cluster_id"], n["emails"], n["llm_label"], flush=True)

# Dendrogram above the deepest cut: last K-1 merges, children are merges or sub-clusters.
first = 2 * N - 1 - (K - 1)
def leaf_of(node):
    while node >= N:
        node = int(Z[node - N, 0])
    return node
merges = []
for l, r, h, n in Z[-(K - 1):]:
    side = []
    for c in (int(l), int(r)):
        side.append({"merge": c - first} if c >= first else {"sub": int(sub[leaf_of(c)])})
    merges.append({"left": side[0], "right": side[1], "height": float(h), "size": int(n)})
H = Z[:, 2]
def cut_height(k):  # midway between the merges just below and just above a k-cluster cut
    return float((H[-k] + H[-(k - 1)]) / 2)
levels = [int(par.max()), int(cl.max()), K]
info = {"levels": levels, "cuts": {str(k): cut_height(k) for k in levels},
        "llm_model": a.llm, "nodes": nodes, "merges": merges}
(out / "deep_tree.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
sizes = [n["emails"] for n in nodes]
print("done", K, "subclusters; smallest", min(sizes), "largest", max(sizes), "cuts", info["cuts"], flush=True)
