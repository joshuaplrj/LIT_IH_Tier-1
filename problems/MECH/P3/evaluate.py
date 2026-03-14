"""
GearPro — Evaluation Script   (MECH-P3)
========================================
Usage:
    python evaluate.py --submission <path-to-report.json>

Expected report.json schema
----------------------------
{
    "overall_gear_ratio":    float -- must be in [99, 101] for full credit
    "ratio_error_pct":       float -- |ratio - 100| / 100 * 100; must be <= 1%
    "stage_ratios":          list[float] -- [i1, i2, i3]; product must match overall_gear_ratio
    "stages": [
        {
            "stage":                 int
            "sun_teeth":             int
            "planet_teeth":          int
            "ring_teeth":            int
            "module_mm":             float
            "face_width_mm":         float
            "num_planets":           int   -- typically 3 or 4
            "helix_angle_deg":       float
            "agma_bending_sf":       float -- must be >= 1.2 for all stages
            "agma_contact_sf":       float -- must be >= 1.2 for all stages
        }, ...
    ],
    "overall_efficiency_pct": float -- must be > 97
    "bearing_l10_life_hr":    float -- must be > 175200 (design life)
    "output_speed_rpm":       float -- must be in [1450, 1550]
    "input_torque_MNm":       float -- should be ~3.2
    "agma_standard":          str   -- must equal "AGMA 6006"
}

Scoring rubric (total = 100 points):
    Gear Ratio Accuracy  (25 pts): overall ratio within 1% of 100:1 + product consistency
    AGMA Compliance      (30 pts): all stages meet bending and contact SF >= 1.2
    Bearing Selection    (20 pts): L10 bearing life > design life; gear geometry conditions
    Efficiency           (25 pts): overall efficiency > 97%; per-stage validation
"""

import argparse
import json
import math
import sys

REQUIRED_FIELDS = [
    "overall_gear_ratio", "ratio_error_pct", "stage_ratios", "stages",
    "overall_efficiency_pct", "bearing_l10_life_hr", "output_speed_rpm",
    "input_torque_MNm", "agma_standard",
]
STAGE_REQUIRED = [
    "stage", "sun_teeth", "planet_teeth", "ring_teeth", "module_mm",
    "face_width_mm", "num_planets", "helix_angle_deg",
    "agma_bending_sf", "agma_contact_sf",
]

GEAR_RATIO_TARGET   = 100.0
OUTPUT_SPEED_TARGET = 1500.0
DESIGN_LIFE_HR      = 175_200.0
EFF_TARGET          = 97.0
MIN_SF              = 1.2


def load_submission(path: str) -> tuple:
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, [f"File not found: {path}"]
    except json.JSONDecodeError as e:
        return None, [f"JSON parse error: {e}"]
    return data, []


def check_required_fields(data: dict) -> list:
    return [f for f in REQUIRED_FIELDS if f not in data]


# ---------------------------------------------------------------------------
# Gear Ratio Accuracy scoring (25 pts)
# ---------------------------------------------------------------------------

