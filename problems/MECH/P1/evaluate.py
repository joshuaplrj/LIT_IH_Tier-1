"""
AeroBot — Evaluation Script   (MECH-P1)
=========================================
Usage:
    python evaluate.py --submission <path-to-report.json>

Expected report.json schema
----------------------------
{
    "configuration":            str   — e.g. "quad-plane"
    "mtow_kg":                  float — total aircraft mass [kg]; must be <= 15
    "wing_area_m2":             float — wing reference area [m²]; must be > 0
    "aspect_ratio":             float — wing AR; must be in [4, 20]
    "airfoil":                  str   — airfoil designation
    "cruise_cl":                float — lift coefficient at cruise; must be in (0.3, 1.4)
    "cruise_cd":                float — drag coefficient at cruise; must be > 0
    "ld_ratio":                 float — L/D; must be >= 10 for full score
    "power_cruise_W":           float — electrical cruise power [W]; must be > 0
    "battery_capacity_Wh":      float — battery capacity [Wh]; must be > 0
    "endurance_hr":             float — predicted cruise endurance [hr]; must be >= 2.0
    "range_km":                 float — predicted range [km]; must be >= 100
    "vtol_rotor_diameter_m":    float — single VTOL rotor diameter [m]; must be > 0
    "vtol_disk_loading_kg_m2":  float — disk loading [kg/m²]; must be <= 25
    "hover_power_W":            float — total electrical hover power [W]; must be > 0
    "static_margin_percent":    float — static margin [%]; must be in [5, 20]
    "wing_spar_safety_factor":  float — spar bending SF; must be >= 1.5
    "bom":                      list  — bill of materials items
}

Scoring rubric (total = 100 points):
    Aerodynamics        (25 pts): L/D, cruise CL, wing area consistency
    Structural Integrity(25 pts): spar SF, MTOW within limit, static margin
    Propulsion Efficiency(25 pts): hover power (disk loading), battery/endurance
    Design Documentation(25 pts): presence and completeness of all required fields + BOM
"""

import argparse
import json
import math
import sys

REQUIRED_FIELDS = [
    "configuration", "mtow_kg", "wing_area_m2", "aspect_ratio", "airfoil",
    "cruise_cl", "cruise_cd", "ld_ratio", "power_cruise_W", "battery_capacity_Wh",
    "endurance_hr", "range_km", "vtol_rotor_diameter_m", "vtol_disk_loading_kg_m2",
    "hover_power_W", "static_margin_percent", "wing_spar_safety_factor", "bom",
]

# Physical constants
G       = 9.81
RHO_AIR = 1.225


def load_submission(path: str) -> tuple:
    """Load and parse the submission JSON. Returns (data, errors)."""
    errors = []
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, [f"File not found: {path}"]
    except json.JSONDecodeError as e:
        return None, [f"JSON parse error: {e}"]
    return data, errors


def check_required_fields(data: dict) -> list:
    """Return list of missing field names."""
    return [f for f in REQUIRED_FIELDS if f not in data]


# ---------------------------------------------------------------------------
# Aerodynamics scoring (25 pts)
# ---------------------------------------------------------------------------

def score_aerodynamics(data: dict) -> tuple:
    """Returns (score, max_score, details_dict, errors)."""
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # L/D ratio  (10 pts)
    ld = data.get("ld_ratio", 0)
    if ld >= 14:
        ld_pts = 10
    elif ld >= 12:
        ld_pts = 7
    elif ld >= 10:
        ld_pts = 4
    else:
        ld_pts = 0
        errors.append(f"L/D ratio {ld:.2f} is below minimum acceptable (10).")
    details["ld_ratio"] = {"value": ld, "points": ld_pts, "max": 10}
    score += ld_pts

    # Wing area consistency check (10 pts)
    # Verify: L ≈ W at cruise  =>  |computed_S - reported_S| / reported_S < 15%
    mtow     = data.get("mtow_kg", 0)
    cl       = data.get("cruise_cl", 0)
    s_report = data.get("wing_area_m2", 0)
    v        = 20.0
    if mtow > 0 and cl > 0 and s_report > 0:
        s_check = (mtow * G) / (0.5 * RHO_AIR * v**2 * cl)
        rel_err = abs(s_check - s_report) / s_check
        if rel_err < 0.05:
            wing_pts = 10
        elif rel_err < 0.15:
            wing_pts = 6
        else:
            wing_pts = 2
            errors.append(f"Wing area inconsistency: computed {s_check:.4f} m², reported {s_report:.4f} m² (error {rel_err*100:.1f}%).")
    else:
        wing_pts = 0
        errors.append("Cannot verify wing area — mtow_kg, cruise_cl, or wing_area_m2 is zero/missing.")
    details["wing_area_consistency"] = {"relative_error_pct": round(rel_err * 100, 2) if mtow > 0 and cl > 0 and s_report > 0 else None, "points": wing_pts, "max": 10}
    score += wing_pts

    # CL in reasonable range (5 pts)
    if 0.5 <= cl <= 1.2:
        cl_pts = 5
    elif 0.3 <= cl < 0.5 or 1.2 < cl <= 1.4:
        cl_pts = 2
    else:
        cl_pts = 0
        errors.append(f"cruise_cl = {cl} is outside plausible range [0.3, 1.4].")
    details["cruise_cl"] = {"value": cl, "points": cl_pts, "max": 5}
    score += cl_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Structural integrity scoring (25 pts)
# ---------------------------------------------------------------------------

