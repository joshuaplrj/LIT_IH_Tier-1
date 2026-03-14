"""
MotorForge — Evaluation / Scoring Script
EEE-P3

Usage:
    python evaluate.py --submission submission/motor_design_report.json

Reads the structured JSON design report, validates all fields, checks
requirement compliance, and outputs a JSON scoring report to stdout.
"""

import argparse
import json
import sys
from pathlib import Path


# ─────────────────────────────────────────────
# REQUIREMENTS
# ─────────────────────────────────────────────

REQ_EFFICIENCY_MIN_PCT  = 92.0     # %
REQ_RATED_SPEED_RPM     = 4_000.0
REQ_RATED_POWER_W       = 10_000.0
REQ_PEAK_TORQUE_NM      = 40.0
REQ_OD_MAX_MM           = 200.0
REQ_LENGTH_MAX_MM       = 150.0
REQ_WEIGHT_MAX_KG       = 12.0
T_INSULATION_MAX_C      = 155.0

# Weights
WEIGHT_EFFICIENCY       = 0.30
WEIGHT_TORQUE_DENSITY   = 0.25
WEIGHT_THERMAL          = 0.25
WEIGHT_DOCUMENTATION    = 0.20


def error_result(msg: str) -> dict:
    return {"total": 0, "breakdown": {}, "errors": [msg]}


# ─────────────────────────────────────────────
# REQUIRED SCHEMA FIELDS
# ─────────────────────────────────────────────

REQUIRED_TOP_KEYS = [
    "motor_parameters",
    "magnetic_analysis",
    "loss_breakdown",
    "thermal_analysis",
    "performance_verification",
    "foc_controller",
    "simulation_results",
]

REQUIRED_MOTOR_PARAMS = ["poles", "slots", "bore_diameter_mm", "stack_length_mm",
                          "outer_diameter_mm", "air_gap_mm", "turns_per_phase",
                          "magnet_grade"]

REQUIRED_LOSS_FIELDS  = ["copper_W", "iron_W", "total_loss_W", "efficiency_pct"]

REQUIRED_THERMAL      = ["winding_temp_C", "thermal_ok"]

REQUIRED_SIM          = ["torque_speed_curve", "efficiency_map"]


# ─────────────────────────────────────────────
# SCORING FUNCTIONS
# ─────────────────────────────────────────────

def score_efficiency(report: dict) -> dict:
    """Score efficiency metric (max 30 pts)."""
    eff = None
    errors = []

    # Try loss_breakdown first, then performance_verification
    lb = report.get("loss_breakdown", {})
    pv = report.get("performance_verification", {})

    eff = lb.get("efficiency_pct") or pv.get("efficiency_pct")

    if eff is None:
        return {"score": 0, "max": 30, "errors": ["efficiency_pct not found in report"]}

    eff = float(eff)

    if eff >= REQ_EFFICIENCY_MIN_PCT:
        # Full marks if at or above target
        pts = 30.0
    elif eff >= 88.0:
        # Partial credit: linear from 0 pts at 88% to 30 pts at 92%
        pts = round(30.0 * (eff - 88.0) / (REQ_EFFICIENCY_MIN_PCT - 88.0), 2)
    else:
        pts = 0.0

    return {
        "score": pts,
        "max": 30,
        "efficiency_pct": round(eff, 2),
        "target": REQ_EFFICIENCY_MIN_PCT,
        "pass": bool(eff >= REQ_EFFICIENCY_MIN_PCT),
    }


def score_torque_density(report: dict) -> dict:
    """Score torque density (max 25 pts). Target: >= 3.5 Nm/kg for full marks."""
    pv = report.get("performance_verification", {})
    weight_info = report.get("weight_breakdown", {})

    td = pv.get("torque_density_Nm_kg")

    if td is None:
        # Compute from peak torque and total weight if available
        torque = (pv.get("peak_torque_Nm") or
                  report.get("magnetic_analysis", {}).get("rated_torque_Nm"))
        weight = (pv.get("weight_kg") or weight_info.get("total_kg"))
        if torque and weight and float(weight) > 0:
            td = float(torque) / float(weight)
        else:
            return {"score": 0, "max": 25,
                    "errors": ["torque_density_Nm_kg not computable from report"]}

    td = float(td)
    TARGET_HIGH = 3.5   # Nm/kg → full marks
    TARGET_LOW  = 2.0   # Nm/kg → zero marks

    if td >= TARGET_HIGH:
        pts = 25.0
    elif td >= TARGET_LOW:
        pts = round(25.0 * (td - TARGET_LOW) / (TARGET_HIGH - TARGET_LOW), 2)
    else:
        pts = 0.0

    return {
        "score": pts,
        "max": 25,
        "torque_density_Nm_kg": round(td, 3),
        "target_Nm_kg": TARGET_HIGH,
    }


