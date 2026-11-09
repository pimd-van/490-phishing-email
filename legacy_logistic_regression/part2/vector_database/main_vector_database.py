"""Build the configured guidance collection in the shared RAG Chroma store."""

from __future__ import annotations

import json
import re
from pathlib import Path

from sentence_transformers import SentenceTransformer
import chromadb

HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parents[1]
CONFIG_FILE = HERE / "config_vector_database.json"
RESULT_FILE = HERE / "result_vector_database.json"
SOURCES_FILE = HERE / "sources.json"


def load_settings() -> dict:
    lines = CONFIG_FILE.read_text(encoding="utf-8").splitlines()
    settings = json.loads("\n".join(line for line in lines if not line.lstrip().startswith("//")))
    required = (
        "embedding_model",
        "collection_name",
        "chunk_size_tokens",
        "chunk_overlap_tokens",
        "embedding_batch_size",
        "query_prefix",
        "document_dir",
        "database_dir",
    )
    missing = [key for key in required if key not in settings]
    if missing:
        raise ValueError(f"Missing config values: {', '.join(missing)}")
    size = settings["chunk_size_tokens"]
    overlap = settings["chunk_overlap_tokens"]
    if not isinstance(size, int) or size <= 0 or not isinstance(overlap, int) or not 0 <= overlap < size:
        raise ValueError("chunk_size_tokens must be positive and overlap must be smaller")
    for key in ("embedding_batch_size",):
        if not isinstance(settings[key], int) or settings[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if not isinstance(settings["embedding_model"], str) or not settings["embedding_model"].strip():
        raise ValueError("embedding_model must be a non-empty string")
    return settings


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_DIR / path


def split_text(text: str, tokenizer, size: int, overlap: int) -> list[tuple[str, int]]:
    """Split text on model token boundaries while preserving original content."""
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
        verbose=False,
    )
    token_ids = encoded["input_ids"]
    offsets = encoded["offset_mapping"]
    chunks = []
    for start in range(0, len(token_ids), size - overlap):
        end = min(start + size, len(token_ids))
        content = text[offsets[start][0]:offsets[end - 1][1]].strip()
        if content:
            amount = len(tokenizer.encode(content, add_special_tokens=False))
            chunks.append((content, amount))
        if end == len(token_ids):
            break
    return chunks


def build() -> tuple[dict, list[dict]]:
    settings = load_settings()
    document_dir = resolve_path(settings["document_dir"])
    database_dir = resolve_path(settings["database_dir"])
    files = sorted(
        (path for path in document_dir.iterdir()
         if path.is_file() and path.suffix.lower() in {".md", ".txt"}),
        key=lambda path: path.name.casefold(),
    )
    if not files:
        raise ValueError(f"No .md or .txt documents found in {document_dir}")
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    letters = {source["file"]: source["letter"] for source in sources if "letter" in source}
    missing = [path.name for path in files if path.name not in letters]
    if missing:
        raise ValueError(f"Missing letter in sources.json: {', '.join(missing)}")
    used_letters = list(letters.values())
    if any(not isinstance(letter, str) or re.fullmatch(r"[a-z]", letter) is None for letter in used_letters):
        raise ValueError("Each source letter must be one lowercase a-z character")
    if len(set(used_letters)) != len(used_letters):
        raise ValueError("Each source needs a unique letter")

    model = SentenceTransformer(settings["embedding_model"])
    records = []
    for path in files:
        content = path.read_text(encoding="utf-8")
        for number, (chunk, token_amount) in enumerate(split_text(
            content,
            model.tokenizer,
            settings["chunk_size_tokens"],
            settings["chunk_overlap_tokens"],
        )):
            records.append({
                "id": f"{letters[path.name]}{number + 1}",
                "content": chunk,
                "token_amount": token_amount,
                "source": path.name,
                "chunk_number": number,
            })
    if not records:
        raise ValueError("Documents contain no indexable text")

    batch_size = settings["embedding_batch_size"]
    embeddings = []
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        vectors = model.encode(
            [record["content"] for record in batch],
            batch_size=batch_size,
            normalize_embeddings=True,
        )
        embeddings.extend(vectors.tolist())

    client = chromadb.PersistentClient(path=str(database_dir))
    collection_name = settings["collection_name"]
    existing = {collection.name for collection in client.list_collections()}
    if collection_name in existing:
        client.delete_collection(collection_name)
    collection = client.create_collection(
        collection_name,
        metadata={"embedding_model": settings["embedding_model"], "hnsw:space": "cosine"},
    )
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        collection.upsert(
            ids=[record["id"] for record in batch],
            documents=[record["content"] for record in batch],
            metadatas=[{
                "source": record["source"],
                "chunk_number": record["chunk_number"],
                "token_amount": record["token_amount"],
            } for record in batch],
            embeddings=embeddings[start:start + batch_size],
        )
    summary = {
        "collection": collection_name,
        "sources": len(files),
        "chunks": collection.count(),
        "database_dir": str(database_dir),
    }
    result_chunks = [
        {"chunk_id": record["id"], "token": record["token_amount"], "content": record["content"]}
        for record in records
    ]
    return summary, result_chunks


def main() -> None:
    try:
        summary, result_chunks = build()
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        raise SystemExit(f"Cannot build Chroma: {error}") from error
    output = json.dumps(result_chunks, indent=2, ensure_ascii=False) + "\n"
    temporary = RESULT_FILE.with_suffix(".json.tmp")
    temporary.write_text(output, encoding="utf-8")
    temporary.replace(RESULT_FILE)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
