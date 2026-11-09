"""Semantic hierarchical clustering of the Linear SVM phishing handoff.

Stages (run all by default, each is cached):
  embed    BGE-M3 dense embeddings -> vectors.npz + persistent Chroma collection
  cluster  agglomerative trees, level diagnostics, parent/child cut selection
  profile  per-cluster keywords (c-TF-IDF), exemplars, stats, optional LLM label
  sample   700 rows allocated to clusters in proportion to cluster size
  viz      2-D t-SNE coordinates and a compact JSON for the visualization page
"""
import argparse, csv, json, re, time, urllib.request
from pathlib import Path

import numpy as np

SEED = 42
SAMPLE_SIZE = 700
MODEL = "BAAI/bge-m3"
MAX_TOKENS = 2048
URL = re.compile(r"https?://[^\s<>\"]+", re.I)
FINE_LEVELS = [10, 12, 15, 18, 20, 25, 30, 35, 40]
PARENT_LEVELS = [4, 5, 6, 7, 8]
csv.field_size_limit(1 << 30)


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len({r["id"] for r in rows}) == len(rows)
    return rows


def email_text(r):
    s = " ".join(URL.sub(" token_url ", r["subject"]).split())
    b = " ".join(URL.sub(" token_url ", r["body"]).split())
    return f"Subject: {s}\nBody: {b}"


# --------------------------------------------------------------------- embed
def stage_embed(rows, out):
    import chromadb, torch
    from sentence_transformers import SentenceTransformer

    texts = [email_text(r) for r in rows]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        torch.set_num_threads(40)
    model = SentenceTransformer(MODEL, device=device,
                                model_kwargs={"torch_dtype": torch.float16 if device == "cuda" else torch.float32})
    print("embedding on", device, flush=True)
    model.max_seq_length = MAX_TOKENS
    tok = model.tokenizer
    lengths = [len(x) for x in tok(texts, add_special_tokens=True, truncation=False)["input_ids"]]
    t0 = time.perf_counter()
    vecs = model.encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True,
                        show_progress_bar=False).astype(np.float32)
    secs = time.perf_counter() - t0
    assert np.isfinite(vecs).all()
    ids = np.array([r["id"] for r in rows])
    meta = {"model": MODEL, "max_seq_length": MAX_TOKENS, "normalized": True, "rows": len(rows), "device": device,
            "text_format": "Subject: <subject>\\nBody: <body>, URLs -> token_url",
            "truncated_rows": int(sum(l > MAX_TOKENS for l in lengths)),
            "median_tokens": int(np.median(lengths)), "embed_seconds": round(secs, 1)}
    np.savez_compressed(out / "vectors.npz", ids=ids, embeddings=vecs, meta=json.dumps(meta))

    client = chromadb.PersistentClient(path=str(out / "chroma"))
    name = "svm_handoff_bge_m3"
    try:
        client.delete_collection(name)
    except Exception:
        pass
    col = client.create_collection(name, metadata={"hnsw:space": "cosine", **{k: str(v) for k, v in meta.items()}})
    keys = ["test_row", "source", "language", "url_count", "attachment_count", "has_attachments", "sender_domain"]
    for i in range(0, len(rows), 500):
        part = rows[i:i + 500]
        col.add(ids=[r["id"] for r in part], embeddings=vecs[i:i + 500].tolist(), documents=texts[i:i + 500],
                metadatas=[{**{k: str(r.get(k, "")) for k in keys},
                            "svm_decision_score": json.loads(r["svm_result"])["decision_score"]} for r in part])
    print("embed", meta, "chroma count", col.count(), flush=True)


def load_vectors(out, rows):
    with np.load(out / "vectors.npz") as z:
        ids, vecs, meta = z["ids"], z["embeddings"], json.loads(z["meta"].item())
    assert list(ids) == [r["id"] for r in rows], "vectors.npz does not match input order"
    return vecs, meta


# ------------------------------------------------------------------- cluster
def quotas(counts, n=SAMPLE_SIZE):
    whole, rem = np.divmod(n * counts, counts.sum())
    order = np.argsort(-rem, kind="stable")
    whole[order[: n - whole.sum()]] += 1
    return whole


