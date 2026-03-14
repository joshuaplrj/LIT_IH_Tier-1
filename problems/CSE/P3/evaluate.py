"""
Infinite Chess Grandmaster — Evaluation Script
CSE Problem 3

Usage:
    python evaluate.py --results tournament_results.json [--board_sizes 8 10 12 16]

Tournament results JSON format (produced by starter.py or your harness):
    {
        "8":  {"agent_wins": 42, "baseline_wins": 5, "draws": 3, "total": 50},
        "10": {"agent_wins": 35, "baseline_wins": 12, "draws": 3, "total": 50},
        ...
    }

Output (JSON to stdout):
    {
        "total": 0-100,
        "breakdown": {
            "win_rate_8x8":    {"score": X, "max": 40},
            "larger_boards":   {"score": X, "max": 30},
            "architecture":    {"score": X, "max": 20},
            "documentation":   {"score": X, "max": 10}
        },
        "errors": []
    }

Note: The scoring rubric for P3 is primarily win-rate based. The mapping used here:
    - 8×8 win rate >= 80%:  full 40 pts; below 80%: 0 (hard threshold per spec)
    - Larger boards: partial credit by win rate above random (50%)
    - Architecture + documentation: judge-assigned
"""

import argparse
import json
import os
import sys
from typing import List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def result(total, breakdown, errors):
    return {"total": round(float(total), 2), "breakdown": breakdown, "errors": errors}


def zero_result(reason: str):
    return result(
        0,
        {
            "win_rate_8x8":  {"score": 0, "max": 40},
            "larger_boards": {"score": 0, "max": 30},
            "architecture":  {"score": 0, "max": 20},
            "documentation": {"score": 0, "max": 10},
        },
        [reason],
    )


def load_results(path: str):
    if not os.path.isfile(path):
        return None, [f"Results file not found: {path}"]
    try:
        with open(path) as f:
            data = json.load(f)
        return data, []
    except Exception as e:
        return None, [f"Could not parse JSON: {e}"]


# ---------------------------------------------------------------------------
# Metric: 8×8 Win Rate (40 pts — hard threshold at 80%)
# ---------------------------------------------------------------------------

def score_win_rate_8x8(data: dict) -> tuple:
    errors = []
    entry = data.get("8") or data.get(8)
    if not entry:
        errors.append("No 8×8 results found in tournament file.")
        return 0.0, errors

    total = entry.get("total", 0)
    wins  = entry.get("agent_wins", 0)
    if total == 0:
        errors.append("Total games for 8×8 is 0.")
        return 0.0, errors

    if total < 50:
        errors.append(f"8×8 games played: {total}. At least 50 required per spec.")

    win_rate = wins / total
    if win_rate < 0.80:
        errors.append(
            f"8×8 win rate = {win_rate:.1%} — below the 80% threshold. "
            f"Score capped at 0 for this category per the problem specification."
        )
        return 0.0, errors

    # Full score for >= 80% win rate; bonus scaling above 80% up to 100%
    excess = (win_rate - 0.80) / 0.20   # 0 at 80%, 1 at 100%
    score = 40.0 + 0.0 * excess          # spec says 40 pts flat — no over-bonus
    score = min(score, 40.0)
    return round(score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Larger Boards (30 pts — N=10, 12, 16)
# ---------------------------------------------------------------------------

def score_larger_boards(data: dict) -> tuple:
    errors = []
    board_sizes = [10, 12, 16]
    pts_per_size = 10.0
    total_score = 0.0

    for n in board_sizes:
        entry = data.get(str(n)) or data.get(n)
        if not entry:
            errors.append(f"No results for N={n}.")
            continue

        total = entry.get("total", 0)
        wins  = entry.get("agent_wins", 0)
        if total == 0:
            errors.append(f"N={n}: 0 games played.")
            continue
        if total < 50:
            errors.append(f"N={n}: only {total} games played (50 required).")

        win_rate = wins / total
        # Partial credit: linear from 0 at win_rate=0.5 (random) to full at win_rate=1.0
        if win_rate <= 0.50:
            size_score = 0.0
            errors.append(f"N={n}: win rate {win_rate:.1%} at or below random baseline.")
        else:
            size_score = pts_per_size * (win_rate - 0.50) / 0.50
        total_score += size_score

    return round(total_score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Architecture Document (20 pts — judge-assigned)
# ---------------------------------------------------------------------------

def score_architecture(arch_score: float, arch_path: Optional[str]) -> tuple:
    errors = []
    auto = 0.0

    if arch_path and os.path.isfile(arch_path):
        with open(arch_path) as f:
            content = f.read()
        keywords = [
            "alpha-beta", "transposition", "evaluation", "iterative deepening",
            "bomb", "teleporter", "time dilation", "move ordering"
        ]
        found = sum(1 for kw in keywords if kw.lower() in content.lower())
        auto = 5.0 * (found / len(keywords))
        errors.append(
            f"Architecture doc auto-score: {auto:.1f}/5 "
            f"({found}/{len(keywords)} keywords found). "
            f"Remaining {20 - auto:.0f} pts judge-assigned."
        )
    else:
        errors.append("No architecture document provided (--arch flag). Auto-score = 0.")

    judge = float(max(0, min(15, arch_score)))
    return round(min(auto + judge, 20.0), 2), errors


# ---------------------------------------------------------------------------
# Metric: Documentation / Tournament Report (10 pts — judge-assigned)
# ---------------------------------------------------------------------------

def score_documentation(doc_score: float) -> tuple:
    s = float(max(0, min(10, doc_score)))
    errors = []
    if s == 0:
        errors.append("Documentation score not provided (--doc_score). Set to 0.")
    return s, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate an Infinite Chess Grandmaster submission."
    )
    parser.add_argument("--results",    type=str, required=True,
                        help="Path to tournament_results.json.")
    parser.add_argument("--arch",       type=str, default=None,
                        help="Path to evaluation function architecture document (optional).")
    parser.add_argument("--arch_score", type=float, default=0.0,
                        help="Judge-assigned architecture score (0–15, added to auto).")
    parser.add_argument("--doc_score",  type=float, default=0.0,
                        help="Judge-assigned documentation score (0–10).")
    args = parser.parse_args()

    errors = []
    breakdown = {
        "win_rate_8x8":  {"score": 0.0, "max": 40},
        "larger_boards": {"score": 0.0, "max": 30},
        "architecture":  {"score": 0.0, "max": 20},
        "documentation": {"score": 0.0, "max": 10},
    }

    data, load_errors = load_results(args.results)
    errors.extend(load_errors)
    if data is None:
        print(json.dumps(zero_result(" | ".join(errors)), indent=2))
        sys.exit(0)

    s, e = score_win_rate_8x8(data)
    breakdown["win_rate_8x8"]["score"] = s
    errors.extend(e)

    s, e = score_larger_boards(data)
    breakdown["larger_boards"]["score"] = s
    errors.extend(e)

    s, e = score_architecture(args.arch_score, args.arch)
    breakdown["architecture"]["score"] = s
    errors.extend(e)

    s, e = score_documentation(args.doc_score)
    breakdown["documentation"]["score"] = s
    errors.extend(e)

    total = sum(v["score"] for v in breakdown.values())
    print(json.dumps(result(total, breakdown, errors), indent=2))


if __name__ == "__main__":
    main()
