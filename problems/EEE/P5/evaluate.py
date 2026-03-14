"""
E-Harvest — Evaluation / Scoring Script
EEE-P5

Usage:
    python evaluate.py --submission submission/eharvest_design_report.json

Reads the structured JSON design report and outputs a JSON scoring report
to stdout.
"""

import argparse
import json
from pathlib import Path


# ─────────────────────────────────────────────
# REQUIREMENTS
# ─────────────────────────────────────────────

PCE_TARGET_PCT      = 40.0     # % at -10 dBm
V_OUT_TARGET_V      = 1.8
V_OUT_TOL           = 0.05     # ± 5%
P_OUT_TARGET_UW     = 100.0    # μW
FREQ1_GHZ           = 0.915
FREQ2_GHZ           = 2.4

REQUIRED_TOP_KEYS = [
    "antenna_design",
    "matching_network",
    "rectifier_circuit",
    "voltage_regulator",
    "energy_buffer",
    "simulation_results",
    "pcb_layout_notes",
]


def error_result(msg: str) -> dict:
    return {"total": 0, "breakdown": {}, "errors": [msg]}


# ─────────────────────────────────────────────
# SCORING FUNCTIONS
# ─────────────────────────────────────────────

def score_pce(report: dict) -> dict:
    """Score PCE at -10 dBm (max 40 pts)."""
    rect = report.get("rectifier_circuit", {})
    errors = []

    # Prefer pre-computed field; otherwise scan curve
    pce_f1 = rect.get("pce_at_neg10dbm_freq1_pct")
    pce_f2 = rect.get("pce_at_neg10dbm_freq2_pct")

    if pce_f1 is None:
        curve1 = rect.get("pce_curve_freq1", [])
        entry = next((r for r in curve1 if r.get("p_in_dbm") == -10), None)
        pce_f1 = entry["pce_pct"] if entry else None

    if pce_f2 is None:
        curve2 = rect.get("pce_curve_freq2", [])
        entry = next((r for r in curve2 if r.get("p_in_dbm") == -10), None)
        pce_f2 = entry["pce_pct"] if entry else None

    if pce_f1 is None and pce_f2 is None:
        return {"score": 0, "max": 40, "errors": ["PCE data not found for either frequency"]}

    def pts_for_pce(pce):
        if pce is None:
            return 0.0
        pce = float(pce)
        if pce >= PCE_TARGET_PCT:
            return 20.0
        elif pce >= 20.0:
            return round(20.0 * (pce - 20.0) / (PCE_TARGET_PCT - 20.0), 2)
        return 0.0

    pts_f1 = pts_for_pce(pce_f1)
    pts_f2 = pts_for_pce(pce_f2)
    total  = pts_f1 + pts_f2

    if pce_f1 is None:
        errors.append("PCE at 915 MHz missing")
    if pce_f2 is None:
        errors.append("PCE at 2.4 GHz missing")

    return {
        "score": round(total, 2),
        "max": 40,
        "pce_freq1_pct": round(float(pce_f1), 2) if pce_f1 is not None else None,
        "pce_freq2_pct": round(float(pce_f2), 2) if pce_f2 is not None else None,
        "target_pct": PCE_TARGET_PCT,
        "pass_freq1": bool(pce_f1 and float(pce_f1) >= PCE_TARGET_PCT),
        "pass_freq2": bool(pce_f2 and float(pce_f2) >= PCE_TARGET_PCT),
        "errors": errors,
    }


def score_bandwidth(report: dict) -> dict:
    """
    Score bandwidth coverage (max 25 pts).
    Awards points for: dual-band coverage, bandwidth at each band, diplexer/wideband design.
    """
    ant = report.get("antenna_design", {})
    rect = report.get("rectifier_circuit", {})
    notes = []
    pts = 0.0

    # Both bands present (10 pts)
    has_f1 = (ant.get("s11_db_freq1") is not None or
              ant.get("gain_dbi_freq1") is not None)
    has_f2 = (ant.get("s11_db_freq2") is not None or
              ant.get("gain_dbi_freq2") is not None)

    if has_f1 and has_f2:
        pts += 10.0
    elif has_f1 or has_f2:
        pts += 5.0
        notes.append("Only one frequency band covered (dual-band required)")
    else:
        notes.append("No antenna frequency data found")

    # S11 quality at each band (5 pts each)
    s11_f1 = ant.get("s11_db_freq1")
    s11_f2 = ant.get("s11_db_freq2")

    if s11_f1 is not None and float(s11_f1) <= -10.0:
        pts += 5.0
    elif s11_f1 is not None:
        pts += round(5.0 * max(0, -float(s11_f1) / 10.0), 2)
        notes.append(f"S11 at 915 MHz is {s11_f1} dB (target ≤ -10 dB)")

    if s11_f2 is not None and float(s11_f2) <= -10.0:
        pts += 5.0
    elif s11_f2 is not None:
        pts += round(5.0 * max(0, -float(s11_f2) / 10.0), 2)
        notes.append(f"S11 at 2.4 GHz is {s11_f2} dB (target ≤ -10 dB)")

    # Bandwidth reported (5 pts)
    bw1 = ant.get("bandwidth_mhz_freq1")
    bw2 = ant.get("bandwidth_mhz_freq2")
    if bw1 and bw2:
        pts += 5.0
    elif bw1 or bw2:
        pts += 2.5
        notes.append("Bandwidth reported for only one band")
    else:
        notes.append("Antenna bandwidth not reported")

    return {
        "score": round(min(pts, 25.0), 2),
        "max": 25,
        "notes": notes,
    }


