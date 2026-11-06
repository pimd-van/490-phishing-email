"""Build svm_clusters.html from viz_template.html + svm_bge_m3/viz_data.json (+ deep_tree.json)."""
import csv, json
from pathlib import Path

here = Path(__file__).resolve().parent
d = here / "svm_bge_m3"
v = json.loads((d / "viz_data.json").read_text(encoding="utf-8"))
deep = d / "deep_tree.json"
if deep.exists():
    t = json.loads(deep.read_text(encoding="utf-8"))
    with open(d / "assignments.csv", encoding="utf-8") as f:
        index = {r["id"]: i for i, r in enumerate(csv.DictReader(f))}
    for n in t["nodes"]:
        n["members"] = [index[x] for x in n["members"]]  # point indices, most typical first
    v["deep"] = t
data = json.dumps(v, ensure_ascii=False).replace("</", "<\\/")
page = (here / "viz_template.html").read_text(encoding="utf-8").replace("__DATA__", data)
(here / "svm_clusters.html").write_text(page, encoding="utf-8")
print("built", len(page) // 1024, "KB")
