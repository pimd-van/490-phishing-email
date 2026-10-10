"""Generate comparable action plans with four local Ollama models."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import chromadb

LLM_DIR = Path(__file__).resolve().parent
PART2_DIR = LLM_DIR.parent
RAG_DIR = PART2_DIR / "RAG"
CONFIG_FILE = LLM_DIR / "config_LLM.json"
DATA_FILE = PART2_DIR / "data.csv"
RETRIEVAL_FILE = RAG_DIR / "result_RAG.json"
OUTPUT_FILE = LLM_DIR / "result_LLM.json"
VECTOR_CONFIG_FILE = PART2_DIR / "vector_database" / "config_vector_database.json"
PROJECT_DIR = PART2_DIR.parent
OLLAMA_URL = "http://127.0.0.1:11434"
MODELS = ("llama3.1:8b", "mistral:7b", "qwen2.5:7b", "phi3:mini")


def load_config() -> dict:
    lines = CONFIG_FILE.read_text(encoding="utf-8").splitlines()
    config = json.loads("\n".join(line for line in lines if not line.lstrip().startswith("//")))
    if not isinstance(config["prompt"], str) or not config["prompt"].strip():
        raise ValueError("config_LLM.json must contain a non-empty prompt")
    if not isinstance(config.get("generation"), dict) or not config["generation"]:
        raise ValueError("config_LLM.json must contain shared generation settings")
    for name in ("max_body_chars", "request_timeout_seconds"):
        if not isinstance(config[name], int) or config[name] <= 0:
            raise ValueError(f"{name} must be a positive integer")
    return config


def load_rows(limit: int | None) -> list[dict]:
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if limit is not None:
        rows = rows[:limit]
    if not rows or any(not row.get("id") for row in rows):
        raise ValueError("data.csv has no usable rows or contains a missing id")
    return rows


def load_guidance(rows: list[dict]) -> dict[str, str]:
    retrieval = json.loads(RETRIEVAL_FILE.read_text(encoding="utf-8"))
    ids_by_query = {item["query_id"]: item["top_retrieved_chunk"] for item in retrieval}
    missing = [row["id"] for row in rows if row["id"] not in ids_by_query]
    if missing:
        raise ValueError(f"No retrieval result for {len(missing)} input rows; run main_RAG.py first")

    lines = VECTOR_CONFIG_FILE.read_text(encoding="utf-8").splitlines()
    vector_config = json.loads("\n".join(line for line in lines if not line.lstrip().startswith("//")))
    database_dir = Path(vector_config["database_dir"])
    if not database_dir.is_absolute():
        database_dir = PROJECT_DIR / database_dir
    collection = chromadb.PersistentClient(path=str(database_dir)).get_collection(
        vector_config["collection_name"]
    )
    all_ids = list(dict.fromkeys(
        chunk_id for row in rows for chunk_id in ids_by_query[row["id"]]
    ))
    chunks = collection.get(ids=all_ids, include=["documents", "metadatas"])
    by_id = dict(zip(chunks["ids"], zip(chunks["documents"], chunks["metadatas"])))
    if len(by_id) != len(all_ids):
        raise ValueError("Some retrieved chunks are missing from Chroma; rebuild and rerun main_RAG.py")

    guidance = {}
    for row in rows:
        passages = []
        for chunk_id in ids_by_query[row["id"]]:
            document, metadata = by_id[chunk_id]
            passages.append(f"[{chunk_id}] Source: {metadata['source']}\n{document}")
        guidance[row["id"]] = "\n\n".join(passages)
    return guidance


def generate(model: str, prompt: str, email: str, guidance: str, config: dict) -> str:
    payload = {
        "model": model,
        "stream": False,
        "options": config["generation"],
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"EMAIL\n{email}\n\nRETRIEVED GUIDANCE\n{guidance}"},
        ],
    }
    url = OLLAMA_URL + "/api/chat"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=config["request_timeout_seconds"]) as response:
            answer = json.load(response)["message"]["content"].strip()
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Ollama request failed for {model}: {error}") from error
    if not answer:
        raise ValueError(f"Ollama returned an empty answer for {model}")
    return answer


def write_output(records: list[dict]) -> None:
    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT_FILE)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", help="Override the shared action-plan instruction in config_LLM.json")
    parser.add_argument("--limit", type=int, help="Process only the first N emails")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    config = load_config()
    prompt = args.prompt if args.prompt is not None else config["prompt"]
    if not prompt.strip():
        parser.error("--prompt must not be empty")
    rows = load_rows(args.limit)
    guidance = load_guidance(rows)
    records = [
        {"id": row["id"], "subject": row.get("subject", ""), "body": row.get("body", "")}
        for row in rows
    ]
    for slot, model in enumerate(MODELS, start=1):
        print(f"Running model{slot}: {model} ({len(rows)} emails)", flush=True)
        for row, record in zip(rows, records):
            email = (
                f"Subject: {record['subject']}\n"
                f"Body: {record['body'][:config['max_body_chars']]}"
            )
            record[f"model{slot}"] = {
                "model": model,
                "action_plan": generate(model, prompt, email, guidance[row["id"]], config),
            }
            write_output(records)
    print(f"Wrote {len(records)} emails to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
