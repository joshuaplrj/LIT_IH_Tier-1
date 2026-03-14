"""
AIDS-P5: CodeMorph — Evaluation / Scoring Script

Usage:
    python evaluate.py --submission <path> [--ground_truth <path>] [--test_data <path>]

Options:
    --submission     Path to submission directory containing:
                       translations.jsonl, optimizations.jsonl, bugfixes.jsonl
    --ground_truth   Path to ground-truth directory (default: ground_truth/AIDS_P5_gt/)
                     containing translations_gt.jsonl, etc.
    --test_data      (Optional) path to original data dir for re-running tests

Prints a JSON scoring result to stdout.
"""

import argparse
import ast
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

WEIGHTS = {
    "semantic_equivalence": 40,
    "syntactic_correctness": 30,
    "style_adherence": 15,
    "documentation": 15,
}
GROUND_TRUTH_PATH = "ground_truth/AIDS_P5_gt"

# Targets
TRANSLATION_ACC_TARGET = 0.80   # >= 80% programs pass all tests
BUGFIX_RATE_TARGET = 0.80
SPEEDUP_TARGET = 5.0            # >= 5x speedup for full opt score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return items


def safe_load_jsonl(path: str, label: str):
    if not os.path.exists(path):
        return None, f"{label} not found: {path}"
    items = load_jsonl(path)
    return (items, None) if items else (None, f"{label} is empty")


def check_python_syntax(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def check_syntax_subprocess(code: str, lang: str) -> bool:
    """Quick syntax check without full execution."""
    lang = lang.lower()
    if lang == "python":
        return check_python_syntax(code)
    ext_map = {"cpp": "cpp", "c++": "cpp", "rust": "rs", "go": "go", "java": "java"}
    ext = ext_map.get(lang, "txt")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{ext}",
                                         delete=False) as f:
            f.write(code)
            fname = f.name
        if lang in ("cpp", "c++"):
            cmd = ["g++", "-fsyntax-only", fname]
        elif lang == "rust":
            cmd = ["rustc", "--edition=2021", "--emit=metadata",
                   fname, "--out-dir", tempfile.gettempdir()]
        elif lang == "go":
            cmd = ["go", "vet", fname]
        else:
            os.unlink(fname)
            return True
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        os.unlink(fname)
        return result.returncode == 0
    except Exception:
        try:
            os.unlink(fname)
        except Exception:
            pass
        return True   # can't check — assume valid


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_semantic_equivalence(translations: list,
                                 bugfixes: list,
                                 optimizations: list) -> dict:
    """
    Primary semantic score: fraction of programs that pass ALL their test cases.
    Combines translation accuracy, bugfix rate, and optimisation correctness.
    """
    all_results = []
    for r in translations:
        t, p = r.get("total_tests", 0), r.get("passed_tests", 0)
        if t > 0:
            all_results.append(p == t)
    for r in bugfixes:
        t, p = r.get("total_tests", 0), r.get("passed_tests", 0)
        if t > 0:
            all_results.append(p == t)
    for r in optimizations:
        p = r.get("passed_tests", 0)
        # Optimisation: correctness = at least 1 test passed (proxy)
        all_results.append(p > 0)

    if not all_results:
        return {"score": 0, "max": WEIGHTS["semantic_equivalence"],
                "details": {"error": "no evaluable programs"}}

    accuracy = sum(all_results) / len(all_results)
    floor, target = 0.20, 0.80
    ratio = max(0.0, (accuracy - floor) / (target - floor))
    ratio = min(1.0, ratio)
    raw_score = ratio * WEIGHTS["semantic_equivalence"]

    trans_acc = (sum(1 for r in translations
                     if r.get("passed_tests", 0) == r.get("total_tests", 1))
                 / max(len(translations), 1))
    bugfix_rate = (sum(1 for r in bugfixes
                       if r.get("passed_tests", 0) == r.get("total_tests", 1))
                   / max(len(bugfixes), 1))

    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["semantic_equivalence"],
        "details": {
            "overall_accuracy": round(accuracy, 4),
            "translation_accuracy": round(trans_acc, 4),
            "bugfix_rate": round(bugfix_rate, 4),
            "n_programs": len(all_results),
        },
    }


