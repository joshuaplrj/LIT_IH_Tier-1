"""
Byzantine Maze — Evaluation Script
CSE Problem 2

Usage:
    python evaluate.py --log consensus_log.json [--proof proof_sketch.md] [--spec protocol_spec.md]

Output (JSON to stdout):
    {
        "total": 0-100,
        "breakdown": {
            "safety":     {"score": X, "max": 30},
            "liveness":   {"score": X, "max": 25},
            "simulation": {"score": X, "max": 20},
            "proof":      {"score": X, "max": 15},
            "efficiency": {"score": X, "max": 10}
        },
        "errors": []
    }
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def result(total, breakdown, errors):
    return {"total": round(float(total), 2), "breakdown": breakdown, "errors": errors}


def zero_result(reason: str):
    return result(
        0,
        {
            "safety":     {"score": 0, "max": 30},
            "liveness":   {"score": 0, "max": 25},
            "simulation": {"score": 0, "max": 20},
            "proof":      {"score": 0, "max": 15},
            "efficiency": {"score": 0, "max": 10},
        },
        [reason],
    )


def load_log(path: str):
    if not os.path.isfile(path):
        return None, [f"Log file not found: {path}"]
    try:
        with open(path) as f:
            data = json.load(f)
        return data, []
    except Exception as e:
        return None, [f"Could not parse log JSON: {e}"]


# ---------------------------------------------------------------------------
# Metric: Safety (30 pts)
# ---------------------------------------------------------------------------

def score_safety(data: dict) -> tuple:
    """
    Safety: All honest nodes that decided must have decided the same value.
    Full score (30) if safety_ok is True in log.
    Partial credit if some nodes agreed.
    """
    errors = []
    decisions = data.get("decisions", {})
    byzantine_ids = set(data.get("byzantine_ids", []))

    # Filter to honest nodes only
    honest_decisions = {
        nid: val for nid, val in decisions.items()
        if int(nid) not in byzantine_ids
    }

    if not honest_decisions:
        errors.append("No honest node decisions found in log.")
        return 0.0, errors

    decided_values = set(v for v in honest_decisions.values() if v is not None)

    if len(decided_values) > 1:
        errors.append(
            f"SAFETY VIOLATION: Honest nodes decided different values: {decided_values}"
        )
        # Partial score: fraction of nodes that agreed with the majority value
        from collections import Counter
        majority_val = Counter(
            v for v in honest_decisions.values() if v is not None
        ).most_common(1)
        if majority_val:
            majority_count = majority_val[0][1]
            total_decided = sum(1 for v in honest_decisions.values() if v is not None)
            partial = 30.0 * (majority_count / max(total_decided, 1)) * 0.5  # max 50% partial
            return round(partial, 2), errors
        return 0.0, errors

    # All decided nodes agreed — full safety score
    safety_flag = data.get("safety_ok", False)
    if safety_flag or len(decided_values) <= 1:
        return 30.0, errors

    return 0.0, errors


# ---------------------------------------------------------------------------
# Metric: Liveness (25 pts)
# ---------------------------------------------------------------------------

def score_liveness(data: dict) -> tuple:
    """
    Liveness: All honest nodes eventually decide.
    Partial credit proportional to fraction of honest nodes that decided.
    """
    errors = []
    decisions = data.get("decisions", {})
    byzantine_ids = set(data.get("byzantine_ids", []))
    n = data.get("n_nodes", 10)
    f = data.get("f", 3)
    honest_count = n - f

    honest_decided = sum(
        1 for nid, val in decisions.items()
        if int(nid) not in byzantine_ids and val is not None
    )

    fraction = honest_decided / max(honest_count, 1)

    if fraction < 1.0:
        errors.append(
            f"Liveness incomplete: {honest_decided}/{honest_count} honest nodes decided."
        )

    score = round(25.0 * fraction, 2)
    return score, errors


# ---------------------------------------------------------------------------
# Metric: Simulation Correctness (20 pts)
# ---------------------------------------------------------------------------

def score_simulation(data: dict, log_path: str) -> tuple:
    """
    Check structural correctness of the simulation log.
    Rubric:
        - Log file is valid JSON:                5 pts
        - Required keys present:                 5 pts
        - N >= 3f+1 enforced:                    5 pts
        - Byzantine node IDs within range:       5 pts
    """
    errors = []
    score = 0.0

    # Valid JSON — already confirmed by caller
    score += 5.0

    # Required keys
    required_keys = {"n_nodes", "f", "byzantine_ids", "decisions", "safety_ok", "liveness_ok"}
    missing = required_keys - set(data.keys())
    if not missing:
        score += 5.0
    else:
        errors.append(f"Missing keys in log: {missing}")

    # N >= 3f+1
    n = data.get("n_nodes", 0)
    f = data.get("f", 0)
    if n >= 3 * f + 1:
        score += 5.0
    else:
        errors.append(f"N={n} < 3f+1={3*f+1}. BFT invariant violated.")

    # Byzantine node IDs in range
    byz_ids = data.get("byzantine_ids", [])
    if all(0 <= b < n for b in byz_ids):
        score += 5.0
    else:
        errors.append(f"Byzantine node IDs out of range [0, {n-1}]: {byz_ids}")

    return round(score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Proof Quality (15 pts) — judge-assigned
# ---------------------------------------------------------------------------

def score_proof(proof_path: Optional[str]) -> tuple:
    """
    Automatically checks only whether the proof file exists and has content.
    Full grading requires human review.

    Auto-score (5 pts): File exists and is non-empty.
    Judge-assigned (10 pts): Pass via --proof_score flag.
    """
    errors = []
    if not proof_path:
        errors.append("No proof file provided (--proof flag). Proof score = 0.")
        return 0.0, errors
    if not os.path.isfile(proof_path):
        errors.append(f"Proof file not found: {proof_path}")
        return 0.0, errors
    with open(proof_path) as f:
        content = f.read().strip()
    if len(content) < 200:
        errors.append("Proof file appears too short (< 200 chars). Verify content.")
        return 2.0, errors
    # Keyword checks — basic
    keywords = ["safety", "liveness", "quorum", "invariant"]
    found = sum(1 for kw in keywords if kw.lower() in content.lower())
    auto_score = 5.0 * (found / len(keywords))
    errors.append(
        f"Proof auto-score: {auto_score:.1f}/5. "
        f"Remaining 10 pts assigned by judges after human review."
    )
    return round(auto_score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Efficiency (10 pts) — judge-assigned
# ---------------------------------------------------------------------------

def score_efficiency(efficiency_score: float) -> tuple:
    errors = []
    s = float(max(0, min(10, efficiency_score)))
    if s < 10:
        errors.append(f"Efficiency score {s}/10 — judges should evaluate "
                      f"message complexity and latency under normal operation.")
    return s, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a Byzantine Maze submission."
    )
    parser.add_argument("--log",            type=str, required=True,
                        help="Path to consensus_log.json produced by simulation.")
    parser.add_argument("--proof",          type=str, default=None,
                        help="Path to proof_sketch.md (optional).")
    parser.add_argument("--proof_score",    type=float, default=0.0,
                        help="Judge-assigned proof quality score (0–10, added to auto-score).")
    parser.add_argument("--efficiency",     type=float, default=0.0,
                        help="Judge-assigned efficiency score (0–10).")
    args = parser.parse_args()

    errors: List[str] = []
    breakdown = {
        "safety":     {"score": 0.0, "max": 30},
        "liveness":   {"score": 0.0, "max": 25},
        "simulation": {"score": 0.0, "max": 20},
        "proof":      {"score": 0.0, "max": 15},
        "efficiency": {"score": 0.0, "max": 10},
    }

    # Load log
    data, load_errors = load_log(args.log)
    errors.extend(load_errors)
    if data is None:
        print(json.dumps(zero_result(" | ".join(errors)), indent=2))
        sys.exit(0)

    # Safety
    s_safety, e = score_safety(data)
    breakdown["safety"]["score"] = s_safety
    errors.extend(e)

    # Liveness
    s_liveness, e = score_liveness(data)
    breakdown["liveness"]["score"] = s_liveness
    errors.extend(e)

    # Simulation correctness
    s_sim, e = score_simulation(data, args.log)
    breakdown["simulation"]["score"] = s_sim
    errors.extend(e)

    # Proof quality
    auto_proof, e = score_proof(args.proof)
    judge_proof = float(max(0, min(10, args.proof_score)))
    total_proof = min(auto_proof + judge_proof, 15.0)
    breakdown["proof"]["score"] = round(total_proof, 2)
    errors.extend(e)

    # Efficiency
    s_eff, e = score_efficiency(args.efficiency)
    breakdown["efficiency"]["score"] = s_eff
    errors.extend(e)

    total = sum(v["score"] for v in breakdown.values())
    print(json.dumps(result(total, breakdown, errors), indent=2))


if __name__ == "__main__":
    main()
