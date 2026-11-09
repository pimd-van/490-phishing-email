"""Retrieve the closest guidance chunks for each handoff email in data.csv."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from part2.vector_database.main_vector_database import load_settings, resolve_path

RAG_DIR = Path(__file__).resolve().parent
DATA_FILE = PROJECT_DIR / "part2" / "data.csv"
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

# These stable IDs identify the guidance passages that form the expected
# action-plan context. They are selected from the email scenario, independently
# of the chunks returned by Chroma, so retrieval quality can be compared.
NIST_ACTIONS = "a2"
NIST_INCIDENT_RESPONSE = "a3"
CISA_ATTACHMENTS = "d1"
CISA_ORGANIZATION_RESPONSE = "c2"
GOOGLE_SCAM_RESPONSE = "g1"

COMPROMISE_OR_FINANCIAL_PATTERN = re.compile(
    r"password|passcode|credential|log ?in|sign ?in|bank|account|payment|"
    r"transfer|credit card|financial|verification code|mfa|sensitive information|"
    r"social security|identity theft|personal information",
    re.IGNORECASE,
)
ATTACHMENT_PATTERN = re.compile(
    r"attachment|attached file|download|open the file|document|invoice|\.pdf\b|\.zip\b",
    re.IGNORECASE,
)
ORGANIZATION_PATTERN = re.compile(
    r"company|business|employee|workstation|network|administrator|\badmin\b|"
    r"organization|corporate|it department|malware",
    re.IGNORECASE,
)


def required_chunks(row: dict[str, str]) -> list[str]:
    """Choose expected action-plan guidance using the email's risk indicators."""
    email_text = "\n".join((row.get("subject") or "", row.get("body") or ""))
    required = [NIST_ACTIONS, GOOGLE_SCAM_RESPONSE]
    if COMPROMISE_OR_FINANCIAL_PATTERN.search(email_text):
        required.append(NIST_INCIDENT_RESPONSE)

    attachment_count = (row.get("attachment_count") or "").strip()
    has_attachments = (row.get("has_attachments") or "").strip().lower()
    if attachment_count.isdigit() and int(attachment_count) > 0:
        required.append(CISA_ATTACHMENTS)
    elif has_attachments in {"1", "true", "yes"} or ATTACHMENT_PATTERN.search(email_text):
        required.append(CISA_ATTACHMENTS)

    if ORGANIZATION_PATTERN.search(email_text):
        required.append(CISA_ORGANIZATION_RESPONSE)
    return list(dict.fromkeys(required))


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
                    "required_chunk": required_chunks(row),
                })
    return queries


def run_check() -> list[dict]:
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
        required_ids = query["required_chunk"]
        matched_required = set(required_ids).intersection(chunk_ids)
        score_percent = round(100.0 * len(matched_required) / len(required_ids), 2)
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

    chunks_by_query = {result["query_id"]: result["required_chunk"] for result in results}
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "chunk" not in fieldnames:
        fieldnames.append("chunk")
    temporary_data = DATA_FILE.with_suffix(".csv.tmp")
    with temporary_data.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row["chunk"] = json.dumps(chunks_by_query.get(row.get("id", ""), []), ensure_ascii=False)
            writer.writerow(row)
    temporary_data.replace(DATA_FILE)
    return results


def main() -> None:
    try:
        results = run_check()
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        raise SystemExit(f"Cannot check retrieval: {error}") from error
    print(json.dumps({
        "queries": len(results),
        "result_file": str(RESULT_FILE),
        "updated_data_file": str(DATA_FILE),
        "chunks_per_query": load_rag_settings()["top_k"],
    }, indent=2))


if __name__ == "__main__":
    main()
