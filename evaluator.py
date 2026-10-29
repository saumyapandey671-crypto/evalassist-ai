"""
evaluator.py – core scoring engine for EvalAssist AI.

For each criterion:
  S  = TF-IDF cosine similarity (criterion vs. answer or best sentence)
  K  = keyword coverage (share of criterion content-words found in answer)
  R  = min(1, 0.65·S + 0.35·K)
  marks_awarded = (max_marks / n_criteria) × R

Bands:
  R ≥ 0.75  → Strong coverage
  R 0.45–0.74 → Partial coverage
  R < 0.45  → Limited evidence
"""

from __future__ import annotations

import re
import math
from typing import TypedDict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Simple English stop-word list (subset – sufficient for keyword extraction)
# ---------------------------------------------------------------------------
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "we", "you",
    "he", "she", "they", "them", "their", "our", "your", "his", "her",
    "not", "no", "so", "if", "then", "than", "about", "up", "out",
    "into", "over", "after", "before", "between", "through", "during",
    "each", "all", "both", "any", "some", "such", "only", "also",
    "use", "used", "using",
}

DEFAULT_RUBRIC = [
    "Define the BFS algorithm and explain its core purpose",
    "Describe the data structure used by BFS and why it is appropriate",
    "Explain the time and space complexity of BFS with justification",
    "Compare BFS with depth-first search and state when BFS is preferred",
]

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class CriterionResult(TypedDict):
    criterion: str
    S: float          # cosine similarity (0–1)
    K: float          # keyword coverage (0–1)
    R: float          # combined ratio (0–1)
    marks_available: float
    marks_suggested: float
    band: str
    feedback: str
    matched_words: list[str]
    missing_words: list[str]
    matched_sentence: str  # best-matching sentence (passage mode)

class EvaluationResult(TypedDict):
    criteria: list[CriterionResult]
    total_marks_available: float
    total_marks_suggested: float
    overall_R: float


class ValidationError(ValueError):
    """Raised for invalid inputs with a user-friendly message."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sentences(text: str) -> list[str]:
    """Split *text* into sentences (simple regex split)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 10]


def _stem(word: str) -> str:
    """Very light Porter-style suffix stripping (no external library)."""
    w = word.lower()
    for suffix in ("ing", "tion", "tions", "ed", "ly", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) > 3:
            return w[: -len(suffix)]
    return w


def _content_words(text: str) -> list[str]:
    """Return stemmed content words (length > 2, not stop-words)."""
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return [
        _stem(t) for t in tokens
        if len(t) > 2 and t not in _STOP_WORDS
    ]


def _tfidf_cosine(a: str, b: str) -> float:
    """Cosine similarity between two strings using TF-IDF."""
    try:
        vec = TfidfVectorizer(stop_words="english")
        tfidf = vec.fit_transform([a, b])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return float(sim)
    except ValueError:
        return 0.0


def _best_sentence_sim(criterion: str, answer: str) -> tuple[float, str]:
    """
    Return (max_similarity, best_sentence) by comparing the criterion
    against each sentence in the answer.
    """
    sents = _sentences(answer)
    if not sents:
        return 0.0, ""
    best_sim = 0.0
    best_sent = sents[0]
    for sent in sents:
        s = _tfidf_cosine(criterion, sent)
        if s > best_sim:
            best_sim = s
            best_sent = sent
    return best_sim, best_sent


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_inputs(answer: str, max_marks: int | float) -> None:
    """Raise ValidationError with a friendly message if inputs are invalid."""
    if not answer or not answer.strip():
        raise ValidationError(
            "The answer field is empty. Please paste or upload an answer before evaluating."
        )
    try:
        m = float(max_marks)
    except (TypeError, ValueError):
        raise ValidationError("Maximum marks must be a number.")
    if m < 1 or m > 100:
        raise ValidationError(
            f"Maximum marks must be between 1 and 100 (got {max_marks})."
        )


# ---------------------------------------------------------------------------
# Core scorer
# ---------------------------------------------------------------------------

def score_criterion(
    criterion: str,
    answer: str,
    marks_available: float,
    mode: str = "passage",
) -> CriterionResult:
    """
    Score a single criterion against the full answer.

    mode = "passage"  → use best-matching sentence for S
    mode = "whole"    → use the entire answer for S
    """
    # --- Similarity (S) ---
    if mode == "passage":
        S, matched_sentence = _best_sentence_sim(criterion, answer)
    else:
        S = _tfidf_cosine(criterion, answer)
        matched_sentence = ""

    # --- Keyword coverage (K) ---
    crit_words = _content_words(criterion)
    ans_stems = set(_content_words(answer))

    matched_words: list[str] = []
    missing_words: list[str] = []
    seen: set[str] = set()

    for raw_token in re.findall(r"[a-zA-Z]+", criterion.lower()):
        if len(raw_token) <= 2 or raw_token in _STOP_WORDS:
            continue
        stem = _stem(raw_token)
        if stem in seen:
            continue
        seen.add(stem)
        if stem in ans_stems:
            matched_words.append(raw_token)
        else:
            missing_words.append(raw_token)

    K = len(matched_words) / max(len(matched_words) + len(missing_words), 1)

    # --- Combined ratio (R) ---
    R = min(1.0, 0.65 * S + 0.35 * K)

    # --- Marks ---
    marks_suggested = round(marks_available * R, 2)

    # --- Band & feedback ---
    if R >= 0.75:
        band = "Strong coverage"
        feedback = "Good coverage of this criterion."
    elif R >= 0.45:
        band = "Partial coverage"
        top_missing = missing_words[:4]
        if top_missing:
            feedback = (
                f"Partial coverage. Consider addressing: "
                + ", ".join(top_missing) + "."
            )
        else:
            feedback = "Partial coverage. Expand your explanation."
    else:
        band = "Limited evidence"
        top_missing = missing_words[:4]
        if top_missing:
            feedback = (
                f"Limited evidence. Key missing concepts: "
                + ", ".join(top_missing) + "."
            )
        else:
            feedback = "Limited evidence for this criterion."

    return CriterionResult(
        criterion=criterion,
        S=round(S, 4),
        K=round(K, 4),
        R=round(R, 4),
        marks_available=round(marks_available, 2),
        marks_suggested=marks_suggested,
        band=band,
        feedback=feedback,
        matched_words=matched_words,
        missing_words=missing_words,
        matched_sentence=matched_sentence,
    )


def evaluate(
    answer: str,
    rubric: list[str],
    max_marks: float,
    mode: str = "passage",
) -> EvaluationResult:
    """
    Evaluate an answer against all rubric criteria.

    Returns an EvaluationResult dict ready to be serialised as JSON.
    """
    validate_inputs(answer, max_marks)

    criteria = [c.strip() for c in rubric if c.strip()]
    if not criteria:
        criteria = DEFAULT_RUBRIC[:]

    n = len(criteria)
    marks_per = max_marks / n

    results: list[CriterionResult] = []
    for crit in criteria:
        results.append(score_criterion(crit, answer, marks_per, mode=mode))

    total_suggested = sum(r["marks_suggested"] for r in results)
    overall_R = sum(r["R"] for r in results) / n

    return EvaluationResult(
        criteria=results,
        total_marks_available=float(max_marks),
        total_marks_suggested=round(total_suggested, 2),
        overall_R=round(overall_R, 4),
    )
