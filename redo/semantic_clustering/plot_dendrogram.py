"""Render the 60-leaf dendrogram (colored by 8 parents, dashed cuts at 8 and 20) to PNG."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = Path(__file__).resolve().parent
T = json.loads((here / "svm_bge_m3" / "deep_tree.json").read_text(encoding="utf-8"))
M, S, LV, cuts = T["merges"], T["nodes"], T["levels"], T["cuts"]
root = len(M) - 1
cols = ["#2b6cb0", "#c53030", "#2f855a", "#6b46c1", "#c05621", "#0f8a8a", "#b83280", "#5a7d1a"]

order = []
def walk(n):
    for k in ("left", "right"):
        x = M[n][k]
        walk(x["merge"]) if "merge" in x else order.append(x["sub"])
walk(root)

y0 = cuts[str(LV[2])] * 0.9
pos = {}
def info(x):
    if "merge" in x:
        return pos[x["merge"]]
    s = S[x["sub"] - 1]
    return order.index(x["sub"]), y0, s["parent_id"]

fig, ax = plt.subplots(figsize=(22, 9), dpi=130)
post = []
def walk_post(n):
    for k in ("left", "right"):
        if "merge" in M[n][k]:
            walk_post(M[n][k]["merge"])
    post.append(n)
walk_post(root)
for i in post:
    m = M[i]
    (xa, ha, pa), (xb, hb, pb) = info(m["left"]), info(m["right"])
    p = pa if pa == pb else 0
    pos[i] = ((xa + xb) / 2, m["height"], p)
    ax.plot([xa, xa, xb, xb], [ha, m["height"], m["height"], hb],
            color=cols[(p - 1) % 8] if p else "#333333", lw=2.2 if p else 1.6, solid_joinstyle="round")
for L in LV[:2]:
    h = cuts[str(L)]
    ax.axhline(h, ls="--", color="#666", lw=1)
    ax.text(len(order) - .5, h + .15, f"cut: {L} clusters", ha="right", color="#444", fontsize=10)
labels = [f"S{k} {(S[k-1].get('llm_label') or '')[:28]} [C{S[k-1]['cluster_id']}] ({S[k-1]['emails']})" for k in order]
ax.set_xticks(range(len(order)))
ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
for t, k in zip(ax.get_xticklabels(), order):
    t.set_color(cols[(S[k-1]["parent_id"] - 1) % 8])
ax.set_xlim(-.6, len(order) - .4)
ax.set_ylim(y0, M[root]["height"] * 1.03)
ax.set_ylabel("Ward distance")
ax.set_title("6,995 SVM-flagged phishing emails — Ward tree cut at 8 / 20 / 60 clusters "
             "(leaves = 60 sub-clusters, color = parent cluster)", fontsize=12)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#e8e8e8"); ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(here / "svm_dendrogram_60.png")
print("saved")
