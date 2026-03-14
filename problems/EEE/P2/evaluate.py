"""
FaultSense — Evaluation / Scoring Script
EEE-P2

Usage:
    python evaluate.py --submission submission/predictions.csv \
                       --ground_truth HIDDEN_fault_labels.csv \
                       [--dataset_dir prerequisites/EEE/EEE-P2/fault_dataset]

Outputs a JSON scoring report to stdout.

Ground truth CSV expected columns:
    fault_id, fault_type, affected_bus[, fault_resistance_ohm, fault_location_pct]
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

WEIGHT_CLASSIFICATION = 0.50
WEIGHT_BUS            = 0.30
WEIGHT_SPEED          = 0.20

FAULT_TYPES  = ["normal", "SLG", "LL", "DLG", "LLL", "HIF"]
VALID_BUSES  = {1, 5, 10, 30}

# Speed thresholds in ms per sample
SPEED_FULL_MARKS  = 1.0    # ≤ 1 ms → full 20 pts
SPEED_HALF_MARKS  = 5.0    # ≤ 5 ms → 10 pts
SPEED_MIN_MARKS   = 20.0   # ≤ 20 ms → 5 pts


def error_result(msg: str) -> dict:
    return {"total": 0, "breakdown": {}, "errors": [msg]}


# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────

def validate_submission(sub_df: pd.DataFrame) -> list:
    """Return a list of error strings (empty = valid)."""
    errors = []

    required_cols = {"fault_id", "predicted_fault_type", "predicted_affected_bus"}
    missing = required_cols - set(sub_df.columns)
    if missing:
        errors.append(f"Missing columns: {missing}")
        return errors  # can't proceed

    if sub_df["fault_id"].duplicated().any():
        errors.append("Duplicate fault_id entries detected")

    invalid_types = set(sub_df["predicted_fault_type"].unique()) - set(FAULT_TYPES)
    if invalid_types:
        errors.append(f"Invalid fault types: {invalid_types}")

    # Convert bus to int for checking
    try:
        buses = sub_df["predicted_affected_bus"].astype(int)
        invalid_buses = set(buses.unique()) - VALID_BUSES
        if invalid_buses:
            errors.append(f"Invalid bus IDs: {invalid_buses}")
    except ValueError:
        errors.append("predicted_affected_bus must be numeric (1, 5, 10, or 30)")

    return errors


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

def score_classification(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Score fault type classification (max 50 pts).
    Full marks for >= 95% accuracy; linear interpolation below.
    """
    acc = accuracy_score(y_true, y_pred)
    target_acc = 0.95

    if acc >= target_acc:
        pts = 50.0
    else:
        pts = round(50.0 * (acc / target_acc), 2)

    # Per-class accuracy
    cm = confusion_matrix(y_true, y_pred, labels=FAULT_TYPES)
    per_class_acc = {}
    for i, cls in enumerate(FAULT_TYPES):
        total_cls = cm[i].sum()
        correct   = cm[i, i]
        per_class_acc[cls] = round(correct / total_cls, 3) if total_cls > 0 else None

    hif_recall = per_class_acc.get("HIF", 0) or 0
    hif_note = (f"HIF recall: {hif_recall:.1%} "
                f"({'PASS' if hif_recall >= 0.90 else 'BELOW target 90%'})")

    return {
        "score": pts,
        "max": 50,
        "overall_accuracy": round(acc, 4),
        "per_class_accuracy": per_class_acc,
        "hif_note": hif_note,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": FAULT_TYPES,
    }


def score_bus_identification(y_true_bus: np.ndarray, y_pred_bus: np.ndarray) -> dict:
    """Score bus identification accuracy (max 30 pts)."""
    acc = accuracy_score(y_true_bus, y_pred_bus)
    pts = round(30.0 * acc, 2)
    return {
        "score": pts,
        "max": 30,
        "accuracy": round(acc, 4),
    }


def score_speed(ms_per_sample: float) -> dict:
    """Score inference speed (max 20 pts)."""
    if ms_per_sample <= SPEED_FULL_MARKS:
        pts = 20.0
    elif ms_per_sample <= SPEED_HALF_MARKS:
        # Linear between 1 ms (20 pts) and 5 ms (10 pts)
        pts = round(20.0 - 10.0 * (ms_per_sample - 1.0) / (5.0 - 1.0), 2)
    elif ms_per_sample <= SPEED_MIN_MARKS:
        pts = 5.0
    else:
        pts = 0.0

    return {
        "score": pts,
        "max": 20,
        "ms_per_sample": round(ms_per_sample, 4),
        "note": f"{'PASS' if ms_per_sample <= SPEED_FULL_MARKS else 'SLOW'} "
                f"(target ≤ {SPEED_FULL_MARKS} ms)",
    }


