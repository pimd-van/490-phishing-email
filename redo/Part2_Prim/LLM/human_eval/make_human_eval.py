"""Make the blind human-scoring form for metrics M3 (faithfulness) and M4 (completeness, actionability, safety).

Run from the project root after main_LLM.py:
    python part2/LLM/human_eval/make_human_eval.py --n 50 --condition rag

Picks N emails from the evaluation set, stratified by gold fit (fixed seed), takes the answer of every model
for each, hides the model name, shuffles the order and writes:
  human_eval_form.csv   one row per answer, with the email, the guidance the model was given, the gold guidance
                        and empty score columns (give one copy to each rater)
  human_eval_key.csv    item -> model; keep it away from the raters until scoring is done
The rubric is in rubric_TH.md.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PROJECT_DIR = Path(__file__).resolve().parents[3]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
from part2.vector_database.main_vector_database import resolve_path, read_commented_json  # noqa: E402
from part2.LLM.evaluate_LLM import latest_records  # noqa: E402
from part2.LLM.main_LLM import load_chunks  # noqa: E402
from part2.RAG.main_RAG import email_text  # noqa: E402

HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE.parent / "config_LLM.json"
SEED = 20261102
SCORE_COLUMNS = ["faithfulness_supported_steps", "faithfulness_total_steps", "completeness_1to5",
                 "actionability_1to5", "safety_pass_1_or_0", "notes"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--condition", default="rag")
    p.add_argument("--prompt-version")
    a = p.parse_args()
    c = read_commented_json(CONFIG_FILE)
    pv = a.prompt_version or c["prompt_version"]
    recs = [r for r in latest_records(resolve_path(c["result_file"]), c["eval_set"])
            if r["condition"] == a.condition and r["prompt_version"] == pv and not r.get("error")]
    by_id = collections.defaultdict(dict)
    for r in recs:
        by_id[r["id"]][r["model"]] = r
    models = sorted({r["model"] for r in recs})
    complete = sorted(i for i, m in by_id.items() if len(m) == len(models))
    if len(complete) < a.n:
        raise SystemExit(f"only {len(complete)} emails have answers from all {len(models)} models")
    # stratified by gold fit, proportional
    rng = random.Random(SEED)
    strata = collections.defaultdict(list)
    for i in complete:
        strata[next(iter(by_id[i].values()))["gold_fit"]].append(i)
    picked = []
    for fit, ids in sorted(strata.items()):
        take = round(a.n * len(ids) / len(complete))
        picked += rng.sample(ids, min(take, len(ids)))
    picked = sorted(picked)[: a.n]

    emails = {}
    for line in open(resolve_path(c["input_file"]), encoding="utf-8"):
        rec = json.loads(line)
        if rec["id"] in picked:
            emails[rec["id"]] = rec
    chunks = load_chunks(c["vector_config"])
    items = []
    for i in picked:
        for m in models:
            r = by_id[i][m]
            pr = r.get("parsed") or {}
            steps = "\n".join(f"{n + 1}. {x['action']} [{x.get('chunk_id') or '-'}]" for n, x in enumerate(pr.get("actions") or []))
            answer = f"REASON: {pr.get('reason', '')}\nSTEPS:\n{steps}" if pr.get("format_ok") else f"(unreadable answer)\n{r.get('raw', '')[:1500]}"
            items.append({"email_id": i, "model": m, "answer": answer,
                          "given": "\n\n".join(f"[{x}] {chunks[x]['text']}" for x in r["given_chunk_ids"]),
                          "gold": "\n\n".join(f"[{x}] {chunks[x]['text']}" for x in r["gold_chunk_ids"] if x in chunks) or "(gold: no specific guidance fits; general steps expected)"})
    rng.shuffle(items)
    with open(HERE / "human_eval_form.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item", "email", "guidance_given_to_model", "gold_guidance", "answer"] + SCORE_COLUMNS)
        for n, it in enumerate(items, 1):
            w.writerow([f"H{n:03d}", email_text(emails[it["email_id"]], 3000, 3), it["given"], it["gold"], it["answer"]] + [""] * len(SCORE_COLUMNS))
    with open(HERE / "human_eval_key.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["item", "email_id", "model", "condition", "prompt_version"])
        for n, it in enumerate(items, 1):
            w.writerow([f"H{n:03d}", it["email_id"], it["model"], a.condition, pv])
    print(f"{len(items)} answers ({len(picked)} emails x {len(models)} models) -> human_eval_form.csv; key in human_eval_key.csv")


if __name__ == "__main__":
    main()
