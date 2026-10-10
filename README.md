# MeAJOR phishing detection + local XAI (Part 1)

This project implements Part 1 of the [project specification](https://docs.google.com/document/d/15kVxt9aNmvQ114YDVgkt_Ednd2EB_I83po7deYI8ywM/edit). It compares four classifiers across text, text+URL, text+attachment, and text+URL+attachment inputs. The separate local LLM classification benchmark is not the Part 2 RAG explanation pipeline.

`part1/data.py`, `features.py`, `models.py`, `metrics.py`, and `xai.py` contain the Part 1 stages. `part1/pipeline.py` runs them and saves the selected model and results. `part1/inference.py` exposes single-email prediction and explanation functions. `part1/handoff.py` packages predicted phishing emails for Part 2; its per-row evidence is Logistic Regression TF-IDF contribution, not SHAP/LIME. `part1/external.py` evaluates the frozen model on E-PhishLLM. The separate local LLM classifier benchmark lives in `experiments/`. `run.py` remains a short compatible entry point. The old output archive remains at `results/archive_20260919/`; only the files directly under `results/` are the current run.

## Run on Windows

```powershell
cd C:\Users\pimde\Desktop\pimdej\490\xai_phishing
py -3.10 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

Or call Part 1 from Python after training:

```python
from part1.pipeline import run_experiment
from part1.inference import predict_email, explain_email
from part1.handoff import prepare_handoff

run_experiment(skip_download=True)
prediction = predict_email("Account notice", "Please review your account")
explanation = explain_email("Account notice", "Please review your account")
handoff = prepare_handoff()
```

`predict_email` returns the binary prediction and phishing probability. `explain_email` returns the real SHAP/LIME schema used in `results/local_explanations.json`. These two functions currently require the selected text-only model. They do not assign phishing indicator categories or SHAP/LIME agreement labels.

`run.py` downloads the [official MeAJOR v2.0 CSV](https://zenodo.org/records/18471483) to `data/`, verifies its published MD5, and then runs the full experiment. If it is already present, the script verifies it and reuses it. The CSV, models, and results are ignored by Git. The original data is licensed CC BY 4.0; cite Cardoso et al. and DOI `10.5281/zenodo.18471483` if you publish results.

## Method

1. Keep binary labels, normalize subject/body to lowercase, turn `[NAME]` into `token_name`, remove empty messages and duplicate normalized subject+body text.
2. Make one stratified 70/15/15 train/validation/test split with seed 42. Fit TF-IDF, numeric scaling, and attachment type encoding only on training rows.
3. Use up to 5,000 TF-IDF unigram/bigram features. Add the dataset's five numeric URL features and/or attachment count, flag, and type according to each feature set.
4. Train XGBoost, Logistic Regression, Multinomial Naive Bayes, and Random Forest on each feature set. Select by validation F1, then evaluate the selected model once on test.
5. Explain the first three predicted phishing test rows with LIME and SHAP. SHAP uses up to 20 present inputs for each row (ranked by linear contribution for Logistic Regression, otherwise by input magnitude) and holds all other inputs fixed; its baseline is the probability with those selected inputs set to zero. The contribution values are local and do not describe global model importance.

## Outputs

- `results/validation_metrics.csv`: 16 model/feature combinations, including confusion counts and FP/FN rates.
- `results/test_metrics.json`: selected model and held-out test scores.
- `results/test_predictions.csv`: one row per test email, with its cleaned-data row index and phishing probability.
- `results/local_explanations.json`: SHAP and LIME feature contributions for three predicted phishing emails. `test_row` is the zero-based position in `test_predictions.csv`.
- `results/best_model.joblib`: selected model, TF-IDF vectorizer, encoders, and feature names.

The split is random within labels, so the test estimates performance on this corpus mixture. It is not a test of transfer to an unseen source or a different year. The MeAJOR phishing label also reflects the source corpus labeling; inspect source composition before interpreting results as real-world precision.

## MeAJOR v2.0 results (seed 42)

Validation F1 for every model and feature set:

| Features | XGBoost | Logistic Regression | Naive Bayes | Random Forest |
|---|---:|---:|---:|---:|
| Text | 0.9396 | **0.9744** | 0.9455 | 0.9505 |
| Text + URL | 0.9563 | 0.9739 | 0.9450 | 0.9546 |
| Text + attachment | 0.9403 | 0.9735 | 0.9465 | 0.9512 |
| Text + URL + attachment | 0.9564 | 0.9734 | 0.9461 | 0.9590 |

The selected text-only Logistic Regression model scored **0.9727 F1**, 0.9757 accuracy, 0.9740 precision, and 0.9714 recall on the held-out test set (15,678 rows). Its FP rate was 0.0208 and FN rate was 0.0286. After cleaning, 104,515 of 108,685 source rows remained. The explanation examples are in `results/local_explanations.json`; one predicted phishing row had positive SHAP contributions from terms such as `your`, `account`, and `transfer`.

## External evaluation

To test the frozen selected model on a separate source, run:

```powershell
.\.venv\Scripts\python -m part1.external
```

The default input is `../tmp/e-phishGen-repo/ephishLLM.json`, from the [official E-PhishGen repository](https://github.com/pajola/e-phishGen). Pass `--input PATH` if the file is elsewhere. The script evaluates English records only, uses the existing vectorizer/model and 0.5 threshold, removes exact normalized matches with MeAJOR, and writes `results/external_ephishllm_en_metrics.json` plus row-level predictions. It does not fit or tune anything on the external set. E-PhishLLM is synthetic, so its score measures transfer to a different generation process, not performance on live inbox traffic.

| Test set | Rows | Accuracy | Precision | Recall | F1 | FP rate | FN rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| MeAJOR held-out | 15,678 | 0.9757 | 0.9740 | 0.9714 | 0.9727 | 0.0208 | 0.0286 |
| E-PhishLLM English | 11,502 | 0.6561 | 0.7047 | 0.5856 | 0.6396 | 0.2672 | 0.4144 |

There were zero exact normalized text matches between E-PhishLLM English and MeAJOR. This large score drop shows that the original random-split score does not transfer to this external synthetic benchmark. The E-PhishLLM data has 5,996 phishing and 5,506 legitimate records; 2,485 phishing emails were missed and 1,471 legitimate emails were flagged.

## Part 2 handoff (MeAJOR test only)

After running `run.py`, prepare the records to send to Part 2:

```powershell
.\.venv\Scripts\python -m part1.handoff
```

`results/part2_handoff.jsonl` contains one JSON object per MeAJOR test email **predicted** as phishing (6,972 records). Each has a stable `id`, zero-based `test_row`, normalized `subject` and `body`, `prediction`, `probability_phishing`, and positive/negative text terms. The term values are each TF-IDF value multiplied by its Logistic Regression coefficient; their unit is **log-odds**, not probability. The full log-odds equals `intercept_log_odds` plus contributions from *all* present terms. The JSON lists only the five strongest terms in each direction, so the displayed values alone need not sum to the prediction.

`part2/part2_handoff.csv` has the same handoff rows for a CSV-based Part 2 workflow. It retains the cleaned source columns (except the true `label`), with normalized `subject` and `body`, plus `id`, `test_row`, `phishing_result` (JSON), `xai` (JSON), and an initially empty `output` column for the Part 2 JSON response. The `xai` value is the per-row Logistic Regression contribution object described above; it is not SHAP/LIME. Parse `phishing_result` and `xai` as JSON when reading the CSV, and serialize the Part 2 response as JSON into `output`. Match rows by `id`. The `part2/` folder contains only this CSV; Part 2 implementation has not yet been added.

`results/part2_ground_truth.csv` stores the same IDs with the true labels and TP/FP outcome for later evaluation. Keep this file out of the Part 2 generation input. The three detailed SHAP/LIME examples remain in `results/local_explanations.json`; the explanations for every handoff row are direct Logistic Regression contributions, not SHAP or LIME. No E-PhishLLM records enter these files.

The Part 2 vector database is in `part2/vector_database/`, with guidance files in `document/` and settings in `config_vector_database.json`. Run `.venv/bin/python part2/vector_database/main_vector_database.py` to build the Chroma collection under `part2/RAG/.chroma/`. `result_vector_database.json` then lists every chunk with `chunk_id`, token count, and full content. Short chunk IDs combine the unique a-z `letter` assigned to each document in `sources.json` with its one-based chunk number (for example, `a2`). `part2/data.csv` contains 100 copied handoff rows. Run `.venv/bin/python part2/RAG/main_RAG.py` to create a scenario-based `required_chunk` list for each email and retrieve the closest chunks. `part2/RAG/config_RAG.json` controls the query text, top-k, and optional email-length limit. `part2/RAG/result_RAG.json` stores the query input, required chunks, `score_chunk` coverage percentage, and the retrieved IDs. The CSV `chunk` column contains only the required chunk IDs. The full Part 1 handoff remains at `part2/part2_handoff.csv`.

To generate action plans, start Ollama with the four models fixed in `part2/LLM/main_LLM.py`, then run `.venv/bin/python part2/LLM/main_LLM.py`. It sends each email and its retrieved guidance to all four models using one prompt and one set of generation settings. In the vector database, RAG, and LLM config files, each setting occupies one line with a preceding `//` comment stating its allowed values and the effect of changing it. The programs accept full-line comments in these files, which are not strict JSON. Use `--prompt "..."` for a one-run prompt override, or `--limit N` for a smaller run. `part2/LLM/result_LLM.json` contains each email's `id`, `subject`, `body`, and `model1` through `model4` action plans. The file is updated after each response, so an interrupted run can leave incomplete rows.

## Local LLM classification benchmark

`experiments/evaluate_local_llms.py` evaluates the four Part 2 instruction models as a separate
zero-shot binary classifier experiment. It uses the complete 15,678-row held-out
MeAJOR test split used by the Part 1 ML evaluation, a deterministic prompt, and stores row-level outputs,
latency, model revisions, and aggregate metrics under `results/llm_classification/`.
The main comparison uses Q5_K_M; the Phi-3 ablation compares FP16, Q8_0, Q6_K,
Q5_K_M, and Q4_K_M on exactly the same records.

```powershell
.\.venv\Scripts\python -m experiments.evaluate_local_llms --suite all --server C:\path\to\llama-server.exe
```
