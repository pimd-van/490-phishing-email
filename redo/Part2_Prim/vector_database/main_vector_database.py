"""Build the configured guidance collection in the shared RAG Chroma store.

Run from the project root:
    python part2/vector_database/main_vector_database.py                      # main KB (BGE-M3, 20 chunks)
    python part2/vector_database/main_vector_database.py --config part2/vector_database/config_vector_database_bge_large.json
    python part2/vector_database/main_vector_database.py --config part2/vector_database/config_vector_database_kb17.json

id_mode "file_stem": every document file is one chunk and its ID is the file name without extension
(BRD-01.txt -> BRD-01), so retrieved IDs match the gold labels. A file that would split into more than
one chunk is an error in this mode.
id_mode "letter": the original behaviour (letter from sources.json + chunk number, e.g. a2).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parents[1]
DEFAULT_CONFIG = HERE / "config_vector_database.json"


def read_commented_json(path: Path) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return json.loads("\n".join(line for line in lines if not line.lstrip().startswith("//")))


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_DIR / path


def load_settings(config_file: str | Path | None = None) -> dict:
    config_path = resolve_path(str(config_file)) if config_file else DEFAULT_CONFIG
    settings = read_commented_json(config_path)
    required = (
        "embedding_model", "collection_name", "chunk_size_tokens", "chunk_overlap_tokens",
        "embedding_batch_size", "query_prefix", "document_dir", "database_dir",
    )
    missing = [key for key in required if key not in settings]
    if missing:
        raise ValueError(f"Missing config values: {', '.join(missing)}")
    size = settings["chunk_size_tokens"]
    overlap = settings["chunk_overlap_tokens"]
    if not isinstance(size, int) or size <= 0 or not isinstance(overlap, int) or not 0 <= overlap < size:
        raise ValueError("chunk_size_tokens must be positive and overlap must be smaller")
    if not isinstance(settings["embedding_batch_size"], int) or settings["embedding_batch_size"] <= 0:
        raise ValueError("embedding_batch_size must be a positive integer")
    if not isinstance(settings["embedding_model"], str) or not settings["embedding_model"].strip():
        raise ValueError("embedding_model must be a non-empty string")
    settings.setdefault("id_mode", "letter")
    if settings["id_mode"] not in ("letter", "file_stem"):
        raise ValueError('id_mode must be "letter" or "file_stem"')
    settings.setdefault("sources_file", "part2/vector_database/sources.json")
    settings.setdefault("max_seq_length", 0)
    settings.setdefault("result_file", "part2/vector_database/result_vector_database.json")
    settings.setdefault("gold_id_map", "")
    settings["_config_path"] = str(config_path)
    return settings


def load_model(settings: dict):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(settings["embedding_model"])
    if settings.get("max_seq_length"):
        model.max_seq_length = int(settings["max_seq_length"])
    return model


def split_text(text: str, tokenizer, size: int, overlap: int) -> list[tuple[str, int]]:
    """Split text on model token boundaries while preserving original content."""
    encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, truncation=False, verbose=False)
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


def build(config_file=None) -> tuple[dict, list[dict], Path]:
    import chromadb

    settings = load_settings(config_file)
    document_dir = resolve_path(settings["document_dir"])
    database_dir = resolve_path(settings["database_dir"])
    files = sorted(
        (path for path in document_dir.iterdir() if path.is_file() and path.suffix.lower() in {".md", ".txt"}),
        key=lambda path: path.name.casefold(),
    )
    if not files:
        raise ValueError(f"No .md or .txt documents found in {document_dir}")
    sources = json.loads(resolve_path(settings["sources_file"]).read_text(encoding="utf-8"))
    by_file = {source["file"]: source for source in sources}
    missing = [path.name for path in files if path.name not in by_file]
    if missing:
        raise ValueError(f"Missing in {settings['sources_file']}: {', '.join(missing)}")
    if settings["id_mode"] == "letter":
        letters = {name: s["letter"] for name, s in by_file.items() if "letter" in s}
        no_letter = [path.name for path in files if path.name not in letters]
        if no_letter:
            raise ValueError(f"Missing letter in sources: {', '.join(no_letter)}")
        used = [letters[path.name] for path in files]
        if any(re.fullmatch(r"[a-z]", letter or "") is None for letter in used) or len(set(used)) != len(used):
            raise ValueError("Each source needs a unique lowercase a-z letter")

    model = load_model(settings)
    records = []
    for path in files:
        content = path.read_text(encoding="utf-8")
        pieces = split_text(content, model.tokenizer, settings["chunk_size_tokens"], settings["chunk_overlap_tokens"])
        if settings["id_mode"] == "file_stem" and len(pieces) != 1:
            raise ValueError(f"{path.name} gives {len(pieces)} chunks; file_stem mode needs exactly one "
                             f"(raise chunk_size_tokens or shorten the file)")
        source = by_file[path.name]
        for number, (chunk, token_amount) in enumerate(pieces):
            chunk_id = path.stem if settings["id_mode"] == "file_stem" else f"{source['letter']}{number + 1}"
            records.append({
                "id": chunk_id, "content": chunk, "token_amount": token_amount, "source": path.name,
                "chunk_number": number, "header": source.get("header", ""), "title": source.get("title", ""),
                "url": source.get("url", ""),
            })
    if not records:
        raise ValueError("Documents contain no indexable text")

    batch_size = settings["embedding_batch_size"]
    embeddings = model.encode([r["content"] for r in records], batch_size=batch_size, normalize_embeddings=True).tolist()

    client = chromadb.PersistentClient(path=str(database_dir))
    collection_name = settings["collection_name"]
    if collection_name in {c.name if hasattr(c, "name") else c for c in client.list_collections()}:
        client.delete_collection(collection_name)  # rebuild from scratch so an old KB version never lingers
    collection = client.create_collection(
        collection_name,
        metadata={"embedding_model": settings["embedding_model"], "hnsw:space": "cosine",
                  "id_mode": settings["id_mode"], "max_seq_length": int(settings["max_seq_length"] or 0)},
    )
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        collection.upsert(
            ids=[r["id"] for r in batch],
            documents=[r["content"] for r in batch],
            metadatas=[{"source": r["source"], "chunk_number": r["chunk_number"], "token_amount": r["token_amount"],
                        "header": r["header"], "title": r["title"], "url": r["url"]} for r in batch],
            embeddings=embeddings[start:start + batch_size],
        )
    summary = {"collection": collection_name, "embedding_model": settings["embedding_model"],
               "sources": len(files), "chunks": collection.count(), "database_dir": str(database_dir)}
    result_chunks = [{"chunk_id": r["id"], "token": r["token_amount"], "content": r["content"]} for r in records]
    return summary, result_chunks, resolve_path(settings["result_file"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="config file (default: config_vector_database.json next to this script)")
    args = parser.parse_args()
    try:
        summary, result_chunks, result_file = build(args.config)
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        raise SystemExit(f"Cannot build Chroma: {error}") from error
    temporary = result_file.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result_chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(result_file)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
