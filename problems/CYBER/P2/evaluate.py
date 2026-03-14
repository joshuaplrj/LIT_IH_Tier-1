#!/usr/bin/env python3
"""
CYBER-P2: Rootkit Genesis — Part B Evaluator
Parses a forensic_report.md file and scores it against required sections.

Usage:
    python evaluate.py --submission forensic_report.md

Scoring (Part B = 60% of total problem score):
  - Hidden processes identified    20 points
  - Persistence mechanism          20 points
  - C2 address traced              20 points
  - Rootkit configuration          20 points
  - Timeline reconstructed         20 points

Each section is awarded full, partial, or zero points based on
content completeness checks described below.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Section definitions: (heading_regex, content_checks, max_points)
# content_checks: list of (regex_pattern, partial_credit_fraction, description)
# ---------------------------------------------------------------------------
SECTION_RUBRIC = [
    {
        "name": "hidden_processes",
        "heading_pattern": r"##\s*Hidden Processes",
        "max_points": 20,
        "checks": [
            (r"\bPID\b|\bpid\b|\bprocess id\b",        0.4,  "mentions PID numbers"),
            (r"\d{3,6}",                               0.3,  "contains numeric PID values"),
            (r"\bhidden\b|\bconcealed\b|\bmasked\b",    0.3,  "uses 'hidden' terminology"),
        ],
        "require_nonempty": True,
    },
    {
        "name": "hidden_files",
        "heading_pattern": r"##\s*Hidden Files",
        "max_points": 0,  # not scored separately — part of configuration
        "checks": [],
        "require_nonempty": True,
    },
    {
        "name": "persistence_mechanism",
        "heading_pattern": r"##\s*Persistence Mechanism",
        "max_points": 20,
        "checks": [
            (r"\bsystemd\b|\bcron\b|\binit\b|\bbootloader\b|\brc\.local\b|\b\.service\b",
             0.4, "identifies persistence type (systemd/cron/init/bootloader)"),
            (r"\/etc\/|\/lib\/systemd\/|\/var\/spool\/cron",
             0.3, "provides filesystem path of persistence artifact"),
            (r"\bsurviv\b|\breboot\b|\bpersist\b|\bstartup\b",
             0.3, "explains how persistence survives reboot"),
        ],
        "require_nonempty": True,
    },
    {
        "name": "c2_address",
        "heading_pattern": r"##\s*C2 Address",
        "max_points": 20,
        "checks": [
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b",           0.6,  "contains an IP address"),
            (r":\d{2,5}",                               0.2,  "contains a port number"),
            (r"\btrace\b|\bidentif\b|\bestablish\b|\bconnect\b|\bfound\b",
             0.2, "describes how C2 was traced"),
        ],
        "require_nonempty": True,
    },
    {
        "name": "rootkit_configuration",
        "heading_pattern": r"##\s*Rootkit Configuration",
        "max_points": 20,
        "checks": [
            (r"\bhidden\s+process\b|\btarget\s+process\b|\bprocess\s+name\b",
             0.35, "identifies target process names"),
            (r"\bhidden\s+file\b|\bfile\s+prefix\b|\bfile\s+pattern\b",
             0.35, "identifies hidden file patterns"),
            (r"\bC2\b|\bc2\b|\battacker\b|\bcommand.and.control\b",
             0.30, "identifies C2 configuration"),
        ],
        "require_nonempty": True,
    },
    {
        "name": "timeline",
        "heading_pattern": r"##\s*Timeline",
        "max_points": 20,
        "checks": [
            (r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}:\d{2}:\d{2}",
             0.4, "contains datetime stamps"),
            (r"\binfect\b|\binitial\b|\bfirst\b|\bentry\b|\bcompromise\b",
             0.3, "describes initial infection event"),
            (r"\bpersist\b|\bC2\b|\breverse shell\b|\bestablish\b",
             0.3, "describes persistence or C2 establishment event"),
        ],
        "require_nonempty": True,
    },
    {
        "name": "iocs",
        "heading_pattern": r"##\s*IOCs",
        "max_points": 0,  # bonus quality indicator — not separately scored
        "checks": [],
        "require_nonempty": False,
    },
    {
        "name": "detection_scripts",
        "heading_pattern": r"##\s*Detection Scripts",
        "max_points": 0,  # bonus quality indicator — not separately scored
        "checks": [],
        "require_nonempty": False,
    },
]

REQUIRED_SECTIONS = [s["name"] for s in SECTION_RUBRIC if s["require_nonempty"]]


# ---------------------------------------------------------------------------
# Parser: extract section content from Markdown
# ---------------------------------------------------------------------------

def extract_sections(markdown_text: str) -> Dict[str, str]:
    """
    Returns a dict mapping section name (heading text, lowercased, spaces->underscores)
    to the raw body text of that section.
    """
    sections: Dict[str, str] = {}
    current_heading = None
    current_body: List[str] = []

    for line in markdown_text.splitlines():
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_body).strip()
            current_heading = h2_match.group(1).strip().lower().replace(" ", "_")
            current_body = []
        else:
            if current_heading is not None:
                current_body.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_body).strip()

    return sections


def find_section_body(markdown_text: str, heading_pattern: str) -> str:
    """
    Extract the body of a section whose heading matches heading_pattern.
    Returns empty string if not found.
    """
    lines = markdown_text.splitlines()
    in_section = False
    body_lines: List[str] = []

    for line in lines:
        if re.match(heading_pattern, line, re.IGNORECASE):
            in_section = True
            body_lines = []
            continue
        if in_section:
            # Stop at the next ## heading
            if re.match(r"^##\s", line):
                break
            body_lines.append(line)

    return "\n".join(body_lines).strip()


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def score_section(section_body: str, checks: List[Tuple], max_points: int) -> Tuple[float, List[str]]:
    """
    Apply content checks to section body. Returns (points_earned, detail_list).
    """
    if max_points == 0:
        return 0.0, []

    earned = 0.0
    details = []

    if not section_body:
        return 0.0, ["Section is empty — no points awarded."]

    for pattern, weight, description in checks:
        if re.search(pattern, section_body, re.IGNORECASE):
            points = max_points * weight
            earned += points
            details.append(f"PASS ({points:.1f}pts): {description}")
        else:
            details.append(f"FAIL (0pts): {description}")

    return min(earned, float(max_points)), details


def validate_report(markdown_text: str) -> List[str]:
    """Return format errors; empty list = valid."""
    errors = []
    for rubric in SECTION_RUBRIC:
        if rubric["require_nonempty"]:
            body = find_section_body(markdown_text, rubric["heading_pattern"])
            if not body:
                errors.append(f"Missing or empty required section: ## {rubric['name'].replace('_',' ').title()}")
    return errors


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate(submission_path: str) -> Dict:
    result = {
        "total":     0,
        "breakdown": {},
        "errors":    [],
    }

    if not os.path.isfile(submission_path):
        result["errors"].append(f"Submission file not found: {submission_path}")
        print(json.dumps(result, indent=2))
        return result

    try:
        with open(submission_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as exc:
        result["errors"].append(f"Could not read submission: {exc}")
        print(json.dumps(result, indent=2))
        return result

    if not text.strip():
        result["errors"].append("Submission file is empty.")
        print(json.dumps(result, indent=2))
        return result

    # Format validation
    fmt_errors = validate_report(text)
    result["errors"].extend(fmt_errors)

    # Score each section
    total = 0.0
    for rubric in SECTION_RUBRIC:
        if rubric["max_points"] == 0:
            continue  # bonus sections, not scored numerically
        body = find_section_body(text, rubric["heading_pattern"])
        points, details = score_section(body, rubric["checks"], rubric["max_points"])
        total += points
        result["breakdown"][rubric["name"]] = {
            "score":   round(points, 2),
            "max":     rubric["max_points"],
            "details": details,
        }

    result["total"] = round(total, 2)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="CYBER-P2 Evaluator — Rootkit Genesis (Part B Forensic Report)"
    )
    parser.add_argument("--submission", required=True,
                        help="Path to forensic_report.md")
    args = parser.parse_args()

    result = evaluate(args.submission)
    print(json.dumps(result, indent=2))
    sys.exit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
