#!/usr/bin/env python3
"""
CYBER-P1: Phantom Protocol — Evaluator
Scores a submission.json against ground_truth.json.

Usage:
    python evaluate.py --submission submission.json --ground_truth ground_truth.json

Ground truth JSON format:
{
  "channels": [
    {
      "channel_id": "CC-001",
      "type": "timing | packet_size | doh_tunneling",
      "flow_key": "src_ip:src_port->dst_ip:dst_port/proto",
      "packet_range": [first_pkt_no, last_pkt_no],
      "decoded_message": "plaintext string",
      "severity": "Low | Medium | Critical"
    }
  ]
}
"""

import argparse
import json
import sys
import os
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Configuration — update GROUND_TRUTH_PATH for local testing
# ---------------------------------------------------------------------------
GROUND_TRUTH_PATH = "ground_truth.json"   # <-- REPLACE with actual path

WEIGHT_DETECTION   = 0.50   # Precision / Recall F1
WEIGHT_DECODING    = 0.30   # Exact-match decoded messages
WEIGHT_SEVERITY    = 0.20   # Severity classification accuracy

MAX_SCORE = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: str, label: str) -> Dict:
    if not os.path.isfile(path):
        return {"error": f"{label} file not found: {path}"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        return {"error": f"{label} is not valid JSON: {exc}"}


def validate_submission(data: Dict) -> List[str]:
    """Return a list of format error strings; empty list means valid."""
    errors = []
    if not isinstance(data, dict):
        errors.append("Submission root must be a JSON object.")
        return errors
    if "channels" not in data:
        errors.append("Missing top-level key: 'channels'")
    else:
        for i, ch in enumerate(data.get("channels", [])):
            for field in ("channel_id", "type", "flow_key", "packet_range",
                          "decoded_message", "severity", "confidence"):
                if field not in ch:
                    errors.append(f"Channel index {i} missing field: '{field}'")
            if "type" in ch and ch["type"] not in ("timing", "packet_size", "doh_tunneling"):
                errors.append(f"Channel index {i}: invalid type '{ch['type']}'")
            if "severity" in ch and ch["severity"] not in ("Low", "Medium", "Critical"):
                errors.append(f"Channel index {i}: invalid severity '{ch['severity']}'")
    if "summary" not in data:
        errors.append("Missing top-level key: 'summary'")
    return errors


# ---------------------------------------------------------------------------
# Matching — a predicted channel matches a ground-truth channel if their
# flow_keys are identical (exact 5-tuple string match).
# ---------------------------------------------------------------------------

def match_channels(
    pred_channels: List[Dict],
    gt_channels: List[Dict],
) -> Tuple[int, int, int]:
    """
    Returns (true_positives, false_positives, false_negatives).
    A TP requires flow_key match.
    """
    gt_keys  = {ch["flow_key"] for ch in gt_channels}
    pred_keys = {ch["flow_key"] for ch in pred_channels}

    tp = len(gt_keys & pred_keys)
    fp = len(pred_keys - gt_keys)
    fn = len(gt_keys - pred_keys)
    return tp, fp, fn


def score_detection(pred: List[Dict], gt: List[Dict]) -> Tuple[float, Dict]:
    tp, fp, fn = match_channels(pred, gt)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    raw_score = round(f1 * WEIGHT_DETECTION * MAX_SCORE, 2)
    return raw_score, {
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn,
    }


def score_decoding(pred: List[Dict], gt: List[Dict]) -> Tuple[float, Dict]:
    """Exact-match decoded messages for correctly detected channels."""
    gt_by_key  = {ch["flow_key"]: ch["decoded_message"] for ch in gt}
    pred_by_key = {ch["flow_key"]: ch["decoded_message"] for ch in pred}

    correct = 0
    total   = len(gt_by_key)
    for key, gt_msg in gt_by_key.items():
        pred_msg = pred_by_key.get(key, "")
        if pred_msg.strip() == gt_msg.strip():
            correct += 1

    fraction  = correct / total if total > 0 else 0.0
    raw_score = round(fraction * WEIGHT_DECODING * MAX_SCORE, 2)
    return raw_score, {"correct": correct, "total": total, "fraction": round(fraction, 4)}


def score_severity(pred: List[Dict], gt: List[Dict]) -> Tuple[float, Dict]:
    """Severity accuracy for correctly detected channels."""
    gt_by_key  = {ch["flow_key"]: ch["severity"] for ch in gt}
    pred_by_key = {ch["flow_key"]: ch["severity"] for ch in pred}

    correct = 0
    total   = len(gt_by_key)
    for key, gt_sev in gt_by_key.items():
        if pred_by_key.get(key) == gt_sev:
            correct += 1

    fraction  = correct / total if total > 0 else 0.0
    raw_score = round(fraction * WEIGHT_SEVERITY * MAX_SCORE, 2)
    return raw_score, {"correct": correct, "total": total, "fraction": round(fraction, 4)}


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate(submission_path: str, ground_truth_path: str) -> Dict:
    result = {
        "total":     0,
        "breakdown": {},
        "errors":    [],
    }

    # Load submission
    submission = load_json(submission_path, "Submission")
    if "error" in submission:
        result["errors"].append(submission["error"])
        print(json.dumps(result, indent=2))
        return result

    # Validate submission format
    fmt_errors = validate_submission(submission)
    if fmt_errors:
        result["errors"].extend(fmt_errors)
        # Do not abort — compute partial scores where possible

    pred_channels = submission.get("channels", [])

    # Load ground truth
    ground_truth = load_json(ground_truth_path, "Ground truth")
    if "error" in ground_truth:
        result["errors"].append(ground_truth["error"])
        result["errors"].append("Cannot compute detection/decoding scores without ground truth.")
        print(json.dumps(result, indent=2))
        return result

    gt_channels = ground_truth.get("channels", [])

    # Score each component
    det_score,  det_detail  = score_detection(pred_channels, gt_channels)
    dec_score,  dec_detail  = score_decoding(pred_channels, gt_channels)
    sev_score,  sev_detail  = score_severity(pred_channels, gt_channels)

    total = round(det_score + dec_score + sev_score, 2)

    result["total"] = total
    result["breakdown"] = {
        "detection_precision_recall": {
            "score": det_score,
            "max":   round(WEIGHT_DETECTION * MAX_SCORE, 2),
            "detail": det_detail,
        },
        "decoded_messages": {
            "score": dec_score,
            "max":   round(WEIGHT_DECODING * MAX_SCORE, 2),
            "detail": dec_detail,
        },
        "severity_classification": {
            "score": sev_score,
            "max":   round(WEIGHT_SEVERITY * MAX_SCORE, 2),
            "detail": sev_detail,
        },
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="CYBER-P1 Evaluator — Phantom Protocol")
    parser.add_argument("--submission",   required=True,
                        help="Path to submission JSON file")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help=f"Path to ground truth JSON file (default: {GROUND_TRUTH_PATH})")
    args = parser.parse_args()

    result = evaluate(args.submission, args.ground_truth)
    print(json.dumps(result, indent=2))
    sys.exit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
