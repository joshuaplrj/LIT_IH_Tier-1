"""
IT-P4: AccessibilityAI — Evaluator
=====================================
Usage:
    python evaluate.py --submission ./submission [--ground_truth ./ground_truth]

Reads:
    submission/reports/<slug>/violations.json   — detected violations per site
    submission/summary.json                     — aggregate metrics
    ground_truth/<slug>.json                    — ground truth violations (list of dicts)

Ground truth file schema (per item):
    {
        "url": "https://...",
        "criterion": "1.4.3",
        "element_selector": "button.cta",
        "severity": "serious"
    }

Outputs JSON:
    {
      "total": 0-100,
      "breakdown": {
        "detection_precision_recall": {"score": X, "max": 50},
        "report_quality":             {"score": X, "max": 25},
        "false_positive_rate":        {"score": X, "max": 25}
      },
      "errors": []
    }
"""

import argparse
import json
import os
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

PRECISION_EXCELLENT = 0.90
PRECISION_ACCEPTABLE = 0.50
RECALL_EXCELLENT = 0.80
RECALL_ACCEPTABLE = 0.40

# False positive rate
FPR_EXCELLENT = 0.05     # <= 5% FPR => full marks
FPR_LIMIT = 0.10         # > 10% FPR => 0 marks for this section (stated requirement)
FPR_ACCEPTABLE = 0.10

# Auto-fix rate bonus threshold
AUTO_FIX_BONUS_THRESHOLD = 0.30  # 30% auto-fix rate for bonus

GROUND_TRUTH_PATH = "./ground_truth"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    if not path.exists():
        return None, f"File not found: {path}"
    try:
        with open(path) as f:
            return json.load(f), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error in {path}: {exc}"


def url_slug(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    slug = (parsed.netloc + parsed.path).strip("/").replace("/", "_").replace(".", "_")
    return slug or "root"


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
# Violation matching
# ---------------------------------------------------------------------------


def _violation_key(item: Dict) -> str:
    """Stable key for matching a detected violation to a ground truth entry.

    Matches on (criterion, element_selector) with normalised whitespace.
    """
    criterion = str(item.get("criterion", "")).strip()
    selector = str(item.get("element_selector", "")).strip().lower()
    return f"{criterion}|{selector}"


def compute_detection_metrics(
    detected: List[Dict],
    ground_truth: List[Dict],
) -> Dict[str, float]:
    """Compute TP, FP, FN, precision, recall, FPR for one site."""
    gt_keys: Set[str] = {_violation_key(g) for g in ground_truth}
    det_keys: Set[str] = {_violation_key(d) for d in detected}

    tp = len(gt_keys & det_keys)
    fp = len(det_keys - gt_keys)
    fn = len(gt_keys - det_keys)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + len(gt_keys)) if (fp + len(gt_keys)) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "fpr": round(fpr, 4),
        "f1": round(f1, 4),
    }


# ---------------------------------------------------------------------------
# Score sections
# ---------------------------------------------------------------------------


def score_detection_precision_recall(
    submission_dir: Path,
    ground_truth_dir: Optional[Path],
    errors: List[str],
) -> Tuple[float, Dict]:
    """Score detection precision and recall (50 pts).

    If no ground truth is provided, fall back to summary.json self-reported values.
    """
    max_score = 50.0

    all_metrics: List[Dict] = []

    if ground_truth_dir and ground_truth_dir.exists():
        # Evaluate each site against ground truth
        for gt_file in ground_truth_dir.glob("*.json"):
            gt_data, gt_err = load_json(gt_file)
            if gt_err:
                errors.append(gt_err)
                continue
            if not isinstance(gt_data, list):
                errors.append(f"Ground truth {gt_file.name} should be a list")
                continue

            # Derive slug from ground truth filename (without extension)
            slug = gt_file.stem
            violations_path = submission_dir / "reports" / slug / "violations.json"
            detected, det_err = load_json(violations_path)
            if det_err:
                errors.append(f"No violations file for site '{slug}': {det_err}")
                detected = []

            if not isinstance(detected, list):
                detected = []

            metrics = compute_detection_metrics(detected, gt_data)
            all_metrics.append(metrics)

        if not all_metrics:
            errors.append("No ground truth files could be matched to submission reports")
            return 0.0, {}

        avg_precision = sum(m["precision"] for m in all_metrics) / len(all_metrics)
        avg_recall = sum(m["recall"] for m in all_metrics) / len(all_metrics)

    else:
        # Fallback: read from summary.json
        summary, summ_err = load_json(submission_dir / "summary.json")
        if summ_err or summary is None:
            errors.append("summary.json missing and no ground truth available — detection score is 0")
            return 0.0, {}
        avg_precision = float(summary.get("precision", 0.0))
        avg_recall = float(summary.get("recall", 0.0))

    precision_score = linear_scale(avg_precision, PRECISION_ACCEPTABLE, PRECISION_EXCELLENT, 25.0)
    recall_score = linear_scale(avg_recall, RECALL_ACCEPTABLE, RECALL_EXCELLENT, 25.0)
    total = min(precision_score + recall_score, max_score)

    return total, {
        "avg_precision": round(avg_precision, 4),
        "avg_recall": round(avg_recall, 4),
    }


