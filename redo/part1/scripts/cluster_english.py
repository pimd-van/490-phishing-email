"""Score Ward and average-cosine cuts, then select the covered 10% labeling sample."""

import argparse
import csv
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
import scipy
from scipy.cluster.hierarchy import cut_tree, linkage
import sklearn
from sklearn.metrics import silhouette_samples
from sklearn.metrics.pairwise import cosine_distances
from threadpoolctl import threadpool_limits

csv.field_size_limit(1 << 30)
LEVELS = list(range(2, 61))
METHODS = {"ward": ("ward", "euclidean"), "average_cosine": ("average", "cosine")}


def allocate(sizes, n):
    shares, remainders = np.divmod(n * sizes, sizes.sum())
    order = np.argsort(-remainders, kind="stable")
    shares[order[:n - shares.sum()]] += 1
    return shares


def calculate(key):
    # Fork shares the read-only full distance matrix among score workers.
    groups = _cuts[key]
    sizes = np.bincount(groups)
    if len(sizes) != key[1]:
        raise ValueError(f"Tree cut {key} produced {len(sizes)} clusters")
    quotas = allocate(sizes, _sample_size)
    scores = silhouette_samples(_distances, groups, metric="precomputed")
    return {
        "method": key[0], "k": key[1], "silhouette": float(scores.mean()),
        "largest_share": float(sizes.max() / sizes.sum()),
        "sizes": sizes.tolist(), "quotas": quotas.tolist(),
        "cluster_silhouette": (np.bincount(groups, weights=scores) / sizes).tolist(),
    }, scores


def write_rows(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_sample(out, rows, fields, groups, scores, selected):
    sample, summary = [], []
    cluster_ids = np.empty(len(rows), dtype=int)
    order = np.argsort(-np.array(selected["sizes"]), kind="stable")
    for cluster_id, group in enumerate(order, 1):
        members = np.flatnonzero(groups == group)
        cluster_ids[members] = cluster_id
        quota = selected["quotas"][group]
        ranked = members[np.argsort(-scores[members], kind="stable")]
        percentiles = np.linspace(100, 0, quota) if quota > 1 else np.array([50.0])
        ranks = np.floor((1 - percentiles / 100) * (len(members) - 1) + 0.5).astype(int)
        picked = ranked[ranks]
        if len(set(picked)) != quota:
            raise ValueError(f"Duplicate sample positions in cluster {cluster_id}")
        for pos, percentile in zip(picked, percentiles):
            sample.append({
                **rows[pos], "cluster_id": cluster_id, "silhouette_percentile": f"{percentile:.8f}",
                "silhouette": f"{scores[pos]:.8f}",
            })
        summary.append({
            "cluster_id": cluster_id, "total_rows": len(members), "sample_rows": quota,
            "mean_silhouette": f"{selected['cluster_silhouette'][group]:.8f}",
        })
    if len(sample) != _sample_size or len({row["id"] for row in sample}) != _sample_size:
        raise ValueError("Proportional sampling did not yield the expected unique rows")
    dataset = out / "dataset"
    write_rows(dataset / "rag_label_sample_10pct.csv",
               ["cluster_id", "silhouette_percentile", "silhouette", *fields], sample)
    write_rows(dataset / "rag_sample_cluster_quotas.csv", list(summary[0]), summary)
    write_rows(out / "clustering" / "assignments.csv", ["id", "cluster_id", "silhouette"], (
        {"id": row["id"], "cluster_id": group, "silhouette": float(score)}
        for row, group, score in zip(rows, cluster_ids, scores)
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Root containing dataset/ and clustering/")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    root = args.out / "clustering"
    with (args.out / "dataset" / "svm_handoff.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows, fields = list(reader), reader.fieldnames
    with np.load(root / "vectors.npz") as data:
        ids, vectors = data["ids"], data["embeddings"]
    if ids.tolist() != [row["id"] for row in rows] or len(set(ids)) != len(ids):
        raise ValueError("Embedding and handoff IDs/order differ")
    global _cuts, _distances, _sample_size
    _sample_size = (len(ids) + 5) // 10
    _cuts = {}
    for name, (method, metric) in METHODS.items():
        tree = linkage(vectors, method=method, metric=metric)
        np.save(root / f"linkage_{name}.npy", tree)
        labels = cut_tree(tree, n_clusters=LEVELS)
        for col, k in enumerate(LEVELS):
            _cuts[name, k] = labels[:, col].copy()
        print(f"Built {name} linkage", flush=True)
    with threadpool_limits(limits=args.jobs):
        _distances = cosine_distances(vectors)
    np.fill_diagonal(_distances, 0)
    _distances.setflags(write=False)
    keys = list(_cuts)
    with threadpool_limits(limits=1), mp.get_context("fork").Pool(args.jobs) as pool:
        results = dict(zip(keys, pool.map(calculate, keys)))
    ranked = sorted((item[0] for item in results.values()), key=lambda row: -row["silhouette"])
    covered = [row for row in ranked if min(row["quotas"]) > 0]
    balanced = [row for row in covered if row["largest_share"] <= 0.25]
    if not covered:
        raise ValueError("No candidate covers every cluster in the proportional sample")
    selected = covered[0]
    key = (selected["method"], selected["k"])
    write_sample(args.out, rows, fields, _cuts[key], results[key][1], selected)
    report = {
        "rows": len(ids), "sample_rows": _sample_size, "levels": LEVELS,
        "silhouette_metric": "cosine", "silhouette_evaluation_rows": len(ids),
        "selection_rule": "highest silhouette among cuts with a nonzero proportional quota in every cluster",
        "best_unrestricted": ranked[0], "best_every_cluster": selected,
        "best_balanced": balanced[0] if balanced else None,
        "results": ranked, "scipy_version": scipy.__version__, "sklearn_version": sklearn.__version__,
    }
    (root / "silhouette_k02_k60.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Selected {key[0]} at k={key[1]}, silhouette {selected['silhouette']:.8f}")
    print(f"Wrote {_sample_size} sample rows, quotas {selected['quotas']}")


if __name__ == "__main__":
    main()
