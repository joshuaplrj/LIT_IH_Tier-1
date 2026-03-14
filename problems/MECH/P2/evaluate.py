"""
ThermoCell — Evaluation Script   (MECH-P2)
===========================================
Usage:
    python evaluate.py --submission <path-to-report.json>

Expected report.json schema
----------------------------
{
    "technology_selected":       str   -- "molten_salt" | "PCM" | "thermochemical"
    "storage_medium":            str
    "hot_tank_volume_m3":        float -- hot-side tank volume [m³]; must be > 0
    "cold_tank_volume_m3":       float -- cold-side tank volume [m³]; must be > 0
    "tank_material":             str
    "insulation_thickness_m":    float -- [m]; must be > 0
    "thermal_loss_rate_kW":      float -- combined heat loss [kW]; must be >= 0
    "round_trip_efficiency_pct": float -- [%]; must be > 95
    "hx_area_m2":                float -- [m²]; must be > 0
    "hx_effectiveness":          float -- [-]; must be > 0.90
    "energy_density_kWh_m3":     float -- [kWh/m³]; checked for plausibility
    "cycle_lifetime_cycles":     int   -- must be >= 10950
    "thermal_stress_MPa":        float -- [MPa]; must be > 0 (analysis required)
    "cost_per_kWh_usd":          float -- [USD/kWh]; must be < 20
    "total_salt_mass_kg":        float -- [kg]; must be > 0
    "charge_time_hr":            float -- [hr]; must be consistent with 50 MW charge power
    "discharge_time_hr":         float -- [hr]; must be ~10 hr at 100 MW discharge power
}

Scoring rubric (total = 100 points):
    Energy Density              (30 pts): kWh/m³ plausibility + salt mass consistency
    Charge/Discharge Efficiency (30 pts): round-trip efficiency + HX effectiveness
    Structural/Thermal Analysis (25 pts): thermal stress analysis + cycle life
    Cost Estimate               (15 pts): cost per kWh vs. $20/kWh target
"""

import argparse
import json
import sys

REQUIRED_FIELDS = [
    "technology_selected", "storage_medium", "hot_tank_volume_m3",
    "cold_tank_volume_m3", "tank_material", "insulation_thickness_m",
    "thermal_loss_rate_kW", "round_trip_efficiency_pct", "hx_area_m2",
    "hx_effectiveness", "energy_density_kWh_m3", "cycle_lifetime_cycles",
    "thermal_stress_MPa", "cost_per_kWh_usd", "total_salt_mass_kg",
    "charge_time_hr", "discharge_time_hr",
]

# Reference values for consistency checks
STORAGE_CAPACITY_MWH   = 1_000.0
DISCHARGE_POWER_MW     = 100.0
CHARGE_POWER_MW        = 50.0
SALT_CP                = 1_520.0   # J/(kg·K)
SALT_DENSITY           = 1_800.0   # kg/m³
DELTA_T                = 275.0     # K


def load_submission(path: str) -> tuple:
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
    return [f for f in REQUIRED_FIELDS if f not in data]


# ---------------------------------------------------------------------------
# Energy Density scoring (30 pts)
# ---------------------------------------------------------------------------

def score_energy_density(data: dict) -> tuple:
    max_score = 30
    score     = 0
    details   = {}
    errors    = []

    # Salt mass consistency (15 pts)
    # Expected: m = Q / (cp * delta_T)
    m_salt = data.get("total_salt_mass_kg", 0)
    m_expected = (STORAGE_CAPACITY_MWH * 3.6e9) / (SALT_CP * DELTA_T)   # ~8.608e6 kg
    if m_salt > 0:
        rel_err = abs(m_salt - m_expected) / m_expected
        if rel_err < 0.05:
            salt_pts = 15
        elif rel_err < 0.15:
            salt_pts = 10
        elif rel_err < 0.30:
            salt_pts = 5
        else:
            salt_pts = 0
            errors.append(f"Salt mass {m_salt:.2e} kg deviates {rel_err*100:.1f}% from expected {m_expected:.2e} kg.")
    else:
        salt_pts = 0
        errors.append("total_salt_mass_kg is zero or missing.")
    details["salt_mass_consistency"] = {
        "reported_kg": m_salt, "expected_kg": round(m_expected, 0),
        "relative_error_pct": round(abs(m_salt - m_expected) / m_expected * 100, 2) if m_salt > 0 else None,
        "points": salt_pts, "max": 15
    }
    score += salt_pts

    # Volumetric energy density plausibility (15 pts)
    # Solar Salt sensible storage: ~80–100 kWh/m³ typical
    ed = data.get("energy_density_kWh_m3", 0)
    if 60.0 <= ed <= 130.0:
        ed_pts = 15
    elif 40.0 <= ed < 60.0 or 130.0 < ed <= 170.0:
        ed_pts = 8
        errors.append(f"Energy density {ed:.1f} kWh/m³ is outside typical molten-salt range (60–130 kWh/m³).")
    else:
        ed_pts = 0
        errors.append(f"Energy density {ed:.1f} kWh/m³ is implausible for the selected technology.")
    details["energy_density_kWh_m3"] = {"value": ed, "points": ed_pts, "max": 15}
    score += ed_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Efficiency scoring (30 pts)
# ---------------------------------------------------------------------------

