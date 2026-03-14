"""
IT-P1: SmartCity Digital Twin — Evaluator
==========================================
Usage:
    python evaluate.py --submission ./submission [--ground_truth ./ground_truth]

Reads:
    submission/benchmarks.json      — performance metrics from the benchmark harness
    submission/architecture.md      — written architecture document
    submission/docker-compose.yml   — runnable compose file

Outputs JSON to stdout:
    {
      "total": 0-100,
      "breakdown": {
        "data_ingestion":   {"score": X, "max": 25},
        "simulation_accuracy": {"score": X, "max": 30},
        "visualization":    {"score": X, "max": 25},
        "scalability":      {"score": X, "max": 20}
      },
      "errors": []
    }
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants — tweak these thresholds to match the judging rubric
# ---------------------------------------------------------------------------

# Data ingestion (25 pts)
INGESTION_EPS_FULL = 10_000        # events/sec needed for full marks
INGESTION_EPS_HALF = 1_000         # events/sec for half marks

# Simulation accuracy (30 pts)
# Mean Absolute Error on held-out traffic predictions (lower is better)
TRAFFIC_MAE_EXCELLENT = 0.05       # normalised 0-1 scale
TRAFFIC_MAE_ACCEPTABLE = 0.20

ENERGY_MAE_EXCELLENT = 0.05
ENERGY_MAE_ACCEPTABLE = 0.25

# Visualization (25 pts) — checked via documentation heuristics
# Scalability (20 pts)
CONCURRENT_USERS_FULL = 50
P99_LATENCY_EXCELLENT_MS = 500
P99_LATENCY_ACCEPTABLE_MS = 2_000

GROUND_TRUTH_PATH = "./ground_truth"   # placeholder — replace with actual path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Tuple[Optional[Dict], Optional[str]]:
    """Return (parsed_dict, None) or (None, error_message)."""
    if not path.exists():
        return None, f"File not found: {path}"
    try:
        with open(path) as f:
            return json.load(f), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error in {path}: {exc}"


def file_exists_nonzero(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def linear_scale(value: float, low: float, high: float, max_score: float) -> float:
    """Map value linearly from [low, high] -> [0, max_score]. Clamps at boundaries."""
    if high == low:
        return max_score if value >= high else 0.0
    ratio = (value - low) / (high - low)
    return round(max(0.0, min(max_score, ratio * max_score)), 2)


def inverse_linear_scale(value: float, low_threshold: float, high_threshold: float, max_score: float) -> float:
    """Inverse scale — lower value is better (e.g., MAE, latency)."""
    if value <= low_threshold:
        return max_score
    if value >= high_threshold:
        return 0.0
    ratio = (high_threshold - value) / (high_threshold - low_threshold)
    return round(ratio * max_score, 2)


# ---------------------------------------------------------------------------
# Scoring sections
# ---------------------------------------------------------------------------


def score_data_ingestion(benchmarks: Optional[Dict], errors: List[str]) -> float:
    """Score data ingestion pipeline (25 pts).

    Sub-criteria:
        - ingestion_rate_eps reported   (15 pts — linear)
        - benchmarks.json present & valid (5 pts)
        - sensor_stream parsed without errors (5 pts — self-reported)
    """
    max_score = 25.0

    if benchmarks is None:
        errors.append("benchmarks.json missing — data ingestion cannot be scored")
        return 0.0

    eps = benchmarks.get("ingestion_rate_eps", 0)
    if not isinstance(eps, (int, float)):
        errors.append("ingestion_rate_eps must be a number")
        eps = 0

    # 15 pts for raw throughput
    eps_score = linear_scale(float(eps), INGESTION_EPS_HALF, INGESTION_EPS_FULL, 15.0)

    # 5 pts simply for a valid, non-zero benchmarks.json
    valid_bench_score = 5.0

    # 5 pts for self-reported zero ingestion errors (trust but penalise 0 eps)
    zero_error_score = 5.0 if eps > 0 else 0.0

    total = eps_score + valid_bench_score + zero_error_score
    return min(total, max_score)


def score_simulation_accuracy(benchmarks: Optional[Dict], errors: List[str]) -> float:
    """Score predictive simulation accuracy (30 pts).

    Sub-criteria:
        - Traffic MAE (15 pts — inverse linear)
        - Energy MAE  (15 pts — inverse linear)
    """
    max_score = 30.0
    if benchmarks is None:
        return 0.0

    traffic_mae = benchmarks.get("prediction_mae_traffic", 1.0)
    energy_mae = benchmarks.get("prediction_mae_energy", 1.0)

    if not isinstance(traffic_mae, (int, float)):
        errors.append("prediction_mae_traffic must be a number")
        traffic_mae = 1.0
    if not isinstance(energy_mae, (int, float)):
        errors.append("prediction_mae_energy must be a number")
        energy_mae = 1.0

    traffic_score = inverse_linear_scale(float(traffic_mae), TRAFFIC_MAE_EXCELLENT, TRAFFIC_MAE_ACCEPTABLE, 15.0)
    energy_score = inverse_linear_scale(float(energy_mae), ENERGY_MAE_EXCELLENT, ENERGY_MAE_ACCEPTABLE, 15.0)

    return min(traffic_score + energy_score, max_score)


def score_visualization(submission_dir: Path, errors: List[str]) -> float:
    """Score 3D web visualization (25 pts).

    Sub-criteria (heuristic — no live browser test):
        - frontend/ directory present (10 pts)
        - docker-compose.yml references a frontend service (10 pts)
        - architecture.md mentions 3D/WebGL/deck.gl/Three.js (5 pts)
    """
    max_score = 25.0
    score = 0.0

    frontend_dir = submission_dir / "app" / "frontend"
    if frontend_dir.exists():
        score += 10.0
    else:
        errors.append("submission/app/frontend/ directory not found — 3D visualization evidence missing")

    compose_path = submission_dir / "docker-compose.yml"
    if compose_path.exists():
        compose_text = compose_path.read_text(errors="replace").lower()
        if "frontend" in compose_text or "nginx" in compose_text or "web" in compose_text:
            score += 10.0
        else:
            errors.append("docker-compose.yml does not appear to contain a frontend service")
    else:
        errors.append("docker-compose.yml not found")

    arch_path = submission_dir / "architecture.md"
    if arch_path.exists():
        arch_text = arch_path.read_text(errors="replace").lower()
        keywords = ["webgl", "3d", "deck.gl", "three.js", "deckgl", "visualization", "map"]
        if any(kw in arch_text for kw in keywords):
            score += 5.0
        else:
            errors.append("architecture.md does not mention 3D/WebGL keywords")
    else:
        errors.append("architecture.md not found")

    return min(score, max_score)


def score_scalability(benchmarks: Optional[Dict], submission_dir: Path, errors: List[str]) -> float:
    """Score scalability (20 pts).

    Sub-criteria:
        - Concurrent users tested >= 50 (10 pts)
        - P99 latency (10 pts — inverse linear)
    """
    max_score = 20.0
    if benchmarks is None:
        return 0.0

    concurrent = benchmarks.get("concurrent_users_tested", 0)
    p99 = benchmarks.get("p99_latency_ms", 99_999)

    if not isinstance(concurrent, (int, float)):
        errors.append("concurrent_users_tested must be a number")
        concurrent = 0
    if not isinstance(p99, (int, float)):
        errors.append("p99_latency_ms must be a number")
        p99 = 99_999

    users_score = 10.0 if float(concurrent) >= CONCURRENT_USERS_FULL else linear_scale(float(concurrent), 0, CONCURRENT_USERS_FULL, 10.0)
    latency_score = inverse_linear_scale(float(p99), P99_LATENCY_EXCELLENT_MS, P99_LATENCY_ACCEPTABLE_MS, 10.0)

    return min(users_score + latency_score, max_score)


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------


def evaluate(submission_dir: Path, ground_truth_dir: Optional[Path]) -> Dict:
    errors: List[str] = []

    # Load benchmarks
    bench_path = submission_dir / "benchmarks.json"
    benchmarks, bench_err = load_json(bench_path)
    if bench_err:
        errors.append(bench_err)

    # Score each category
    ingestion_score = score_data_ingestion(benchmarks, errors)
    accuracy_score = score_simulation_accuracy(benchmarks, errors)
    viz_score = score_visualization(submission_dir, errors)
    scale_score = score_scalability(benchmarks, submission_dir, errors)

    total = round(ingestion_score + accuracy_score + viz_score + scale_score, 2)

    result = {
        "total": total,
        "breakdown": {
            "data_ingestion":       {"score": round(ingestion_score, 2), "max": 25},
            "simulation_accuracy":  {"score": round(accuracy_score, 2), "max": 30},
            "visualization":        {"score": round(viz_score, 2),       "max": 25},
            "scalability":          {"score": round(scale_score, 2),     "max": 20},
        },
        "errors": errors,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="IT-P1 SmartCity Digital Twin — Evaluator")
    parser.add_argument("--submission", required=True, help="Path to submission directory")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH, help="Path to ground truth directory")
    args = parser.parse_args()

    submission_dir = Path(args.submission)
    ground_truth_dir = Path(args.ground_truth) if args.ground_truth else None

    if not submission_dir.exists():
        result = {
            "total": 0,
            "breakdown": {
                "data_ingestion":      {"score": 0, "max": 25},
                "simulation_accuracy": {"score": 0, "max": 30},
                "visualization":       {"score": 0, "max": 25},
                "scalability":         {"score": 0, "max": 20},
            },
            "errors": [f"Submission directory not found: {submission_dir}"],
        }
    else:
        result = evaluate(submission_dir, ground_truth_dir)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
