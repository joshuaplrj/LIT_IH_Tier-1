"""
ChronoReconstruct — Evaluation Script
CSE Problem 1

Usage:
    python evaluate.py --submission solution.csv [--ground_truth ground_truth/CSE_P1_gt.csv]

Output (JSON to stdout):
    {
        "total": 0-100,
        "breakdown": {
            "kendall_tau":   {"score": X, "max": 60},
            "monotonicity":  {"score": X, "max": 20},
            "efficiency":    {"score": X, "max": 10},
            "novelty":       {"score": X, "max": 10}
        },
        "errors": []
    }
"""

import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GROUND_TRUTH_PATH = "ground_truth/CSE_P1_gt.csv"   # placeholder — update for your setup
N_FILES = 500
EFFICIENCY_TIME_LIMIT = 600   # 10 minutes in seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def result(total, breakdown, errors):
    return {"total": round(float(total), 2), "breakdown": breakdown, "errors": errors}


def zero_result(reason: str):
    return result(
        0,
        {
            "kendall_tau":  {"score": 0, "max": 60},
            "monotonicity": {"score": 0, "max": 20},
            "efficiency":   {"score": 0, "max": 10},
            "novelty":      {"score": 0, "max": 10},
        },
        [reason],
    )


def load_submission(path: str):
    """Load and validate submission CSV. Returns (array, errors)."""
    errors = []
    if not os.path.isfile(path):
        errors.append(f"Submission file not found: {path}")
        return None, errors

    try:
        df = pd.read_csv(path)
    except Exception as e:
        errors.append(f"Could not parse CSV: {e}")
        return None, errors

    if "file_index" not in df.columns:
        errors.append("Missing required column 'file_index' in submission.")
        return None, errors

    arr = df["file_index"].values
    if len(arr) != N_FILES:
        errors.append(f"Expected {N_FILES} rows, got {len(arr)}.")
        return None, errors

    arr = arr.astype(int)

    # Check that it is a valid permutation
    if sorted(arr.tolist()) != list(range(N_FILES)):
        errors.append(
            "Submission is not a valid permutation of 0..499. "
            "Check for duplicates or out-of-range indices."
        )
        return None, errors

    return arr, errors


def load_ground_truth(path: str):
    """Load ground-truth permutation CSV."""
    if not os.path.isfile(path):
        return None, [f"Ground truth file not found: {path}"]
    try:
        df = pd.read_csv(path)
        arr = df["file_index"].values.astype(int)
        return arr, []
    except Exception as e:
        return None, [f"Could not parse ground truth: {e}"]


# ---------------------------------------------------------------------------
# Metric: Kendall's Tau
# ---------------------------------------------------------------------------

def compute_kendall_tau_score(pred: np.ndarray, truth: np.ndarray) -> float:
    """
    Compute normalised Kendall's Tau between predicted and ground-truth orderings.
    Returns a score in [0, 60].

    Kendall's Tau ranges from -1 (perfect reversal) to +1 (perfect agreement).
    We map it linearly to [0, 60]: score = 60 * (tau + 1) / 2
    """
    # Convert permutations to rank arrays for tau computation
    n = len(pred)
    pred_rank = np.empty(n, dtype=int)
    pred_rank[pred] = np.arange(n)

    truth_rank = np.empty(n, dtype=int)
    truth_rank[truth] = np.arange(n)

    tau, _ = stats.kendalltau(pred_rank, truth_rank)
    if np.isnan(tau):
        tau = 0.0
    # Map [-1, 1] -> [0, 60]
    normalised = (tau + 1.0) / 2.0
    return round(60.0 * normalised, 3)


# ---------------------------------------------------------------------------
# Metric: Monotonicity
# ---------------------------------------------------------------------------

