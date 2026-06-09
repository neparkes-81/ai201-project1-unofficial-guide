"""
Vector Store
------------------------
Loads the chunks produced by ingestion.py, embeds them with all-MiniLM-L6-v2,
and stores them in a persistent ChromaDB collection ready for retrieval.

Usage:
    python vector_store.py            # build (or rebuild) the collection

Input:  ./chunks.json     (list of {text, metadata} dicts from ingestion.py)
Output: ./chroma_db/      (persistent Chroma database on disk)
"""

import json
from pathlib import Path

import chromadb

from embedding import embed_texts, MODEL_NAME


# ── Config ────────────────────────────────────────────────────────────────────

CHUNKS_FILE = "./chunks.json"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "uf_linguistics_reviews"

# Cosine distance fits L2-normalized sentence embeddings better than the
# Chroma default (squared L2). Scores then range ~0 (identical) to ~2 (opposite).
DISTANCE_SPACE = "cosine"


# ── Metadata sanitizing ───────────────────────────────────────────────────────

def sanitize_metadata(metadata: dict) -> dict:
    """
    Chroma metadata values must be str | int | float | bool — no lists, no None.
    Two fields from our chunks need fixing:
      - `tags` is a list   -> join into a comma-separated string
      - `would_take_again` is sometimes None -> drop the key entirely
    Any other None value is dropped too, defensively.
    """
    clean = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            clean[key] = ", ".join(str(v) for v in value)
        else:
            clean[key] = value
    return clean


# ── Build the collection ──────────────────────────────────────────────────────

def load_chunks(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunk(s) from {path}")
    return chunks


def get_collection(reset: bool = False):
    """
    Return the Chroma collection, creating it if needed.
    If reset=True, delete any existing collection first so we start clean.
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass  # collection didn't exist yet — fine

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": DISTANCE_SPACE},
    )
    return collection


def build():
    """Embed every chunk and load it into a fresh Chroma collection."""
    chunks = load_chunks(CHUNKS_FILE)
    collection = get_collection(reset=True)

    texts = [c["text"] for c in chunks]
    metadatas = [sanitize_metadata(c["metadata"]) for c in chunks]
    # Stable, unique ids. rating_id is unique per review; fall back to index.
    ids = [
        str(c["metadata"].get("rating_id") or f"chunk-{i}")
        for i, c in enumerate(chunks)
    ]

    print(f"Embedding {len(texts)} chunk(s) with {MODEL_NAME} ...")
    embeddings = embed_texts(texts)

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(
        f"\nDone. {collection.count()} chunk(s) stored in collection "
        f"'{COLLECTION_NAME}' at {Path(CHROMA_PATH).resolve()}"
    )
    return collection


if __name__ == "__main__":
    build()
