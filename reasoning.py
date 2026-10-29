"""
reasoning.py – rule engine, search demos, minimax, and uncertainty tools.

All functions here are for the /ai-engine educational demo page.
They are NOT used in the actual scoring pipeline.
"""

from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------------------
# Rule Engine
# ---------------------------------------------------------------------------

class RuleResult:
    def __init__(self, rule: str, fired: bool, conclusion: str, trace: list[str]):
        self.rule = rule
        self.fired = fired
        self.conclusion = conclusion
        self.trace = trace


def apply_rules(completeness: float, correctness: float) -> dict[str, Any]:
    """
    Apply the three provisional-mark rules and return a trace.

    R1: completeness >= 0.75 AND correctness >= 0.75 → HIGH provisional score
    R2: completeness < 0.40 OR  correctness < 0.40  → Detailed review needed
    R3: otherwise → Partial score, targeted feedback
    """
    trace: list[str] = []
    fired_rule: str = ""
    conclusion: str = ""

    trace.append(f"Inputs: completeness={completeness:.2f}, correctness={correctness:.2f}")

    # R1
    if completeness >= 0.75 and correctness >= 0.75:
        fired_rule = "R1"
        conclusion = "High provisional score – strong evidence on both dimensions."
        trace.append("R1 FIRED: completeness ≥ 0.75 AND correctness ≥ 0.75")
    # R2
    elif completeness < 0.40 or correctness < 0.40:
        fired_rule = "R2"
        conclusion = "Detailed teacher review needed – one or both signals are weak."
        trace.append("R1 skipped: condition not met")
        trace.append(
            f"R2 FIRED: completeness < 0.40 ({completeness:.2f}) OR "
            f"correctness < 0.40 ({correctness:.2f})"
        )
    # R3
    else:
        fired_rule = "R3"
        conclusion = "Partial score – provide targeted feedback on gaps."
        trace.append("R1 skipped: condition not met")
        trace.append("R2 skipped: both values are ≥ 0.40")
        trace.append("R3 FIRED: default – partial score")

    trace.append(f"Conclusion: {conclusion}")

    return {
        "fired_rule": fired_rule,
        "conclusion": conclusion,
        "trace": trace,
        "completeness": completeness,
        "correctness": correctness,
    }


# ---------------------------------------------------------------------------
# Search algorithm state graph
# ---------------------------------------------------------------------------

# Evaluation states: S0 (start) → S6 (goal)
# Graph as adjacency list; dead-end nodes have no children.
SEARCH_GRAPH: dict[str, list[str]] = {
    "S0": ["S1", "S2"],
    "S1": ["S3", "S4"],
    "S2": ["S5"],
    "S3": [],          # dead end
    "S4": ["S6"],      # S6 is the goal
    "S5": [],          # dead end
    "S6": [],          # goal
}

SEARCH_HEURISTIC: dict[str, float] = {
    "S0": 4,
    "S1": 2,
    "S2": 3,
    "S3": 5,  # dead end – far
    "S4": 1,
    "S5": 4,  # dead end – far
    "S6": 0,  # goal
}

SEARCH_EDGE_COST: dict[tuple[str, str], float] = {
    ("S0", "S1"): 1,
    ("S0", "S2"): 2,
    ("S1", "S3"): 3,
    ("S1", "S4"): 1,
    ("S2", "S5"): 1,
    ("S4", "S6"): 1,
}


def _reconstruct(came_from: dict[str, str | None], node: str) -> list[str]:
    path: list[str] = []
    cur: str | None = node
    while cur is not None:
        path.append(cur)
        cur = came_from.get(cur)
    return path[::-1]


def search_bfs(goal: str = "S6") -> dict[str, Any]:
    from collections import deque
    frontier: deque[str] = deque(["S0"])
    came_from: dict[str, str | None] = {"S0": None}
    visited: list[str] = []
    steps: list[dict] = []

    while frontier:
        node = frontier.popleft()
        visited.append(node)
        steps.append({"expand": node, "frontier": list(frontier), "visited": visited[:]})
        if node == goal:
            return {"algorithm": "BFS", "path": _reconstruct(came_from, node),
                    "visited": visited, "steps": steps, "found": True}
        for child in SEARCH_GRAPH.get(node, []):
            if child not in came_from:
                came_from[child] = node
                frontier.append(child)

    return {"algorithm": "BFS", "path": [], "visited": visited, "steps": steps, "found": False}


