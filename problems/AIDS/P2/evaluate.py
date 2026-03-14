"""
AIDS-P2: GraphFlood — Evaluation / Scoring Script

Usage:
    python evaluate.py --submission <path> [--ground_truth <path>] [--test_data <path>]

Options:
    --submission       Path to predictions.csv
                       (columns: post_id, label, score, top_spreaders)
    --ground_truth     Path to ground-truth CSV (default: ground_truth/AIDS_P2_gt.csv)
                       (columns: post_id, true_label)
    --test_data        (Optional) path to cascades_test.csv with timing info
    --throughput_json  Path to throughput_report.json produced by starter.py

Prints a JSON scoring result to stdout.
"""

import argparse
import csv
import json
import os
import sys

import numpy as np

# Optional sklearn for metrics
try:
    from sklearn.metrics import (
        f1_score, roc_auc_score, precision_score, recall_score,
        confusion_matrix,
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WEIGHTS = {
    "detection_f1": 40,
    "streaming_throughput": 25,
    "false_positive_rate": 20,
    "network_graph_analysis": 15,
}
GROUND_TRUTH_PATH = "ground_truth/AIDS_P2_gt.csv"
THROUGHPUT_TARGET = 50_000   # posts/minute


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(path: str) -> list:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def safe_load(path: str, label: str):
    if not os.path.exists(path):
        return None, f"{label} file not found: {path}"
    try:
        rows = load_csv(path)
        if not rows:
            return None, f"{label} is empty: {path}"
        return rows, None
    except Exception as exc:
        return None, f"Failed to parse {label}: {exc}"


def align_predictions(sub_rows: list, gt_rows: list):
    """Return aligned (y_true, y_score, y_pred) arrays."""
    gt_map = {str(r["post_id"]): int(r["true_label"]) for r in gt_rows}
    y_true, y_score, y_pred = [], [], []
    for row in sub_rows:
        pid = str(row.get("post_id", ""))
        if pid not in gt_map:
            continue
        try:
            score = float(row.get("score", 0.5))
            pred = int(row.get("label", 0))
        except ValueError:
            continue
        y_true.append(gt_map[pid])
        y_score.append(score)
        y_pred.append(pred)
    return np.array(y_true), np.array(y_score), np.array(y_pred)


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_detection_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Compute F1 score for misinformation class (label=1).
    Full marks at F1 >= 0.80, zero at F1 <= 0.40.
    """
    if not SKLEARN_AVAILABLE:
        return {"score": 0, "max": WEIGHTS["detection_f1"],
                "details": {"error": "sklearn not available"}}
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    auc = 0.0
    try:
        auc = float(roc_auc_score(y_true, y_pred))
    except Exception:
        pass

    target, floor = 0.80, 0.40
    scaled = max(0.0, (f1 - floor) / (target - floor))
    raw_score = min(1.0, scaled) * WEIGHTS["detection_f1"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["detection_f1"],
        "details": {"f1": round(f1, 4), "auc_roc": round(auc, 4),
                    "n_evaluated": len(y_true)},
    }


def score_false_positive_rate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Compute false positive rate (FPR) among legitimate posts.
    Full marks at FPR <= 0.10; zero at FPR >= 0.50.
    """
    if not SKLEARN_AVAILABLE:
        return {"score": 0, "max": WEIGHTS["false_positive_rate"],
                "details": {"error": "sklearn not available"}}
    try:
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred,
                                          labels=[0, 1]).ravel()
        fpr = float(fp / (fp + tn + 1e-9))
    except Exception as exc:
        return {"score": 0, "max": WEIGHTS["false_positive_rate"],
                "details": {"error": str(exc)}}

    target, ceiling = 0.10, 0.50
    if fpr <= target:
        ratio = 1.0
    elif fpr >= ceiling:
        ratio = 0.0
    else:
        ratio = 1.0 - (fpr - target) / (ceiling - target)

    raw_score = ratio * WEIGHTS["false_positive_rate"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["false_positive_rate"],
        "details": {"false_positive_rate": round(fpr, 4),
                    "fp": int(fp), "tn": int(tn)},
    }


