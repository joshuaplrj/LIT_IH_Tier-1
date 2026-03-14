"""
Self-Healing Compiler — Evaluation Script
CSE Problem 4

Usage:
    python evaluate.py --bugs_dir bugs/ --compiler compiler/main.py --tests tests/regression/

Output (JSON to stdout):
    {
        "total": 0-100,
        "breakdown": {
            "detection":     {"score": X, "max": 40},
            "localization":  {"score": X, "max": 20},
            "patch_quality": {"score": X, "max": 25},
            "fuzzer_quality":{"score": X, "max": 15}
        },
        "errors": []
    }
"""

import argparse
import json
import os
import subprocess
import sys
from typing import List, Optional

GROUND_TRUTH_PATH = "ground_truth/CSE_P4_gt.csv"   # placeholder
TOTAL_BUGS = 15
REGRESSION_TESTS_DIR = "tests/regression/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def result(total, breakdown, errors):
    return {"total": round(float(total), 2), "breakdown": breakdown, "errors": errors}


def zero_result(reason: str):
    return result(
        0,
        {
            "detection":      {"score": 0, "max": 40},
            "localization":   {"score": 0, "max": 20},
            "patch_quality":  {"score": 0, "max": 25},
            "fuzzer_quality": {"score": 0, "max": 15},
        },
        [reason],
    )


# ---------------------------------------------------------------------------
# Metric: Detection (40 pts)
# ---------------------------------------------------------------------------