# ─────────────────────────────────────────────
# SPEED BENCHMARK
# ─────────────────────────────────────────────

def benchmark_inference_speed(dataset_dir: str, n_samples: int = 50) -> float:
    """
    Load n_samples fault files and measure average feature-extraction time.
    Returns ms per sample.
    """
    files = sorted(Path(dataset_dir).glob("fault_*.csv"))[:n_samples]
    if not files:
        return 999.0  # penalize if dataset not found

    times = []
    for fp in files:
        t0 = time.perf_counter()
        df = pd.read_csv(fp)
        # Time the load + basic feature extraction (mimics real inference)
        _ = df.values
        times.append(time.perf_counter() - t0)

    ms_per_sample = np.mean(times) * 1000
    return float(ms_per_sample)


# ─────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────

def evaluate(submission_path: str, ground_truth_path: str, dataset_dir: str) -> dict:
    errors = []

    # --- Load submission ---
    try:
        sub_df = pd.read_csv(submission_path)
    except FileNotFoundError:
        return error_result(f"Submission file not found: {submission_path}")
    except Exception as e:
        return error_result(f"Could not parse submission CSV: {e}")

    val_errors = validate_submission(sub_df)
    if val_errors:
        return {"total": 0, "breakdown": {}, "errors": val_errors}

    # --- Load ground truth ---
    try:
        gt_df = pd.read_csv(ground_truth_path)
    except FileNotFoundError:
        # Cannot score without labels; return a structural-only check
        return {
            "total": None,
            "breakdown": {},
            "errors": [
                f"Ground truth file not found: {ground_truth_path}. "
                "Submission structure is valid. Scoring requires ground truth."
            ],
        }

    # Merge on fault_id
    merged = gt_df.merge(sub_df, on="fault_id", how="inner")
    n_total  = len(gt_df)
    n_scored = len(merged)
    if n_scored < n_total:
        errors.append(f"Only {n_scored}/{n_total} fault IDs matched in submission")

    if n_scored == 0:
        return error_result("No matching fault IDs between submission and ground truth")

    y_true_type = merged["fault_type"].values
    y_pred_type = merged["predicted_fault_type"].values

    gt_bus_col  = "affected_bus" if "affected_bus" in gt_df.columns else None
    if gt_bus_col:
        y_true_bus = merged[gt_bus_col].astype(str).values
        y_pred_bus = merged["predicted_affected_bus"].astype(str).values
    else:
        y_true_bus = y_pred_bus = None

    # ── Classification score (50 pts) ──
    cls_result = score_classification(y_true_type, y_pred_type)

    # ── Bus score (30 pts) ──
    if y_true_bus is not None:
        bus_result = score_bus_identification(y_true_bus, y_pred_bus)
    else:
        bus_result = {"score": 0, "max": 30, "accuracy": None,
                      "note": "Ground truth missing 'affected_bus' column"}
        errors.append("Ground truth missing 'affected_bus' — bus score set to 0")

    # ── Speed score (20 pts) ──
    ms_per_sample = benchmark_inference_speed(dataset_dir, n_samples=50)
    speed_result  = score_speed(ms_per_sample)

    total = round(cls_result["score"] + bus_result["score"] + speed_result["score"], 2)

    return {
        "total": total,
        "breakdown": {
            "classification_accuracy": cls_result,
            "bus_identification":      bus_result,
            "inference_speed":         speed_result,
        },
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="FaultSense Evaluator")
    parser.add_argument("--submission",    required=True,
                        help="Path to predictions.csv")
    parser.add_argument("--ground_truth",
                        default="prerequisites/EEE/EEE-P2/HIDDEN_fault_labels.csv",
                        help="Path to ground truth labels CSV")
    parser.add_argument("--dataset_dir",
                        default="prerequisites/EEE/EEE-P2/fault_dataset",
                        help="Directory of fault CSVs for speed benchmark")
    args = parser.parse_args()

    result = evaluate(args.submission, args.ground_truth, args.dataset_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