def score_voltage_stability(report: dict) -> dict:
    """Score output voltage stability over input power range (max 20 pts)."""
    sim = report.get("simulation_results", {})
    v_table = sim.get("output_voltage_vs_input_power", [])

    regulator = report.get("voltage_regulator", {})
    v_reg = regulator.get("v_out_V")
    errors = []

    if not v_table and v_reg is None:
        return {"score": 0, "max": 20,
                "errors": ["No output voltage data in simulation_results or voltage_regulator"]}

    if v_table:
        stable_points = [r for r in v_table if r.get("stable") is True]
        stable_range  = len(stable_points)
        total_points  = len(v_table)

        # Points for stable range
        if total_points > 0:
            fraction = stable_range / total_points
        else:
            fraction = 0.0

        pts = round(20.0 * fraction, 2)

        # Bonus: regulator specified
        if regulator.get("iq_nA", 999) < 1000:  # < 1 μA quiescent
            pts = min(pts + 2.0, 20.0)

        return {
            "score": pts,
            "max": 20,
            "stable_points": stable_range,
            "total_points":  total_points,
            "stable_fraction_pct": round(fraction * 100, 1),
            "v_out_V": v_reg,
        }

    # Fallback: regulator claims fixed voltage
    if v_reg is not None:
        v = float(v_reg)
        if abs(v - V_OUT_TARGET_V) / V_OUT_TARGET_V <= V_OUT_TOL:
            pts = 12.0
        else:
            pts = 5.0
            errors.append(f"Regulator v_out {v} V is outside ±5% of {V_OUT_TARGET_V} V target")

        iq_na = regulator.get("iq_nA", 9999)
        if float(iq_na) < 1000:
            pts = min(pts + 3.0, 20.0)

        return {"score": round(pts, 2), "max": 20, "v_out_V": v, "errors": errors}

    return {"score": 0, "max": 20, "errors": errors}


def score_documentation(report: dict) -> dict:
    """Score documentation completeness (max 15 pts)."""
    pts = 0.0
    notes = []

    # Required top-level keys (1 pt each)
    for key in REQUIRED_TOP_KEYS:
        if key in report:
            pts += 1.0
        else:
            notes.append(f"Missing top-level key: '{key}'")

    # Rectifier diode selection documented
    rect = report.get("rectifier_circuit", {})
    if rect.get("diode"):
        pts += 1.0
    else:
        notes.append("rectifier_circuit.diode not specified")

    # Matching network component values
    mn = report.get("matching_network", {})
    if mn.get("freq1", {}).get("l_series_nH") or mn.get("l_series_nH"):
        pts += 1.0
    else:
        notes.append("matching_network component values missing")

    # Energy buffer analysis
    buf = report.get("energy_buffer", {})
    if buf.get("capacitance_uF") and buf.get("voltage_droop_pct") is not None:
        pts += 1.5
    else:
        notes.append("energy_buffer.capacitance_uF or voltage_droop_pct missing")

    # PCB layout notes
    pcb = report.get("pcb_layout_notes", {})
    if pcb.get("layers") and pcb.get("ground_plane"):
        pts += 1.5
    else:
        notes.append("pcb_layout_notes incomplete (layers, ground_plane required)")

    # Simulation data (PCE curve)
    sim = report.get("simulation_results", {})
    pce_curve = sim.get("pce_vs_input_power_freq1", [])
    if isinstance(pce_curve, list) and len(pce_curve) >= 5:
        pts += 2.0
    else:
        notes.append("simulation_results.pce_vs_input_power_freq1 missing or too short")

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

    missing = [k for k in REQUIRED_TOP_KEYS if k not in report]
    if len(missing) == len(REQUIRED_TOP_KEYS):
        return error_result("Submission appears empty — no required keys present")

    errors = []
    if missing:
        errors.append(f"Missing top-level keys: {missing}")

    pce_result   = score_pce(report)
    bw_result    = score_bandwidth(report)
    vstab_result = score_voltage_stability(report)
    doc_result   = score_documentation(report)

    errors.extend(pce_result.pop("errors", []))
    errors.extend(vstab_result.pop("errors", []))
    errors.extend(bw_result.get("notes", []))
    errors.extend(doc_result.get("notes", []))

    total = round(
        pce_result["score"] + bw_result["score"] +
        vstab_result["score"] + doc_result["score"],
        2
    )

    return {
        "total": total,
        "breakdown": {
            "pce":               pce_result,
            "bandwidth":         bw_result,
            "voltage_stability": vstab_result,
            "documentation":     doc_result,
        },
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="E-Harvest Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to eharvest_design_report.json")
    args = parser.parse_args()

    result = evaluate(args.submission)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
