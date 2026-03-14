"""
PowerShield — Evaluation / Scoring Script
EEE-P4

Usage:
    python evaluate.py --submission submission/sscb_design_report.json

Reads the structured JSON design report and outputs a JSON scoring report
to stdout.
"""

import argparse
import json
from pathlib import Path


# ─────────────────────────────────────────────
# REQUIREMENTS
# ─────────────────────────────────────────────

V_DC_V              = 400.0
I_RATED_A           = 200.0
I_FAULT_KA          = 10.0
T_BREAK_MAX_US      = 100.0
V_CLAMP_MAX_V       = 600.0
T_J_MAX_C           = 150.0
N_CYCLES_ENDURANCE  = 10_000

# Target interrupt time for full marks
T_BREAK_FULL_MARKS_US  = 10.0    # ≤ 10 μs → full 35 pts
T_BREAK_HALF_MARKS_US  = 50.0    # ≤ 50 μs → 17.5 pts
T_BREAK_MIN_MARKS_US   = 100.0   # ≤ 100 μs → 7 pts (minimum pass)


def error_result(msg: str) -> dict:
    return {"total": 0, "breakdown": {}, "errors": [msg]}


# ─────────────────────────────────────────────
# SCHEMA CHECK
# ─────────────────────────────────────────────

REQUIRED_KEYS = [
    "semiconductor_selection",
    "topology",
    "snubber_clamping",
    "gate_driver",
    "fault_detection",
    "thermal_design",
    "simulation_results",
    "bom",
    "timing_breakdown",
]


# ─────────────────────────────────────────────
# SCORING FUNCTIONS
# ─────────────────────────────────────────────

def score_interrupt_time(report: dict) -> dict:
    """Score interrupt time (max 35 pts)."""
    tb = report.get("timing_breakdown", {})
    sim = report.get("simulation_results", {})

    t_int = (tb.get("total_us") or
             sim.get("fault_interruption", {}).get("t_interrupt_us"))

    if t_int is None:
        return {"score": 0, "max": 35, "errors": ["Interrupt time not found in report"]}

    t_int = float(t_int)

    if t_int <= T_BREAK_FULL_MARKS_US:
        pts = 35.0
    elif t_int <= T_BREAK_HALF_MARKS_US:
        # Linear from 35 at 10 μs to 17.5 at 50 μs
        pts = round(35.0 - 17.5 * (t_int - T_BREAK_FULL_MARKS_US) /
                    (T_BREAK_HALF_MARKS_US - T_BREAK_FULL_MARKS_US), 2)
    elif t_int <= T_BREAK_MIN_MARKS_US:
        # Linear from 17.5 at 50 μs to 7 at 100 μs
        pts = round(17.5 - 10.5 * (t_int - T_BREAK_HALF_MARKS_US) /
                    (T_BREAK_MIN_MARKS_US - T_BREAK_HALF_MARKS_US), 2)
    else:
        pts = 0.0

    # Voltage clamping check
    fault_sim = sim.get("fault_interruption", {})
    peak_v = fault_sim.get("peak_voltage_V", 0)
    v_ok = float(peak_v) <= V_CLAMP_MAX_V if peak_v else None

    if v_ok is False:
        pts = max(0, pts - 10.0)  # deduct 10 pts for exceeding clamping limit

    return {
        "score": round(pts, 2),
        "max": 35,
        "interrupt_time_us": round(t_int, 2),
        "target_us": T_BREAK_MAX_US,
        "full_marks_target_us": T_BREAK_FULL_MARKS_US,
        "pass": bool(t_int <= T_BREAK_MAX_US),
        "peak_switch_voltage_V": peak_v,
        "voltage_clamp_pass": v_ok,
    }


def score_protection_accuracy(report: dict) -> dict:
    """Score fault detection and protection accuracy (max 30 pts)."""
    fd = report.get("fault_detection", {})
    pts = 0.0
    notes = []

    # Detection method described (5 pts)
    if fd.get("method"):
        pts += 5.0
    else:
        notes.append("fault_detection.method not described")

    # Threshold set (5 pts)
    threshold = fd.get("threshold_A")
    if threshold:
        t = float(threshold)
        if I_RATED_A < t < I_FAULT_KA * 1000:
            pts += 5.0
        else:
            notes.append(f"threshold_A {t:.0f} A outside valid range "
                         f"({I_RATED_A:.0f}–{I_FAULT_KA*1000:.0f} A)")

    # Detection time (10 pts)
    t_det = fd.get("detection_time_us")
    if t_det:
        t_det = float(t_det)
        if t_det <= 2.0:
            pts += 10.0
        elif t_det <= 10.0:
            pts += round(10.0 * (1.0 - (t_det - 2.0) / 8.0), 2)
        else:
            notes.append(f"detection_time_us {t_det:.1f} μs is too slow (target ≤ 2 μs)")

    # Nuisance trip guard described (5 pts)
    if fd.get("nuisance_trip_guard"):
        pts += 5.0
    else:
        notes.append("nuisance_trip_guard not described (hysteresis/blanking time)")

    # Bidirectional check (5 pts)
    topo = report.get("topology", {})
    if topo.get("bidirectional") is True:
        pts += 5.0
    else:
        notes.append("topology.bidirectional not confirmed")

    return {
        "score": round(min(pts, 30.0), 2),
        "max": 30,
        "notes": notes,
    }


