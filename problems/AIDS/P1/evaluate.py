"""
AIDS-P1: NeuroDecode — Evaluation / Scoring Script

Usage:
    python evaluate.py --submission <path> --ground_truth <path>

Options:
    --submission    Path to predictions.csv (trial_id, subject_id, predicted_class, confidence)
    --ground_truth  Path to ground-truth CSV  (default: ground_truth/AIDS_P1_gt.csv)
    --test_data     Optional: path to raw test EEG for latency re-check
    --latency_json  Path to latency_benchmark.json produced by starter.py

Prints a JSON scoring result to stdout.
"""

import argparse
import csv
import json
import os
import sys

# ---------------------------------------------------------------------------
# Constants — scoring weights from problem spec
# ---------------------------------------------------------------------------
WEIGHTS = {
    "classification_accuracy": 40,
    "cross_subject_generalization": 30,
    "inference_latency": 20,
    "model_explainability": 10,
}
GROUND_TRUTH_PATH = "ground_truth/AIDS_P1_gt.csv"
LATENCY_TARGET_MS = 50.0   # must be below this to receive full latency score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(path: str) -> list:
    """Load a CSV file and return list of dicts."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def safe_load(path: str, label: str):
    """Load CSV, returning (rows, error_msg). error_msg is None on success."""
    if not os.path.exists(path):
        return None, f"{label} file not found: {path}"
    try:
        rows = load_csv(path)
        if not rows:
            return None, f"{label} file is empty: {path}"
        return rows, None
    except Exception as exc:
        return None, f"Failed to parse {label}: {exc}"


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_classification(submission_rows: list, gt_rows: list) -> dict:
    """
    Compute overall accuracy and per-class accuracy.
    Returns {"score": float, "max": 40, "details": {...}}
    """
    gt_map = {str(r["trial_id"]): int(r["true_class"]) for r in gt_rows}
    correct, total = 0, 0
    per_class_correct = {}
    per_class_total = {}

    for row in submission_rows:
        tid = str(row.get("trial_id", ""))
        pred = int(row.get("predicted_class", -1))
        if tid not in gt_map:
            continue
        true = gt_map[tid]
        per_class_total[true] = per_class_total.get(true, 0) + 1
        if pred == true:
            correct += 1
            per_class_correct[true] = per_class_correct.get(true, 0) + 1
        total += 1

    if total == 0:
        return {"score": 0, "max": WEIGHTS["classification_accuracy"],
                "details": {"error": "no matching trial IDs"}}

    accuracy = correct / total
    # Scale: 0.25 chance level → 0 pts, 0.80+ → full pts
    chance = 0.25
    target = 0.80
    scaled = max(0.0, (accuracy - chance) / (target - chance))
    raw_score = min(1.0, scaled) * WEIGHTS["classification_accuracy"]

    per_class_acc = {
        str(cls): (per_class_correct.get(cls, 0) / per_class_total[cls])
        for cls in per_class_total
    }
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["classification_accuracy"],
        "details": {
            "overall_accuracy": round(accuracy, 4),
            "per_class_accuracy": per_class_acc,
            "n_evaluated": total,
        },
    }


def score_cross_subject(submission_rows: list, gt_rows: list) -> dict:
    """
    Compute cross-subject accuracy — only trials where subject_id matches
    a held-out test subject listed in ground truth.
    Ground truth CSV must include a column 'is_cross_subject' = 1/0.
    """
    gt_map = {str(r["trial_id"]): r for r in gt_rows}
    correct, total = 0, 0

    for row in submission_rows:
        tid = str(row.get("trial_id", ""))
        if tid not in gt_map:
            continue
        gt = gt_map[tid]
        if str(gt.get("is_cross_subject", "0")) != "1":
            continue
        pred = int(row.get("predicted_class", -1))
        true = int(gt["true_class"])
        total += 1
        if pred == true:
            correct += 1

    if total == 0:
        return {"score": 0, "max": WEIGHTS["cross_subject_generalization"],
                "details": {"warning": "no cross-subject trials found in ground truth"}}

    accuracy = correct / total
    chance = 0.25
    target = 0.60
    scaled = max(0.0, (accuracy - chance) / (target - chance))
    raw_score = min(1.0, scaled) * WEIGHTS["cross_subject_generalization"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["cross_subject_generalization"],
        "details": {
            "cross_subject_accuracy": round(accuracy, 4),
            "n_cross_subject_trials": total,
        },
    }


def score_latency(latency_json_path: str) -> dict:
    """
    Score inference latency. Full marks if mean_ms < 50 ms.
    Partial credit down to 500 ms; zero above 500 ms.
    """
    if not latency_json_path or not os.path.exists(latency_json_path):
        return {"score": 0, "max": WEIGHTS["inference_latency"],
                "details": {"warning": "latency_benchmark.json not provided"}}
    try:
        with open(latency_json_path) as f:
            data = json.load(f)
        mean_ms = float(data.get("mean_ms", 9999))
    except Exception as exc:
        return {"score": 0, "max": WEIGHTS["inference_latency"],
                "details": {"error": str(exc)}}

    if mean_ms <= LATENCY_TARGET_MS:
        ratio = 1.0
    elif mean_ms >= 500:
        ratio = 0.0
    else:
        ratio = 1.0 - (mean_ms - LATENCY_TARGET_MS) / (500 - LATENCY_TARGET_MS)

    raw_score = ratio * WEIGHTS["inference_latency"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["inference_latency"],
        "details": {"mean_ms": mean_ms, "target_ms": LATENCY_TARGET_MS},
    }


def score_explainability(submission_dir: str) -> dict:
    """
    Check for explainability visualizations (one PNG per class in
    submission/explainability/).
    Awards points based on presence; full manual review would be needed in practice.
    """
    expected = 4  # one per class
    explain_dir = os.path.join(submission_dir, "explainability")
    if not os.path.isdir(explain_dir):
        return {"score": 0, "max": WEIGHTS["model_explainability"],
                "details": {"warning": "explainability/ directory not found"}}
    pngs = [f for f in os.listdir(explain_dir) if f.endswith(".png")]
    found = len(pngs)
    ratio = min(1.0, found / expected)
    raw_score = ratio * WEIGHTS["model_explainability"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["model_explainability"],
        "details": {"pngs_found": found, "pngs_expected": expected},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P1 NeuroDecode Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to predictions.csv")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help="Path to ground-truth CSV")
    parser.add_argument("--test_data", default=None,
                        help="(Optional) path to raw test EEG for latency re-run")
    parser.add_argument("--latency_json", default=None,
                        help="Path to latency_benchmark.json")
    args = parser.parse_args()

    errors = []
    breakdown = {}

    # --- Load submission ---
    submission_rows, err = safe_load(args.submission, "submission")
    if err:
        errors.append(err)
        submission_rows = []

    # --- Load ground truth ---
    gt_rows, err = safe_load(args.ground_truth, "ground_truth")
    if err:
        errors.append(err)
        gt_rows = []

    # --- Derive submission directory for explainability check ---
    submission_dir = os.path.dirname(os.path.abspath(args.submission))

    # --- Latency JSON: look next to submission if not specified ---
    latency_json = args.latency_json
    if not latency_json:
        candidate = os.path.join(submission_dir, "latency_benchmark.json")
        if os.path.exists(candidate):
            latency_json = candidate

    # --- Score each dimension ---
    if submission_rows and gt_rows:
        breakdown["classification_accuracy"] = score_classification(
            submission_rows, gt_rows)
        breakdown["cross_subject_generalization"] = score_cross_subject(
            submission_rows, gt_rows)
    else:
        breakdown["classification_accuracy"] = {
            "score": 0, "max": WEIGHTS["classification_accuracy"],
            "details": {"error": "missing submission or ground truth"}}
        breakdown["cross_subject_generalization"] = {
            "score": 0, "max": WEIGHTS["cross_subject_generalization"],
            "details": {"error": "missing submission or ground truth"}}

    breakdown["inference_latency"] = score_latency(latency_json)
    breakdown["model_explainability"] = score_explainability(submission_dir)

    total = sum(v["score"] for v in breakdown.values())

    result = {
        "total": round(total, 2),
        "breakdown": breakdown,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
