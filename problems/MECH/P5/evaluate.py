"""
HyperCool — Evaluation Script   (MECH-P5)
==========================================
Usage:
    python evaluate.py --submission <path-to-report.json>

Expected report.json schema
----------------------------
{
    "coolant_selected":              str   -- "water" | "novec_7100" | "R134a" | other
    "cooling_technology":            str   -- "microchannel_cold_plate" | "immersion" | "heat_pipe"
    "chip_heat_flux_W_cm2":          float -- [W/cm²]; problem spec is 100
    "die_area_cm2":                  float -- [cm²]; used with heat flux to get chip power
    "q_total_kW":                    float -- total rack load [kW]; must be ~50
    "evaporator_channel_width_um":   float -- [μm]; must be > 0
    "evaporator_channel_height_um":  float -- [μm]; must be > 0
    "evaporator_htc_W_m2K":          float -- [W/(m²·K)]; must be > 10000 for two-phase credit
    "evaporator_pressure_drop_kPa":  float -- [kPa] per cold plate; must be > 0
    "condenser_area_m2":             float -- [m²]; must be > 0
    "condenser_type":                str   -- "air" | "liquid"
    "thermal_resistance_total_K_W":  float -- [K/W]; must lead to Tj < 85°C
    "junction_temp_C":               float -- [°C]; MUST be < 85 (hard fail otherwise)
    "saturation_temp_C":             float -- [°C]; must be < 85 and above freezing
    "critical_heat_flux_W_cm2":      float -- [W/cm²]; must be > chip heat flux
    "chf_safety_factor":             float -- CHF / 100 W/cm²; must be >= 1.5
    "pump_power_W":                  float -- [W]; used to compute COP
    "system_cop":                    float -- Q_total / W_pump; must be > 10
}

Scoring rubric (total = 100 points):
    Thermal Resistance  (35 pts): R_total, junction temperature < 85°C
    Pressure Drop       (25 pts): reasonable pressure drop; two-phase HTC demonstrated
    Reliability         (25 pts): CHF safety factor >= 1.5; COP > 10; saturation temp valid
    Scalability         (15 pts): system can handle full 50 kW rack; condenser sized correctly
"""

import argparse
import json
import sys

REQUIRED_FIELDS = [
    "coolant_selected", "cooling_technology", "chip_heat_flux_W_cm2",
    "die_area_cm2", "q_total_kW", "evaporator_channel_width_um",
    "evaporator_channel_height_um", "evaporator_htc_W_m2K",
    "evaporator_pressure_drop_kPa", "condenser_area_m2", "condenser_type",
    "thermal_resistance_total_K_W", "junction_temp_C", "saturation_temp_C",
    "critical_heat_flux_W_cm2", "chf_safety_factor", "pump_power_W", "system_cop",
]

TJ_LIMIT_C     = 85.0
CHF_SF_MIN     = 1.5
HTC_2PHASE_MIN = 10_000.0   # W/(m²·K) minimum to credit two-phase operation


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
# Thermal Resistance scoring (35 pts)
# ---------------------------------------------------------------------------

def score_thermal_resistance(data: dict) -> tuple:
    max_score = 35
    score     = 0
    details   = {}
    errors    = []

    Tj = data.get("junction_temp_C", 9999)

    # Junction temperature (20 pts) — HARD FAIL if >= 85°C
    if Tj < 75.0:
        tj_pts = 20
    elif Tj < 80.0:
        tj_pts = 15
    elif Tj < 85.0:
        tj_pts = 10
    else:
        tj_pts = 0
        errors.append(f"HARD FAIL: Junction temperature {Tj:.2f}°C >= {TJ_LIMIT_C}°C limit. Chip will fail.")
    details["junction_temp_C"] = {"value": Tj, "limit": TJ_LIMIT_C, "points": tj_pts, "max": 20}
    score += tj_pts

    # Thermal resistance consistency (15 pts)
    # Check: R_total * Q_chip + T_sat ≈ Tj
    R     = data.get("thermal_resistance_total_K_W", 0)
    T_sat = data.get("saturation_temp_C", 61.0)
    q_chip_w = data.get("chip_heat_flux_W_cm2", 100) * data.get("die_area_cm2", 1.0) * 100.0   # W
    if R > 0 and q_chip_w > 0:
        Tj_check = T_sat + R * q_chip_w
        err_pct = abs(Tj_check - Tj) / max(abs(Tj), 1e-6) * 100.0
        if err_pct < 5.0:
            r_pts = 15
        elif err_pct < 15.0:
            r_pts = 9
        else:
            r_pts = 3
            errors.append(f"R_total inconsistency: R={R:.5f} K/W, T_sat={T_sat}°C, Q={q_chip_w:.0f} W "
                          f"gives Tj={Tj_check:.1f}°C, reported {Tj:.1f}°C (error {err_pct:.1f}%).")
    else:
        r_pts = 0
        errors.append("Cannot verify R_total — thermal_resistance_total_K_W or die_area_cm2 is zero.")
    details["thermal_resistance_total_K_W"] = {"value": R, "Tj_check": round(Tj_check if R > 0 and q_chip_w > 0 else 0, 2),
                                                "points": r_pts, "max": 15}
    score += r_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Pressure Drop scoring (25 pts)
# ---------------------------------------------------------------------------

