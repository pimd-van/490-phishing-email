"""Shared text preparation and metrics for the English benchmark."""

import hashlib
from pathlib import Path
import re

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

EXPECTED_MD5 = "aa8f59e96787cbd696c0b650e5400dc9"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def clean_text(value: object) -> str:
    s = "" if pd.isna(value) else str(value)
    s = re.sub(r"\[([A-Z][A-Z0-9_]{1,})\]", lambda m: " token_" + m.group(1).lower() + " ", s)
    return re.sub(r"\s+", " ", s.lower()).strip()


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": accuracy_score(y, pred),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "fnr": fn / (fn + tp) if fn + tp else 0.0,
    }


def predict_knn_in_blocks(model, X, block_rows=256):
    """Keep KNN's pairwise distance matrix bounded to at most 256 query rows."""
    outputs = []
    for start in range(0, X.shape[0], block_rows):
        neighbors = model.kneighbors(X[start:start + block_rows], return_distance=False)
        for row in neighbors:
            outputs.append(np.bincount(model._y[row].astype(int), minlength=2).argmax())
    return np.asarray(outputs, dtype=int)
