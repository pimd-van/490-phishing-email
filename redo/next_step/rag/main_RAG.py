"""Retrieve the closest guidance chunks for the English labeling sample."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from vector_database.main_vector_database import SOURCES_FILE, load_settings, resolve_path

RAG_DIR = Path(__file__).resolve().parent
DATA_FILE = PROJECT_DIR.parent / "dataset" / "sample_10per.csv"
RESULT_FILE = RAG_DIR / "result_RAG.json"
CONFIG_FILE = RAG_DIR / "config_RAG.json"


def load_rag_settings() -> dict:
    lines = CONFIG_FILE.read_text(encoding="utf-8").splitlines()
    settings = json.loads("\n".join(line for line in lines if not line.lstrip().startswith("//")))
    if not isinstance(settings.get("action_plan_query"), str) or not settings["action_plan_query"].strip():
        raise ValueError("action_plan_query must be non-empty text")
    for key in ("top_k", "max_email_chars"):
        minimum = 1 if key == "top_k" else 0
        if not isinstance(settings.get(key), int) or settings[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")
    return settings

def load_labels(path: Path) -> dict[str, list[str]]:
    """Read final labels by email ID and validate them against the indexed catalog."""
    catalog = {row["chunk_id"] for row in json.loads(SOURCES_FILE.read_text(encoding="utf-8"))}
    catalog.discard("GEN-02")
    labels = {}
    with path.open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"Expected a JSON object on label line {line_number}")
            email_id, chunks = record.get("id"), record.get("chunk_ids")
            if not isinstance(email_id, str) or not email_id.strip() or email_id in labels:
                raise ValueError(f"Missing or duplicate id on label line {line_number}")
            if (not isinstance(chunks, list) or any(not isinstance(chunk, str) or chunk not in catalog
                    for chunk in chunks) or len(chunks) != len(set(chunks)) or len(chunks) > 5):
                raise ValueError(f"Invalid chunk_ids on label line {line_number}")
            labels[email_id] = chunks
    if not labels:
        raise ValueError(f"No labels in {path}")
    return labels


def load_queries(rag_settings: dict) -> list[dict[str, str]]:
    queries = []
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            query_id = (row.get("id") or "").strip()
            subject = (row.get("subject") or "").strip()
            body = (row.get("body") or "").strip()
            email_text = "\n\n".join(part for part in (subject, body) if part)
            if rag_settings["max_email_chars"]:
                email_text = email_text[:rag_settings["max_email_chars"]]
            query = f"{rag_settings['action_plan_query']}{email_text}" if email_text else ""
            if query_id and query:
                queries.append({
                    "query_id": query_id,
                    "input": query,
                })
    return queries


def run_check(labels: dict[str, list[str]]) -> list[dict]:
    settings = load_settings()
    rag_settings = load_rag_settings()
    database_dir = resolve_path(settings["database_dir"])
    client = chromadb.PersistentClient(path=str(database_dir))
    collection = client.get_collection(settings["collection_name"])
    if collection.metadata.get("embedding_model") != settings["embedding_model"]:
        raise ValueError("The Chroma collection uses a different embedding model; rebuild it first")
    if collection.count() == 0:
        raise ValueError("The Chroma collection is empty; build it first")

    queries = load_queries(rag_settings)
    if not queries:
        raise ValueError(f"No usable input rows found in {DATA_FILE}")

    unknown_ids = labels.keys() - {query["query_id"] for query in queries}
    if unknown_ids:
        raise ValueError(f"Label IDs absent from the sample: {', '.join(sorted(unknown_ids)[:5])}")

    model = SentenceTransformer(settings["embedding_model"])
    query_texts = [f"{settings.get('query_prefix', '')}{query['input']}" for query in queries]
    vectors = model.encode(
        query_texts,
        batch_size=settings["embedding_batch_size"],
        normalize_embeddings=True,
    ).tolist()

    results = []
    top_k = min(rag_settings["top_k"], collection.count())
    for query, query_text, vector in zip(queries, query_texts, vectors):
        retrieved = collection.query(
            query_embeddings=[vector],
            n_results=top_k,
        )
        chunk_ids = retrieved["ids"][0]
        required_ids = labels.get(query["query_id"])
        score_percent = (
            round(100.0 * len(set(required_ids).intersection(chunk_ids)) / len(required_ids), 2)
            if required_ids else None
        )
        results.append({
            "query_id": query["query_id"],
            "input": query_text,
            "required_chunk": required_ids,
            "score_chunk": score_percent,
            "top_retrieved_chunk": chunk_ids,
        })

    temporary_result = RESULT_FILE.with_suffix(".json.tmp")
    temporary_result.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_result.replace(RESULT_FILE)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, help="Final labels as JSONL with id and chunk_ids")
    args = parser.parse_args()
    try:
        results = run_check(load_labels(args.labels) if args.labels else {})
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        raise SystemExit(f"Cannot check retrieval: {error}") from error
    print(json.dumps({
        "queries": len(results),
        "result_file": str(RESULT_FILE),
        "labeled_queries": sum(row["required_chunk"] is not None for row in results),
        "chunks_per_query": load_rag_settings()["top_k"],
    }, indent=2))


if __name__ == "__main__":
    main()
