"""
app.py – Flask application for EvalAssist AI.

Routes:
  GET  /                    → Home page
  GET  /evaluate            → Evaluate page (form)
  GET  /how-it-works        → How It Works page
  GET  /ai-engine           → AI Engine page
  GET  /responsible-ai      → Responsible AI page
  GET  /faq                 → FAQ page
  GET  /docs                → Docs / Get Started page
  GET  /status              → Status check page

API:
  POST /api/evaluate        → JSON evaluation
  POST /api/rules           → JSON rule engine result
  POST /api/search          → JSON search result
  POST /api/minimax         → JSON minimax result
  GET  /api/selftest        → JSON self-test results
"""

from __future__ import annotations

import time
import traceback
from flask import Flask, render_template, request, jsonify, abort

from evaluator import evaluate, DEFAULT_RUBRIC, ValidationError
from reasoning import (
    apply_rules, search_bfs, search_dfs, search_ids,
    search_greedy, search_astar, minimax,
    bayes_update, fuzzy_membership, certainty_factor, dempster_shafer,
    SEARCH_GRAPH, SEARCH_HEURISTIC, SEARCH_EDGE_COST, DEFAULT_LEAVES,
)
from extract import extract_text, ExtractionError, SUPPORTED_EXTENSIONS

app = Flask(__name__)
app.config["DEBUG"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB


# ---------------------------------------------------------------------------
# In-memory session history (per process, not persisted)
# ---------------------------------------------------------------------------
_history: list[dict] = []


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html", active="home")


@app.route("/evaluate")
def evaluate_page():
    return render_template(
        "evaluate.html",
        active="evaluate",
        history=_history,
        default_rubric=DEFAULT_RUBRIC,
    )


@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html", active="how-it-works")


@app.route("/ai-engine")
def ai_engine():
    return render_template(
        "ai_engine.html",
        active="ai-engine",
        search_graph=SEARCH_GRAPH,
        heuristic=SEARCH_HEURISTIC,
        edge_cost=SEARCH_EDGE_COST,
        default_leaves=DEFAULT_LEAVES,
    )


@app.route("/responsible-ai")
def responsible_ai():
    return render_template("responsible_ai.html", active="responsible-ai")


@app.route("/faq")
def faq():
    return render_template("faq.html", active="faq")


@app.route("/docs")
def docs():
    return render_template("docs.html", active="docs")


@app.route("/status")
def status():
    return render_template("status.html", active="status")


# ---------------------------------------------------------------------------
# API: evaluate
# ---------------------------------------------------------------------------

@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    data = request.get_json(silent=True) or {}

    # File upload via multipart?
    if request.files.get("file"):
        f = request.files["file"]
        try:
            text = extract_text(f.read(), f.filename or "upload.bin")
        except ExtractionError as exc:
            return jsonify({"error": str(exc)}), 400
        data["answer"] = text

    answer      = data.get("answer", "").strip()
    question    = data.get("question", "").strip()
    label       = data.get("label", "").strip()
    max_marks   = data.get("max_marks", 10)
    raw_rubric  = data.get("rubric", "")
    mode        = data.get("mode", "passage")

    # Parse rubric
    if isinstance(raw_rubric, list):
        rubric = raw_rubric
    else:
        rubric = [line.strip() for line in raw_rubric.splitlines() if line.strip()]

    try:
        result = evaluate(answer, rubric, float(max_marks), mode=mode)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Evaluation error: {exc}"}), 500

    # Store in session history
    _history.insert(0, {
        "label":            label or "Untitled",
        "question":         question[:80] + "…" if len(question) > 80 else question,
        "max_marks":        result["total_marks_available"],
        "suggested":        result["total_marks_suggested"],
        "overall_R":        result["overall_R"],
        "n_criteria":       len(result["criteria"]),
        "timestamp":        time.strftime("%H:%M"),
    })
    if len(_history) > 20:
        _history.pop()

    return jsonify(result)


# ---------------------------------------------------------------------------
# API: multipart file-upload evaluate (separate endpoint for form POST)
# ---------------------------------------------------------------------------

@app.route("/api/evaluate/upload", methods=["POST"])
def api_evaluate_upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file provided."}), 400
    try:
        text = extract_text(f.read(), f.filename or "upload.bin")
    except ExtractionError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"text": text})


# ---------------------------------------------------------------------------
# API: rule engine
# ---------------------------------------------------------------------------

@app.route("/api/rules", methods=["POST"])
def api_rules():
    data = request.get_json(silent=True) or {}
    completeness = float(data.get("completeness", 0.5))
    correctness  = float(data.get("correctness", 0.5))
    completeness = max(0.0, min(1.0, completeness))
    correctness  = max(0.0, min(1.0, correctness))
    return jsonify(apply_rules(completeness, correctness))


# ---------------------------------------------------------------------------
# API: search algorithms
# ---------------------------------------------------------------------------

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(silent=True) or {}
    algo = data.get("algorithm", "bfs").lower()

    algorithms = {
        "bfs":     search_bfs,
        "dfs":     search_dfs,
        "ids":     search_ids,
        "greedy":  search_greedy,
        "astar":   search_astar,
    }
    fn = algorithms.get(algo)
    if not fn:
        return jsonify({"error": f"Unknown algorithm: {algo}"}), 400

    return jsonify(fn())