def stage_cluster(rows, out):
    from scipy.cluster.hierarchy import linkage, cut_tree
    from sklearn.metrics import silhouette_score

    vecs, _ = load_vectors(out, rows)
    rng = np.random.default_rng(SEED)
    ev = np.sort(rng.choice(len(vecs), min(3000, len(vecs)), replace=False))
    trees = {"ward": linkage(vecs, method="ward", metric="euclidean"),
             "average_cosine": linkage(vecs, method="average", metric="cosine")}
    levels = sorted(set(FINE_LEVELS + PARENT_LEVELS))
    diag = []
    cuts = {}
    for name, tree in trees.items():
        np.save(out / f"linkage_{name}.npy", tree)
        cuts[name] = cut_tree(tree, n_clusters=levels)
        for j, k in enumerate(levels):
            g = cuts[name][:, j]
            c = np.bincount(g)
            diag.append({"linkage": name, "clusters": k,
                         "silhouette_cosine": float(silhouette_score(vecs[ev], g[ev], metric="cosine")),
                         "largest_share": float(c.max() / len(g)), "smallest": int(c.min()),
                         "clusters_under_10_rows": int((c < 10).sum()),
                         "clusters_getting_sample": int(np.count_nonzero(quotas(c)))})
    # Rule: a usable cut has no cluster over 25% of emails and every cluster
    # receives at least one sampled row; among those pick the best silhouette.
    def ok(d): return d["largest_share"] <= .25 and d["clusters_getting_sample"] == d["clusters"]
    fine_c = [d for d in diag if d["clusters"] in FINE_LEVELS and ok(d)] or [d for d in diag if d["clusters"] in FINE_LEVELS]
    fine = max(fine_c, key=lambda d: d["silhouette_cosine"])
    par_c = [d for d in diag if d["linkage"] == fine["linkage"] and d["clusters"] in PARENT_LEVELS]
    parent = max(par_c, key=lambda d: d["silhouette_cosine"])
    name = fine["linkage"]
    child = cuts[name][:, levels.index(fine["clusters"])]
    par = cuts[name][:, levels.index(parent["clusters"])]
    # Renumber: parents by size, children by (parent, size) -> stable readable ids.
    p_order = np.argsort(-np.bincount(par), kind="stable")
    p_map = {old: new + 1 for new, old in enumerate(p_order)}
    par_id = np.array([p_map[x] for x in par])
    c_keys = sorted(set(child), key=lambda c: (par_id[child == c][0], -(child == c).sum()))
    c_map = {old: new + 1 for new, old in enumerate(c_keys)}
    child_id = np.array([c_map[x] for x in child])
    for c in set(child_id):  # nesting check
        assert len(set(par_id[child_id == c])) == 1
    np.savez(out / "assignment.npz", parent=par_id, cluster=child_id)
    sel = {"linkage": name, "fine": fine, "parent": parent,
           "rule": "fine level: largest cluster <=25% and every cluster gets >=1 of 700 samples, max cosine silhouette; parent level: max silhouette on same tree",
           "silhouette_rows": len(ev)}
    (out / "diagnostics.json").write_text(json.dumps({"selected": sel, "candidates": diag}, indent=2))
    print("cluster", json.dumps(sel), flush=True)


# ------------------------------------------------------------------- profile
def clean_for_terms(t):
    t = URL.sub(" ", t.lower())
    t = re.sub(r"token_[a-z_]+", " ", t)
    return re.sub(r"[^a-z฀-๿ ]+", " ", t)


def ollama_label(terms, examples, model):
    prompt = ("You are analysing a cluster of phishing/spam emails. Based on the keywords and example emails, "
              "reply with JSON only: {\"label\": \"<3-6 word name of the lure/theme>\", "
              "\"description\": \"<one sentence: what these emails ask the victim to do or believe>\"}.\n\n"
              f"Keywords: {', '.join(terms)}\n\nExamples:\n" + "\n---\n".join(examples))
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "format": "json",
         "options": {"temperature": 0, "seed": SEED, "num_ctx": 8192}}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        ans = json.loads(json.loads(r.read())["response"])
    return str(ans.get("label", "")).strip(), str(ans.get("description", "")).strip()


