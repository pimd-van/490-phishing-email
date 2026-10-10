"""Build the configured guidance collection in the shared RAG Chroma store."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
import chromadb

HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parents[1]
CONFIG_FILE = HERE / "config.json"


def load_settings() -> dict:
    settings = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = (
        "embedding_model",
        "collection_name",
        "chunk_size_tokens",
        "chunk_overlap_tokens",
        "embedding_batch_size",
        "top_k",
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
    for key in ("embedding_batch_size", "top_k"):
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


def build() -> dict:
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

    model = SentenceTransformer(settings["embedding_model"])
    records = []
    for path in files:
        content = path.read_text(encoding="utf-8")
        source_id = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:16]
        for number, (chunk, token_amount) in enumerate(split_text(
            content,
            model.tokenizer,
            settings["chunk_size_tokens"],
            settings["chunk_overlap_tokens"],
        )):
            records.append({
                "id": f"{source_id}:{number:04d}",
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
    return {
        "collection": collection_name,
        "sources": len(files),
        "chunks": collection.count(),
        "database_dir": str(database_dir),
    }


def main() -> None:
    try:
        result = build()
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        raise SystemExit(f"Cannot build Chroma: {error}") from error
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
