"""
IT-P5: MeshNet — Evaluator
============================
Usage:
    python evaluate.py --submission ./submission [--ground_truth ./ground_truth]

Reads:
    submission/simulation_results.json   — benchmark runs for 100, 1000, 10000 nodes
    submission/protocol_spec.md          — written protocol specification
    submission/src/                      — simulator source code

Outputs JSON:
    {
      "total": 0-100,
      "breakdown": {
        "protocol_correctness": {"score": X, "max": 35},
        "efficiency":           {"score": X, "max": 25},
        "fault_tolerance":      {"score": X, "max": 25},
        "documentation":        {"score": X, "max": 15}
      },
      "errors": []
    }
"""

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Protocol correctness (35 pts)
DELIVERY_RATE_EXCELLENT = 95.0   # % delivery on clean network
DELIVERY_RATE_ACCEPTABLE = 70.0
OTA_DELIVERY_EXCELLENT = 90.0
OTA_DELIVERY_ACCEPTABLE = 50.0

# Efficiency (25 pts)
# Energy per message (lower is better)
ENERGY_EXCELLENT_J = 0.001       # J per message
ENERGY_ACCEPTABLE_J = 0.01
# Latency (lower is better, in seconds)
LATENCY_EXCELLENT_S = 30.0       # sensor reading reaches gateway within 30 s
LATENCY_ACCEPTABLE_S = 300.0     # 5 minutes

# Fault tolerance (25 pts)
# Delivery rate under 50% node failure (use the 10k-node run as proxy)
FAULT_DELIVERY_EXCELLENT = 80.0
FAULT_DELIVERY_ACCEPTABLE = 50.0

# Documentation (15 pts) — heuristic keyword checks on protocol_spec.md

GROUND_TRUTH_PATH = "./ground_truth"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
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


def find_run(runs: List[Dict], num_nodes: int) -> Optional[Dict]:
    """Find the simulation run closest to num_nodes."""
    if not runs:
        return None
    return min(runs, key=lambda r: abs(r.get("num_nodes", 0) - num_nodes))


# ---------------------------------------------------------------------------
# Score sections
# ---------------------------------------------------------------------------


def score_protocol_correctness(sim_results: Optional[Dict], errors: List[str]) -> float:
    """Score protocol correctness (35 pts).

    Sub-criteria:
        - Data delivery rate on 1000-node run (20 pts)
        - OTA delivery rate on 1000-node run (15 pts)
    """
    max_score = 35.0
    if sim_results is None:
        errors.append("simulation_results.json missing — protocol correctness score is 0")
        return 0.0

    runs = sim_results.get("runs", [])
    if not isinstance(runs, list) or not runs:
        errors.append("simulation_results.json has no 'runs' array")
        return 0.0

    run = find_run(runs, 1000) or runs[0]

    delivery = run.get("data_delivery_rate_pct", 0.0)
    ota = run.get("ota_delivery_rate_pct", 0.0)

    if not isinstance(delivery, (int, float)):
        errors.append("data_delivery_rate_pct must be a number")
        delivery = 0.0
    if not isinstance(ota, (int, float)):
        errors.append("ota_delivery_rate_pct must be a number")
        ota = 0.0

    delivery_score = linear_scale(float(delivery), DELIVERY_RATE_ACCEPTABLE, DELIVERY_RATE_EXCELLENT, 20.0)
    ota_score = linear_scale(float(ota), OTA_DELIVERY_ACCEPTABLE, OTA_DELIVERY_EXCELLENT, 15.0)

    return min(delivery_score + ota_score, max_score)


def score_efficiency(sim_results: Optional[Dict], errors: List[str]) -> float:
    """Score efficiency (25 pts).

    Sub-criteria:
        - Energy per message (12 pts — lower is better)
        - Average latency (13 pts — lower is better)
    """
    max_score = 25.0
    if sim_results is None:
        return 0.0

    runs = sim_results.get("runs", [])
    run = find_run(runs, 1000) if runs else None
    if run is None:
        errors.append("No valid simulation run found for efficiency scoring")
        return 0.0

    energy = run.get("avg_energy_j_per_message", float("inf"))
    latency = run.get("avg_latency_sec", float("inf"))

    if not isinstance(energy, (int, float)):
        errors.append("avg_energy_j_per_message must be a number")
        energy = float("inf")
    if not isinstance(latency, (int, float)):
        errors.append("avg_latency_sec must be a number")
        latency = float("inf")

    energy_score = inverse_linear_scale(float(energy), ENERGY_EXCELLENT_J, ENERGY_ACCEPTABLE_J, 12.0)
    latency_score = inverse_linear_scale(float(latency), LATENCY_EXCELLENT_S, LATENCY_ACCEPTABLE_S, 13.0)

    return min(energy_score + latency_score, max_score)


