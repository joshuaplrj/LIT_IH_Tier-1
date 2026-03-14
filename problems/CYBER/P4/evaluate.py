#!/usr/bin/env python3
"""
CYBER-P4: Supply Chain Sentinel — Evaluator
Scores a submission.json against the ground truth.

Usage:
    python evaluate.py --submission submission.json [--ground_truth ground_truth.json]

Scoring rubric:
  Detection rate (TP / total compromised)    50 points
  False positive rate penalty                20 points  (lower FPR = higher score)
  SBOM completeness                          30 points
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GROUND_TRUTH_PATH = "ground_truth.json"  # <-- REPLACE with actual path

# Ground truth format:
# {
#   "compromised_packages": [
#     {"name": "...", "version": "...", "ecosystem": "..."}
#   ],
#   "total_packages": 500
# }

WEIGHT_DETECTION  = 0.50
WEIGHT_FPR        = 0.20   # penalty converted to score: score = (1 - FPR) * max
WEIGHT_SBOM       = 0.30
MAX_SCORE         = 100

SBOM_REQUIRED_FIELDS = ("name", "version", "purl")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_json(path: str, label: str) -> Dict:
    if not os.path.isfile(path):
        return {"_error": f"{label} file not found: {path}"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return {"_error": f"{label} invalid JSON: {e}"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_submission(data: Dict) -> List[str]:
    errors = []
    if not isinstance(data, dict):
        errors.append("Submission root must be a JSON object.")
        return errors

    required_keys = ("compromised_packages", "sbom", "blast_radius", "remediation_plan")
    for k in required_keys:
        if k not in data:
            errors.append(f"Missing top-level key: '{k}'")

    for i, pkg in enumerate(data.get("compromised_packages", [])):
        for field in ("name", "version", "ecosystem", "attack_vector",
                      "payload_type", "severity", "remediation"):
            if field not in pkg:
                errors.append(f"compromised_packages[{i}] missing field '{field}'")

    sbom = data.get("sbom", {})
    if "components" not in sbom:
        errors.append("sbom missing 'components' key")
    else:
        for i, comp in enumerate(sbom.get("components", [])[:5]):  # spot-check first 5
            for field in SBOM_REQUIRED_FIELDS:
                if field not in comp:
                    errors.append(f"sbom.components[{i}] missing field '{field}'")

    return errors


# ---------------------------------------------------------------------------
# Package key normalisation
# ---------------------------------------------------------------------------

def pkg_key(name: str, version: str, ecosystem: str = "") -> str:
    return f"{ecosystem.lower()}/{name.lower()}@{version.lower()}"


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_detection(
    pred_compromised: List[Dict],
    gt_compromised: List[Dict],
) -> Tuple[float, Dict]:
    """
    Detection rate = TP / (TP + FN).
    A TP requires matching name + version + ecosystem.
    """
    max_pts = round(WEIGHT_DETECTION * MAX_SCORE, 2)
    gt_keys  = {pkg_key(p["name"], p["version"], p.get("ecosystem", "")) for p in gt_compromised}
    pred_keys = {pkg_key(p["name"], p["version"], p.get("ecosystem", "")) for p in pred_compromised}

    tp = len(gt_keys & pred_keys)
    fn = len(gt_keys - pred_keys)
    fp = len(pred_keys - gt_keys)

    detection_rate = tp / len(gt_keys) if gt_keys else 0.0
    earned = round(detection_rate * max_pts, 2)

    return earned, {
        "true_positives":  tp,
        "false_negatives": fn,
        "false_positives": fp,
        "detection_rate":  round(detection_rate, 4),
        "missed":          sorted(gt_keys - pred_keys),
    }


def score_false_positive_rate(
    pred_compromised: List[Dict],
    gt_compromised: List[Dict],
    total_packages: int,
) -> Tuple[float, Dict]:
    """
    FPR = FP / (FP + TN)  where TN = total_packages - len(gt_compromised).
    Score = (1 - FPR) * max_pts  (lower FPR is better).
    """
    max_pts = round(WEIGHT_FPR * MAX_SCORE, 2)
    gt_keys  = {pkg_key(p["name"], p["version"], p.get("ecosystem", "")) for p in gt_compromised}
    pred_keys = {pkg_key(p["name"], p["version"], p.get("ecosystem", "")) for p in pred_compromised}

    fp        = len(pred_keys - gt_keys)
    negatives = max(total_packages - len(gt_keys), 1)
    fpr       = fp / negatives
    earned    = round((1.0 - fpr) * max_pts, 2)
    earned    = max(earned, 0.0)

    return earned, {
        "false_positives": fp,
        "total_negatives": negatives,
        "fpr":             round(fpr, 4),
    }


def score_sbom(sbom: Dict, total_packages: int) -> Tuple[float, Dict]:
    """
    SBOM completeness = fraction of expected packages present in SBOM,
    multiplied by fraction of components that have all required fields.
    """
    max_pts = round(WEIGHT_SBOM * MAX_SCORE, 2)
    components = sbom.get("components", [])

    # Coverage: unique (name, version) pairs in SBOM vs total
    unique = len({(c.get("name", ""), c.get("version", "")) for c in components})
    coverage = min(unique / max(total_packages, 1), 1.0)

    # Field completeness: fraction of components with all required fields
    complete_count = sum(
        1 for c in components if all(f in c for f in SBOM_REQUIRED_FIELDS)
    )
    field_frac = complete_count / len(components) if components else 0.0

    # Bonus: PURL format check
    purl_ok = sum(1 for c in components if re.match(r"^pkg:[a-z]+/", c.get("purl", "")))
    purl_frac = purl_ok / len(components) if components else 0.0

    completeness = coverage * 0.6 + field_frac * 0.3 + purl_frac * 0.1
    earned = round(completeness * max_pts, 2)

    return earned, {
        "components_in_sbom": unique,
        "total_expected":     total_packages,
        "coverage":           round(coverage, 4),
        "field_completeness": round(field_frac, 4),
        "purl_format_ok":     round(purl_frac, 4),
    }


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate(submission_path: str, ground_truth_path: str) -> Dict:
    result = {"total": 0, "breakdown": {}, "errors": []}

    submission = load_json(submission_path, "Submission")
    if "_error" in submission:
        result["errors"].append(submission["_error"])
        print(json.dumps(result, indent=2))
        return result

    fmt_errors = validate_submission(submission)
    result["errors"].extend(fmt_errors)

    pred_compromised = submission.get("compromised_packages", [])
    sbom             = submission.get("sbom", {})

    # Load ground truth
    gt = load_json(ground_truth_path, "Ground truth")
    has_gt = "_error" not in gt
    if not has_gt:
        result["errors"].append(gt.get("_error", "Ground truth unavailable."))

    gt_compromised  = gt.get("compromised_packages", []) if has_gt else []
    total_packages  = gt.get("total_packages", 500)

    # Score detection rate
    det_score, det_detail = score_detection(pred_compromised, gt_compromised)
    result["breakdown"]["detection_rate"] = {
        "score":  det_score,
        "max":    round(WEIGHT_DETECTION * MAX_SCORE, 2),
        "detail": det_detail,
    }

    # Score false positive rate
    fpr_score, fpr_detail = score_false_positive_rate(
        pred_compromised, gt_compromised, total_packages
    )
    result["breakdown"]["false_positive_rate"] = {
        "score":  fpr_score,
        "max":    round(WEIGHT_FPR * MAX_SCORE, 2),
        "detail": fpr_detail,
    }

    # Score SBOM completeness
    sbom_score, sbom_detail = score_sbom(sbom, total_packages)
    result["breakdown"]["sbom_completeness"] = {
        "score":  sbom_score,
        "max":    round(WEIGHT_SBOM * MAX_SCORE, 2),
        "detail": sbom_detail,
    }

    result["total"] = round(det_score + fpr_score + sbom_score, 2)
    return result


def main():
    parser = argparse.ArgumentParser(description="CYBER-P4 Evaluator — Supply Chain Sentinel")
    parser.add_argument("--submission",   required=True,
                        help="Path to submission.json")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help=f"Path to ground truth JSON (default: {GROUND_TRUTH_PATH})")
    args = parser.parse_args()

    result = evaluate(args.submission, args.ground_truth)
    print(json.dumps(result, indent=2))
    sys.exit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