def search_dfs(goal: str = "S6") -> dict[str, Any]:
    stack: list[str] = ["S0"]
    came_from: dict[str, str | None] = {"S0": None}
    visited: list[str] = []
    steps: list[dict] = []

    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.append(node)
        steps.append({"expand": node, "frontier": stack[:], "visited": visited[:]})
        if node == goal:
            return {"algorithm": "DFS", "path": _reconstruct(came_from, node),
                    "visited": visited, "steps": steps, "found": True}
        for child in reversed(SEARCH_GRAPH.get(node, [])):
            if child not in came_from:
                came_from[child] = node
                stack.append(child)

    return {"algorithm": "DFS", "path": [], "visited": visited, "steps": steps, "found": False}


def search_ids(goal: str = "S6") -> dict[str, Any]:
    """Iterative deepening DFS."""
    all_visited: list[str] = []
    steps: list[dict] = []

    def dls(node: str, depth: int, came_from: dict) -> str | None:
        if node == goal:
            return node
        if depth == 0:
            return None
        for child in SEARCH_GRAPH.get(node, []):
            if child not in came_from:
                came_from[child] = node
                all_visited.append(child)
                steps.append({"expand": child, "depth": depth - 1})
                result = dls(child, depth - 1, came_from)
                if result:
                    return result
        return None

    for limit in range(7):
        cf: dict[str, str | None] = {"S0": None}
        all_visited.clear()
        steps.clear()
        all_visited.append("S0")
        if dls("S0", limit, cf) == goal:
            return {
                "algorithm": "Iterative Deepening",
                "path": _reconstruct(cf, goal),
                "visited": all_visited,
                "steps": steps,
                "found": True,
                "depth_limit": limit,
            }

    return {"algorithm": "Iterative Deepening", "path": [], "visited": all_visited,
            "steps": steps, "found": False}


def search_greedy(goal: str = "S6") -> dict[str, Any]:
    import heapq
    heap: list[tuple[float, str]] = [(SEARCH_HEURISTIC["S0"], "S0")]
    came_from: dict[str, str | None] = {"S0": None}
    visited: list[str] = []
    steps: list[dict] = []

    while heap:
        h, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.append(node)
        steps.append({"expand": node, "h": h, "visited": visited[:]})
        if node == goal:
            return {"algorithm": "Greedy Best-First", "path": _reconstruct(came_from, node),
                    "visited": visited, "steps": steps, "found": True}
        for child in SEARCH_GRAPH.get(node, []):
            if child not in visited:
                came_from[child] = node
                heapq.heappush(heap, (SEARCH_HEURISTIC[child], child))

    return {"algorithm": "Greedy Best-First", "path": [], "visited": visited,
            "steps": steps, "found": False}


def search_astar(goal: str = "S6") -> dict[str, Any]:
    import heapq
    heap: list[tuple[float, str]] = [(SEARCH_HEURISTIC["S0"], "S0")]
    came_from: dict[str, str | None] = {"S0": None}
    g_cost: dict[str, float] = {"S0": 0.0}
    visited: list[str] = []
    steps: list[dict] = []

    while heap:
        f, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.append(node)
        steps.append({"expand": node, "f": f, "g": g_cost[node], "visited": visited[:]})
        if node == goal:
            return {"algorithm": "A*", "path": _reconstruct(came_from, node),
                    "visited": visited, "steps": steps, "found": True}
        for child in SEARCH_GRAPH.get(node, []):
            edge = (node, child)
            new_g = g_cost[node] + SEARCH_EDGE_COST.get(edge, 1)
            if child not in g_cost or new_g < g_cost[child]:
                g_cost[child] = new_g
                came_from[child] = node
                f_val = new_g + SEARCH_HEURISTIC[child]
                heapq.heappush(heap, (f_val, child))

    return {"algorithm": "A*", "path": [], "visited": visited, "steps": steps, "found": False}


# ---------------------------------------------------------------------------
# Minimax with Alpha-Beta pruning
# ---------------------------------------------------------------------------

# Default tree: [3, 5, 2, 9] – four leaves, depth 2
# Internal tree structure: MAX node at root, MIN nodes at depth 1
DEFAULT_LEAVES = [3, 5, 2, 9]


