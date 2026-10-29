# EvalAssist AI

**Faster, fairer, explainable assignment feedback.**

EvalAssist AI is a locally-hosted Flask web application that helps teachers mark written answers against a rubric. The AI suggests provisional marks; the teacher reviews, edits, and approves the final score.

---

## Features

- **Rubric-based scoring** – define one criterion per line; EvalAssist scores each independently
- **TF-IDF cosine similarity** (S) combined with **keyword coverage** (K) into a transparent formula: `R = min(1, 0.65·S + 0.35·K)`
- **Best-matching sentence mode** – finds the most relevant sentence in the answer for each criterion
- **Explainable results** – matched/missing word chips, formula with real values, matched sentence
- **File upload** – .txt, .pdf, .docx up to 8 MB, processed locally
- **Teacher review panel** – edit marks, add comments, approve or return for re-marking
- **Session history** – in-memory only, cleared on restart; labelled "Not saved"
- **AI Engine demos** – rule engine, search algorithms (BFS/DFS/IDS/Greedy/A*), minimax with α-β pruning, Bayesian reasoning, fuzzy membership, certainty factors, Dempster-Shafer
- **Privacy-first** – nothing stored, nothing sent to external servers
- **Status check** – `/status` runs 10 built-in self-checks with pass/fail and timing

---

## Setup

### Requirements

- Python 3.10 or later
- pip

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

### Run tests

```bash
pytest tests/test_core.py -v
```

---

## Project structure

```
evalassist/
├── app.py              # Flask routes and API endpoints
├── evaluator.py        # Scoring engine (TF-IDF, keyword coverage, formula)
├── reasoning.py        # Rule engine, search algorithms, minimax, uncertainty
├── extract.py          # Text extraction from .txt, .pdf, .docx
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── evaluate.html
│   ├── how_it_works.html
│   ├── ai_engine.html
│   ├── responsible_ai.html
│   ├── faq.html
│   ├── docs.html
│   ├── status.html
│   └── 404.html
├── static/
│   ├── css/style.css
│   └── js/app.js
└── tests/
    └── test_core.py
```

---

## Scoring formula

For each rubric criterion:

| Signal | Description |
|--------|-------------|
| **S** | TF-IDF cosine similarity between the criterion and the answer (or best-matching sentence) |
| **K** | Share of criterion content words found in the answer |
| **R** | `min(1, 0.65·S + 0.35·K)` |
| **marks** | `(max_marks / n_criteria) × R` |

**Bands:**
- R ≥ 0.75 → Strong coverage
- 0.45 ≤ R < 0.75 → Partial coverage
- R < 0.45 → Limited evidence

> ⚠ The weights (0.65, 0.35) are a starting heuristic, not a validated grading model.

---

## Known limitations

- TF-IDF does not understand meaning — correct paraphrases without the exact keyword will score lower than expected
- Keyword matching is brittle with spelling mistakes or abbreviations
- Scanned PDFs produce no extractable text; OCR is not supported
- Feedback is template-based, not natural-language generated
- The scoring weights are a heuristic that has not been validated against human-marked data

---

## Responsible use

> **Use anonymised data — replace student names and IDs before uploading any file.**

> **Marks must be approved by a teacher before they are used for any formal purpose.**

EvalAssist is not suitable for:
- High-stakes exams without mandatory human review of every mark
- Handwritten answers (no handwriting recognition)
- Highly subjective essays without a well-defined rubric
- Any context where the teacher cannot or does not review each provisional score

---

## Pages

| URL | Page |
|-----|------|
| `/` | Home |
| `/evaluate` | Main evaluator (form + results) |
| `/how-it-works` | Scoring explanation + formula |
| `/ai-engine` | Interactive AI demos |
| `/responsible-ai` | Ethics, limitations, privacy |
| `/faq` | 10 frequently asked questions |
| `/docs` | Setup, API reference, troubleshooting |
| `/status` | Live self-check (10 checks) |

---

## API

**POST /api/evaluate** — JSON body:
```json
{
  "answer":    "Student's written answer text",
  "rubric":    "Criterion 1\nCriterion 2",
  "max_marks": 10,
  "mode":      "passage"
}
```

See `/docs` for the full API reference.

---

## Licence

© 2026 EvalAssist AI. For educational and research use.