def score_gear_ratio(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    overall = data.get("overall_gear_ratio", 0)
    err_pct = abs(overall - GEAR_RATIO_TARGET) / GEAR_RATIO_TARGET * 100.0 if overall > 0 else 999

    # Ratio accuracy (15 pts)
    if err_pct <= 0.5:
        ratio_pts = 15
    elif err_pct <= 1.0:
        ratio_pts = 10
    elif err_pct <= 3.0:
        ratio_pts = 5
    else:
        ratio_pts = 0
        errors.append(f"Overall ratio {overall:.4f} is {err_pct:.2f}% from target 100 (limit 1%).")
    details["overall_ratio"] = {"value": overall, "error_pct": round(err_pct, 3),
                                 "points": ratio_pts, "max": 15}
    score += ratio_pts

    # Output speed in acceptable band (10 pts)
    out_spd = data.get("output_speed_rpm", 0)
    if 1450 <= out_spd <= 1550:
        spd_pts = 10
    elif 1400 <= out_spd <= 1600:
        spd_pts = 5
    else:
        spd_pts = 0
        errors.append(f"Output speed {out_spd:.1f} RPM is outside [1450, 1550] RPM band.")
    details["output_speed_rpm"] = {"value": out_spd, "target": OUTPUT_SPEED_TARGET,
                                    "points": spd_pts, "max": 10}
    score += spd_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# AGMA Compliance scoring (30 pts)
# ---------------------------------------------------------------------------

def score_agma(data: dict) -> tuple:
    max_score = 30
    score     = 0
    details   = {}
    errors    = []

    stages = data.get("stages", [])

    # AGMA standard stated (5 pts)
    std = data.get("agma_standard", "")
    if "6006" in str(std):
        std_pts = 5
    elif "AGMA" in str(std).upper():
        std_pts = 2
        errors.append(f"AGMA standard '{std}' — expected 'AGMA 6006' for wind turbine gearboxes.")
    else:
        std_pts = 0
        errors.append(f"AGMA standard field missing or incorrect: '{std}'.")
    details["agma_standard"] = {"value": std, "points": std_pts, "max": 5}
    score += std_pts

    if not stages or not isinstance(stages, list) or len(stages) < 3:
        errors.append(f"Expected 3 stages; found {len(stages) if isinstance(stages, list) else 0}.")
        details["stage_sf"] = {"points": 0, "max": 25}
        return score, max_score, details, errors

    # Per-stage SF checks (25 pts total: bending 12 + contact 13)
    bend_pass = 0
    cont_pass = 0
    stage_details = []
    for s in stages[:3]:
        missing_stage = [f for f in STAGE_REQUIRED if f not in s]
        if missing_stage:
            errors.append(f"Stage {s.get('stage','?')} missing fields: {missing_stage}")
            stage_details.append({"stage": s.get("stage"), "ok": False})
            continue

        sf_b = s.get("agma_bending_sf", 0)
        sf_c = s.get("agma_contact_sf", 0)

        # Geometric consistency: i = 1 + Zr/Zs; Zr = Zs + 2*Zp
        Zs, Zp, Zr = s["sun_teeth"], s["planet_teeth"], s["ring_teeth"]
        mesh_ok = (Zr == Zs + 2 * Zp)
        assem_ok = ((Zs + Zr) % s["num_planets"] == 0)

        bend_ok = sf_b >= MIN_SF
        cont_ok = sf_c >= MIN_SF
        if bend_ok:
            bend_pass += 1
        else:
            errors.append(f"Stage {s['stage']} bending SF {sf_b:.3f} < required {MIN_SF}.")
        if cont_ok:
            cont_pass += 1
        else:
            errors.append(f"Stage {s['stage']} contact SF {sf_c:.3f} < required {MIN_SF}.")
        if not mesh_ok:
            errors.append(f"Stage {s['stage']} fails mesh condition: Zr={Zr} != Zs+2*Zp={Zs+2*Zp}.")
        if not assem_ok:
            errors.append(f"Stage {s['stage']} fails assembly condition: (Zs+Zr)={Zs+Zr} not divisible by N={s['num_planets']}.")

        stage_details.append({
            "stage": s["stage"], "sf_b": sf_b, "sf_c": sf_c,
            "mesh_ok": mesh_ok, "assembly_ok": assem_ok
        })

    bend_pts = round(12 * bend_pass / 3)
    cont_pts = round(13 * cont_pass / 3)
    details["stage_bending_sf"] = {"stages_passing": bend_pass, "of": 3, "points": bend_pts, "max": 12}
    details["stage_contact_sf"] = {"stages_passing": cont_pass, "of": 3, "points": cont_pts, "max": 13}
    details["stage_details"]    = stage_details
    score += bend_pts + cont_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Bearing Selection scoring (20 pts)
# ---------------------------------------------------------------------------

def score_bearing(data: dict) -> tuple:
    max_score = 20
    score     = 0
    details   = {}
    errors    = []

    l10 = data.get("bearing_l10_life_hr", 0)
    if l10 >= 2 * DESIGN_LIFE_HR:      # >= 350,400 hr  (excellent)
        l10_pts = 20
    elif l10 >= DESIGN_LIFE_HR:        # >= 175,200 hr  (acceptable)
        l10_pts = 14
    elif l10 >= 0.5 * DESIGN_LIFE_HR:  # >= 87,600 hr   (marginal)
        l10_pts = 7
        errors.append(f"Bearing L10 life {l10:,.0f} hr is below design life {DESIGN_LIFE_HR:,.0f} hr.")
    else:
        l10_pts = 0
        errors.append(f"Bearing L10 life {l10:,.0f} hr is critically insufficient.")
    details["bearing_l10_life_hr"] = {
        "value": l10, "design_life": DESIGN_LIFE_HR, "points": l10_pts, "max": 20
    }
    score += l10_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Efficiency scoring (25 pts)
# ---------------------------------------------------------------------------

def score_efficiency(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    eta = data.get("overall_efficiency_pct", 0)
    if eta >= 98.5:
        eta_pts = 25
    elif eta >= 97.0:
        eta_pts = 18
    elif eta >= 95.0:
        eta_pts = 8
        errors.append(f"Efficiency {eta:.2f}% is below 97% target.")
    else:
        eta_pts = 0
        errors.append(f"Efficiency {eta:.2f}% is critically below 97% target.")
    details["overall_efficiency_pct"] = {"value": eta, "target": EFF_TARGET,
                                          "points": eta_pts, "max": 25}
    score += eta_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="GearPro gearbox evaluator (MECH-P3)")
    parser.add_argument("--submission", required=True, help="Path to report.json")
    args = parser.parse_args()

    data, load_errors = load_submission(args.submission)
    if data is None:
        result = {"total": 0, "breakdown": {}, "errors": load_errors}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    missing = check_required_fields(data)
    all_errors = list(load_errors)
    if missing:
        all_errors.append(f"Missing required top-level fields: {missing}")

    breakdown = {}

    ratio_score, ratio_max, ratio_det, ratio_err = score_gear_ratio(data)
    agma_score,  agma_max,  agma_det,  agma_err  = score_agma(data)
    bear_score,  bear_max,  bear_det,  bear_err  = score_bearing(data)
    eff_score,   eff_max,   eff_det,   eff_err   = score_efficiency(data)

    all_errors.extend(ratio_err + agma_err + bear_err + eff_err)

    breakdown["gear_ratio_accuracy"] = {"score": ratio_score, "max": ratio_max, "details": ratio_det}
    breakdown["agma_compliance"]      = {"score": agma_score,  "max": agma_max,  "details": agma_det}
    breakdown["bearing_selection"]    = {"score": bear_score,  "max": bear_max,  "details": bear_det}
    breakdown["efficiency"]           = {"score": eff_score,   "max": eff_max,   "details": eff_det}

    total = ratio_score + agma_score + bear_score + eff_score

    result = {
        "total":     total,
        "breakdown": breakdown,
        "errors":    all_errors,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
