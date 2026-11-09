"""Reuse exact BGE-M3 inputs from the prior run and embed the remaining English rows."""

import argparse
import csv
import json
import os
from pathlib import Path
import re
import time

import numpy as np
import pandas as pd

from benchmark_english import EXPECTED_MD5, LANGUAGE_TAGS, md5sum, sha256

MODEL = "BAAI/bge-m3"
MAX_TOKENS = 2048
URL = re.compile(r"https?://[^\s<>\"]+", re.I)
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

MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
TEXT_FORMAT = "Subject: <subject>\\nBody: <body>, URLs -> token_url"


def load_legacy(handoff, cache):
    rows = read_rows(handoff)
    with np.load(cache) as data:
        vectors = data["embeddings"]
        meta = json.loads(data["meta"].item())
        ids = data["ids"].tolist()
    if ids != [row["id"] for row in rows] or vectors.shape != (len(rows), 1024):
        raise ValueError("Prior embeddings and prior handoff IDs/order differ")
    required = {
        "model": MODEL, "max_seq_length": MAX_TOKENS, "normalized": True,
        "device": "cpu", "text_format": TEXT_FORMAT, "rows": len(rows),
    }
    if any(meta.get(key) != value for key, value in required.items()):
        raise ValueError(f"Incompatible prior embedding metadata: {meta}")
    if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5):
        raise ValueError("Prior embeddings are not finite unit vectors")
    matching = {}
    for row, vector in zip(rows, vectors):
        matching.setdefault(email_text(row), (row["id"], vector))
    return matching


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--prior-handoff", type=Path, required=True)
    parser.add_argument("--prior-vectors", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cuda", choices=("cpu", "cuda"))
    parser.add_argument("--batch-size", default=8, type=int)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    t0 = time.perf_counter()
    if md5sum(args.source) != EXPECTED_MD5:
        raise ValueError("Source CSV does not match the official MeAJOR MD5")
    rows = read_rows(args.handoff)
    raw = pd.read_csv(args.source, usecols=["subject", "body", "language"], low_memory=False)
    source_rows = raw.iloc[[int(row["source_row"]) for row in rows]].fillna("").to_dict("records")
    for row, source_row in zip(rows, source_rows):
        if source_row["language"] not in LANGUAGE_TAGS or row["language"] != source_row["language"]:
            raise ValueError(f"Source language mismatch for {row['id']}")
    texts = [email_text(row) for row in source_rows]
    legacy = load_legacy(args.prior_handoff, args.prior_vectors)
    vectors = np.empty((len(rows), 1024), dtype=np.float32)
    missing = []
    provenance = []
    for i, text in enumerate(texts):
        previous = legacy.get(text)
        if previous is None:
            missing.append(i)
            provenance.append((rows[i]["id"], "new", ""))
        else:
            old_id, vectors[i] = previous
            provenance.append((rows[i]["id"], "reused", old_id))
    print(f"Exact BGE matches: {len(rows) - len(missing)}. To encode: {len(missing)}.", flush=True)

    import torch
    import sentence_transformers
    from sentence_transformers import SentenceTransformer

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA PyTorch cannot see a GPU")
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    model = SentenceTransformer(
        MODEL, revision=MODEL_REVISION, device=args.device,
        model_kwargs={"torch_dtype": torch.float32},
    )
    model.max_seq_length = MAX_TOKENS
    lengths = np.array([
        len(tokens) for tokens in model.tokenizer(texts, add_special_tokens=True, truncation=False)["input_ids"]
    ])
    # The longest emails dominate padding and peak attention memory. Keep like lengths together.
    batch_size = args.batch_size
    for start in range(0, len(missing), 256):
        indexes = sorted(missing[start:start + 256], key=lambda i: lengths[i])
        while True:
            try:
                vectors[indexes] = model.encode(
                    [texts[i] for i in indexes], batch_size=batch_size, normalize_embeddings=True,
                    convert_to_numpy=True, show_progress_bar=False,
                ).astype(np.float32)
                break
            except torch.cuda.OutOfMemoryError:
                if batch_size == 1:
                    raise
                batch_size = max(1, batch_size // 2)
            torch.cuda.empty_cache()
            print(f"Retrying batch at size {batch_size}", flush=True)
        print(f"Encoded {start + len(indexes)}/{len(missing)}", flush=True)
    if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5):
        raise ValueError("Embeddings are not finite unit vectors")

    args.out.mkdir(parents=True, exist_ok=True)
    meta = {
        "model": MODEL, "new_model_revision": MODEL_REVISION, "max_seq_length": MAX_TOKENS,
        "normalized": True, "dtype": "float32", "new_device": args.device,
        "torch_version": str(torch.__version__), "sentence_transformers_version": sentence_transformers.__version__,
        "text_format": TEXT_FORMAT, "text_source": "official MeAJOR raw subject and body, as in the prior run",
        "rows": len(rows), "reused_rows": len(rows) - len(missing), "new_rows": len(missing),
        "prior_handoff_sha256": sha256(args.prior_handoff), "prior_vectors_sha256": sha256(args.prior_vectors),
        "handoff_sha256": sha256(args.handoff),
        "truncated_rows": int(np.count_nonzero(lengths > MAX_TOKENS)),
        "median_tokens": float(np.median(lengths)),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    ids = np.array([row["id"] for row in rows])
    temp = args.out / "vectors.tmp.npz"
    np.savez_compressed(temp, ids=ids, embeddings=vectors, meta=json.dumps(meta))
    (args.out / "embedding_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    with (args.out / "embedding_provenance.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("id", "embedding_origin", "prior_id"))
        writer.writerows(provenance)
    temp.replace(args.out / "vectors.npz")


if __name__ == "__main__":
    main()
