"""
Ingestion + Chunking
------------------------
Reads saved .html files from a local folder, extracts review data from
the embedded __RELAY_STORE__ JSON blob, and produces metadata-enriched
chunks ready for embedding.

Usage:
    python rmp_ingest.py

Input:  ./documents/*.html   (saved professor pages)
Output: ./chunks.json          (list of chunk dicts)
"""

import os
import json
import re
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────────────────

HTML_DIR = "./documents"   # folder containing your saved .html files
OUTPUT_FILE = "./chunks.json"


# ── Step 1: Ingestion — read HTML files from disk ─────────────────────────────

def load_html_files(directory: str) -> list[tuple[str, str]]:
    """
    Returns a list of (filename, html_content) tuples.
    Plain Python file I/O — no library needed for .html files.
    """
    pages = []
    for path in Path(directory).glob("*.html"):
        with open(path, "r", encoding="utf-8") as f:
            pages.append((path.name, f.read()))
    print(f"Loaded {len(pages)} HTML file(s) from {directory}")
    return pages


# ── Step 2: Extract structured data from the Relay store JSON ─────────────────

def extract_relay_store(html: str) -> dict:
    """
    RMP embeds all page data as window.__RELAY_STORE__ = {...} in a <script> tag.
    This is cleaner and more reliable than parsing the React HTML directly.
    """
    match = re.search(
        r'window\.__RELAY_STORE__\s*=\s*(\{.*?\});\s*\n',
        html,
        re.DOTALL
    )
    if not match:
        raise ValueError("Could not find __RELAY_STORE__ in page HTML")
    return json.loads(match.group(1))


def extract_professor_meta(store: dict) -> dict:
    """
    Pull professor-level fields from the store.
    The teacher object is always keyed by a base64 id like 'VGVhY2hlci03MjkyMDA='.
    """
    teacher = next(
        (v for v in store.values()
         if isinstance(v, dict) and v.get("__typename") == "Teacher"),
        None
    )
    if not teacher:
        raise ValueError("No Teacher object found in Relay store")

    school_ref = teacher.get("school", {}).get("__ref", "")
    school = store.get(school_ref, {})

    return {
        "professor_id":   teacher.get("legacyId"),
        "first_name":     teacher.get("firstName", ""),
        "last_name":      teacher.get("lastName", ""),
        "department":     teacher.get("department", ""),
        "school":         school.get("name", ""),
        "avg_rating":     teacher.get("avgRating"),
        "avg_difficulty": teacher.get("avgDifficulty"),
        "num_ratings":    teacher.get("numRatings"),
        "would_take_again_pct": teacher.get("wouldTakeAgainPercent"),
    }


def extract_ratings(store: dict) -> list[dict]:
    """
    Pull all Rating objects out of the store.
    Each has: comment, class, date, helpfulRating, clarityRating,
              difficultyRating, wouldTakeAgain, grade, ratingTags.
    """
    ratings = [
        v for v in store.values()
        if isinstance(v, dict) and v.get("__typename") == "Rating"
    ]
    return ratings


# ── Step 3: Chunking — review-as-chunk with metadata prepend ──────────────────

def build_chunk(rating: dict, professor: dict) -> dict | None:
    """
    One review = one chunk.

    Metadata header is prepended as plain text so the embedding model
    sees structured signal alongside the freeform comment.
    Overlap: 0 — reviews are self-contained opinion units.

    Returns None if the review has no comment text (skip it).
    """
    comment = (rating.get("comment") or "").strip()
    if not comment:
        return None

    # Build the metadata header line
    would_take = "Yes" if rating.get("wouldTakeAgain") == 1 else "No"
    grade = rating.get("grade") or "N/A"
    tags_raw = rating.get("ratingTags") or ""
    tags = [t.strip() for t in tags_raw.split("--") if t.strip()]
    tags_str = ", ".join(tags) if tags else "none"

    header = (
        f"Professor: {professor['first_name']} {professor['last_name']} | "
        f"Department: {professor['department']} | "
        f"School: {professor['school']} | "
        f"Course: {rating.get('class', 'N/A')} | "
        f"Quality: {rating.get('helpfulRating', 'N/A')}/5 | "
        f"Difficulty: {rating.get('difficultyRating', 'N/A')}/5 | "
        f"Would take again: {would_take} | "
        f"Grade: {grade} | "
        f"Tags: {tags_str}"
    )

    chunk_text = f"{header}\n{comment}"

    return {
        # Text that gets embedded
        "text": chunk_text,
        # Metadata stored alongside in ChromaDB (for filtering / display)
        "metadata": {
            "professor_id":    professor["professor_id"],
            "professor_name":  f"{professor['first_name']} {professor['last_name']}",
            "department":      professor["department"],
            "school":          professor["school"],
            "course":          rating.get("class"),
            "quality_rating":  rating.get("helpfulRating"),
            "clarity_rating":  rating.get("clarityRating"),
            "difficulty":      rating.get("difficultyRating"),
            "would_take_again": rating.get("wouldTakeAgain"),
            "grade":           rating.get("grade"),
            "date":            rating.get("date"),
            "tags":            tags,
            "rating_id":       rating.get("legacyId"),
        }
    }


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run():
    all_chunks = []

    pages = load_html_files(HTML_DIR)

    for filename, html in pages:
        print(f"\nProcessing: {filename}")
        try:
            store = extract_relay_store(html)
        except ValueError as e:
            print(f"  Skipping — {e}")
            continue

        try:
            professor = extract_professor_meta(store)
        except ValueError as e:
            print(f"  Skipping — {e}")
            continue

        print(
            f"  Professor: {professor['first_name']} {professor['last_name']} "
            f"({professor['department']}, {professor['school']})"
        )

        ratings = extract_ratings(store)
        print(f"  Found {len(ratings)} rating(s) in Relay store")

        page_chunks = []
        for rating in ratings:
            chunk = build_chunk(rating, professor)
            if chunk:
                page_chunks.append(chunk)

        print(f"  Produced {len(page_chunks)} chunk(s)")
        all_chunks.extend(page_chunks)

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(all_chunks)} total chunks written to {OUTPUT_FILE}")
    return all_chunks


if __name__ == "__main__":
    run()
