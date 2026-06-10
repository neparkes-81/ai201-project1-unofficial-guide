# The Unofficial Guide — Project 1
In this project, I build **The Unofficial Guide**: a RAG (Retrieval-Augmented Generation) system that makes student-generated knowledge searchable and answerable. A user asks a plain-language question such as "Is the housing lottery actually random?" or "Which CS professor gives the most useful feedback?" — and gets a grounded, cited answer drawn from real documents you collected. My project will specifically focus on student opinions concerning professors, retriving information from the specific pages of the Rate my Professor site.

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->
My unofficial guide will focus on the domain of student reviews of University of Florida Linguistics department professors. Professor reviews are not published on official university sites and are often pass on between students through word-of-mouth or online forums. 

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate my Professor | Reviews for Professor Edith Kaan | https://www.ratemyprofessors.com/professor/729200 |
| 2 | Rate my Professor | Reviews for Professor Sarah Moeller | https://www.ratemyprofessors.com/professor/2069291 |
| 3 | Rate my Professor | Reviews for Professor Eleonora Rossi | https://www.ratemyprofessors.com/professor/2657746 |
| 4 | Rate my Professor | Reviews for Professor Jamie Garner | https://www.ratemyprofessors.com/professor/2469970 |
| 5 | Rate my Professor | Reviews for Professor Paula Golombek | https://www.ratemyprofessors.com/professor/1854514 |
| 6 | Rate my Professor | Reviews for Professor Hannah Treadway | https://www.ratemyprofessors.com/professor/2763389 |
| 7 | Rate my Professor | Reviews for Professor Steffi Wulff | https://www.ratemyprofessors.com/professor/1854516 |
| 8 | Rate my Professor | Reviews for Professor Ethan Kutlu | https://www.ratemyprofessors.com/professor/2184150 |
| 9 | Rate my Professor | Reviews for Professor Alexandrine Dunlap | https://www.ratemyprofessors.com/professor/2967403 |
| 10 | Rate my Professor | Reviews for Professor Imanol Suarez-Palma | https://www.ratemyprofessors.com/professor/2573403 |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
~128

**Overlap:**
0

**Why these choices fit your documents:**
Based on the structure of reviews on Rate my Professor, I have decided to use a document-aware chunking strategy. It will treat each review as an individual chunk. This makes sense as it isolates and contains the context behind each review. Whereas other approaches may groups reviews together if they are similar despite being different opinions (semantic approach) or lose sight of document-dependent boundaries of information (fixed-size and recursive approach). Reviews are traditionally short and should be no more than 128 tokens.

**Final chunk count:**
46
---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
all-MiniLM-L6-v2 via sentence-transformers