def score_detection(bugs_dir: str) -> tuple:
    """
    Count the number of bug directories with a valid trigger.mr and report.txt.
    Score = 40 * (detected / 15).

    Full validation requires a judge to verify that each trigger.mr actually
    reproduces the bug — auto-score counts well-formed reports.
    """
    errors = []
    if not os.path.isdir(bugs_dir):
        errors.append(f"Bugs directory not found: {bugs_dir}")
        return 0.0, errors

    valid_bugs = 0
    for entry in sorted(os.listdir(bugs_dir)):
        bug_path = os.path.join(bugs_dir, entry)
        if not os.path.isdir(bug_path) or not entry.startswith("bug_"):
            continue
        has_trigger = os.path.isfile(os.path.join(bug_path, "trigger.mr"))
        has_report  = os.path.isfile(os.path.join(bug_path, "report.txt"))
        if has_trigger and has_report:
            # Check report is non-trivial
            with open(os.path.join(bug_path, "report.txt")) as f:
                content = f.read()
            if len(content.strip()) > 50 and "TODO" not in content:
                valid_bugs += 1
            elif len(content.strip()) > 50:
                errors.append(f"{entry}/report.txt still contains TODO placeholders.")
                valid_bugs += 0.5   # partial credit
        else:
            errors.append(f"{entry}: missing trigger.mr or report.txt.")

    found = min(valid_bugs, TOTAL_BUGS)
    score = 40.0 * (found / TOTAL_BUGS)
    errors.append(f"Detected {found}/{TOTAL_BUGS} bugs (auto-count, judge verification required).")
    return round(score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Localization (20 pts)
# ---------------------------------------------------------------------------

def score_localization(bugs_dir: str, gt_path: str) -> tuple:
    """
    Compare reported localization (file + function) against ground truth.
    Without ground truth, perform keyword completeness check only.
    """
    errors = []
    if not os.path.isdir(bugs_dir):
        return 0.0, [f"Bugs directory not found: {bugs_dir}"]

    # Try to load ground truth
    gt = {}
    if os.path.isfile(gt_path):
        try:
            with open(gt_path) as f:
                import csv
                reader = csv.DictReader(f)
                for row in reader:
                    gt[row["bug_id"]] = {"file": row["file"], "function": row["function"]}
        except Exception as e:
            errors.append(f"Could not load ground truth: {e}")

    total_score = 0.0
    pts_per_bug = 20.0 / TOTAL_BUGS

    for entry in sorted(os.listdir(bugs_dir)):
        bug_path = os.path.join(bugs_dir, entry)
        if not os.path.isdir(bug_path) or not entry.startswith("bug_"):
            continue
        report_path = os.path.join(bug_path, "report.txt")
        if not os.path.isfile(report_path):
            continue

        with open(report_path) as f:
            content = f.read()

        if gt:
            bug_id = entry   # "bug_01"
            if bug_id in gt:
                expected_file = gt[bug_id]["file"]
                expected_fn   = gt[bug_id]["function"]
                file_match = expected_file.lower() in content.lower()
                fn_match   = expected_fn.lower() in content.lower()
                if file_match and fn_match:
                    total_score += pts_per_bug
                elif file_match or fn_match:
                    total_score += pts_per_bug * 0.5
                    errors.append(f"{bug_id}: partial localization (file={file_match}, fn={fn_match}).")
                else:
                    errors.append(f"{bug_id}: localization incorrect.")
        else:
            # No GT — check that report mentions "Location:" with a non-TODO value
            has_location = "location:" in content.lower()
            not_placeholder = "TODO" not in content
            if has_location and not_placeholder:
                total_score += pts_per_bug * 0.5   # partial — no GT verification
            else:
                errors.append(f"{entry}: localization incomplete or placeholder.")

    if not gt:
        errors.append(
            "Ground truth not available. Localization scored at 50% — "
            "judges must verify file+function accuracy."
        )

    return round(total_score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Patch Quality (25 pts)
# ---------------------------------------------------------------------------

def score_patch_quality(bugs_dir: str, compiler_path: str,
                        regression_dir: str) -> tuple:
    """
    Apply all patches and run regression suite.
    Score = 25 * (regression_pass_rate).

    If compiler or regression tests not available, scores based on patch file presence.
    """
    errors = []

    if not os.path.isdir(bugs_dir):
        return 0.0, [f"Bugs directory not found: {bugs_dir}"]

    # Count submitted patches
    patches = []
    for entry in sorted(os.listdir(bugs_dir)):
        bug_path = os.path.join(bugs_dir, entry)
        if not os.path.isdir(bug_path):
            continue
        patch_path = os.path.join(bug_path, "fix.patch")
        if os.path.isfile(patch_path):
            with open(patch_path) as f:
                content = f.read().strip()
            if content and not content.startswith("# TODO"):
                patches.append(patch_path)

    if not patches:
        errors.append("No valid patch files found.")
        return 0.0, errors

    errors.append(f"Found {len(patches)} patch files.")

    # Run regression if available
    if not os.path.isfile(compiler_path):
        errors.append(
            f"Compiler not found at {compiler_path}. "
            f"Patch quality scored on patch count only: {len(patches)}/{TOTAL_BUGS}."
        )
        return round(25.0 * (len(patches) / TOTAL_BUGS), 2), errors

    if not os.path.isdir(regression_dir):
        errors.append(
            f"Regression tests dir not found: {regression_dir}. "
            "Cannot run regression validation."
        )
        return round(25.0 * (len(patches) / TOTAL_BUGS) * 0.5, 2), errors

    # Count regression test files
    test_files = [f for f in os.listdir(regression_dir) if f.endswith(".mr")]
    if not test_files:
        errors.append("No .mr test files found in regression directory.")
        return 0.0, errors

    passed = 0
    for tf in test_files:
        full_path = os.path.join(regression_dir, tf)
        try:
            proc = subprocess.run(
                [sys.executable, compiler_path, full_path],
                capture_output=True, text=True, timeout=5
            )
            if proc.returncode == 0:
                passed += 1
        except subprocess.TimeoutExpired:
            errors.append(f"Timeout compiling {tf}")
        except Exception as e:
            errors.append(f"Error running compiler on {tf}: {e}")

    pass_rate = passed / len(test_files) if test_files else 0.0
    score = 25.0 * pass_rate
    errors.append(f"Regression: {passed}/{len(test_files)} tests passed ({pass_rate:.1%}).")
    return round(score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Fuzzer Quality (15 pts)
# ---------------------------------------------------------------------------

def score_fuzzer_quality(fuzzer_path: Optional[str],
                         bugs_dir: str,
                         judge_score: float) -> tuple:
    """
    Auto-checks: fuzzer exists, has sufficient lines, imports relevant libraries.
    Judge-assigned component for coverage quality.
    """
    errors = []
    auto = 0.0

    if not fuzzer_path:
        fuzzer_path = "fuzzer.py"

    if not os.path.isfile(fuzzer_path):
        errors.append(f"Fuzzer file not found: {fuzzer_path}")
    else:
        with open(fuzzer_path) as f:
            content = f.read()
        lines = len([l for l in content.splitlines() if l.strip()])
        keywords = ["random", "generate", "grammar", "mutation", "coverage",
                    "subprocess", "fuzz", "property"]
        found_kw = sum(1 for kw in keywords if kw.lower() in content.lower())
        if lines >= 100:
            auto += 3.0
        if found_kw >= 3:
            auto += 2.0
        errors.append(
            f"Fuzzer auto-score: {auto}/5 ({lines} code lines, {found_kw}/8 keywords)."
        )

    judge = float(max(0, min(10, judge_score)))
    total = min(auto + judge, 15.0)
    errors.append(
        f"Remaining {15 - auto:.0f} pts judge-assigned for coverage and diversity."
    )
    return round(total, 2), errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a Self-Healing Compiler submission."
    )
    parser.add_argument("--bugs_dir",      type=str, default="bugs/",
                        help="Directory containing bug_XX/ subdirectories.")
    parser.add_argument("--compiler",      type=str, default="compiler/main.py",
                        help="Path to the (patched) MiniRust compiler.")
    parser.add_argument("--tests",         type=str, default=REGRESSION_TESTS_DIR,
                        help="Regression test directory.")
    parser.add_argument("--ground_truth",  type=str, default=GROUND_TRUTH_PATH,
                        help="Ground truth CSV for localization scoring.")
    parser.add_argument("--fuzzer",        type=str, default="fuzzer.py",
                        help="Path to the submitted fuzzer script.")
    parser.add_argument("--fuzzer_score",  type=float, default=0.0,
                        help="Judge-assigned fuzzer quality score (0–10).")
    args = parser.parse_args()

    errors = []
    breakdown = {
        "detection":      {"score": 0.0, "max": 40},
        "localization":   {"score": 0.0, "max": 20},
        "patch_quality":  {"score": 0.0, "max": 25},
        "fuzzer_quality": {"score": 0.0, "max": 15},
    }

    s, e = score_detection(args.bugs_dir)
    breakdown["detection"]["score"] = s
    errors.extend(e)

    s, e = score_localization(args.bugs_dir, args.ground_truth)
    breakdown["localization"]["score"] = s
    errors.extend(e)

    s, e = score_patch_quality(args.bugs_dir, args.compiler, args.tests)
    breakdown["patch_quality"]["score"] = s
    errors.extend(e)

    s, e = score_fuzzer_quality(args.fuzzer, args.bugs_dir, args.fuzzer_score)
    breakdown["fuzzer_quality"]["score"] = s
    errors.extend(e)

    total = sum(v["score"] for v in breakdown.values())
    print(json.dumps(result(total, breakdown, errors), indent=2))


if __name__ == "__main__":
    main()
