# SHAP and LIME for the Part 2 handoff

The Part 2 input CSVs are unchanged. SHAP and LIME explanations are stored in `xai/shap_lime_explanations.csv` and joined to `part2/part2_handoff.csv` by `id`:

| File and column | Method | Unit |
| --- | --- | --- |
| `part2/part2_handoff.csv` → `xai` | Original TF-IDF value × Logistic Regression coefficient | Log-odds contribution |
| `xai/shap_lime_explanations.csv` → `shap` | `shap.LinearExplainer` with an independent TF-IDF background | SHAP value in log-odds |
| `xai/shap_lime_explanations.csv` → `lime` | `lime.lime_text.LimeTextExplainer` with word removal | Local probability surrogate weight |

These three numbers have different baselines and should not be compared as though they share a scale. The positive class is phishing (`1`). `shap` lists the five strongest positive and negative **present TF-IDF features**. Its base value accounts for the entire background; only the displayed present features are shown, so the ten listed terms do not sum to the model output. The full SHAP vector plus `base_value_log_odds` does sum to `model_output_log_odds` (checked for each row). A fixed random sample of 200 training rows forms the SHAP background.

`lime` removes words from the full normalized subject + body text to create 500 perturbed versions per email. It fits a local linear model to the selected Logistic Regression model's phishing probability. `weight` is the local surrogate's coefficient, not a SHAP value or an exact change in probability. `surrogate_r2` reports local fit quality; low values mean the displayed LIME terms should be treated cautiously. The surrogate is linear, so `surrogate_estimate` can occasionally lie outside 0–1. A stable row-specific seed makes each explanation reproducible.

Across the 6,972 explanations, median LIME `surrogate_r2` is **0.4847** and 3,730 rows are below 0.5. These rows have weak local surrogate fit; filter or review them before using LIME as evidence in a report.

Method references: [SHAP LinearExplainer](https://shap.readthedocs.io/en/stable/generated/shap.LinearExplainer.html) and [LIME TextExplainer](https://lime-ml.readthedocs.io/en/latest/lime.html#lime.lime_text.LimeTextExplainer).

## Checked example

`meajor_test_56745` (`test_row=5139`, source label `1`) claims the recipient's internet banking profile was locked and asks them to follow `token_url` to unlock the account. The original handoff gives phishing probability **0.8061**. Both new methods rank the same five terms toward phishing: `account`, `your`, `security`, `internet`, and `reply`. Their values are on different scales:

| Term | SHAP log-odds | LIME local weight |
| --- | ---: | ---: |
| `account` | +0.8170 | +0.2277 |
| `your` | +0.5767 | +0.1839 |
| `security` | +0.3084 | +0.0686 |
| `internet` | +0.2755 | +0.0577 |
| `reply` | +0.2740 | +0.0520 |

LIME's local `surrogate_r2` is **0.7802** for this row. The account lock and unlock link make the email suspicious to a reader. The listed words show what the model relied on locally; they do not prove that the link itself was inspected or that any individual word causes phishing.

The training code for the original Part 1 run was not committed. `scripts/recompute_shap_lime.py` reconstructs its verified text-only split (70/15/15, seed 42), TF-IDF (5,000 unigram/bigram features, sublinear TF), and default `LogisticRegression()` from the official MeAJOR v2.0 CSV. The reconstructed model predicts phishing for exactly the same 6,972 test IDs as the original handoff. The script reads the historical handoff but does not edit it. One malformed historical row remains as it was; the separate XAI file still covers its ID using the source dataset. Small differences between old and reconstructed probabilities remain possible; see [the recheck](part1_text_only_recheck.md).

To reproduce the separate XAI file:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-xai.txt
.\.venv\Scripts\python scripts\recompute_shap_lime.py --source C:\path\to\meajor_cleaned_preprocessed.csv
```

The official CSV is from [MeAJOR v2.0](https://zenodo.org/records/18471483) and must have MD5 `aa8f59e96787cbd696c0b650e5400dc9`. The script writes a resumable checkpoint under ignored `results/`, then creates `xai/shap_lime_explanations.csv` with `id`, `test_row`, `subject`, `shap`, and `lime`. It checks the set of predicted-phishing IDs before writing. Neither Part 2 CSV is modified. Dependencies are in `requirements-xai.txt`.
