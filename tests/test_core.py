"""
tests/test_core.py – pytest test suite for EvalAssist AI core.

Covers:
 1. Empty answer raises ValidationError
 2. Default rubric gives 4 rows
 3. 3 custom criteria give 3 rows
 4. max_marks 20 → allocations sum to 20, total ≤ 20
 5. .jpg rejected (ExtractionError)
 6. Rules (0.9, 0.9) → R1
 7. Rules (0.2, 0.8) → R2
 8. Minimax [3,5,2,9] = 3 (no pruning)
 9. Minimax [3,5,2,9] = 3 (with alpha-beta)
10. 6,000-word answer evaluates in under 2 seconds
11. Every page route returns HTTP 200
"""

import sys
import os
import time
import pytest

# Ensure the project root is on sys.path so imports work when run from any cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluator import evaluate, ValidationError, DEFAULT_RUBRIC
from reasoning import apply_rules, minimax
from extract import extract_text, ExtractionError


# ── 1. Empty answer raises ValidationError ──────────────────────────

def test_empty_answer_raises():
    with pytest.raises(ValidationError, match="empty"):
        evaluate("", DEFAULT_RUBRIC, 10)


# ── 2. Default rubric gives 4 rows ─────────────────────────────────

def test_default_rubric_four_rows():
    answer = "BFS uses a queue to explore nodes level by level."
    result = evaluate(answer, [], 10)
    assert len(result["criteria"]) == 4, (
        f"Expected 4 criteria, got {len(result['criteria'])}"
    )


# ── 3. 3 custom criteria give 3 rows ───────────────────────────────

def test_three_custom_criteria():
    rubric = [
        "Define the algorithm",
        "Explain the time complexity",
        "Compare with other approaches",
    ]
    result = evaluate("BFS is a graph algorithm with O(V+E) complexity.", rubric, 30)
    assert len(result["criteria"]) == 3


# ── 4. max_marks 20: allocations sum to 20, total ≤ 20 ─────────────

def test_marks_allocation_sum_and_cap():
    answer = (
        "BFS explores all neighbours at the present depth level before moving to nodes "
        "at the next depth level. It uses a queue. Time complexity is O(V+E). "
        "Unlike DFS which uses a stack, BFS is better for shortest path problems."
    )
    result = evaluate(answer, DEFAULT_RUBRIC, 20)

    # Sum of marks_available should equal max_marks
    total_available = sum(cr["marks_available"] for cr in result["criteria"])
    assert abs(total_available - 20) < 0.01, (
        f"Expected marks_available sum = 20, got {total_available}"
    )

    # Total suggested must not exceed max_marks
    assert result["total_marks_suggested"] <= 20.01, (
        f"Suggested total {result['total_marks_suggested']} exceeds max 20"
    )

    # total_marks_available field
    assert result["total_marks_available"] == 20.0


# ── 5. .jpg rejected ────────────────────────────────────────────────

def test_jpg_rejected():
    with pytest.raises(ExtractionError):
        extract_text(b"\xff\xd8\xff fake image bytes", "photo.jpg")


# ── 6. Rules (0.9, 0.9) → R1 ────────────────────────────────────────

def test_rule_r1_fires():
    result = apply_rules(0.9, 0.9)
    assert result["fired_rule"] == "R1", (
        f"Expected R1, got {result['fired_rule']}"
    )


# ── 7. Rules (0.2, 0.8) → R2 ────────────────────────────────────────

def test_rule_r2_fires():
    result = apply_rules(0.2, 0.8)
    assert result["fired_rule"] == "R2", (
        f"Expected R2, got {result['fired_rule']}"
    )


# ── 8. Minimax [3,5,2,9] = 3 (no pruning) ──────────────────────────

def test_minimax_no_pruning():
    result = minimax([3, 5, 2, 9], alpha_beta=False)
    assert result["root_value"] == 3, (
        f"Expected root 3, got {result['root_value']}"
    )
    # With no pruning, no leaves should be pruned
    assert result["pruned"] == [], (
        f"Expected no pruning, got pruned={result['pruned']}"
    )


# ── 9. Minimax [3,5,2,9] = 3 (with alpha-beta) ─────────────────────

def test_minimax_alpha_beta():
    result = minimax([3, 5, 2, 9], alpha_beta=True)
    assert result["root_value"] == 3, (
        f"Expected root 3, got {result['root_value']}"
    )
    # With alpha-beta, at least one node should be pruned
    assert len(result["pruned"]) > 0, "Expected at least one pruned node with α-β"


# ── 10. 6,000-word answer evaluates in under 2 seconds ─────────────

def test_large_answer_speed():
    # ~6,000 words
    word = "algorithm queue vertex edge breadth depth complexity "
    answer = word * 860  # ≈ 6,020 words
    t0 = time.perf_counter()
    result = evaluate(answer, DEFAULT_RUBRIC, 10)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"Evaluation took {elapsed:.2f}s — expected < 2s"
    assert len(result["criteria"]) == 4


# ── 11. Every page route returns HTTP 200 ──────────────────────────

def test_all_pages_return_200():
    import importlib
    import app as app_module
    client = app_module.app.test_client()

    pages = [
        "/",
        "/evaluate",
        "/how-it-works",
        "/ai-engine",
        "/responsible-ai",
        "/faq",
        "/docs",
        "/status",
    ]
    for path in pages:
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"GET {path} returned {resp.status_code}, expected 200"
        )
