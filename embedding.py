"""
Embedding
------------------------
Wraps the all-MiniLM-L6-v2 sentence-transformers model so the rest of the
pipeline has a single place to turn text into vectors.

Why all-MiniLM-L6-v2 (per planning.md > Retrieval Approach):
    - Corpus is mono-lingual English, reviews rarely exceed ~256 tokens, and
      there's limited semantic variation — so a small, fast model is the right
      cost/accuracy trade-off. It produces 384-dimensional embeddings.

This module is imported by vector_store.py (to embed chunks at ingest time)
and retrieval.py (to embed the incoming query). The same model must be used
for both so the vectors live in the same space.
"""

from sentence_transformers import SentenceTransformer


# ── Config ────────────────────────────────────────────────────────────────────

MODEL_NAME = "all-MiniLM-L6-v2"

# Cache the loaded model so we don't pay the load cost on every import / call.
_model: SentenceTransformer | None = None


# ── Model loading ─────────────────────────────────────────────────────────────

def get_model() -> SentenceTransformer:
    """
    Lazily load (and cache) the sentence-transformers model.
    First call downloads the weights (~90 MB) and may take a few seconds.
    """
    global _model
    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME} ...")
        _model = SentenceTransformer(MODEL_NAME)
        dim = _model.get_sentence_embedding_dimension()
        print(f"  Model loaded ({dim}-dimensional embeddings)")
    return _model


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of texts. Returns a list of plain Python float lists
    (Chroma expects lists, not numpy arrays).

    Embeddings are L2-normalized so that cosine distance in Chroma behaves
    sensibly — see vector_store.py where the collection is created with the
    cosine space.
    """
    model = get_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 1,
    )
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Convenience wrapper for embedding a single query string."""
    return embed_texts([query])[0]


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    vec = embed_query("How hard are Professor Kaan's classes?")
    print(f"Sample query embedding: dim={len(vec)}, first 5 values={vec[:5]}")
