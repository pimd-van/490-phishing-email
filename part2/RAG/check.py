"""Retrieve the closest guidance chunk for each handoff email in data.csv."""

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

from part2.vector_database.main import load_settings, resolve_path

RAG_DIR = Path(__file__).resolve().parent
DATA_FILE = PROJECT_DIR / "part2" / "data.csv"
RESULT_FILE = RAG_DIR / "result.json"

ACTION_PLAN_QUERY = (
    "Based on this suspicious phishing email, what should the recipient do next? "
    "Find practical guidance to avoid interacting with the message, verify the sender, "
    "handle suspicious links and attachments, report the message, and respond if they "
    "clicked a link, opened an attachment, or shared credentials. Email:\n\n"
)

# These stable IDs identify the guidance passages that form the expected
# action-plan context. They are selected from the email scenario, independently
# of the chunks returned by Chroma, so retrieval quality can be compared.
NIST_ACTIONS = "c5d5497a95bffd73:0001"
NIST_INCIDENT_RESPONSE = "c5d5497a95bffd73:0002"
CISA_ATTACHMENTS = "6ff07056ee35f708:0000"
CISA_ORGANIZATION_RESPONSE = "79e1cb0105dec19f:0001"
GOOGLE_SCAM_RESPONSE = "f7bdef8f0eceacab:0000"

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


def load_queries() -> list[dict[str, str]]:
    queries = []
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            query_id = (row.get("id") or "").strip()
            subject = (row.get("subject") or "").strip()
            body = (row.get("body") or "").strip()
            email_text = "\n\n".join(part for part in (subject, body) if part)
            query = f"{ACTION_PLAN_QUERY}{email_text}" if email_text else ""
            if query_id and query:
                queries.append({
                    "query_id": query_id,
                    "input": query,
                    "required_chunk": required_chunks(row),
                })
    return queries


def run_check() -> list[dict]:
    settings = load_settings()
    database_dir = resolve_path(settings["database_dir"])
    client = chromadb.PersistentClient(path=str(database_dir))
    collection = client.get_collection(settings["collection_name"])
    if collection.metadata.get("embedding_model") != settings["embedding_model"]:
        raise ValueError("The Chroma collection uses a different embedding model; rebuild it first")
    if collection.count() == 0:
        raise ValueError("The Chroma collection is empty; build it first")

    queries = load_queries()
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
    top_k = min(settings["top_k"], collection.count())
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
        "chunks_per_query": load_settings()["top_k"],
    }, indent=2))


if __name__ == "__main__":
    main()