def stage_profile(rows, out, llm_model):
    from sklearn.feature_extraction.text import CountVectorizer

    vecs, _ = load_vectors(out, rows)
    with np.load(out / "assignment.npz") as z:
        par, cl = z["parent"], z["cluster"]
    docs = [clean_for_terms(r["subject"] + " " + r["body"]) for r in rows]
    cv = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=5, max_df=0.5,
                         token_pattern=r"(?u)\b[a-z฀-๿][a-z฀-๿]{2,}\b")
    X = cv.fit_transform(docs)
    terms = np.array(cv.get_feature_names_out())

    def ctfidf(groups):
        ks = sorted(set(groups))
        tf = np.vstack([np.asarray(X[groups == k].sum(axis=0)).ravel() for k in ks]).astype(float)
        tf = tf / tf.sum(axis=1, keepdims=True)
        avg = X.sum() / len(ks)
        idf = np.log(1 + avg / np.asarray(X.sum(axis=0)).ravel())
        sc = tf * idf
        return {k: terms[np.argsort(-sc[i])[:12]].tolist() for i, k in enumerate(ks)}

    kw_c, kw_p = ctfidf(cl), ctfidf(par)
    counts = np.bincount(cl)[1:]
    q = quotas(counts)
    score = np.array([json.loads(r["svm_result"])["decision_score"] for r in rows])
    clusters = []
    for k in range(1, cl.max() + 1):
        m = np.flatnonzero(cl == k)
        cen = vecs[m].mean(axis=0); cen /= np.linalg.norm(cen)
        sims = vecs[m] @ cen
        ex = m[np.argsort(-sims)[:5]]
        src, lang = {}, {}
        for i in m:
            src[rows[i]["source"]] = src.get(rows[i]["source"], 0) + 1
            lang[rows[i]["language"]] = lang.get(rows[i]["language"], 0) + 1
        clusters.append({
            "cluster_id": int(k), "parent_id": int(par[m[0]]), "emails": int(len(m)),
            "share": round(len(m) / len(rows), 4), "sample_quota": int(q[k - 1]),
            "keywords": kw_c[k], "cohesion_mean_cosine": round(float(sims.mean()), 3),
            "sources": dict(sorted(src.items(), key=lambda x: -x[1])),
            "languages": dict(sorted(lang.items(), key=lambda x: -x[1])[:5]),
            "with_url_share": round(float(np.mean([float(rows[i]["url_count"] or 0) > 0 for i in m])), 3),
            "with_attachment_share": round(float(np.mean([str(rows[i]["has_attachments"]).lower() in ("1", "true", "1.0") for i in m])), 3),
            "median_svm_score": round(float(np.median(score[m])), 3),
            "exemplars": [{"id": rows[i]["id"], "subject": rows[i]["subject"][:140],
                           "body_start": " ".join(rows[i]["body"].split())[:300]} for i in ex],
        })
    if llm_model:
        for c in clusters:
            exs = [f"Subject: {e['subject']}\nBody: {e['body_start']}" for e in c["exemplars"]]
            try:
                c["llm_label"], c["llm_description"] = ollama_label(c["keywords"][:10], exs, llm_model)
            except Exception as e:  # keep going without label
                c["llm_label"], c["llm_description"] = "", f"(label failed: {e})"
            print("label", c["cluster_id"], c["llm_label"], flush=True)
    parents = []
    for p in range(1, par.max() + 1):
        kids = [c for c in clusters if c["parent_id"] == p]
        parents.append({"parent_id": p, "emails": int(sum(c["emails"] for c in kids)),
                        "clusters": [c["cluster_id"] for c in kids], "keywords": kw_p[p]})
    if llm_model:
        for p in parents:
            kids = [c for c in clusters if c["parent_id"] == p["parent_id"]]
            exs = [f"Child theme: {c.get('llm_label', '')} - {c.get('llm_description', '')}" for c in kids]
            try:
                p["llm_label"], p["llm_description"] = ollama_label(p["keywords"][:10], exs, llm_model)
            except Exception as e:
                p["llm_label"], p["llm_description"] = "", f"(label failed: {e})"
    (out / "clusters.json").write_text(json.dumps({"llm_model": llm_model, "parents": parents,
                                                   "clusters": clusters}, indent=2, ensure_ascii=False))
    print("profile done", len(clusters), "clusters", flush=True)


