"""Build and query a local Chroma index of phishing guidance documents."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
DOCUMENTS = HERE / "documents"
DATABASE = HERE / ".chroma"
CONFIG = HERE / "config.json"
PROVENANCE = HERE / "sources.json"
SUPPORTED_SUFFIXES = {".md", ".txt"}


def load_config(config_path: Path = CONFIG) -> dict:
    """Read and validate the editable retrieval settings."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    size = config["chunk_size_tokens"]
    overlap = config["chunk_overlap_tokens"]
    batch_size = config["embedding_batch_size"]
    top_k = config["top_k"]
    if not isinstance(size, int) or not isinstance(overlap, int) or size <= 0 or not 0 <= overlap < size:
        raise ValueError("chunk_size_tokens must be positive and overlap must be smaller")
    if not isinstance(batch_size, int) or batch_size <= 0 or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("embedding_batch_size and top_k must be positive integers")
    return config


def chunk_text(text: str, tokenizer, size: int, overlap: int) -> list[str]:
    """Split text using the embedding model's actual tokens."""
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    for start in range(0, len(tokens), size - overlap):
        chunk = tokenizer.decode(tokens[start:start + size], skip_special_tokens=True).strip()
        if chunk:
            chunks.append(chunk)
        if start + size >= len(tokens):
            break
    return chunks


def discover_documents(documents_dir: Path = DOCUMENTS) -> list[Path]:
    """Return supported top-level guidance files in deterministic order."""
    if not documents_dir.is_dir():
        return []
    return sorted(
        (path for path in documents_dir.iterdir()
         if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES),
        key=lambda path: path.name.casefold(),
    )


def _load_provenance(metadata_path: Path) -> dict[str, dict]:
    """Load optional per-file provenance; it never controls discovery."""
    if not metadata_path.is_file():
        return {}
    entries = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("sources.json must contain a JSON list")
    result = {}
    for entry in entries:
        filename = entry.get("file") if isinstance(entry, dict) else None
        if not isinstance(filename, str) or not filename:
            raise ValueError("Each sources.json entry must have a non-empty file")
        if filename in result:
            raise ValueError(f"Duplicate provenance entry for {filename}")
        result[filename] = entry
    return result


def load_sources(
    documents_dir: Path = DOCUMENTS,
    metadata_path: Path = PROVENANCE,
) -> list[dict]:
    """Discover and read all top-level UTF-8 guidance documents."""
    paths = discover_documents(documents_dir)
    if not paths:
        raise ValueError("No top-level .txt or .md guidance documents found")
    provenance = _load_provenance(metadata_path)
    sources = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            continue
        source_id = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:16]
        metadata = {"source_id": source_id, "source": path.name, "filename": path.name}
        for key, value in provenance.get(path.name, {}).items():
            if key != "file" and value is not None:
                metadata[key] = str(value)
        sources.append({"path": path, "content": content, "metadata": metadata})
    if not sources:
        raise ValueError("Guidance corpus is empty or whitespace-only")
    return sources


def _records(sources: list[dict], tokenizer, size: int, overlap: int) -> list[dict]:
    records = []
    for source in sources:
        chunks = chunk_text(source["content"], tokenizer, size, overlap)
        for number, chunk in enumerate(chunks):
            records.append({
                "id": f"{source['metadata']['source_id']}:{number:04d}",
                "document": chunk,
                "metadata": {**source["metadata"], "chunk_number": number},
            })
    if not records:
        raise ValueError("Guidance corpus contains no indexable tokens")
    return records


def _default_model_factory(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _default_client_factory(path: str):
    import chromadb

    return chromadb.PersistentClient(path=path)


def build_index(
    documents_dir: Path = DOCUMENTS,
    database: Path = DATABASE,
    config_path: Path = CONFIG,
    metadata_path: Path = PROVENANCE,
    model_factory: Callable | None = None,
    client_factory: Callable | None = None,
) -> dict:
    """Replace the dedicated collection with exactly the current corpus."""
    config = load_config(config_path)
    sources = load_sources(documents_dir, metadata_path)
    model = (model_factory or _default_model_factory)(config["embedding_model"])
    records = _records(
        sources, model.tokenizer,
        config["chunk_size_tokens"], config["chunk_overlap_tokens"],
    )

    # Validate and embed everything before replacing the last usable index.
    batch_size = config["embedding_batch_size"]
    embeddings = []
    for start in range(0, len(records), batch_size):
        texts = [record["document"] for record in records[start:start + batch_size]]
        vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
        embeddings.extend(vectors.tolist())
    if len(embeddings) != len(records):
        raise ValueError("Embedding model returned an unexpected number of vectors")

    client = (client_factory or _default_client_factory)(str(database))
    name = config["collection_name"]
    if name in [collection.name for collection in client.list_collections()]:
        client.delete_collection(name)
    collection = client.create_collection(
        name,
        metadata={"embedding_model": config["embedding_model"], "hnsw:space": "cosine"},
    )
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        collection.upsert(
            ids=[record["id"] for record in batch],
            documents=[record["document"] for record in batch],
            metadatas=[record["metadata"] for record in batch],
            embeddings=embeddings[start:start + batch_size],
        )
    return {"collection": name, "sources": len(sources), "chunks": collection.count()}


def retrieve(
    query: str,
    database: Path = DATABASE,
    config_path: Path = CONFIG,
    model_factory: Callable | None = None,
    client_factory: Callable | None = None,
) -> list[dict]:
    """Return the nearest guidance chunks; lower cosine distance is closer."""
    if not query.strip():
        raise ValueError("Search query must not be empty")
    config = load_config(config_path)
    client = (client_factory or _default_client_factory)(str(database))
    collection = client.get_collection(config["collection_name"])
    if collection.metadata.get("embedding_model") != config["embedding_model"]:
        raise ValueError("Embedding model changed; rebuild the Chroma collection")
    model = (model_factory or _default_model_factory)(config["embedding_model"])
    vector = model.encode([query], normalize_embeddings=True).tolist()
    result = collection.query(
        query_embeddings=vector,
        n_results=min(config["top_k"], collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"chunk_id": id_, "text": document, "metadata": metadata, "distance": distance}
        for id_, document, metadata, distance in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]
