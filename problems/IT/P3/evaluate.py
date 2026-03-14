"""
IT-P3: EventHorizon — Evaluator
================================
Usage:
    python evaluate.py --submission ./submission [--ground_truth ./ground_truth]

Reads:
    submission/load_test_results.json   — throughput and latency metrics
    submission/cost_estimate.json       — cost model
    submission/architecture.md or .png — C4 architecture artefact
    submission/iac/                     — IaC source directory
    submission/src/                     — function/service source directory

Outputs JSON:
    {
      "total": 0-100,
      "breakdown": {
        "throughput":    {"score": X, "max": 30},
        "p99_latency":   {"score": X, "max": 25},
        "correctness":   {"score": X, "max": 25},
        "architecture":  {"score": X, "max": 20}
      },
      "errors": []
    }
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Throughput (30 pts)
THROUGHPUT_FULL_EPS = 10_000    # events/sec for full marks
THROUGHPUT_HALF_EPS = 1_000

# P99 latency (25 pts)
P99_EXCELLENT_MS = 100
P99_ACCEPTABLE_MS = 1_000

# Correctness (25 pts)
# oversell_count must be 0 for full correctness marks
# error_rate_pct must be < 1% for full marks

# Architecture (20 pts) — document-based heuristics

GROUND_TRUTH_PATH = "./ground_truth"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Tuple[Optional[Dict], Optional[str]]:
    if not path.exists():
        return None, f"File not found: {path}"
    try:
        with open(path) as f:
            return json.load(f), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error in {path}: {exc}"


def linear_scale(value: float, low: float, high: float, max_score: float) -> float:
    if high == low:
        return max_score if value >= high else 0.0
    ratio = (value - low) / (high - low)
    return round(max(0.0, min(max_score, ratio * max_score)), 2)


def inverse_linear_scale(value: float, low_threshold: float, high_threshold: float, max_score: float) -> float:
    if value <= low_threshold:
        return max_score
    if value >= high_threshold:
        return 0.0
    ratio = (high_threshold - value) / (high_threshold - low_threshold)
    return round(ratio * max_score, 2)


# ---------------------------------------------------------------------------
# Score sections
# ---------------------------------------------------------------------------


def score_throughput(results: Optional[Dict], errors: List[str]) -> float:
    """Score throughput (30 pts)."""
    max_score = 30.0
    if results is None:
        errors.append("load_test_results.json missing — throughput score is 0")
        return 0.0

    eps = results.get("throughput_eps", 0)
    if not isinstance(eps, (int, float)):
        errors.append("throughput_eps must be a number")
        return 0.0

    return linear_scale(float(eps), THROUGHPUT_HALF_EPS, THROUGHPUT_FULL_EPS, max_score)


def score_p99_latency(results: Optional[Dict], errors: List[str]) -> float:
    """Score P99 latency (25 pts)."""
    max_score = 25.0
    if results is None:
        return 0.0

    p99 = results.get("p99_latency_ms", float("inf"))
    if not isinstance(p99, (int, float)):
        errors.append("p99_latency_ms must be a number")
        return 0.0

    return inverse_linear_scale(float(p99), P99_EXCELLENT_MS, P99_ACCEPTABLE_MS, max_score)


def score_correctness(results: Optional[Dict], submission_dir: Path, errors: List[str]) -> float:
    """Score correctness (25 pts).

    Sub-criteria:
        - Zero oversell (15 pts hard gate — 0 if oversell_count > 0)
        - Error rate < 1% (10 pts)
    """
    max_score = 25.0
    if results is None:
        errors.append("load_test_results.json missing — correctness score is 0")
        return 0.0

    oversell = results.get("oversell_count", 1)  # default to 1 (penalised) if missing
    error_rate = results.get("error_rate_pct", 100.0)

    if not isinstance(oversell, (int, float)):
        errors.append("oversell_count must be a number")
        oversell = 1
    if not isinstance(error_rate, (int, float)):
        errors.append("error_rate_pct must be a number")
        error_rate = 100.0

    # Hard gate for oversell
    if int(oversell) > 0:
        errors.append(f"Oversell detected: {int(oversell)} items over-sold — zero tolerance, 0/15 for this sub-criterion")
        oversell_score = 0.0
    else:
        oversell_score = 15.0

    # Error rate
    error_score = 10.0 if float(error_rate) < 1.0 else inverse_linear_scale(float(error_rate), 1.0, 10.0, 10.0)

    return min(oversell_score + error_score, max_score)


def score_architecture(submission_dir: Path, errors: List[str]) -> float:
    """Score architecture (20 pts).

    Sub-criteria:
        - Architecture document (C4 or equivalent) present (8 pts)
        - IaC directory non-empty (6 pts)
        - Source code directory non-empty (6 pts)
    """
    max_score = 20.0
    score = 0.0

    arch_md = submission_dir / "architecture.md"
    arch_png = submission_dir / "architecture.png"
    if arch_md.exists() or arch_png.exists():
        if arch_md.exists():
            text = arch_md.read_text(errors="replace").lower()
            keywords = ["lambda", "queue", "sqs", "kafka", "redis", "event", "saga", "idempoten", "serverless"]
            keyword_count = sum(1 for kw in keywords if kw in text)
            arch_score = min(8.0, 2.0 + keyword_count * 0.75)
        else:
            arch_score = 5.0  # image present, can't parse content
        score += arch_score
    else:
        errors.append("No architecture document found (architecture.md or architecture.png)")

    iac_dir = submission_dir / "iac"
    if iac_dir.exists() and any(iac_dir.iterdir()):
        score += 6.0
    else:
        errors.append("submission/iac/ directory missing or empty")

    src_dir = submission_dir / "src"
    if src_dir.exists() and any(src_dir.iterdir()):
        score += 6.0
    else:
        errors.append("submission/src/ directory missing or empty")

    return min(score, max_score)


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------


def evaluate(submission_dir: Path, ground_truth_dir: Optional[Path]) -> Dict:
    errors: List[str] = []

    results, results_err = load_json(submission_dir / "load_test_results.json")
    cost, cost_err = load_json(submission_dir / "cost_estimate.json")

    for err in [results_err, cost_err]:
        if err:
            errors.append(err)

    throughput_score = score_throughput(results, errors)
    latency_score = score_p99_latency(results, errors)
    correctness_score = score_correctness(results, submission_dir, errors)
    arch_score = score_architecture(submission_dir, errors)

    total = round(throughput_score + latency_score + correctness_score + arch_score, 2)

    return {
        "total": total,
        "breakdown": {
            "throughput":   {"score": round(throughput_score, 2),   "max": 30},
            "p99_latency":  {"score": round(latency_score, 2),      "max": 25},
            "correctness":  {"score": round(correctness_score, 2),  "max": 25},
            "architecture": {"score": round(arch_score, 2),         "max": 20},
        },
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="IT-P3 EventHorizon — Evaluator")
    parser.add_argument("--submission", required=True, help="Path to submission directory")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH, help="Path to ground truth directory")
    args = parser.parse_args()

    submission_dir = Path(args.submission)
    ground_truth_dir = Path(args.ground_truth) if args.ground_truth else None

    if not submission_dir.exists():
        result = {
            "total": 0,
            "breakdown": {
                "throughput":   {"score": 0, "max": 30},
                "p99_latency":  {"score": 0, "max": 25},
                "correctness":  {"score": 0, "max": 25},
                "architecture": {"score": 0, "max": 20},
            },
            "errors": [f"Submission directory not found: {submission_dir}"],
        }
    else:
        result = evaluate(submission_dir, ground_truth_dir)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