def score_efficiency(data: dict) -> tuple:
    max_score = 30
    score     = 0
    details   = {}
    errors    = []

    # Round-trip efficiency (20 pts)
    eta = data.get("round_trip_efficiency_pct", 0)
    if eta > 97.0:
        eta_pts = 20
    elif eta > 95.0:
        eta_pts = 16
    elif eta > 90.0:
        eta_pts = 8
        errors.append(f"Round-trip efficiency {eta:.1f}% is below the 95% target.")
    else:
        eta_pts = 0
        errors.append(f"Round-trip efficiency {eta:.1f}% is critically below 95% target.")
    details["round_trip_efficiency_pct"] = {"value": eta, "target": 95.0, "points": eta_pts, "max": 20}
    score += eta_pts

    # HX effectiveness (10 pts)
    hx_eff = data.get("hx_effectiveness", 0)
    if hx_eff >= 0.95:
        hx_pts = 10
    elif hx_eff >= 0.90:
        hx_pts = 7
    elif hx_eff >= 0.80:
        hx_pts = 3
        errors.append(f"HX effectiveness {hx_eff:.3f} is below the 0.90 target.")
    else:
        hx_pts = 0
        errors.append(f"HX effectiveness {hx_eff:.3f} is too low; redesign the heat exchanger.")
    details["hx_effectiveness"] = {"value": hx_eff, "target": 0.90, "points": hx_pts, "max": 10}
    score += hx_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Structural / Thermal Analysis scoring (25 pts)
# ---------------------------------------------------------------------------

def score_structural_thermal(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # Thermal stress analysis present and non-zero (10 pts)
    sigma = data.get("thermal_stress_MPa", -1)
    if sigma > 0:
        # Plausibility: sigma ~ E * alpha * delta_T / (2*(1-nu)) ~ 643 MPa (peak, no mitigation)
        # With proper slow ramp-up, effective sigma can be reduced significantly
        if sigma <= 700.0:
            stress_pts = 10
        else:
            stress_pts = 5
            errors.append(f"Thermal stress {sigma:.1f} MPa seems high; verify calculation or design mitigation.")
    else:
        stress_pts = 0
        errors.append("thermal_stress_MPa is missing or zero — thermal stress analysis required.")
    details["thermal_stress_MPa"] = {"value": sigma, "points": stress_pts, "max": 10}
    score += stress_pts

    # Cycle life >= design life (15 pts)
    N_cycles = data.get("cycle_lifetime_cycles", 0)
    if N_cycles >= 15_000:
        cyc_pts = 15
    elif N_cycles >= DESIGN_LIFE_CYCLES:   # 10,950
        cyc_pts = 10
    elif N_cycles >= 5_000:
        cyc_pts = 5
        errors.append(f"Cycle life {N_cycles:,} is below required {DESIGN_LIFE_CYCLES:,} cycles.")
    else:
        cyc_pts = 0
        errors.append(f"Cycle life {N_cycles:,} is critically insufficient; component will fail before design life.")
    details["cycle_lifetime_cycles"] = {
        "value": N_cycles, "required": DESIGN_LIFE_CYCLES, "points": cyc_pts, "max": 15
    }
    score += cyc_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Cost Estimate scoring (15 pts)
# ---------------------------------------------------------------------------

def score_cost(data: dict) -> tuple:
    max_score = 15
    score     = 0
    details   = {}
    errors    = []

    cost = data.get("cost_per_kWh_usd", 999)
    if cost <= 15.0:
        cost_pts = 15
    elif cost <= 20.0:
        cost_pts = 10
    elif cost <= 30.0:
        cost_pts = 5
        errors.append(f"Cost {cost:.2f} USD/kWh exceeds $20/kWh target.")
    else:
        cost_pts = 0
        errors.append(f"Cost {cost:.2f} USD/kWh is significantly over $20/kWh target.")
    details["cost_per_kWh_usd"] = {"value": cost, "target": 20.0, "points": cost_pts, "max": 15}
    score += cost_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ThermoCell TES design evaluator (MECH-P2)")
    parser.add_argument("--submission", required=True, help="Path to report.json")
    args = parser.parse_args()

    data, load_errors = load_submission(args.submission)
    if data is None:
        result = {"total": 0, "breakdown": {}, "errors": load_errors}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    missing = check_required_fields(data)
    if missing:
        # Deduct from final score but still evaluate what is present
        pass

    all_errors = list(load_errors)
    breakdown  = {}

    ed_score,   ed_max,   ed_det,   ed_err   = score_energy_density(data)
    eff_score,  eff_max,  eff_det,  eff_err  = score_efficiency(data)
    str_score,  str_max,  str_det,  str_err  = score_structural_thermal(data)
    cost_score, cost_max, cost_det, cost_err = score_cost(data)

    all_errors.extend(ed_err + eff_err + str_err + cost_err)
    if missing:
        all_errors.insert(0, f"Missing required fields: {missing}")

    # Penalise for missing fields (5 pts per missing field, capped at 20)
    missing_penalty = min(len(missing) * 5, 20)

    breakdown["energy_density"]             = {"score": ed_score,   "max": ed_max,   "details": ed_det}
    breakdown["charge_discharge_efficiency"]= {"score": eff_score,  "max": eff_max,  "details": eff_det}
    breakdown["structural_thermal_analysis"]= {"score": str_score,  "max": str_max,  "details": str_det}
    breakdown["cost_estimate"]              = {"score": cost_score, "max": cost_max, "details": cost_det}

    raw_total = ed_score + eff_score + str_score + cost_score
    total     = max(0, raw_total - missing_penalty)

    result = {
        "total":            total,
        "breakdown":        breakdown,
        "missing_penalty":  missing_penalty,
        "errors":           all_errors,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
