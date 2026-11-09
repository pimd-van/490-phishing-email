# English-only MeAJOR rerun

The language field was matched exactly against `en`, `en;en`, and `en;en;en` before cleaning, deduplication, splitting, or training. These tags account for 82,175, 21,250, and 218 rows, respectively. The resulting 103,643 source rows yielded 99,693 unique cleaned subject/body pairs. The other 5,042 source rows were excluded by the language filter.

Source data are from Cardoso et al., MeAJOR v2.0, DOI `10.5281/zenodo.18471483`, CC BY 4.0. The cleaned CSV was saved on VM 490-18 as `major_cleaned_preprocessed.csv`. Its expected MD5 is `aa8f59e96787cbd696c0b650e5400dc9`. [MeAJOR v2.0 on Zenodo](https://zenodo.org/records/18471483)

## Benchmark and handoff

The benchmark reused the original text cleaning and seven model configurations. Each split was stratified by label using seed 42 and a 70/15/15 ratio, yielding 69,785 training, 14,954 validation, and 14,954 test rows. TF-IDF used up to 5,000 unigram and bigram features, sublinear term frequencies, and a vocabulary fit on the training split. Model selection used validation F1, with precision and recall as tie breakers. Test metrics were recorded separately.

Linear SVM placed first by validation F1 (0.973957) and scored 0.975190 F1 on test (6,171 true positives, 163 false positives, 151 false negatives, and 8,469 true negatives). The handoff contains all 6,334 test rows it predicted as phishing. The `source_row` is the zero-based data row of the official CSV, excluding the header. Handoff IDs use `meajor_en_v1_test_<source_row>`. The `test_row` is the row's zero-based position in the English-only test split.

The handoff includes cleaned subject and body, the SVM decision margin, and the original TF-IDF × coefficient contributions. The SHAP/LIME sidecar joins on `id`. SHAP uses the seed-42 sample of 200 training vectors and checks full-feature additivity for each row. The CSV lists the top terms present in each email. LIME fits a local surrogate to SVM margins using 500 text perturbations and a seed equal to 42 plus the source row.

## Clustering and labeling sample

BGE-M3 uses the historical input format built from the official CSV's raw subject and body. It collapses whitespace, replaces URLs with `token_url`, and formats the text as `Subject: …\nBody: …`. The model uses normalized float32 vectors and a maximum sequence length of 2,048 tokens.

The run reused 964 prior vectors after checking the prior handoff ID order and embedding metadata, then matching the complete formatted BGE input exactly. It encoded 5,370 new inputs with BGE-M3 on the Tesla T4. The provenance CSV maps each reused row to its prior ID. Both historical inputs are the same Git blobs recorded in the multilingual run.

Ward with Euclidean distance and average linkage with cosine distance were evaluated at each `k` from 2 through 60. Cosine silhouette used all 6,334 vectors at each cut. The selected cut maximized mean silhouette among cuts whose proportional 10% allocation put at least one sample row in every cluster. The selected cut was Ward at 60 clusters, with a mean silhouette of 0.096375 and cluster sizes from 18 to 385. The unrestricted maximum was average-cosine at two clusters (0.178714), where the cluster of five rows received a quota of zero.

Cluster IDs are integers assigned in descending cluster size. The sample has 633 rows, which is 10% rounded to the nearest integer. It assigns quotas of 2 to 38 rows per cluster by the largest remainder method, then spaces targets evenly from the highest to the lowest silhouette rank within each cluster. A one-row quota uses the 50th-percentile target. Equal silhouette values are ordered by handoff position.

## Files

| File | Contents |
|---|---|
| [Benchmark summary](benchmark/summary.json) and [split manifest](benchmark/split_manifest.csv) | Source checksum, exclusions, source rows and labels for each split, and test margins |
| [Validation metrics](benchmark/validation_metrics.csv) and [test metrics](benchmark/test_metrics.csv) | Accuracy, precision, recall, F1, and confusion matrices for all seven models |
| [SVM handoff](dataset/svm_handoff.csv) and [SHAP/LIME sidecar](xai/shap_lime_explanations.csv) | Predicted-phishing test rows, cleaned text, and margin explanations |
| [Embedding metadata](clustering/embedding_metadata.json) and [provenance](clustering/embedding_provenance.csv) | Model revision, source hashes, and exact matches to the prior cache |
| [Full silhouette results](clustering/silhouette_k02_k60.json), [assignments](clustering/assignments.csv), [Ward tree](clustering/linkage_ward.npy), and [average cosine tree](clustering/linkage_average_cosine.npy) | All 118 candidates, selected per-row silhouettes, and linkage matrices in handoff order |
| [RAG labeling sample](dataset/rag_label_sample_10pct.csv) and [cluster quotas](dataset/rag_sample_cluster_quotas.csv) | Rows selected for labeling and the proportional allocation |
| [Audit](audit.json) | Verification of the source filter, split, handoff and explanations, embedding provenance, and sample |

## Reproduce

The multilingual archive contains the exact historical inputs required to reproduce vector reuse. The same two files can be recovered from commit `40218e9` using their original paths `redo/dataset/svm_handoff.csv` and `redo/semantic_clustering/svm_bge_m3/vectors.npz`.

Run on Linux with Python 3.12 from the repository root. Install [requirements.txt](requirements.txt) in a benchmark environment. The embedding step can use a separate environment with those requirements, `sentence-transformers==5.7.0`, `transformers==5.19.0`, `huggingface-hub==2.2.0`, and PyTorch 2.8.0. The VM used the `2.8.0+cu128` build for CUDA. Use `--device cpu` if running without CUDA. A Git checkout with `core.autocrlf=false` preserves the prior handoff's original line endings for checksum verification.

```bash
source_csv=/path/to/major_cleaned_preprocessed.csv
scripts=redo/master/english_only/scripts
out=/path/to/new-english-only-run
prior_handoff=redo/delete_multilingual/dataset/svm_handoff.csv
prior_vectors=redo/delete_multilingual/semantic_clustering/svm_bge_m3/vectors.npz

export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python "$scripts/benchmark_english.py" --source "$source_csv" --out "$out"
python "$scripts/explain_english.py" --source "$source_csv" \
  --handoff "$out/dataset/svm_handoff.csv" \
  --output "$out/xai/shap_lime_explanations.csv" --jobs 12
python "$scripts/embed_english.py" --source "$source_csv" \
  --handoff "$out/dataset/svm_handoff.csv" \
  --prior-handoff "$prior_handoff" --prior-vectors "$prior_vectors" \
  --out "$out/clustering" --device cuda
python "$scripts/cluster_english.py" --out "$out" --jobs 8
python "$scripts/audit_english.py" --source "$source_csv" \
  --prior-handoff "$prior_handoff" --prior-vectors "$prior_vectors" --out "$out"
```

The generated `clustering/vectors.npz` is an intermediate cache. Clustering results and the sample are tracked here. CPU and GPU inference can differ at floating-point precision, which can affect very close distances.