# -------------------------------------------------------------------- sample
def stage_sample(rows, out):
    with np.load(out / "assignment.npz") as z:
        par, cl = z["parent"], z["cluster"]
    counts = np.bincount(cl)[1:]
    q = quotas(counts)
    rng = np.random.default_rng(SEED)
    chosen = set()
    for k, n in enumerate(q, start=1):
        chosen.update(rng.choice(np.flatnonzero(cl == k), n, replace=False).tolist())
    assert len(chosen) == SAMPLE_SIZE
    fields = list(rows[0].keys())
    def safe(v): return "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
    with open(out / "sample_700.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "parent_cluster_id", "cluster_id"] + [x for x in fields if x != "id"])
        for i in sorted(chosen):
            w.writerow([rows[i]["id"], par[i], cl[i]] + [safe(rows[i][x]) for x in fields if x != "id"])
    with open(out / "assignments.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "test_row", "parent_cluster_id", "cluster_id", "in_sample_700"])
        for i, r in enumerate(rows):
            w.writerow([r["id"], r["test_row"], par[i], cl[i], int(i in chosen)])
    print("sample", len(chosen), dict(zip(range(1, len(q) + 1), q.tolist())), flush=True)


# ----------------------------------------------------------------------- viz
def stage_viz(rows, out):
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    from scipy.cluster.hierarchy import linkage

    vecs, meta = load_vectors(out, rows)
    with np.load(out / "assignment.npz") as z:
        par, cl = z["parent"], z["cluster"]
    red = PCA(n_components=50, random_state=SEED).fit_transform(vecs)
    xy = TSNE(n_components=2, metric="cosine", init="pca", perplexity=40, random_state=SEED).fit_transform(red)
    xy = (xy - xy.min(0)) / (xy.max(0) - xy.min(0))
    sampled = set()
    with open(out / "assignments.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["in_sample_700"] == "1":
                sampled.add(r["id"])
    info = json.loads((out / "clusters.json").read_text())
    cents = np.vstack([vecs[cl == c["cluster_id"]].mean(0) for c in info["clusters"]])
    cents /= np.linalg.norm(cents, axis=1, keepdims=True)
    ctree = linkage(cents, method="average", metric="cosine").tolist()
    diag = json.loads((out / "diagnostics.json").read_text())
    points = [[round(float(a), 4), round(float(b), 4), int(c), int(p), int(r["id"] in sampled),
               r["subject"][:90]] for (a, b), c, p, r in zip(xy, cl, par, rows)]
    (out / "viz_data.json").write_text(json.dumps({"meta": meta, "diagnostics": diag, "clusters": info,
                                                   "centroid_tree": ctree, "points": points},
                                                  ensure_ascii=False))
    print("viz done", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", default="all", choices=["embed", "cluster", "profile", "sample", "viz", "all"])
    ap.add_argument("--llm", default="qwen2.5:7b", help="Ollama model for cluster labels; '' to skip")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = read_rows(a.input)
    for st in ["embed", "cluster", "profile", "sample", "viz"]:
        if a.stage in (st, "all"):
            if st == "embed" and a.stage == "all" and (out / "vectors.npz").exists():
                print("embed: reuse vectors.npz", flush=True); continue
            {"embed": lambda: stage_embed(rows, out), "cluster": lambda: stage_cluster(rows, out),
             "profile": lambda: stage_profile(rows, out, a.llm), "sample": lambda: stage_sample(rows, out),
             "viz": lambda: stage_viz(rows, out)}[st]()


if __name__ == "__main__":
    main()
