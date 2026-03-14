"""
IT-P2: HealthBridge — Evaluator
================================
Usage:
    python evaluate.py --submission ./submission [--ground_truth ./ground_truth]

Reads:
    submission/global_model.pt          — PyTorch state dict
    submission/results.json             — training metrics
    submission/privacy_analysis.json    — epsilon budget log
    submission/robustness_report.json   — poisoning experiment results

Outputs JSON:
    {
      "total": 0-100,
      "breakdown": {
        "model_accuracy":      {"score": X, "max": 40},
        "privacy_preservation":{"score": X, "max": 30},
        "system_robustness":   {"score": X, "max": 20},
        "documentation":       {"score": X, "max": 10}
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
# Thresholds (adjust to match judging rubric)
# ---------------------------------------------------------------------------

# Model accuracy (40 pts)
ACCURACY_EXCELLENT = 0.90    # >= 90% global accuracy => full marks
ACCURACY_ACCEPTABLE = 0.60   # >= 60% => partial marks

# Privacy preservation (30 pts)
DP_EPSILON_LIMIT = 3.0       # epsilon must be <= 3.0 for any privacy score
DP_EPSILON_FULL = 1.0        # epsilon <= 1.0 => full bonus marks

# System robustness (20 pts)
# Accuracy drop under poisoning attack
ROBUSTNESS_EXCELLENT_DROP = 0.02   # <= 2% drop => full marks
ROBUSTNESS_ACCEPTABLE_DROP = 0.15  # <= 15% drop => half marks

GROUND_TRUTH_PATH = "./ground_truth"   # placeholder

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


def score_model_accuracy(results: Optional[Dict], gt_dir: Optional[Path], errors: List[str]) -> float:
    """Score model accuracy (40 pts).

    Uses results.json reported global_accuracy.
    If ground truth test labels are available, recompute from predictions instead.
    """
    max_score = 40.0
    if results is None:
        errors.append("results.json missing — model accuracy cannot be scored")
        return 0.0

    acc = results.get("global_accuracy", 0.0)
    if not isinstance(acc, (int, float)):
        errors.append("global_accuracy must be a number")
        return 0.0

    # TODO: if gt_dir exists, override acc by loading global_model.pt and running inference

    base_score = linear_scale(float(acc), ACCURACY_ACCEPTABLE, ACCURACY_EXCELLENT, 36.0)

    # Bonus 4 pts for completing convergence curve with >= 5 rounds
    curve = results.get("convergence_curve", [])
    convergence_bonus = 4.0 if isinstance(curve, list) and len(curve) >= 5 else 0.0

    return min(base_score + convergence_bonus, max_score)


def score_privacy_preservation(privacy: Optional[Dict], errors: List[str]) -> float:
    """Score privacy preservation (30 pts).

    Sub-criteria:
        - Epsilon <= 3.0 (hard requirement — 0 if violated): 20 pts
        - Delta correctly set to 1e-5 or smaller: 5 pts
        - Epsilon <= 1.0 (excellent privacy): 5 bonus pts
    """
    max_score = 30.0
    if privacy is None:
        errors.append("privacy_analysis.json missing — privacy score is 0")
        return 0.0

    # Read final cumulative epsilon from last round entry
    rounds_log = privacy.get("rounds", [])
    if not rounds_log:
        errors.append("privacy_analysis.json has no round entries")
        return 0.0

    last_entry = rounds_log[-1] if isinstance(rounds_log, list) else {}
    cumulative_eps = last_entry.get("cumulative_eps", float("inf"))
    delta = privacy.get("delta", 1.0)

    if not isinstance(cumulative_eps, (int, float)):
        errors.append("cumulative_eps must be a number")
        return 0.0

    # Hard limit
    if float(cumulative_eps) > DP_EPSILON_LIMIT:
        errors.append(
            f"Epsilon budget exceeded: {cumulative_eps:.4f} > {DP_EPSILON_LIMIT} — privacy guarantee invalid"
        )
        return 0.0

    eps_score = 20.0  # passed the hard limit

    # Delta check
    delta_score = 5.0 if isinstance(delta, (int, float)) and float(delta) <= 1e-5 else 0.0
    if delta_score == 0.0:
        errors.append(f"Delta should be <= 1e-5; got {delta}")

    # Excellent privacy bonus
    bonus = 5.0 if float(cumulative_eps) <= DP_EPSILON_FULL else 0.0

    return min(eps_score + delta_score + bonus, max_score)


def score_system_robustness(robustness: Optional[Dict], results: Optional[Dict], errors: List[str]) -> float:
    """Score system robustness (20 pts).

    Sub-criteria:
        - Robustness report present and coherent: 5 pts
        - Accuracy drop under poisoning within acceptable threshold: 15 pts
    """
    max_score = 20.0
    if robustness is None:
        errors.append("robustness_report.json missing — robustness score is 0")
        return 0.0

    report_present_score = 5.0

    accuracy_drop = robustness.get("accuracy_drop", float("inf"))
    if not isinstance(accuracy_drop, (int, float)):
        errors.append("accuracy_drop must be a number in robustness_report.json")
        return report_present_score

    # Lower drop is better
    drop_score = inverse_linear_scale(
        float(accuracy_drop),
        ROBUSTNESS_EXCELLENT_DROP,
        ROBUSTNESS_ACCEPTABLE_DROP,
        15.0,
    )

    return min(report_present_score + drop_score, max_score)


def score_documentation(submission_dir: Path, results: Optional[Dict], errors: List[str]) -> float:
    """Score documentation (10 pts).

    Checks:
        - results.json has centralized_baseline_accuracy populated: 4 pts
        - per_hospital_accuracy covers all 5 hospitals: 3 pts
        - global_model.pt exists: 3 pts
    """
    max_score = 10.0
    score = 0.0

    model_path = submission_dir / "global_model.pt"
    if model_path.exists():
        score += 3.0
    else:
        errors.append("global_model.pt not found")

    if results is not None:
        baseline = results.get("centralized_baseline_accuracy", None)
        if baseline is not None and isinstance(baseline, (int, float)) and float(baseline) > 0:
            score += 4.0
        else:
            errors.append("centralized_baseline_accuracy missing or zero in results.json")

        per_h = results.get("per_hospital_accuracy", {})
        if isinstance(per_h, dict) and len(per_h) == 5:
            score += 3.0
        else:
            errors.append(f"per_hospital_accuracy should have 5 entries; found {len(per_h) if isinstance(per_h, dict) else 0}")

    return min(score, max_score)


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------


def evaluate(submission_dir: Path, ground_truth_dir: Optional[Path]) -> Dict:
    errors: List[str] = []

    results, results_err = load_json(submission_dir / "results.json")
    privacy, priv_err = load_json(submission_dir / "privacy_analysis.json")
    robustness, rob_err = load_json(submission_dir / "robustness_report.json")

    for err in [results_err, priv_err, rob_err]:
        if err:
            errors.append(err)

    accuracy_score = score_model_accuracy(results, ground_truth_dir, errors)
    privacy_score = score_privacy_preservation(privacy, errors)
    robustness_score = score_system_robustness(robustness, results, errors)
    doc_score = score_documentation(submission_dir, results, errors)

    total = round(accuracy_score + privacy_score + robustness_score + doc_score, 2)

    return {
        "total": total,
        "breakdown": {
            "model_accuracy":       {"score": round(accuracy_score, 2),   "max": 40},
            "privacy_preservation": {"score": round(privacy_score, 2),    "max": 30},
            "system_robustness":    {"score": round(robustness_score, 2), "max": 20},
            "documentation":        {"score": round(doc_score, 2),        "max": 10},
        },
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="IT-P2 HealthBridge — Evaluator")
    parser.add_argument("--submission", required=True, help="Path to submission directory")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH, help="Path to ground truth directory")
    args = parser.parse_args()

    submission_dir = Path(args.submission)
    ground_truth_dir = Path(args.ground_truth) if args.ground_truth else None

    if not submission_dir.exists():
        result = {
            "total": 0,
            "breakdown": {
                "model_accuracy":       {"score": 0, "max": 40},
                "privacy_preservation": {"score": 0, "max": 30},
                "system_robustness":    {"score": 0, "max": 20},
                "documentation":        {"score": 0, "max": 10},
            },
            "errors": [f"Submission directory not found: {submission_dir}"],
        }
    else:
        result = evaluate(submission_dir, ground_truth_dir)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