def score_fault_tolerance(sim_results: Optional[Dict], errors: List[str]) -> float:
    """Score fault tolerance (25 pts).

    Evaluates delivery rate on the 10,000-node run (which operates under node failures).
    Also checks that the run was actually completed at 10,000 nodes.

    Sub-criteria:
        - 10k-node run present (5 pts)
        - Delivery rate under failure conditions (20 pts)
    """
    max_score = 25.0
    if sim_results is None:
        return 0.0

    runs = sim_results.get("runs", [])
    if not runs:
        return 0.0

    # Find 10k run
    run_10k = find_run(runs, 10_000)
    if run_10k is None or run_10k.get("num_nodes", 0) < 5000:
        errors.append("No 10,000-node simulation run found — fault tolerance evaluated on available run")
        run_10k = max(runs, key=lambda r: r.get("num_nodes", 0))

    run_present_score = 5.0 if run_10k.get("num_nodes", 0) >= 5000 else 2.0

    delivery = run_10k.get("data_delivery_rate_pct", 0.0)
    if not isinstance(delivery, (int, float)):
        delivery = 0.0

    delivery_score = linear_scale(float(delivery), FAULT_DELIVERY_ACCEPTABLE, FAULT_DELIVERY_EXCELLENT, 20.0)

    return min(run_present_score + delivery_score, max_score)


def score_documentation(submission_dir: Path, errors: List[str]) -> float:
    """Score documentation (15 pts).

    Sub-criteria:
        - protocol_spec.md exists and covers required topics (10 pts)
        - src/ directory with runnable simulator code (5 pts)
    """
    max_score = 15.0
    score = 0.0

    spec_path = submission_dir / "protocol_spec.md"
    if spec_path.exists():
        text = spec_path.read_text(errors="replace").lower()
        topics = {
            "routing": ["routing", "rpl", "gradient", "parent", "ofv", "hop"],
            "collection": ["trickle", "collection", "store-and-forward", "forward"],
            "ota": ["ota", "firmware", "over-the-air", "chunk", "gossip", "epidemic"],
            "energy": ["energy", "battery", "sleep", "transmit", "receive"],
            "fault": ["fault", "failure", "repair", "resilience", "recovery"],
        }
        covered = 0
        for topic, keywords in topics.items():
            if any(kw in text for kw in keywords):
                covered += 1
        spec_score = min(10.0, 2.0 * covered)
        score += spec_score
        if covered < 3:
            errors.append(f"protocol_spec.md covers only {covered}/5 required topics — partial credit only")
    else:
        errors.append("protocol_spec.md not found")

    src_dir = submission_dir / "src"
    if src_dir.exists() and any(src_dir.iterdir()):
        score += 5.0
    else:
        errors.append("submission/src/ directory missing or empty")

    return min(score, max_score)


# ---------------------------------------------------------------------------
# Validate all three scale runs are present
# ---------------------------------------------------------------------------


def validate_scale_runs(sim_results: Optional[Dict], errors: List[str]) -> None:
    """Warn if any of the required scale runs (100, 1000, 10000) are missing."""
    if sim_results is None:
        return
    runs = sim_results.get("runs", [])
    present_scales = {r.get("num_nodes", 0) for r in runs if isinstance(r, dict)}
    for required in [100, 1000, 10_000]:
        closest = min(present_scales, key=lambda x: abs(x - required)) if present_scales else None
        if closest is None or abs(closest - required) > required * 0.5:
            errors.append(f"Expected a simulation run with ~{required} nodes; none found")


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------


def evaluate(submission_dir: Path, ground_truth_dir: Optional[Path]) -> Dict:
    errors: List[str] = []

    sim_results, sim_err = load_json(submission_dir / "simulation_results.json")
    if sim_err:
        errors.append(sim_err)

    validate_scale_runs(sim_results, errors)

    correctness_score = score_protocol_correctness(sim_results, errors)
    efficiency_score = score_efficiency(sim_results, errors)
    fault_score = score_fault_tolerance(sim_results, errors)
    doc_score = score_documentation(submission_dir, errors)

    total = round(correctness_score + efficiency_score + fault_score + doc_score, 2)

    return {
        "total": total,
        "breakdown": {
            "protocol_correctness": {"score": round(correctness_score, 2), "max": 35},
            "efficiency":           {"score": round(efficiency_score, 2),  "max": 25},
            "fault_tolerance":      {"score": round(fault_score, 2),       "max": 25},
            "documentation":        {"score": round(doc_score, 2),         "max": 15},
        },
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="IT-P5 MeshNet — Evaluator")
    parser.add_argument("--submission", required=True, help="Path to submission directory")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH, help="Path to ground truth directory")
    args = parser.parse_args()

    submission_dir = Path(args.submission)
    ground_truth_dir = Path(args.ground_truth) if args.ground_truth else None

    if not submission_dir.exists():
        result = {
            "total": 0,
            "breakdown": {
                "protocol_correctness": {"score": 0, "max": 35},
                "efficiency":           {"score": 0, "max": 25},
                "fault_tolerance":      {"score": 0, "max": 25},
                "documentation":        {"score": 0, "max": 15},
            },
            "errors": [f"Submission directory not found: {submission_dir}"],
        }
    else:
        result = evaluate(submission_dir, ground_truth_dir)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