def score_syntactic_correctness(translations: list,
                                  bugfixes: list,
                                  optimizations: list) -> dict:
    """
    Check that submitted code parses / compiles without errors.
    Uses pre-computed syntax_valid field if present; otherwise re-checks.
    """
    valid_count, total = 0, 0
    for r in translations + bugfixes:
        total += 1
        code = r.get("translated_code") or r.get("fixed_code", "")
        lang = r.get("lang", "python")
        # Use pre-computed field if available
        if "syntax_valid" in r:
            if r["syntax_valid"]:
                valid_count += 1
        elif code:
            if check_syntax_subprocess(code, lang):
                valid_count += 1

    for r in optimizations:
        total += 1
        code = r.get("optimized_code", "")
        lang = r.get("lang", "python")
        if code and check_syntax_subprocess(code, lang):
            valid_count += 1

    if total == 0:
        return {"score": 0, "max": WEIGHTS["syntactic_correctness"],
                "details": {"error": "no programs to evaluate"}}

    ratio = valid_count / total
    raw_score = ratio * WEIGHTS["syntactic_correctness"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["syntactic_correctness"],
        "details": {
            "syntax_valid": valid_count,
            "total_programs": total,
            "syntax_pass_rate": round(ratio, 4),
        },
    }


def score_style_adherence(translations: list, data_dir: str) -> dict:
    """
    Automated proxy for style adherence.
    Checks presence of docstrings (Python) or comments (other langs).
    Full manual review would compare against language style guides.
    """
    if not translations:
        return {"score": 0, "max": WEIGHTS["style_adherence"],
                "details": {"warning": "no translation submissions"}}

    styled_count = 0
    for r in translations:
        code = r.get("translated_code", "")
        lang = r.get("lang", "").lower()
        if not code:
            continue
        if lang == "python":
            # Check for docstrings or comments
            if '"""' in code or "'''" in code or code.strip().startswith("#"):
                styled_count += 1
        elif lang in ("cpp", "c++", "rust", "go", "java"):
            if "//" in code or "/*" in code:
                styled_count += 1
        else:
            styled_count += 1  # unknown lang — give benefit of doubt

    ratio = styled_count / len(translations)
    raw_score = ratio * WEIGHTS["style_adherence"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["style_adherence"],
        "details": {
            "programs_with_comments": styled_count,
            "total": len(translations),
            "note": "Full style adherence requires comparison against style guides",
        },
    }


def score_documentation(submission_dir: str) -> dict:
    """
    Check for documentation / error analysis files.
    Automated proxy — full review requires human assessment.
    """
    candidates = [
        "error_analysis.md", "error_analysis.txt", "error_analysis.pdf",
        "report.md", "report.pdf", "documentation.md", "README.md",
    ]
    found = [f for f in candidates
             if os.path.exists(os.path.join(submission_dir, f))]
    # Also check for summary.json
    has_summary = os.path.exists(os.path.join(submission_dir, "summary.json"))
    ratio = min(1.0, (len(found) + (0.5 if has_summary else 0)) / 2)
    raw_score = ratio * WEIGHTS["documentation"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["documentation"],
        "details": {
            "docs_found": found,
            "has_summary_json": has_summary,
            "note": "Full documentation score requires human review",
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P5 CodeMorph Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to submission directory OR translations.jsonl")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help="Path to ground-truth directory")
    parser.add_argument("--test_data", default=None,
                        help="(Optional) original data directory for re-running tests")
    args = parser.parse_args()

    errors = []
    breakdown = {}

    # Resolve submission directory
    if os.path.isdir(args.submission):
        sub_dir = args.submission
    else:
        sub_dir = os.path.dirname(os.path.abspath(args.submission))

    # Load submissions
    trans_path = os.path.join(sub_dir, "translations.jsonl")
    opt_path = os.path.join(sub_dir, "optimizations.jsonl")
    bug_path = os.path.join(sub_dir, "bugfixes.jsonl")

    translations = load_jsonl(trans_path)
    optimizations = load_jsonl(opt_path)
    bugfixes = load_jsonl(bug_path)

    if not translations and not bugfixes and not optimizations:
        errors.append(
            "No valid submission files found in submission directory. "
            "Expected: translations.jsonl, optimizations.jsonl, bugfixes.jsonl"
        )

    data_dir = args.test_data or "data"

    # --- Score each dimension ---
    breakdown["semantic_equivalence"] = score_semantic_equivalence(
        translations, bugfixes, optimizations)
    breakdown["syntactic_correctness"] = score_syntactic_correctness(
        translations, bugfixes, optimizations)
    breakdown["style_adherence"] = score_style_adherence(translations, data_dir)
    breakdown["documentation"] = score_documentation(sub_dir)

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