def score_efficiency(report: dict) -> dict:
    """Score SSCB conduction efficiency (max 20 pts)."""
    losses = report.get("loss_analysis", {})
    eff = losses.get("efficiency_pct")

    if eff is None:
        # Try to compute from conduction losses
        p_cond = losses.get("conduction_loss_W")
        if p_cond:
            p_out = I_RATED_A * V_DC_V
            eff = 100.0 * p_out / (p_out + float(p_cond))

    if eff is None:
        return {"score": 0, "max": 20,
                "errors": ["efficiency_pct not found in loss_analysis"]}

    eff = float(eff)

    # Target: > 99.5% efficiency (i.e., < 0.5% losses at rated)
    if eff >= 99.5:
        pts = 20.0
    elif eff >= 98.0:
        pts = round(20.0 * (eff - 98.0) / (99.5 - 98.0), 2)
    else:
        pts = 0.0

    return {
        "score": pts,
        "max": 20,
        "efficiency_pct": round(eff, 3),
        "target_pct": 99.5,
    }


def score_design_quality(report: dict) -> dict:
    """Score design quality and documentation (max 15 pts)."""
    pts = 0.0
    notes = []

    # Required keys present (0.5 pt each, max 4.5 pts)
    for key in REQUIRED_KEYS:
        if key in report:
            pts += 0.5
        else:
            notes.append(f"Missing top-level key: '{key}'")

    # Semiconductor justification
    semi = report.get("semiconductor_selection", {})
    if semi.get("justification") and len(str(semi["justification"])) > 20:
        pts += 1.5
    else:
        notes.append("Semiconductor selection lacks justification")

    # BOM completeness
    bom = report.get("bom", {})
    items = bom.get("items", [])
    if isinstance(items, list) and len(items) >= 5:
        pts += 2.0
    else:
        notes.append("BOM has fewer than 5 line items")

    if bom.get("total_bom_cost_usd", 0) > 0:
        pts += 1.0
    else:
        notes.append("BOM missing total cost")

    # Thermal analysis
    thermal = report.get("thermal_design", {})
    t_j = thermal.get("t_junction_C")
    if t_j and float(t_j) <= T_J_MAX_C:
        pts += 2.0
    elif t_j:
        pts += 0.5
        notes.append(f"Junction temp {float(t_j):.0f} °C exceeds {T_J_MAX_C:.0f} °C limit")
    else:
        notes.append("thermal_design.t_junction_C missing")

    # Gate driver section
    gd = report.get("gate_driver", {})
    if gd.get("v_gs_off_V") is not None and float(gd["v_gs_off_V"]) < 0:
        pts += 1.0  # negative turn-off voltage = good practice
    else:
        notes.append("Gate driver should use negative turn-off voltage for faster switching")

    return {
        "score": round(min(pts, 15.0), 2),
        "max": 15,
        "notes": notes,
    }


# ─────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────

def evaluate(submission_path: str) -> dict:
    try:
        with open(submission_path) as f:
            report = json.load(f)
    except FileNotFoundError:
        return error_result(f"Submission file not found: {submission_path}")
    except json.JSONDecodeError as e:
        return error_result(f"Invalid JSON: {e}")

    errors = []

    missing = [k for k in REQUIRED_KEYS if k not in report]
    if len(missing) == len(REQUIRED_KEYS):
        return error_result("Submission appears empty — no required keys present")

    if missing:
        errors.append(f"Missing keys: {missing}")

    int_result  = score_interrupt_time(report)
    prot_result = score_protection_accuracy(report)
    eff_result  = score_efficiency(report)
    qual_result = score_design_quality(report)

    errors.extend(int_result.pop("errors", []))
    errors.extend(eff_result.pop("errors", []))
    errors.extend(prot_result.get("notes", []))
    errors.extend(qual_result.get("notes", []))

    total = round(
        int_result["score"] + prot_result["score"] +
        eff_result["score"] + qual_result["score"],
        2
    )

    return {
        "total": total,
        "breakdown": {
            "interrupt_time":       int_result,
            "protection_accuracy":  prot_result,
            "efficiency":           eff_result,
            "design_quality":       qual_result,
        },
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="PowerShield Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to sscb_design_report.json")
    args = parser.parse_args()

    result = evaluate(args.submission)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
