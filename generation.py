"""
Generation
------------------------
The final stage of the RAG pipeline. Takes a user question, retrieves the most
relevant review chunks (retrieval.py), and asks Groq's llama-3.3-70b-versatile
to answer using ONLY those chunks — with source attribution.

Grounding requirements (per project spec):
  - The answer is built strictly from the retrieved context, never from the
    model's own prior knowledge.
  - Every claim is attributed to a source via inline [n] citations.
  - Output format is:  answer  +  a numbered Sources list.
  - If the retrieved context doesn't contain enough information to answer,
    the model replies exactly: "I don't have enough information on that."

Setup:
    Put your key in .env  ->  GROQ_API_KEY=your_key_here
    Get a free key at https://console.groq.com

Usage:
    python generation.py                          # runs the 5 evaluation queries
    python generation.py "your own question here" # answers a single question
"""

import os
import re
import sys

from dotenv import load_dotenv
from groq import Groq

from retrieval import retrieve, EVAL_QUERIES


# ── Config ────────────────────────────────────────────────────────────────────

MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.1          # low — we want faithful, not creative, answers
FALLBACK = "I don't have enough information on that."

# RMP professor pages are keyed by the same legacyId we stored as professor_id.
RMP_URL = "https://www.ratemyprofessors.com/professor/{pid}"

SYSTEM_PROMPT = (
    "You are an assistant that answers questions about University of Florida "
    "Linguistics professors using ONLY the student reviews provided as context. "
    "Follow these rules strictly:\n"
    "1. Use ONLY information found in the numbered context sources. Never use "
    "outside or prior knowledge.\n"
    "2. Cite the source(s) you used inline with bracketed numbers, e.g. [1] or "
    "[2][3], placed right after the claim they support.\n"
    "3. If the context does not contain enough information to answer the "
    f'question, reply with exactly this and nothing else: "{FALLBACK}"\n'
    "4. Do not invent professors, courses, ratings, or facts that are not in "
    "the context.\n"
    "5. Keep the answer concise and directly focused on the question."
)


# ── Prompt construction ───────────────────────────────────────────────────────

def format_context(chunks: list[dict]) -> str:
    """
    Render retrieved chunks as a numbered context block the model can cite.
    The [n] here is what the model cites and what maps to the Sources list.
    """
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(f"[{i}] {chunk['text']}")
    return "\n\n".join(blocks)


def source_line(index: int, meta: dict) -> str:
    """One human-readable Sources entry mapping a [n] back to its RMP page."""
    pid = meta.get("professor_id")
    url = RMP_URL.format(pid=pid) if pid else "(url unavailable)"
    course = meta.get("course") or "N/A"
    date = (meta.get("date") or "").split(" ")[0] or "n.d."
    return (
        f"[{index}] {meta.get('professor_name', 'Unknown')} — "
        f"{course}, review dated {date}\n     {url}"
    )


def cited_indices(answer: str) -> list[int]:
    """Pull the distinct [n] citation numbers the model actually used, in order."""
    seen = []
    for m in re.findall(r"\[(\d+)\]", answer):
        n = int(m)
        if n not in seen:
            seen.append(n)
    return seen


# ── Generation ────────────────────────────────────────────────────────────────

def get_client() -> Groq:
    load_dotenv()
    key = os.getenv("GROQ_API_KEY")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "key from https://console.groq.com"
        )
    return Groq(api_key=key)


def answer_question(query: str, debug: bool = True) -> str:
    """
    Full RAG turn: retrieve -> ground -> generate -> attach sources.
    Returns the formatted answer + Sources block as a string.
    """
    # Retrieve. retrieval.py already prints its own debug (queries + distances).
    chunks = retrieve(query, debug=debug)

    client = get_client()
    context = format_context(chunks)
    user_prompt = (
        f"Context (numbered student reviews):\n\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the context above, with inline [n] citations."
    )

    response = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    answer = response.choices[0].message.content.strip()

    # Build the Sources list from only the chunks the model actually cited.
    used = cited_indices(answer)
    if used and answer != FALLBACK:
        sources = "\n".join(
            source_line(n, chunks[n - 1]["metadata"])
            for n in used
            if 1 <= n <= len(chunks)
        )
        return f"{answer}\n\nSources:\n{sources}"

    # Fallback (or an answer with no citations) gets no source list.
    return answer


# ── Entry point ───────────────────────────────────────────────────────────────

def _run_one(query: str) -> None:
    result = answer_question(query)
    print("\n" + "#" * 80)
    print(f"ANSWER for: {query}")
    print("#" * 80)
    print(result)
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _run_one(" ".join(sys.argv[1:]))
    else:
        for q in EVAL_QUERIES:
            _run_one(q)