# ---------------------------------------------------------------------------
# API: minimax
# ---------------------------------------------------------------------------

@app.route("/api/minimax", methods=["POST"])
def api_minimax():
    data    = request.get_json(silent=True) or {}
    leaves  = data.get("leaves", DEFAULT_LEAVES)
    ab      = bool(data.get("alpha_beta", False))

    if not isinstance(leaves, list) or len(leaves) not in (2, 4, 8):
        return jsonify({"error": "leaves must be a list of 2, 4, or 8 integers"}), 400

    return jsonify(minimax(leaves, alpha_beta=ab))


# ---------------------------------------------------------------------------
# API: uncertainty tools
# ---------------------------------------------------------------------------

@app.route("/api/bayes", methods=["POST"])
def api_bayes():
    data = request.get_json(silent=True) or {}
    return jsonify(bayes_update(
        float(data.get("prior", 0.5)),
        float(data.get("likelihood", 0.8)),
        float(data.get("false_positive", 0.2)),
    ))


@app.route("/api/fuzzy", methods=["POST"])
def api_fuzzy():
    data = request.get_json(silent=True) or {}
    score = max(0.0, min(1.0, float(data.get("score", 0.5))))
    return jsonify(fuzzy_membership(score))


@app.route("/api/dempster", methods=["POST"])
def api_dempster():
    data = request.get_json(silent=True) or {}
    return jsonify(dempster_shafer(
        float(data.get("m1", 0.6)),
        float(data.get("m2", 0.7)),
    ))


# ---------------------------------------------------------------------------
# API: self-test
# ---------------------------------------------------------------------------

@app.route("/api/selftest")
def api_selftest():
    checks = []

    def run(name: str, fn):
        t0 = time.perf_counter()
        try:
            fn()
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            checks.append({"name": name, "status": "pass", "ms": elapsed})
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            checks.append({"name": name, "status": "fail",
                            "ms": elapsed, "error": str(exc)})

    # Check 1: empty answer raises ValidationError
    def c1():
        try:
            evaluate("", DEFAULT_RUBRIC, 10)
            raise AssertionError("Expected ValidationError for empty answer")
        except ValidationError:
            pass

    # Check 2: default rubric → 4 criteria
    def c2():
        r = evaluate("BFS uses a queue to explore nodes level by level.", [], 10)
        assert len(r["criteria"]) == 4, f"Expected 4 criteria, got {len(r['criteria'])}"

    # Check 3: custom rubric → correct count
    def c3():
        r = evaluate("Test answer about algorithms.", ["Criterion A", "Criterion B"], 20)
        assert len(r["criteria"]) == 2

    # Check 4: marks sum check
    def c4():
        r = evaluate("BFS explores nodes level by level using a queue.", DEFAULT_RUBRIC, 20)
        total = sum(cr["marks_suggested"] for cr in r["criteria"])
        assert total <= 20.01, f"Total {total} exceeds max 20"
        assert abs(sum(cr["marks_available"] for cr in r["criteria"]) - 20) < 0.01

    # Check 5: rule engine R1
    def c5():
        res = apply_rules(0.9, 0.9)
        assert res["fired_rule"] == "R1"

    # Check 6: rule engine R2
    def c6():
        res = apply_rules(0.2, 0.8)
        assert res["fired_rule"] == "R2"

    # Check 7: minimax default leaves = 3
    def c7():
        res = minimax([3, 5, 2, 9], alpha_beta=False)
        assert res["root_value"] == 3, f"Expected 3, got {res['root_value']}"

    # Check 8: minimax with alpha-beta = 3
    def c8():
        res = minimax([3, 5, 2, 9], alpha_beta=True)
        assert res["root_value"] == 3

    # Check 9: .jpg rejected
    def c9():
        try:
            extract_text(b"fake", "image.jpg")
            raise AssertionError("Expected ExtractionError for .jpg")
        except ExtractionError:
            pass

    # Check 10: pages return 200
    def c10():
        with app.test_client() as client:
            for path in ["/", "/evaluate", "/how-it-works",
                         "/ai-engine", "/responsible-ai",
                         "/faq", "/docs", "/status"]:
                resp = client.get(path)
                assert resp.status_code == 200, f"{path} returned {resp.status_code}"

    for name, fn in [
        ("Empty answer raises error", c1),
        ("Default rubric → 4 criteria", c2),
        ("Custom 2-criteria rubric", c3),
        ("Marks sum ≤ max_marks", c4),
        ("Rule R1: high score", c5),
        ("Rule R2: review needed", c6),
        ("Minimax [3,5,2,9] = 3", c7),
        ("Minimax + alpha-beta = 3", c8),
        (".jpg file rejected", c9),
        ("All page routes → 200", c10),
    ]:
        run(name, fn)

    all_pass = all(c["status"] == "pass" for c in checks)
    return jsonify({"checks": checks, "all_pass": all_pass})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File exceeds the 8 MB limit."}), 413


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
