"""
AIDS-P3: OmniVision — Evaluation / Scoring Script

Usage:
    python evaluate.py --submission <path> [--ground_truth <path>] [--test_data <path>]

Options:
    --submission    Path to metrics.csv produced by starter.py
                    (columns: patient_id, dice_ct_mri, hausdorff_mm, tre_mm, inference_sec)
    --ground_truth  Path to ground-truth CSV (default: ground_truth/AIDS_P3_gt.csv)
                    (columns: patient_id, dice_gt, hausdorff_gt, modalities_present)
    --test_data     (Optional) path to patients data directory for modality coverage check
    --submission_dir Directory containing patient subdirectories with .nii.gz files

Prints a JSON scoring result to stdout.
"""

import argparse
import csv
import json
import math
import os
import sys

import numpy as np

WEIGHTS = {
    "registration_accuracy": 50,
    "modality_coverage": 25,
    "inference_speed": 15,
    "clinical_report": 10,
}
GROUND_TRUTH_PATH = "ground_truth/AIDS_P3_gt.csv"

# Targets for full marks
DICE_TARGET = 0.80       # >= full accuracy marks
DICE_FLOOR = 0.30
HD_TARGET_MM = 5.0       # <= this = full marks
HD_CEILING_MM = 30.0
SPEED_TARGET_S = 30.0    # inference per patient <= 30 s
SPEED_CEILING_S = 300.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(path: str) -> list:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def safe_load(path: str, label: str):
    if not os.path.exists(path):
        return None, f"{label} not found: {path}"
    try:
        rows = load_csv(path)
        return (rows, None) if rows else (None, f"{label} is empty")
    except Exception as exc:
        return None, f"Failed to parse {label}: {exc}"


def parse_float(val, default=float("nan")):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_registration_accuracy(sub_rows: list, gt_rows: list) -> dict:
    """
    Score on Dice coefficient and Hausdorff distance.
    Both must be available; sub_rows values are used as submitted metrics.
    """
    if not sub_rows:
        return {"score": 0, "max": WEIGHTS["registration_accuracy"],
                "details": {"error": "no submission rows"}}

    dices, hds = [], []
    for row in sub_rows:
        d = parse_float(row.get("dice_ct_mri"))
        h = parse_float(row.get("hausdorff_mm"))
        if not math.isnan(d) and d >= 0:
            dices.append(d)
        if not math.isnan(h) and h >= 0:
            hds.append(h)

    if not dices:
        return {"score": 0, "max": WEIGHTS["registration_accuracy"],
                "details": {"error": "no valid Dice values"}}

    mean_dice = float(np.mean(dices))
    mean_hd = float(np.mean(hds)) if hds else HD_CEILING_MM

    # Dice sub-score (60% of registration weight)
    dice_ratio = max(0.0, (mean_dice - DICE_FLOOR) / (DICE_TARGET - DICE_FLOOR))
    dice_ratio = min(1.0, dice_ratio)

    # HD sub-score (40% of registration weight)
    if mean_hd <= HD_TARGET_MM:
        hd_ratio = 1.0
    elif mean_hd >= HD_CEILING_MM:
        hd_ratio = 0.0
    else:
        hd_ratio = 1.0 - (mean_hd - HD_TARGET_MM) / (HD_CEILING_MM - HD_TARGET_MM)

    combined_ratio = 0.6 * dice_ratio + 0.4 * hd_ratio
    raw_score = combined_ratio * WEIGHTS["registration_accuracy"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["registration_accuracy"],
        "details": {
            "mean_dice": round(mean_dice, 4),
            "mean_hausdorff_mm": round(mean_hd, 2),
            "n_patients": len(dices),
        },
    }


def score_modality_coverage(submission_dir: str, sub_rows: list) -> dict:
    """
    Check whether the submission contains output files for each required modality
    (registered_mri, registered_pet, fused_ct_mri) for every patient.
    """
    expected_files = [
        "registered_mri.nii.gz",
        "registered_pet.nii.gz",
        "fused_ct_mri.nii.gz",
    ]
    patient_ids = [r["patient_id"] for r in sub_rows] if sub_rows else []
    if not patient_ids:
        return {"score": 0, "max": WEIGHTS["modality_coverage"],
                "details": {"warning": "no patient IDs found in submission"}}

    found, total = 0, 0
    for pid in patient_ids:
        patient_dir = os.path.join(submission_dir, pid)
        for fname in expected_files:
            total += 1
            fpath = os.path.join(patient_dir, fname)
            # Also accept .npy fallback
            if os.path.exists(fpath) or os.path.exists(fpath.replace(".nii.gz", ".npy")):
                found += 1

    ratio = found / max(total, 1)
    raw_score = ratio * WEIGHTS["modality_coverage"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["modality_coverage"],
        "details": {
            "files_found": found,
            "files_expected": total,
            "coverage_ratio": round(ratio, 4),
        },
    }


def score_inference_speed(sub_rows: list) -> dict:
    """
    Score average per-patient inference time.
    Full marks if mean <= 30 s; zero if mean >= 300 s.
    """
    times = [parse_float(r.get("inference_sec")) for r in (sub_rows or [])]
    times = [t for t in times if not math.isnan(t) and t > 0]
    if not times:
        return {"score": 0, "max": WEIGHTS["inference_speed"],
                "details": {"warning": "no inference times found"}}

    mean_time = float(np.mean(times))
    if mean_time <= SPEED_TARGET_S:
        ratio = 1.0
    elif mean_time >= SPEED_CEILING_S:
        ratio = 0.0
    else:
        ratio = 1.0 - (mean_time - SPEED_TARGET_S) / (SPEED_CEILING_S - SPEED_TARGET_S)

    raw_score = ratio * WEIGHTS["inference_speed"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["inference_speed"],
        "details": {"mean_inference_sec": round(mean_time, 2),
                    "target_sec": SPEED_TARGET_S},
    }


def score_clinical_report(submission_dir: str) -> dict:
    """
    Automated proxy: check for a clinical_report file
    (PDF, TXT, or MD) in the submission directory.
    Full review requires human assessment.
    """
    candidates = ["clinical_report.pdf", "clinical_report.txt",
                  "clinical_report.md", "report.pdf", "report.txt"]
    found = any(os.path.exists(os.path.join(submission_dir, f))
                for f in candidates)
    raw_score = WEIGHTS["clinical_report"] if found else 0
    return {
        "score": float(raw_score),
        "max": WEIGHTS["clinical_report"],
        "details": {
            "report_found": found,
            "note": "Full clinical report score requires human review",
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P3 OmniVision Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to metrics.csv")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help="Path to ground-truth CSV")
    parser.add_argument("--test_data", default=None,
                        help="(Optional) path to test patient data directory")
    parser.add_argument("--submission_dir", default=None,
                        help="Directory with patient subdirs (defaults to dirname of metrics.csv)")
    args = parser.parse_args()

    errors = []
    breakdown = {}

    sub_rows, err = safe_load(args.submission, "submission metrics.csv")
    if err:
        errors.append(err)
        sub_rows = []

    gt_rows, err = safe_load(args.ground_truth, "ground_truth")
    if err:
        errors.append(err)
        gt_rows = []

    submission_dir = args.submission_dir or os.path.dirname(
        os.path.abspath(args.submission))

    breakdown["registration_accuracy"] = score_registration_accuracy(
        sub_rows or [], gt_rows or [])
    breakdown["modality_coverage"] = score_modality_coverage(
        submission_dir, sub_rows or [])
    breakdown["inference_speed"] = score_inference_speed(sub_rows or [])
    breakdown["clinical_report"] = score_clinical_report(submission_dir)

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