**Production tradeoff reflection:**
To avoid unnecessary computation cost derived from an overly complex model, take into consideration that my task data consists of mono-lingual English reviews, text sequence that would likely not go over 256 tokens, and limited meaning variation to require large multi-dimensional models. For that reason, I decide to use all-MiniLM-L6-v2 via sentence-transformers.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
 
 "...using ONLY the student reviews provided as context. "
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

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | How do students feel about the work load in Professor Kaan's classes? | Most say it is a lot of homework and she can be a harsh grader. | Reported "mixed feelings," noting material is "tricky" and there is "lots of homework," but cited only a single review and concluded no one called the workload excessive. | Relevant (4 of 5 chunks were Kaan reviews; 1 stray Kutlu chunk) | Partially accurate - caught the heavy-homework theme but under-cited and missed the harsh-grading sentiment present in the corpus |
| 2 | Any suggestions from students for taking a class with Edith Kaan? | Stay up to date with homework and readings, and ask for the study guide in advance. | Suggested keeping "up with the reading and assignments," noted she is organized, doesn't grade harshly, and gives meaningful feedback, with four citations. | Relevant (4 Kaan reviews + 1 Dunlap) | Partially accurate - captured the "keep up with readings" advice but the "ask for the study guide" suggestion was not in the retrieved chunks |
| 3 | How do students feel about Jamie Garner's LIN2011 course? | Overall positive; students praise her lectures and the minimal workload. | Positive overall: praised lectures, called the course "well-designed" and "decently interesting," noted it's mostly memorization with open-note exams; flagged one "weirdly hard" first module. | Relevant (all 5 chunks were Garner, 3 of them the LIN2011 course) | Accurate - matched the positive consensus and stayed scoped to LIN2011 |
| 4 | Does Ethan Kutlu still work at UF? | No — he once worked at UF but is now at a different school. | "No, Ethan Kutlu no longer works at the University of Florida," cited to the review stating he left. | Relevant (all 5 chunks were Kutlu reviews) | Accurate - correctly answered "no", yet did not reference specific new school. Although this is not a primary detail. |
| 5 | What is the overall rating of professor David Pharies? | List of the individual student ratings. | Listed the per-review quality ratings found: 1/5, 5/5, and 2/5, each cited. | Partially relevant (3 Pharies chunks; final 2 were off-target Steffi Wulff reviews) | Accurate (within grounding) - no aggregate score exists in the chunks, so listing per-review ratings is the faithful answer |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
How do students feel about the work load in Professor Kaan's classes?

**What the system returned:**
"Students have mixed feelings about the workload in Professor Kaan's classes. Some students found the material to be "kinda tricky" but manageable if they stayed up with the reading and assignments [5], while another student mentioned that there were "lots of homework" [5]. However, no student explicitly complained about the workload being excessive."

**Root cause (tied to a specific pipeline stage):**
The issue with this response is that it doesn't properly describe the negative reviews for Dr. Kaan, which did stem from work. It suggests students did not complain about excessive workload, but students gave negative reviews suggesting they would not take a class with her again for this reason. This is clearly an issue with the retrieval step and the chosen top chunks, not representing the full dimension of perspectives needed to answer this query. To make matters worse, one of the chunks was not even for professor Kaan and was for Dr. Kutlu of a similar name. 

**What you would change to fix it:**
I would consider using a larger top-k value such as 7 or 8. This may provide more context where some responses lacked. Although, this is not a solution to the other problem of retrieving stray reviews for other professors. I think after collecting the larger amount of queries, I would add a layer of refinement to ensure only professor-in-question queries are sustained.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
One major aspect of the spec I appreciated was the guidance on prompting. It providing helpful tips and guiding suggestions to make sure I build explicit prompts for my AI assisting tools to ensure their outputs would reflect my expectation.

**One way your implementation diverged from the spec, and why:**
My implementation diverged from the spec simply in ways that benefited my project for its domain. My approach to chunking was slightly more unique then the spec seemed to anticipate, but I saw it a valid divergence for my data format. I also took my own creative privilege with the theme to, again, reflect my domain topic.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
I provided Claude the Chunking Strategy sections of the planning document, a thorough break down of the kind of data I am working with, and an example html file so it can provide chunking code specific to the Rate my Professor pages'. 

- *What it produced:*
It produced a content-aware chunking script as I requested, but included ingestion methods which take in urls and retrieve the html file.

- *What I changed or overrode:*
The ingestion was not accurate to my approach as I had intended to use local files. I changed this to use POSIX methods that read the local files directly and not collect from external sources.

**Instance 2**

- *What I gave the AI:*
For the interface I provided Claude Code the reqiurement to use gradio and update the requirements.txt accordingly. I also outlined styling choices to fit my theme of a UF related guide, providing specifc colors.

- *What it produced:*
It produced a working UI that was well integrated with the pipeline, but it used only the colors I explicit mentionned: orange, blue, white, and beige. This was an issue beacauce it put only white text and for anywhere not with a dark background, the text was unreadable.

- *What I changed or overrode:*
I intstructed Claude to include black text on the specific sections where this was an issue.