def minimax(leaves: list[int], alpha_beta: bool = False) -> dict[str, Any]:
    """
    Minimax on a balanced binary tree built from *leaves*.
    Returns the root value and a trace of nodes evaluated.
    """
    trace: list[dict] = []
    pruned: list[str] = []

    def _minimax(node_id: str, depth: int, is_max: bool,
                 leaf_iter: list[int], idx: list[int],
                 alpha: float, beta: float) -> float:
        if depth == 0:
            val = leaf_iter[idx[0]]
            idx[0] += 1
            trace.append({"node": node_id, "type": "leaf", "value": val})
            return float(val)

        best = -math.inf if is_max else math.inf
        for i, child_suffix in enumerate(["L", "R"]):
            child_id = node_id + child_suffix
            val = _minimax(child_id, depth - 1, not is_max,
                           leaf_iter, idx, alpha, beta)
            if is_max:
                best = max(best, val)
                alpha = max(alpha, best)
            else:
                best = min(best, val)
                beta = min(beta, best)
            if alpha_beta and beta <= alpha:
                pruned.append(child_id)
                trace.append({"node": child_id, "type": "pruned"})
                break

        trace.append({"node": node_id, "type": "max" if is_max else "min", "value": best})
        return best

    # Depth of tree = log2(len(leaves))
    depth = int(math.log2(len(leaves)))
    idx = [0]
    root_val = _minimax("root", depth, True, leaves, idx, -math.inf, math.inf)

    return {
        "root_value": root_val,
        "trace": trace,
        "pruned": pruned,
        "alpha_beta": alpha_beta,
        "leaves": leaves,
    }


# ---------------------------------------------------------------------------
# Uncertainty tools (educational demos)
# ---------------------------------------------------------------------------

def bayes_update(prior: float, likelihood: float, false_positive: float) -> dict[str, Any]:
    """
    P(H|E) = P(E|H)·P(H) / [P(E|H)·P(H) + P(E|¬H)·P(¬H)]
    """
    p_h = prior
    p_e_given_h = likelihood
    p_e_given_not_h = false_positive
    p_not_h = 1 - p_h

    numerator = p_e_given_h * p_h
    denominator = numerator + p_e_given_not_h * p_not_h

    posterior = numerator / denominator if denominator > 0 else 0.0

    return {
        "prior": prior,
        "likelihood": likelihood,
        "false_positive": false_positive,
        "posterior": round(posterior, 4),
        "formula": (
            f"P(H|E) = ({p_e_given_h:.2f} × {p_h:.2f}) / "
            f"({p_e_given_h:.2f} × {p_h:.2f} + "
            f"{p_e_given_not_h:.2f} × {p_not_h:.2f}) = {posterior:.4f}"
        ),
    }


def fuzzy_membership(score: float) -> dict[str, float]:
    """
    Triangular fuzzy membership functions for Low, Medium, High.
    score is in [0, 1].
    """
    def tri(x: float, a: float, b: float, c: float) -> float:
        if x <= a or x >= c:
            return 0.0
        if x <= b:
            return (x - a) / (b - a)
        return (c - x) / (c - b)

    return {
        "low":    round(tri(score, -0.1, 0.0, 0.5), 4),
        "medium": round(tri(score, 0.2, 0.5, 0.8), 4),
        "high":   round(tri(score, 0.5, 1.0, 1.1), 4),
    }


def certainty_factor(cf_h: float, cf_e: float) -> float:
    """
    Simple certainty factor combination: CF(H, E) = CF(H) × max(0, CF(E))
    Values in [-1, 1].
    """
    return round(cf_h * max(0.0, cf_e), 4)


def dempster_shafer(m1_A: float, m2_A: float) -> dict[str, Any]:
    """
    Combine two basic probability assignments for hypothesis A
    using Dempster's rule (simplified: single focal element A + remainder Θ).
    """
    m1_theta = 1 - m1_A
    m2_theta = 1 - m2_A

    # Conflict: m1_A × m2_¬A + m1_¬A × m2_A  – approximated as 0 here (single hypothesis)
    # Combined m(A) = (m1_A × m2_A + m1_A × m2_theta + m1_theta × m2_A) / (1 - K)
    # For single-element frame K = 0
    joint_A = m1_A * m2_A + m1_A * m2_theta + m1_theta * m2_A
    joint_theta = m1_theta * m2_theta
    total = joint_A + joint_theta
    combined = joint_A / total if total > 0 else 0.0

    return {
        "m1_A": m1_A,
        "m2_A": m2_A,
        "combined_A": round(combined, 4),
        "belief": round(combined, 4),
        "plausibility": round(combined + joint_theta / total if total > 0 else 1.0, 4),
    }
