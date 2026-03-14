#!/usr/bin/env python3
"""
CYBER-P3: CryptoPuzzle — Evaluator
Scores a submission.json and report.md against the ground truth.

Usage:
    python evaluate.py --submission submission.json [--ground_truth ground_truth.json]
                       [--report report.md]

Scoring rubric:
  Vulnerability identification  40 points
  Ciphertexts decrypted         40 points
  Security assessment quality   20 points
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Configuration — replace with actual ground truth path when available
# ---------------------------------------------------------------------------
GROUND_TRUTH_PATH = "ground_truth.json"  # <-- REPLACE with actual path

# Ground truth format:
# {
#   "plaintexts": [{"id": 0, "plaintext_hex": "...", "key_hex": "..."}, ...],
#   "vulnerabilities": [{"component": "LWE", "description": "..."}, ...]
# }

WEIGHT_VULN    = 0.40
WEIGHT_DECRYPT = 0.40
WEIGHT_REPORT  = 0.20
MAX_SCORE = 100

# Required report sections
REPORT_REQUIRED_SECTIONS = [
    r"##\s*Executive Summary",
    r"##\s*Key Exchange Analysis",
    r"##\s*Block Cipher Analysis",
    r"##\s*MAC Analysis",
    r"##\s*Vulnerabilities Found",
    r"##\s*Proposed Fixes",
]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_json(path: str, label: str) -> Dict:
    if not os.path.isfile(path):
        return {"_error": f"{label} not found: {path}"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return {"_error": f"{label} invalid JSON: {e}"}


def load_text(path: str, label: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return ""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_submission(data: Dict) -> List[str]:
    errors = []
    if not isinstance(data, dict):
        errors.append("Submission root must be a JSON object.")
        return errors
    if "decryptions" not in data:
        errors.append("Missing key: 'decryptions'")
    else:
        for i, d in enumerate(data.get("decryptions", [])):
            for field in ("id", "plaintext_hex", "key_hex"):
                if field not in d:
                    errors.append(f"decryptions[{i}] missing field '{field}'")
    if "vulnerabilities" not in data:
        errors.append("Missing key: 'vulnerabilities'")
    else:
        for i, v in enumerate(data.get("vulnerabilities", [])):
            for field in ("component", "description", "severity"):
                if field not in v:
                    errors.append(f"vulnerabilities[{i}] missing field '{field}'")
    return errors


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_vulnerabilities(
    pred_vulns: List[Dict],
    gt_vulns: List[Dict],
) -> Tuple[float, Dict]:
    """
    Award points for each correctly identified vulnerability component.
    Full credit requires: correct component name + meaningful description.
    Partial credit (50%) for: correct component but vague description (< 20 chars).
    """
    gt_components = {v["component"].lower() for v in gt_vulns}
    max_pts = round(WEIGHT_VULN * MAX_SCORE, 2)

    if not gt_components:
        return max_pts, {"note": "No ground-truth vulnerabilities to compare against."}

    pts_per_component = max_pts / len(gt_components)
    earned = 0.0
    detail = {}

    found_components = set()
    for pv in pred_vulns:
        comp = pv.get("component", "").lower()
        desc = pv.get("description", "")
        if comp in gt_components and comp not in found_components:
            found_components.add(comp)
            if len(desc) >= 20:
                earned += pts_per_component
                detail[comp] = f"FULL credit ({pts_per_component:.1f}pts)"
            else:
                earned += pts_per_component * 0.5
                detail[comp] = f"PARTIAL credit ({pts_per_component*0.5:.1f}pts) — description too brief"
        elif comp not in gt_components:
            detail[f"unknown_{comp}"] = "Not in ground truth (no credit)"

    for gc in gt_components - found_components:
        detail[gc] = "MISSED — not identified (0pts)"

    return round(earned, 2), detail


def score_decryptions(
    pred_decryptions: List[Dict],
    gt_plaintexts: List[Dict],
) -> Tuple[float, Dict]:
    """
    Score based on fraction of ciphertexts correctly decrypted.
    Exact hex match on plaintext_hex (case-insensitive, stripped).
    """
    max_pts = round(WEIGHT_DECRYPT * MAX_SCORE, 2)
    gt_by_id = {d["id"]: d["plaintext_hex"].lower().strip() for d in gt_plaintexts}
    pred_by_id = {d["id"]: d.get("plaintext_hex", "").lower().strip()
                  for d in pred_decryptions}

    total    = len(gt_by_id)
    correct  = 0
    detail   = {}

    for item_id, gt_pt in gt_by_id.items():
        pred_pt = pred_by_id.get(item_id, "")
        if pred_pt and pred_pt == gt_pt:
            correct += 1
        elif pred_pt:
            detail[item_id] = "WRONG plaintext"
        else:
            detail[item_id] = "NOT decrypted"

    fraction  = correct / total if total > 0 else 0.0
    earned    = round(fraction * max_pts, 2)
    return earned, {"correct": correct, "total": total, "fraction": round(fraction, 4), **detail}


def score_report(report_text: str) -> Tuple[float, Dict]:
    """
    Score the security assessment report on section presence and content depth.
    """
    max_pts = round(WEIGHT_REPORT * MAX_SCORE, 2)
    pts_per_section = max_pts / len(REPORT_REQUIRED_SECTIONS)
    earned = 0.0
    detail = {}

    for pattern in REPORT_REQUIRED_SECTIONS:
        section_name = pattern.replace(r"##\s*", "").replace("\\", "")
        if re.search(pattern, report_text, re.IGNORECASE):
            # Extract body and check it is substantive (> 80 chars)
            body_match = re.search(
                pattern + r"\s*(.*?)(?=##|\Z)", report_text, re.IGNORECASE | re.DOTALL
            )
            body = body_match.group(1).strip() if body_match else ""
            if len(body) > 80:
                earned += pts_per_section
                detail[section_name] = f"PASS ({pts_per_section:.1f}pts)"
            else:
                earned += pts_per_section * 0.5
                detail[section_name] = f"PARTIAL ({pts_per_section*0.5:.1f}pts) — section too brief"
        else:
            detail[section_name] = "MISSING (0pts)"

    return round(earned, 2), detail


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate(submission_path: str, ground_truth_path: str, report_path: str) -> Dict:
    result = {"total": 0, "breakdown": {}, "errors": []}

    # Load submission
    submission = load_json(submission_path, "Submission")
    if "_error" in submission:
        result["errors"].append(submission["_error"])
        print(json.dumps(result, indent=2))
        return result

    fmt_errors = validate_submission(submission)
    result["errors"].extend(fmt_errors)

    pred_decryptions = submission.get("decryptions", [])
    pred_vulns       = submission.get("vulnerabilities", [])

    # Load ground truth
    gt = load_json(ground_truth_path, "Ground truth")
    has_gt = "_error" not in gt

    if not has_gt:
        result["errors"].append(gt.get("_error", "Ground truth unavailable."))

    # Score vulnerabilities
    gt_vulns = gt.get("vulnerabilities", []) if has_gt else []
    v_score, v_detail = score_vulnerabilities(pred_vulns, gt_vulns)
    result["breakdown"]["vulnerability_identification"] = {
        "score": v_score,
        "max":   round(WEIGHT_VULN * MAX_SCORE, 2),
        "detail": v_detail,
    }

    # Score decryptions
    gt_pts = gt.get("plaintexts", []) if has_gt else []
    d_score, d_detail = score_decryptions(pred_decryptions, gt_pts)
    result["breakdown"]["ciphertexts_decrypted"] = {
        "score": d_score,
        "max":   round(WEIGHT_DECRYPT * MAX_SCORE, 2),
        "detail": d_detail,
    }

    # Score report
    report_text = load_text(report_path, "Report")
    r_score, r_detail = score_report(report_text)
    result["breakdown"]["security_assessment"] = {
        "score": r_score,
        "max":   round(WEIGHT_REPORT * MAX_SCORE, 2),
        "detail": r_detail,
    }

    result["total"] = round(v_score + d_score + r_score, 2)
    return result


def main():
    parser = argparse.ArgumentParser(description="CYBER-P3 Evaluator — CryptoPuzzle")
    parser.add_argument("--submission",   required=True,
                        help="Path to submission.json")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help=f"Path to ground truth JSON (default: {GROUND_TRUTH_PATH})")
    parser.add_argument("--report",       default="report.md",
                        help="Path to security assessment report.md (default: report.md)")
    args = parser.parse_args()

    result = evaluate(args.submission, args.ground_truth, args.report)
    print(json.dumps(result, indent=2))
    sys.exit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