def score_report_quality(submission_dir: Path, errors: List[str]) -> float:
    """Score report quality (25 pts).

    Sub-criteria:
        - violations.json files present for each audited site (10 pts)
        - Each violation has required fields (criterion, element_selector, severity, suggested_fix): 10 pts
        - auto-fix patches present and auto_fix_rate >= 30%: 5 pts
    """
    max_score = 25.0
    score = 0.0

    reports_dir = submission_dir / "reports"
    if not reports_dir.exists():
        errors.append("submission/reports/ directory not found")
        return 0.0

    site_dirs = [d for d in reports_dir.iterdir() if d.is_dir()]
    if not site_dirs:
        errors.append("No site report subdirectories found under submission/reports/")
        return 0.0

    score += 10.0  # reports directory with content exists

    required_fields = {"criterion", "element_selector", "severity", "suggested_fix"}
    total_violations = 0
    valid_violations = 0
    auto_fixed = 0

    for site_dir in site_dirs:
        violations_path = site_dir / "violations.json"
        data, err = load_json(violations_path)
        if err:
            errors.append(err)
            continue
        if not isinstance(data, list):
            errors.append(f"violations.json in {site_dir.name} is not a list")
            continue

        for item in data:
            total_violations += 1
            if isinstance(item, dict) and required_fields.issubset(item.keys()):
                valid_violations += 1
            if isinstance(item, dict) and item.get("auto_fixed"):
                auto_fixed += 1

    if total_violations > 0:
        field_completeness = valid_violations / total_violations
        score += round(field_completeness * 10.0, 2)
    else:
        errors.append("No violations found in any report — cannot assess field completeness")

    auto_fix_rate = auto_fixed / total_violations if total_violations > 0 else 0.0
    if auto_fix_rate >= AUTO_FIX_BONUS_THRESHOLD:
        score += 5.0
    else:
        errors.append(
            f"Auto-fix rate {auto_fix_rate:.1%} is below the 30% threshold — no auto-fix bonus"
        )

    return min(score, max_score)


def score_false_positive_rate(
    submission_dir: Path,
    ground_truth_dir: Optional[Path],
    errors: List[str],
) -> float:
    """Score false positive rate (25 pts).

    FPR > 10% => 0 pts (per problem statement).
    """
    max_score = 25.0

    if ground_truth_dir and ground_truth_dir.exists():
        all_fpr: List[float] = []
        for gt_file in ground_truth_dir.glob("*.json"):
            gt_data, gt_err = load_json(gt_file)
            if gt_err or not isinstance(gt_data, list):
                continue
            slug = gt_file.stem
            violations_path = submission_dir / "reports" / slug / "violations.json"
            detected, _ = load_json(violations_path)
            if not isinstance(detected, list):
                detected = []
            metrics = compute_detection_metrics(detected, gt_data)
            all_fpr.append(metrics["fpr"])

        if not all_fpr:
            errors.append("Cannot compute FPR — no matching ground truth / submission pairs found")
            return 0.0

        avg_fpr = sum(all_fpr) / len(all_fpr)
    else:
        summary, _ = load_json(submission_dir / "summary.json")
        avg_fpr = float(summary.get("false_positive_rate_pct", 100) / 100) if summary else 1.0

    if avg_fpr > FPR_LIMIT:
        errors.append(f"False positive rate {avg_fpr:.1%} exceeds 10% hard limit — score is 0 for this section")
        return 0.0

    return inverse_linear_scale(avg_fpr, FPR_EXCELLENT, FPR_ACCEPTABLE, max_score)


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------


def evaluate(submission_dir: Path, ground_truth_dir: Optional[Path]) -> Dict:
    errors: List[str] = []

    det_score, det_detail = score_detection_precision_recall(submission_dir, ground_truth_dir, errors)
    report_score = score_report_quality(submission_dir, errors)
    fpr_score = score_false_positive_rate(submission_dir, ground_truth_dir, errors)

    total = round(det_score + report_score + fpr_score, 2)

    result = {
        "total": total,
        "breakdown": {
            "detection_precision_recall": {"score": round(det_score, 2), "max": 50, "detail": det_detail},
            "report_quality":             {"score": round(report_score, 2), "max": 25},
            "false_positive_rate":        {"score": round(fpr_score, 2), "max": 25},
        },
        "errors": errors,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="IT-P4 AccessibilityAI — Evaluator")
    parser.add_argument("--submission", required=True, help="Path to submission directory")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH, help="Path to ground truth directory")
    args = parser.parse_args()

    submission_dir = Path(args.submission)
    ground_truth_dir = Path(args.ground_truth) if args.ground_truth else None

    if not submission_dir.exists():
        result = {
            "total": 0,
            "breakdown": {
                "detection_precision_recall": {"score": 0, "max": 50},
                "report_quality":             {"score": 0, "max": 25},
                "false_positive_rate":        {"score": 0, "max": 25},
            },
            "errors": [f"Submission directory not found: {submission_dir}"],
        }
    else:
        result = evaluate(submission_dir, ground_truth_dir)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