def score_thermal(report: dict) -> dict:
    """Score thermal compliance (max 25 pts)."""
    ta = report.get("thermal_analysis", {})
    t_winding = ta.get("winding_temp_C")
    thermal_ok = ta.get("thermal_ok")

    if t_winding is None:
        return {"score": 0, "max": 25, "errors": ["winding_temp_C missing"]}

    t_winding = float(t_winding)

    if t_winding <= T_INSULATION_MAX_C:
        # Full marks if compliant; bonus for margin
        margin = T_INSULATION_MAX_C - t_winding
        pts = min(25.0, 20.0 + 5.0 * min(margin / 20.0, 1.0))
    elif t_winding <= T_INSULATION_MAX_C + 20.0:
        # Slight over-temperature: partial credit
        excess = t_winding - T_INSULATION_MAX_C
        pts = round(20.0 * (1.0 - excess / 20.0), 2)
    else:
        pts = 0.0

    # Constraint checks
    constraint_errors = []
    pv = report.get("performance_verification", {})
    mp = report.get("motor_parameters", {})

    od_mm = float(mp.get("outer_diameter_mm", 999))
    len_mm = float(mp.get("stack_length_mm", 999))
    weight_kg = float(pv.get("weight_kg", 0) or
                      report.get("weight_breakdown", {}).get("total_kg", 999))

    if od_mm > REQ_OD_MAX_MM:
        constraint_errors.append(f"OD {od_mm:.0f} mm > {REQ_OD_MAX_MM:.0f} mm limit")
        pts = max(0.0, pts - 5.0)
    if len_mm > REQ_LENGTH_MAX_MM:
        constraint_errors.append(f"Length {len_mm:.0f} mm > {REQ_LENGTH_MAX_MM:.0f} mm limit")
        pts = max(0.0, pts - 5.0)
    if weight_kg > REQ_WEIGHT_MAX_KG:
        constraint_errors.append(f"Weight {weight_kg:.1f} kg > {REQ_WEIGHT_MAX_KG:.0f} kg limit")
        pts = max(0.0, pts - 5.0)

    return {
        "score": round(pts, 2),
        "max": 25,
        "winding_temp_C": round(t_winding, 1),
        "insulation_limit_C": T_INSULATION_MAX_C,
        "thermal_pass": bool(t_winding <= T_INSULATION_MAX_C),
        "constraint_violations": constraint_errors,
    }


def score_documentation(report: dict) -> dict:
    """Score documentation completeness (max 15 pts)."""
    pts = 0.0
    notes = []

    # Check required top-level keys (1 pt each, max 7)
    for key in REQUIRED_TOP_KEYS:
        if key in report:
            pts += 1.0
        else:
            notes.append(f"Missing top-level key: '{key}'")

    # Check motor parameters (1 pt each, max 4 from subset)
    mp = report.get("motor_parameters", {})
    for field in REQUIRED_MOTOR_PARAMS[:4]:
        if field in mp:
            pts += 0.5
        else:
            notes.append(f"motor_parameters missing '{field}'")

    # Check loss breakdown
    lb = report.get("loss_breakdown", {})
    for field in REQUIRED_LOSS_FIELDS:
        if field in lb:
            pts += 0.25
        else:
            notes.append(f"loss_breakdown missing '{field}'")

    # Check simulation results
    sim = report.get("simulation_results", {})
    ts_curve = sim.get("torque_speed_curve", [])
    eff_map  = sim.get("efficiency_map", [])
    if isinstance(ts_curve, list) and len(ts_curve) >= 5:
        pts += 1.5
    else:
        notes.append("torque_speed_curve missing or too short (need >= 5 points)")
    if isinstance(eff_map, list) and len(eff_map) >= 10:
        pts += 1.5
    else:
        notes.append("efficiency_map missing or too sparse (need >= 10 points)")

    # Check FOC controller section
    foc = report.get("foc_controller", {})
    if foc.get("Kp_current") and foc.get("Ki_current"):
        pts += 1.0
    else:
        notes.append("foc_controller missing Kp_current / Ki_current")

    return {
        "score": round(min(pts, 15.0), 2),
        "max": 15,
        "notes": notes,
    }


# ─────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────

def evaluate(submission_path: str) -> dict:
    # Load submission
    try:
        with open(submission_path) as f:
            report = json.load(f)
    except FileNotFoundError:
        return error_result(f"Submission file not found: {submission_path}")
    except json.JSONDecodeError as e:
        return error_result(f"Invalid JSON: {e}")

    errors = []

    # Check top-level structure
    missing_keys = [k for k in REQUIRED_TOP_KEYS if k not in report]
    if len(missing_keys) == len(REQUIRED_TOP_KEYS):
        return error_result("Submission appears empty — no required keys present")

    eff_result    = score_efficiency(report)
    td_result     = score_torque_density(report)
    therm_result  = score_thermal(report)
    doc_result    = score_documentation(report)

    errors.extend(eff_result.pop("errors", []))
    errors.extend(td_result.pop("errors", []))
    errors.extend(therm_result.get("constraint_violations", []))
    errors.extend(doc_result.get("notes", []))

    total = round(
        eff_result["score"] + td_result["score"] +
        therm_result["score"] + doc_result["score"],
        2
    )

    return {
        "total": total,
        "breakdown": {
            "efficiency":      eff_result,
            "torque_density":  td_result,
            "thermal":         therm_result,
            "documentation":   doc_result,
        },
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="MotorForge Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to motor_design_report.json")
    args = parser.parse_args()

    result = evaluate(args.submission)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
