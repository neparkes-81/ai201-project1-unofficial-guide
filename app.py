"""
App / Interface
------------------------
A Gradio web UI for the RAG pipeline: ask a question about a UF Linguistics
professor and get a grounded, source-attributed answer.

Pipeline reused as-is:
    retrieval.py  ->  generation.py (answer_question)  ->  this UI

Styling uses University of Florida colors (blue, orange, white, beige).

Run:
    python app.py      # then open the printed http://127.0.0.1:7860 link
"""

import json
import re

import gradio as gr

from generation import answer_question, FALLBACK
from retrieval import EVAL_QUERIES


# ── University of Florida palette ─────────────────────────────────────────────

UF_BLUE = "#0021A5"
UF_ORANGE = "#FA4616"
UF_BEIGE = "#F5EFE6"
UF_WHITE = "#FFFFFF"


# ── Professor roster (read from the corpus so it stays accurate) ───────────────

def load_professors(path: str = "./chunks.json") -> list[str]:
    """Distinct professor names present in the chunked corpus, alphabetized."""
    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    names = {c["metadata"]["professor_name"] for c in chunks}
    return sorted(names)


PROFESSORS = load_professors()


# ── Answer handler ────────────────────────────────────────────────────────────

def respond(question: str) -> str:
    """
    Run the RAG pipeline for one question and return Markdown for the UI.
    Bare source URLs are wrapped as <url> so Markdown renders them clickable.
    """
    question = (question or "").strip()
    if not question:
        return "_Type a question above to get started._"

    try:
        result = answer_question(question, debug=False)
    except RuntimeError as e:
        # Most likely a missing/placeholder GROQ_API_KEY.
        return f"⚠️ **Configuration error:** {e}"
    except Exception as e:
        return f"⚠️ **Something went wrong:** {e}"

    # Autolink bare http(s) URLs in the Sources list.
    result = re.sub(r"(https?://\S+)", r"<\1>", result)

    if result.strip() == FALLBACK:
        return f"ℹ️ {FALLBACK}"
    return result


# ── Theme + CSS (UF colors) ───────────────────────────────────────────────────

uf_theme = gr.themes.Base(
    primary_hue=gr.themes.colors.orange,
    secondary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.stone,
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
)

CSS = f"""
.gradio-container {{ background: {UF_BEIGE} !important; }}

#uf-header {{
    background: {UF_BLUE};
    color: {UF_WHITE};
    padding: 22px 28px;
    border-radius: 12px;
    border-bottom: 6px solid {UF_ORANGE};
    margin-bottom: 10px;
}}
#uf-header h1 {{ margin: 0; font-size: 1.7rem; }}
#uf-header p  {{ margin: 6px 0 0; opacity: 0.92; }}

/* Submit button in UF orange */
#ask-btn {{
    background: {UF_ORANGE} !important;
    color: {UF_WHITE} !important;
    border: none !important;
}}
#ask-btn:hover {{ filter: brightness(0.93); }}

/* Answer card: white panel with an orange accent edge */
#answer-box {{
    background: {UF_WHITE};
    border-left: 5px solid {UF_ORANGE};
    border-radius: 8px;
    padding: 6px 18px;
    min-height: 120px;
    color: #000000;
}}
#answer-box, #answer-box * {{ color: #000000; }}
#answer-box a {{ color: {UF_BLUE}; }}

/* Sample query buttons: black text */
#examples-box, #examples-box * {{ color: #000000 !important; }}

/* Professor roster side box */
#prof-box {{
    background: {UF_WHITE};
    border-top: 5px solid {UF_BLUE};
    border-radius: 8px;
    padding: 10px 18px;
}}
#prof-box h3 {{ color: {UF_BLUE}; margin: 4px 0 8px; }}
#prof-box ul {{ margin: 0; padding-left: 18px; }}
#prof-box li {{ color: #000000; margin: 3px 0; }}

footer {{ display: none !important; }}
"""

# Sidebar HTML listing the professors that can be queried.
PROF_LIST_HTML = (
    '<div id="prof-box"><h3>Professors covered</h3><ul>'
    + "".join(f"<li>{name}</li>" for name in PROFESSORS)
    + "</ul></div>"
)


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="UF Linguistics — Unofficial Guide") as demo:
    gr.HTML(
        """
        <div id="uf-header">
            <h1>🐊 The Unofficial Guide — UF Linguistics</h1>
            <p>Ask what students really say about University of Florida
            Linguistics professors. Answers come only from student reviews,
            with sources cited.</p>
        </div>
        """
    )

    with gr.Row():
        # Main column: ask + answer.
        with gr.Column(scale=4):
            question = gr.Textbox(
                label="Your question",
                placeholder="e.g. How do students feel about the workload in Professor Kaan's classes?",
                lines=2,
            )
            with gr.Row():
                ask_btn = gr.Button("Ask", elem_id="ask-btn", variant="primary")
                clear_btn = gr.ClearButton(value="Clear")

            answer = gr.Markdown(
                value="_Answers will appear here, with a list of the reviews they came from._",
                elem_id="answer-box",
                label="Answer",
            )

            gr.Examples(
                examples=[[q] for q in EVAL_QUERIES],
                inputs=question,
                label="Try one of these",
                elem_id="examples-box",
            )

        # Side column: the professors you can ask about.
        with gr.Column(scale=1):
            gr.HTML(PROF_LIST_HTML)

    gr.Markdown(
        "<sub>Grounded in Rate My Professor student reviews · "
        "Generated with Groq (llama-3.3-70b-versatile) · "
        f'Replies "{FALLBACK}" when the reviews don\'t cover your question.</sub>'
    )

    # Wire up interactions.
    ask_btn.click(fn=respond, inputs=question, outputs=answer)
    question.submit(fn=respond, inputs=question, outputs=answer)
    clear_btn.add([question, answer])


if __name__ == "__main__":
    demo.launch(theme=uf_theme, css=CSS)
