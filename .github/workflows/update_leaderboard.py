#!/usr/bin/env python3
"""
update_leaderboard.py
---------------------
Merges a single evaluation result into leaderboard/leaderboard.json.

Usage:
    python .github/workflows/update_leaderboard.py \
        --team   <team-name>   \
        --discipline <DISC>    \
        --problem    <P#>      \
        --score  <0-100>
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

LEADERBOARD_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "leaderboard", "leaderboard.json"
)

DISCIPLINES = ["CSE", "CYBER", "IT", "EEE", "ECE", "MECH", "AIDS", "MBA"]
PROBLEMS = ["P1", "P2", "P3", "P4", "P5"]
MAX_SCORE_PER_PROBLEM = 100
MAX_POSSIBLE = len(DISCIPLINES) * len(PROBLEMS) * MAX_SCORE_PER_PROBLEM  # 4000


def load_leaderboard(path: str) -> dict:
    """Load leaderboard.json, returning an empty scaffold if the file is missing."""
    if not os.path.exists(path):
        print(f"[update_leaderboard] WARNING: {path} not found — creating fresh file.")
        return {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "disciplines": DISCIPLINES,
            "max_score_per_problem": MAX_SCORE_PER_PROBLEM,
            "teams": {},
        }
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_leaderboard(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def empty_team_entry() -> dict:
    """Return a brand-new team entry with all scores set to null."""
    return {
        "scores": {
            disc: {prob: None for prob in PROBLEMS}
            for disc in DISCIPLINES
        },
        "total_score": 0,
        "problems_solved": 0,
        "max_possible": MAX_POSSIBLE,
    }


def recompute_totals(entry: dict) -> None:
    """Recompute total_score and problems_solved in-place from the scores dict."""
    total = 0
    solved = 0
    for disc in DISCIPLINES:
        disc_scores = entry["scores"].get(disc, {})
        for prob in PROBLEMS:
            val = disc_scores.get(prob)
            if val is not None:
                total += val
                if val > 0:
                    solved += 1
    entry["total_score"] = total
    entry["problems_solved"] = solved


def validate_args(team: str, discipline: str, problem: str, score: int) -> None:
    if not team:
        raise ValueError("Team name must not be empty.")
    if discipline not in DISCIPLINES:
        raise ValueError(
            f"Unknown discipline '{discipline}'. Valid: {DISCIPLINES}"
        )
    if problem not in PROBLEMS:
        raise ValueError(
            f"Unknown problem '{problem}'. Valid: {PROBLEMS}"
        )
    if not (0 <= score <= MAX_SCORE_PER_PROBLEM):
        raise ValueError(
            f"Score {score} out of range [0, {MAX_SCORE_PER_PROBLEM}]."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update leaderboard.json with a single evaluation result."
    )
    parser.add_argument("--team",       required=True, help="Team name")
    parser.add_argument("--discipline", required=True, help="Discipline code (e.g. CSE)")
    parser.add_argument("--problem",    required=True, help="Problem number (e.g. P1)")
    parser.add_argument("--score",      required=True, type=int, help="Score 0-100")
    args = parser.parse_args()

    team       = args.team.strip().lower()
    discipline = args.discipline.strip().upper()
    problem    = args.problem.strip().upper()
    score      = args.score

    # Validate inputs before touching the file
    try:
        validate_args(team, discipline, problem, score)
    except ValueError as exc:
        print(f"[update_leaderboard] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Resolve path relative to this script's actual location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    leaderboard_path = os.path.normpath(
        os.path.join(script_dir, "..", "..", "leaderboard", "leaderboard.json")
    )

    data = load_leaderboard(leaderboard_path)

    # Ensure the teams key exists
    if "teams" not in data:
        data["teams"] = {}

    # Create team entry if it doesn't exist
    if team not in data["teams"]:
        print(f"[update_leaderboard] Creating new entry for team '{team}'.")
        data["teams"][team] = empty_team_entry()

    entry = data["teams"][team]

    # Ensure all disciplines and problems are represented (defensive)
    if "scores" not in entry:
        entry["scores"] = {}
    for disc in DISCIPLINES:
        if disc not in entry["scores"]:
            entry["scores"][disc] = {prob: None for prob in PROBLEMS}
        for prob in PROBLEMS:
            if prob not in entry["scores"][disc]:
                entry["scores"][disc][prob] = None

    old_score = entry["scores"][discipline][problem]
    entry["scores"][discipline][problem] = score

    print(
        f"[update_leaderboard] {team} / {discipline} / {problem}: "
        f"{old_score} -> {score}"
    )

    # Recompute aggregates
    recompute_totals(entry)

    print(
        f"[update_leaderboard] {team} total_score={entry['total_score']}, "
        f"problems_solved={entry['problems_solved']}"
    )

    # Update timestamp
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    save_leaderboard(leaderboard_path, data)
    print(f"[update_leaderboard] leaderboard.json saved to {leaderboard_path}")


if __name__ == "__main__":
    main()
