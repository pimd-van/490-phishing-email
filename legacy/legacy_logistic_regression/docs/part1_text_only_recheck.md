# Part 1 text-only model recheck (2026-11-04)

This is a post hoc alternative comparison on the MeAJOR v2.0 text-only input. The original Part 1 training code and model settings were not committed, so these results should not replace the historical results in the main README.

## Method

- Source: [MeAJOR v2.0](https://zenodo.org/records/18471483), `meajor_cleaned_preprocessed.csv` (MD5 `aa8f59e96787cbd696c0b650e5400dc9`); label `0` is benign and `1` is phishing.
- Keep binary labels. Replace uppercase bracket placeholders of at least two characters (for example `[NAME]`) with spaced `token_name` *before* lowercasing. Collapse whitespace, discard empty text, and keep the first copy of each normalized subject + body pair. This leaves 104,515 rows.
- Stratified train/validation/test split: 70/15/15 with seed 42 (73,160 / 15,677 / 15,678 rows). Fit TF-IDF on train only: 5,000 features, unigrams and bigrams, `sublinear_tf=True`.
- No per-model hyperparameter tuning in this recheck. Models: `MultinomialNB()`, `LogisticRegression()`, `DecisionTreeClassifier(random_state=42)`, and `XGBClassifier(n_estimators=100, random_state=42, n_jobs=-1, tree_method="hist", eval_metric="logloss")`. Run with scikit-learn 1.6.1 and XGBoost 3.4.1.

## Validation results: text only

| Model | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Naive Bayes | 0.9522 | 0.9599 | 0.9316 | 0.9455 |
| **Logistic Regression** | **0.9772** | 0.9745 | 0.9742 | **0.9744** |
| Decision Tree | 0.9319 | 0.9181 | 0.9303 | 0.9242 |
| XGBoost | 0.9718 | 0.9699 | 0.9668 | 0.9683 |

Logistic Regression was highest by validation F1 **among these four models**. On the held-out test set it scored accuracy 0.9757, precision 0.9740, recall 0.9714, and F1 0.9727. Its predicted-phishing set matched all 6,972 IDs in `legacy/legacy_logistic_regression/part2/part2_handoff.csv`. Among 6,971 parseable handoff rows, 6,940 phishing probabilities matched at two decimal places; all ten listed XAI term contributions and their term names matched at two decimals on 6,277 rows. One handoff CSV row has a truncated body and unparseable probability/XAI fields.

Decision Tree replaced Random Forest in this four-model table after observing Random Forest's higher score. For transparency, additional text-only checks gave Random Forest with default unlimited depth F1 **0.9761** and Linear SVM F1 **0.9763**. The original README reports Random Forest F1 **0.9505**, but its uncommitted settings cannot be verified. A diagnostic Random Forest run with `max_depth=20` gave F1 **0.9504**; this does not establish that the original run used that setting. Logistic Regression should therefore be described as best in the four-model table above and as the model used for the XAI/Part 2 handoff, not as best among every model tested.