def score_throughput(throughput_json_path: str) -> dict:
    """
    Score streaming throughput. Full marks >= 50,000 posts/min.
    Linear decay down to 5,000 posts/min.
    """
    if not throughput_json_path or not os.path.exists(throughput_json_path):
        return {"score": 0, "max": WEIGHTS["streaming_throughput"],
                "details": {"warning": "throughput_report.json not provided"}}
    try:
        with open(throughput_json_path) as f:
            data = json.load(f)
        ppm = float(data.get("posts_per_minute", 0))
    except Exception as exc:
        return {"score": 0, "max": WEIGHTS["streaming_throughput"],
                "details": {"error": str(exc)}}

    floor_ppm = 5_000
    if ppm >= THROUGHPUT_TARGET:
        ratio = 1.0
    elif ppm <= floor_ppm:
        ratio = 0.0
    else:
        ratio = (ppm - floor_ppm) / (THROUGHPUT_TARGET - floor_ppm)

    raw_score = ratio * WEIGHTS["streaming_throughput"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["streaming_throughput"],
        "details": {"posts_per_minute": ppm, "target": THROUGHPUT_TARGET},
    }


def score_graph_analysis(sub_rows: list) -> dict:
    """
    Check quality of network graph analysis — specifically whether
    top_spreaders field is populated for predicted misinformation posts.
    Automated proxy: fraction of misinfo predictions that include spreader IDs.
    Full review requires human assessment.
    """
    misinfo_preds = [r for r in sub_rows if str(r.get("label", "0")) == "1"]
    if not misinfo_preds:
        return {"score": 0, "max": WEIGHTS["network_graph_analysis"],
                "details": {"warning": "no misinformation predictions found"}}

    with_spreaders = sum(
        1 for r in misinfo_preds
        if r.get("top_spreaders", "").strip()
    )
    ratio = with_spreaders / len(misinfo_preds)
    raw_score = ratio * WEIGHTS["network_graph_analysis"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["network_graph_analysis"],
        "details": {
            "misinfo_predictions": len(misinfo_preds),
            "with_spreader_analysis": with_spreaders,
            "coverage_ratio": round(ratio, 4),
            "note": "Manual review required for full graph analysis score",
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P2 GraphFlood Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to predictions.csv")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help="Path to ground-truth CSV")
    parser.add_argument("--test_data", default=None,
                        help="(Optional) path to cascades_test.csv")
    parser.add_argument("--throughput_json", default=None,
                        help="Path to throughput_report.json")
    args = parser.parse_args()

    errors = []
    breakdown = {}

    sub_rows, err = safe_load(args.submission, "submission")
    if err:
        errors.append(err)
        sub_rows = []

    gt_rows, err = safe_load(args.ground_truth, "ground_truth")
    if err:
        errors.append(err)
        gt_rows = []

    sub_dir = os.path.dirname(os.path.abspath(args.submission))
    throughput_json = args.throughput_json
    if not throughput_json:
        candidate = os.path.join(sub_dir, "throughput_report.json")
        if os.path.exists(candidate):
            throughput_json = candidate

    if sub_rows and gt_rows:
        y_true, y_score, y_pred = align_predictions(sub_rows, gt_rows)
        if len(y_true) == 0:
            errors.append("No matching post_ids between submission and ground truth.")
            y_true = y_pred = np.array([])

        breakdown["detection_f1"] = (
            score_detection_f1(y_true, y_pred)
            if len(y_true) > 0
            else {"score": 0, "max": WEIGHTS["detection_f1"],
                  "details": {"error": "no aligned predictions"}}
        )
        breakdown["false_positive_rate"] = (
            score_false_positive_rate(y_true, y_pred)
            if len(y_true) > 0
            else {"score": 0, "max": WEIGHTS["false_positive_rate"],
                  "details": {"error": "no aligned predictions"}}
        )
    else:
        for key in ["detection_f1", "false_positive_rate"]:
            breakdown[key] = {"score": 0, "max": WEIGHTS[key],
                              "details": {"error": "missing data"}}

    breakdown["streaming_throughput"] = score_throughput(throughput_json)
    breakdown["network_graph_analysis"] = score_graph_analysis(sub_rows or [])

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