def score_structural(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # MTOW within limit (10 pts)
    mtow = data.get("mtow_kg", 999)
    if mtow <= 15.0:
        mtow_pts = 10
    elif mtow <= 16.0:
        mtow_pts = 5
        errors.append(f"MTOW {mtow:.2f} kg exceeds 15 kg limit.")
    else:
        mtow_pts = 0
        errors.append(f"MTOW {mtow:.2f} kg significantly exceeds 15 kg limit.")
    details["mtow_kg"] = {"value": mtow, "limit": 15.0, "points": mtow_pts, "max": 10}
    score += mtow_pts

    # Spar safety factor (10 pts)
    sf = data.get("wing_spar_safety_factor", 0)
    if sf >= 2.5:
        sf_pts = 10
    elif sf >= 1.5:
        sf_pts = 6
    elif sf >= 1.0:
        sf_pts = 2
        errors.append(f"Spar SF {sf:.2f} is marginal (< 1.5); structure likely underdesigned.")
    else:
        sf_pts = 0
        errors.append(f"Spar SF {sf:.2f} < 1.0: structural failure expected.")
    details["wing_spar_safety_factor"] = {"value": sf, "points": sf_pts, "max": 10}
    score += sf_pts

    # Static margin (5 pts)
    sm = data.get("static_margin_percent", -999)
    if 5.0 <= sm <= 20.0:
        sm_pts = 5
    elif 2.0 <= sm < 5.0 or 20.0 < sm <= 30.0:
        sm_pts = 2
    else:
        sm_pts = 0
        errors.append(f"Static margin {sm:.1f}% is outside acceptable range [5, 20]%.")
    details["static_margin_percent"] = {"value": sm, "points": sm_pts, "max": 5}
    score += sm_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Propulsion efficiency scoring (25 pts)
# ---------------------------------------------------------------------------

def score_propulsion(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # Endurance (10 pts)
    endurance = data.get("endurance_hr", 0)
    if endurance >= 2.0:
        end_pts = 10
    elif endurance >= 1.5:
        end_pts = 6
        errors.append(f"Endurance {endurance:.2f} hr is below 2-hr target.")
    else:
        end_pts = 0
        errors.append(f"Endurance {endurance:.2f} hr is critically below 2-hr target.")
    details["endurance_hr"] = {"value": endurance, "target": 2.0, "points": end_pts, "max": 10}
    score += end_pts

    # Range (5 pts)
    range_km = data.get("range_km", 0)
    if range_km >= 100.0:
        range_pts = 5
    elif range_km >= 80.0:
        range_pts = 2
    else:
        range_pts = 0
        errors.append(f"Range {range_km:.1f} km does not meet 100 km target.")
    details["range_km"] = {"value": range_km, "target": 100.0, "points": range_pts, "max": 5}
    score += range_pts

    # Disk loading — hover efficiency (10 pts)
    dl = data.get("vtol_disk_loading_kg_m2", 999)
    if dl <= 12.0:
        dl_pts = 10
    elif dl <= 18.0:
        dl_pts = 6
    elif dl <= 25.0:
        dl_pts = 2
    else:
        dl_pts = 0
        errors.append(f"Disk loading {dl:.1f} kg/m² is very high; hover efficiency will be poor.")
    details["vtol_disk_loading_kg_m2"] = {"value": dl, "points": dl_pts, "max": 10}
    score += dl_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Design documentation scoring (25 pts)
# ---------------------------------------------------------------------------

def score_documentation(data: dict, missing_fields: list) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # All required fields present (15 pts)
    n_missing = len(missing_fields)
    if n_missing == 0:
        field_pts = 15
    elif n_missing <= 2:
        field_pts = 10
        errors.append(f"Missing fields: {missing_fields}")
    elif n_missing <= 5:
        field_pts = 5
        errors.append(f"Missing fields: {missing_fields}")
    else:
        field_pts = 0
        errors.append(f"Submission is missing {n_missing} required fields: {missing_fields}")
    details["required_fields_present"] = {"missing": missing_fields, "points": field_pts, "max": 15}
    score += field_pts

    # BOM completeness (10 pts)
    bom = data.get("bom", [])
    if isinstance(bom, list) and len(bom) >= 8:
        bom_pts = 10
    elif isinstance(bom, list) and len(bom) >= 4:
        bom_pts = 5
        errors.append(f"BOM has only {len(bom)} items; a complete BOM should have >= 8 entries.")
    else:
        bom_pts = 0
        errors.append("BOM is missing or has fewer than 4 entries.")
    details["bom_completeness"] = {"num_items": len(bom) if isinstance(bom, list) else 0, "points": bom_pts, "max": 10}
    score += bom_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AeroBot VTOL UAV design evaluator (MECH-P1)")
    parser.add_argument("--submission", required=True, help="Path to report.json")
    args = parser.parse_args()

    data, load_errors = load_submission(args.submission)
    if data is None:
        result = {"total": 0, "breakdown": {}, "errors": load_errors}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    missing = check_required_fields(data)

    all_errors = []
    breakdown  = {}

    aero_score, aero_max, aero_det, aero_err = score_aerodynamics(data)
    struct_score, struct_max, struct_det, struct_err = score_structural(data)
    prop_score, prop_max, prop_det, prop_err = score_propulsion(data)
    doc_score, doc_max, doc_det, doc_err = score_documentation(data, missing)

    all_errors.extend(aero_err + struct_err + prop_err + doc_err)

    breakdown["aerodynamics"]         = {"score": aero_score,   "max": aero_max,   "details": aero_det}
    breakdown["structural_integrity"] = {"score": struct_score, "max": struct_max, "details": struct_det}
    breakdown["propulsion_efficiency"]= {"score": prop_score,   "max": prop_max,   "details": prop_det}
    breakdown["design_documentation"] = {"score": doc_score,    "max": doc_max,    "details": doc_det}

    total = aero_score + struct_score + prop_score + doc_score

    result = {
        "total":     total,
        "breakdown": breakdown,
        "errors":    all_errors,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