def compute_monotonicity_score(pred: np.ndarray,
                               signals_dir: str = "signals/",
                               tacho_dir: str = "tachometer/") -> tuple:
    """
    Measure how monotonically the RMS health indicator evolves along the
    predicted ordering. Uses the fraction of adjacent pairs where RMS
    increases (degradation trend).

    Returns (score_out_of_20, details_string).

    NOTE: If signal files are not available during evaluation, this sub-score
    defaults to 0 with a warning.
    """
    if not os.path.isdir(signals_dir):
        return 0.0, "Signal directory not found — monotonicity score set to 0."

    rms_values = []
    try:
        for idx in pred:
            # Try common naming conventions
            candidates = [
                os.path.join(signals_dir, f"signal_{idx:03d}.csv"),
                os.path.join(signals_dir, f"signal_{idx}.csv"),
            ]
            loaded = False
            for c in candidates:
                if os.path.isfile(c):
                    sig = pd.read_csv(c, header=0).iloc[:, 0].values.astype(float)
                    rms_values.append(np.sqrt(np.mean(sig ** 2)))
                    loaded = True
                    break
            if not loaded:
                return 0.0, f"Signal file for index {idx} not found."
    except Exception as e:
        return 0.0, f"Error reading signals for monotonicity: {e}"

    rms = np.array(rms_values)
    n = len(rms) - 1
    if n == 0:
        return 0.0, "Not enough files to compute monotonicity."

    increasing_pairs = int(np.sum(np.diff(rms) > 0))
    mono_fraction = increasing_pairs / n     # fraction of adjacent increasing pairs

    # Map [0.5, 1.0] -> [0, 20]  (random ordering gives ~0.5)
    # Below 0.5: score 0; above 0.5: linear scale to 20
    if mono_fraction <= 0.5:
        score = 0.0
    else:
        score = 20.0 * (mono_fraction - 0.5) / 0.5

    return round(score, 3), f"Monotone fraction: {mono_fraction:.4f}"


# ---------------------------------------------------------------------------
# Metric: Efficiency (provided via flag)
# ---------------------------------------------------------------------------

def compute_efficiency_score(runtime_seconds: float) -> float:
    """
    Returns 10 if runtime < 600s, else 0.
    (Evaluators should time the full pipeline and pass --runtime flag.)
    """
    return 10.0 if runtime_seconds < EFFICIENCY_TIME_LIMIT else 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a ChronoReconstruct submission."
    )
    parser.add_argument("--submission", type=str, required=True,
                        help="Path to the submission solution.csv.")
    parser.add_argument("--ground_truth", type=str, default=GROUND_TRUTH_PATH,
                        help="Path to the ground-truth CSV (file_index column).")
    parser.add_argument("--signals_dir", type=str, default="signals/",
                        help="Path to signals directory (for monotonicity scoring).")
    parser.add_argument("--runtime", type=float, default=None,
                        help="Recorded wall-clock runtime of the submission in seconds.")
    parser.add_argument("--novelty", type=float, default=0.0,
                        help="Novelty score assigned by judges (0–10).")
    args = parser.parse_args()

    errors = []
    breakdown = {
        "kendall_tau":  {"score": 0.0, "max": 60},
        "monotonicity": {"score": 0.0, "max": 20},
        "efficiency":   {"score": 0.0, "max": 10},
        "novelty":      {"score": 0.0, "max": 10},
    }

    # Load submission
    pred, sub_errors = load_submission(args.submission)
    errors.extend(sub_errors)
    if pred is None:
        print(json.dumps(zero_result(" | ".join(errors)), indent=2))
        sys.exit(0)

    # Kendall's Tau
    gt, gt_errors = load_ground_truth(args.ground_truth)
    if gt is not None:
        tau_score = compute_kendall_tau_score(pred, gt)
        breakdown["kendall_tau"]["score"] = tau_score
    else:
        errors.extend(gt_errors)
        errors.append("Kendall Tau score set to 0 — ground truth unavailable.")

    # Monotonicity
    mono_score, mono_msg = compute_monotonicity_score(pred, args.signals_dir)
    breakdown["monotonicity"]["score"] = mono_score
    if mono_msg:
        errors.append(f"Monotonicity note: {mono_msg}")

    # Efficiency
    if args.runtime is not None:
        breakdown["efficiency"]["score"] = compute_efficiency_score(args.runtime)
    else:
        errors.append(
            "Runtime not provided (--runtime flag). Efficiency score set to 0. "
            "Judges should supply the measured runtime."
        )

    # Novelty (judge-assigned)
    novelty = float(np.clip(args.novelty, 0, 10))
    breakdown["novelty"]["score"] = novelty

    total = sum(v["score"] for v in breakdown.values())
    print(json.dumps(result(total, breakdown, errors), indent=2))


if __name__ == "__main__":
    main()
