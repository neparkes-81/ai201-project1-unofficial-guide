"""
Retrieval
------------------------
Embeds an incoming query with the same model used at ingest time, then asks
ChromaDB's collection.query() for the most similar review chunks.

Top-k = 6 (per planning.md > Retrieval Approach).

Includes debugging output: for a given query it prints each retrieved chunk
along with its cosine distance score, so you can see *what* was retrieved and
*how close* it was to the query.

Usage:
    python retrieval.py                          # runs the 5 evaluation queries
    python retrieval.py "your own question here" # runs a single custom query
"""

import sys

from embedding import embed_query
from vector_store import get_collection, COLLECTION_NAME


# ── Config ────────────────────────────────────────────────────────────────────

TOP_K = 5

# The 5 test questions from planning.md > Evaluation Plan.
EVAL_QUERIES = [
    "How do students feel about the work load in Professor Kaan's classes?",
    "Any suggestions from students for taking a class with Edith Kaan?",
    "How do students feel about Jamie Garner's LIN2011 course?",
    "Does Ethan Kutlu still work at UF?",
    "What is the overall rating of professor David Pharies?",
]


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(query: str, top_k: int = TOP_K, debug: bool = True) -> list[dict]:
    """
    Return the top_k most similar chunks for `query`.

    Each result is a dict: {text, metadata, distance}.
    Lower distance = closer match (cosine distance: 0 = identical).
    """
    collection = get_collection(reset=False)

    query_embedding = embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    # Chroma returns parallel lists wrapped in an outer list (one per query).
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved = [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]

    if debug:
        _print_debug(query, retrieved)

    return retrieved


# ── Debugging output ──────────────────────────────────────────────────────────

def _print_debug(query: str, retrieved: list[dict]) -> None:
    """Print the query and each retrieved chunk with its distance score."""
    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print(f"Retrieved {len(retrieved)} chunk(s) from '{COLLECTION_NAME}' "
          f"(lower distance = closer match)")
    print("=" * 80)

    for rank, item in enumerate(retrieved, start=1):
        meta = item["metadata"]
        # First line after the metadata header is the actual review comment.
        comment = item["text"].split("\n", 1)[-1].strip()
        snippet = comment[:160] + ("..." if len(comment) > 160 else "")

        print(f"\n[#{rank}]  distance={item['distance']:.4f}")
        print(f"     professor : {meta.get('professor_name', 'N/A')}")
        print(f"     course    : {meta.get('course', 'N/A')}  "
              f"| quality {meta.get('quality_rating', '?')}/5  "
              f"| difficulty {meta.get('difficulty', '?')}/5")
        print(f"     review    : {snippet}")

    print("\n" + "=" * 80 + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single custom query passed on the command line.
        retrieve(" ".join(sys.argv[1:]))
    else:
        # Default: run all 5 evaluation queries so you can eyeball retrieval.
        for q in EVAL_QUERIES:
            retrieve(q)