def score_pressure_drop(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # Two-phase HTC demonstrated (15 pts)
    htc = data.get("evaporator_htc_W_m2K", 0)
    if htc >= 50_000:
        htc_pts = 15
    elif htc >= 20_000:
        htc_pts = 11
    elif htc >= HTC_2PHASE_MIN:
        htc_pts = 6
        errors.append(f"HTC {htc:.0f} W/(m²·K) is low for two-phase cooling; recheck correlation.")
    else:
        htc_pts = 0
        errors.append(f"HTC {htc:.0f} W/(m²·K) is below {HTC_2PHASE_MIN:.0f} — not in two-phase regime.")
    details["evaporator_htc_W_m2K"] = {"value": htc, "min_two_phase": HTC_2PHASE_MIN,
                                        "points": htc_pts, "max": 15}
    score += htc_pts

    # Pressure drop plausibility (10 pts)
    # Acceptable range: 1–200 kPa per cold plate
    dP = data.get("evaporator_pressure_drop_kPa", -1)
    if 1.0 <= dP <= 50.0:
        dp_pts = 10
    elif 0.1 <= dP < 1.0 or 50.0 < dP <= 200.0:
        dp_pts = 5
        errors.append(f"Pressure drop {dP:.2f} kPa is unusual — verify flow conditions.")
    elif dP > 0:
        dp_pts = 2
        errors.append(f"Pressure drop {dP:.2f} kPa is outside plausible range [1, 200] kPa.")
    else:
        dp_pts = 0
        errors.append(f"Pressure drop {dP} kPa is invalid (must be > 0).")
    details["evaporator_pressure_drop_kPa"] = {"value": dP, "points": dp_pts, "max": 10}
    score += dp_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Reliability scoring (25 pts)
# ---------------------------------------------------------------------------

def score_reliability(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # CHF safety factor (15 pts)
    sf = data.get("chf_safety_factor", 0)
    if sf >= 3.0:
        sf_pts = 15
    elif sf >= 1.5:
        sf_pts = 10
    elif sf >= 1.0:
        sf_pts = 4
        errors.append(f"CHF safety factor {sf:.2f} is below 1.5 minimum — dry-out risk is high.")
    else:
        sf_pts = 0
        errors.append(f"CHF safety factor {sf:.2f} < 1.0 — chip heat flux EXCEEDS CHF; dry-out certain.")
    details["chf_safety_factor"] = {"value": sf, "target": CHF_SF_MIN,
                                     "points": sf_pts, "max": 15}
    score += sf_pts

    # COP (10 pts)
    cop = data.get("system_cop", 0)
    if cop >= 100.0:
        cop_pts = 10
    elif cop >= 50.0:
        cop_pts = 8
    elif cop >= 10.0:
        cop_pts = 5
    else:
        cop_pts = 2
        errors.append(f"System COP {cop:.1f} is low; pump consumes excessive power relative to heat load.")
    details["system_cop"] = {"value": cop, "points": cop_pts, "max": 10}
    score += cop_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Scalability scoring (15 pts)
# ---------------------------------------------------------------------------

def score_scalability(data: dict, missing_fields: list) -> tuple:
    max_score = 15
    score     = 0
    details   = {}
    errors    = []

    # Total rack load ~50 kW (5 pts)
    q_tot = data.get("q_total_kW", 0)
    if 45.0 <= q_tot <= 55.0:
        qtot_pts = 5
    elif 40.0 <= q_tot <= 60.0:
        qtot_pts = 3
    else:
        qtot_pts = 0
        errors.append(f"Total heat load {q_tot} kW is inconsistent with problem spec (50 kW rack).")
    details["q_total_kW"] = {"value": q_tot, "target": 50.0, "points": qtot_pts, "max": 5}
    score += qtot_pts

    # Condenser sized (5 pts)
    cond_a = data.get("condenser_area_m2", 0)
    if cond_a > 0:
        cond_pts = 5
    else:
        cond_pts = 0
        errors.append("condenser_area_m2 is zero or missing.")
    details["condenser_area_m2"] = {"value": cond_a, "points": cond_pts, "max": 5}
    score += cond_pts

    # All required fields (5 pts)
    n_miss = len(missing_fields)
    if n_miss == 0:
        field_pts = 5
    elif n_miss <= 3:
        field_pts = 2
        errors.append(f"Missing fields: {missing_fields}")
    else:
        field_pts = 0
        errors.append(f"Missing {n_miss} required fields: {missing_fields}")
    details["required_fields"] = {"missing": missing_fields, "points": field_pts, "max": 5}
    score += field_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HyperCool two-phase cooling evaluator (MECH-P5)")
    parser.add_argument("--submission", required=True, help="Path to report.json")
    args = parser.parse_args()

    data, load_errors = load_submission(args.submission)
    if data is None:
        result = {"total": 0, "breakdown": {}, "errors": load_errors}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    missing    = check_required_fields(data)
    all_errors = list(load_errors)

    breakdown  = {}

    tr_score,  tr_max,  tr_det,  tr_err  = score_thermal_resistance(data)
    dp_score,  dp_max,  dp_det,  dp_err  = score_pressure_drop(data)
    rel_score, rel_max, rel_det, rel_err = score_reliability(data)
    sc_score,  sc_max,  sc_det,  sc_err  = score_scalability(data, missing)

    all_errors.extend(tr_err + dp_err + rel_err + sc_err)

    breakdown["thermal_resistance"] = {"score": tr_score,  "max": tr_max,  "details": tr_det}
    breakdown["pressure_drop"]      = {"score": dp_score,  "max": dp_max,  "details": dp_det}
    breakdown["reliability"]        = {"score": rel_score, "max": rel_max, "details": rel_det}
    breakdown["scalability"]        = {"score": sc_score,  "max": sc_max,  "details": sc_det}

    total = tr_score + dp_score + rel_score + sc_score

    result = {
        "total":     total,
        "breakdown": breakdown,
        "errors":    all_errors,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
