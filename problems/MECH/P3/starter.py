"""
GearPro — Epicyclic Gear Train Design for Wind Turbine
MECH-P3 Starter Script

Run:
    python starter.py                      # outputs report.json in current directory
    python starter.py --output ./my_dir/   # outputs to specified directory

report.json schema (all fields required for evaluation):
{
    "overall_gear_ratio":   float -- computed from stage ratios; target ~100
    "ratio_error_pct":      float -- |computed - 100| / 100 * 100; must be < 1%
    "stage_ratios":         list[float] -- [i1, i2, i3]; product must equal overall_gear_ratio
    "stages": [
        {
            "stage":           int   -- 1, 2, or 3
            "sun_teeth":       int   -- Z_sun
            "planet_teeth":    int   -- Z_planet
            "ring_teeth":      int   -- Z_ring
            "module_mm":       float -- gear module [mm]
            "face_width_mm":   float -- tooth face width [mm]
            "num_planets":     int   -- number of planet gears
            "helix_angle_deg": float -- helix angle [deg]; 0 for spur
            "agma_bending_sf": float -- safety factor against bending; must be >= 1.2
            "agma_contact_sf": float -- safety factor against pitting; must be >= 1.2
        },
        ...
    ],
    "overall_efficiency_pct": float -- [%]; must be > 97
    "bearing_l10_life_hr":    float -- minimum L10 bearing life [hr]; must be > 175200
    "output_speed_rpm":       float -- generator speed [RPM]; must be in [1450, 1550]
    "input_torque_MNm":       float -- [MN·m]; must be ~3.2
    "agma_standard":          str   -- must be "AGMA 6006"
}
"""

import argparse
import json
import math
import os

# ---------------------------------------------------------------------------
# Problem requirements (do not change)
# ---------------------------------------------------------------------------
INPUT_SPEED_RPM     = 15.0          # RPM  rated rotor speed
INPUT_TORQUE_MNM    = 3.2           # MN·m rated rotor torque
OUTPUT_SPEED_TARGET = 1500.0        # RPM  generator speed
GEAR_RATIO_TARGET   = 100.0         # overall ratio (dimensionless)
DESIGN_LIFE_HR      = 175_200.0     # hours (20 years)
EFF_TARGET_PCT      = 97.0          # %
AGMA_STANDARD       = "AGMA 6006"

# ---------------------------------------------------------------------------
# Material properties — carburised and case-hardened 9310 steel
# ---------------------------------------------------------------------------
ST_MPA   = 380.0    # MPa  AGMA allowable bending stress number
SC_MPA   = 1550.0   # MPa  AGMA allowable contact stress number
E_GEAR   = 206e9    # Pa   Young's modulus

# AGMA application/dynamic factors (wind turbine, class 11 accuracy)
KO       = 1.75     # overload factor
KV       = 1.20     # dynamic factor
KS       = 1.05     # size factor
KM       = 1.30     # load distribution factor (planetary with 3 planets)
SF_BEND  = 1.56     # AGMA 6006 required bending safety factor (20-yr life)
SF_CONT  = 1.30     # AGMA 6006 required contact safety factor

# ---------------------------------------------------------------------------
# Stage design choices (students should iterate to find optimum)
# ---------------------------------------------------------------------------
# Each stage: (Z_sun, Z_planet, Z_ring, module_mm, face_width_mm, N_planets, helix_deg)
# Ratio check: i = 1 + Z_ring / Z_sun
# Assembly check: (Z_sun + Z_ring) % N_planets == 0

STAGE_DESIGNS = [
    # Stage 1: ratio 5:1  (highest torque — use large module)
    {"stage": 1, "sun_teeth": 18, "planet_teeth": 27, "ring_teeth": 72,
     "module_mm": 20.0, "face_width_mm": 200.0, "num_planets": 3, "helix_angle_deg": 15.0},
    # Stage 2: ratio 5:1  (medium torque — medium module)
    {"stage": 2, "sun_teeth": 20, "planet_teeth": 30, "ring_teeth": 80,
     "module_mm": 12.0, "face_width_mm": 140.0, "num_planets": 3, "helix_angle_deg": 15.0},
    # Stage 3: ratio 4:1  (lowest torque — smaller module)
    {"stage": 3, "sun_teeth": 24, "planet_teeth": 36, "ring_teeth": 96,
     "module_mm": 8.0,  "face_width_mm": 100.0, "num_planets": 4, "helix_angle_deg": 20.0},
]


# ---------------------------------------------------------------------------
# Gear geometry validation
# ---------------------------------------------------------------------------

def check_assembly_condition(Zs: int, Zr: int, N_planets: int) -> bool:
    """Assembly condition: (Z_sun + Z_ring) must be divisible by N_planets."""
    return (Zs + Zr) % N_planets == 0


def check_mesh_condition(Zs: int, Zp: int, Zr: int) -> bool:
    """Mesh condition: Z_ring = Z_sun + 2 * Z_planet."""
    return Zr == Zs + 2 * Zp


def stage_ratio(Zs: int, Zr: int) -> float:
    """Planetary ratio with fixed ring: i = 1 + Z_ring / Z_sun."""
    return 1.0 + Zr / Zs


# ---------------------------------------------------------------------------
# AGMA stress calculations (simplified, metric form)
# ---------------------------------------------------------------------------

def tangential_load(torque_Nm: float, pitch_diameter_m: float,
                     N_planets: int) -> float:
    """
    Tangential tooth load per planet mesh:
        W_t = 2 * T / (d * N_planets)

    Returns W_t [N].
    """
    # TODO: add helix factor for helical gears
    return (2.0 * torque_Nm) / (pitch_diameter_m * N_planets)


def agma_bending_stress(Wt: float, module_m: float, face_width_m: float,
                         J_factor: float = 0.36) -> float:
    """
    AGMA bending stress (simplified):
        sigma_b = W_t * Ko * Kv * Ks * Km / (b * m * J)

    Returns sigma_b [Pa].
    """
    # TODO: compute J from actual tooth geometry (Lewis form factor)
    return Wt * KO * KV * KS * KM / (face_width_m * module_m * J_factor)


def agma_contact_stress(Wt: float, pitch_diam_m: float, face_width_m: float,
                         Ze: float = 190.0e3) -> float:
    """
    AGMA contact (Hertz) stress (simplified):
        sigma_c = Ze * sqrt(W_t * Ko * Kv * Ks * Km / (d * b))
    Ze = 190,000 Pa^0.5 for steel-steel.

    Returns sigma_c [Pa].
    """
    # TODO: include geometry factor Zi and elastic coefficient properly
    return Ze * math.sqrt(Wt * KO * KV * KS * KM / (pitch_diam_m * face_width_m))


def safety_factor_bending(sigma_b_Pa: float) -> float:
    """SF_b = (St * Yn) / (sigma_b * KT * KR); simplified with Yn=1 (infinite life)."""
    # TODO: include stress cycle factor Yn and reliability factor KR
    return (ST_MPA * 1e6) / sigma_b_Pa


def safety_factor_contact(sigma_c_Pa: float) -> float:
    """SF_c = (Sc * Zn) / (sigma_c * KT * KR); simplified."""
    # TODO: include Zn (stress cycle factor for contact)
    return (SC_MPA * 1e6) / sigma_c_Pa


# ---------------------------------------------------------------------------
# Stage-by-stage analysis
# ---------------------------------------------------------------------------

def analyse_stage(stage_def: dict, input_torque_Nm: float) -> dict:
    """
    Full AGMA analysis for one planetary stage.
    Returns updated stage dict with safety factors added.
    """
    stage = dict(stage_def)
    Zs = stage["sun_teeth"]
    Zp = stage["planet_teeth"]
    Zr = stage["ring_teeth"]
    m  = stage["module_mm"] * 1e-3   # m
    b  = stage["face_width_mm"] * 1e-3   # m
    N  = stage["num_planets"]

    # Geometric validation
    stage["mesh_condition_ok"]     = check_mesh_condition(Zs, Zp, Zr)
    stage["assembly_condition_ok"] = check_assembly_condition(Zs, Zr, N)
    stage["stage_ratio"]           = round(stage_ratio(Zs, Zr), 4)

    # Sun gear pitch diameter and tangential load
    d_sun = Zs * m
    Wt    = tangential_load(input_torque_Nm, d_sun, N)

    # AGMA stresses
    sigma_b = agma_bending_stress(Wt, m, b)
    sigma_c = agma_contact_stress(Wt, d_sun, b)

    stage["agma_bending_sf"]  = round(safety_factor_bending(sigma_b),  3)
    stage["agma_contact_sf"]  = round(safety_factor_contact(sigma_c),  3)
    stage["sun_pitch_diam_mm"]= round(d_sun * 1000, 2)
    stage["tangential_load_kN"]= round(Wt / 1000, 2)

    return stage


# ---------------------------------------------------------------------------
# Efficiency model
# ---------------------------------------------------------------------------

def stage_mesh_efficiency(Zs: int, Zp: int, i: float, f: float = 0.05) -> float:
    """
    Approximate mesh efficiency for a planetary stage (Niemann formula):
        eta = 1 - f * pi * (1/Zs + 1/Zp) * (i - 1) / i
    f = 0.05 for mineral oil lubrication.
    """
    # TODO: add helical overlap factor
    return 1.0 - f * math.pi * (1.0 / Zs + 1.0 / Zp) * (i - 1.0) / i


def overall_efficiency(stages: list, eta_bearings: float = 0.995) -> float:
    """Return overall gearbox efficiency [%]."""
    eta = eta_bearings
    for s in stages:
        eta *= stage_mesh_efficiency(
            s["sun_teeth"], s["planet_teeth"], s["stage_ratio"]
        )
    return eta * 100.0


# ---------------------------------------------------------------------------
# Bearing life (ISO 281, simplified)
# ---------------------------------------------------------------------------

def bearing_l10_life(C_kN: float, P_kN: float, n_rpm: float,
                      p: float = 10.0 / 3.0) -> float:
    """
    L10 = (C/P)^p * 10^6 / (60 * n)    [hours]
    C = basic dynamic load rating [kN]
    P = equivalent dynamic bearing load [kN]
    p = 10/3 for roller bearings
    """
    # TODO: apply aISO life modification factor for lubrication and contamination
    return ((C_kN / P_kN) ** p) * 1e6 / (60.0 * n_rpm)


def estimate_bearing_life(stages: list, input_torque_Nm: float) -> float:
    """
    Simplified: size planet-pin roller bearings for Stage 1 (worst case).
    Assume C = 2000 kN (typical large cylindrical roller for wind turbine).
    P = W_t per planet.
    """
    # TODO: properly calculate planet speed and select from catalogue
    s1 = stages[0]
    m  = s1["module_mm"] * 1e-3
    Zs = s1["sun_teeth"]
    N  = s1["num_planets"]
    d_sun = Zs * m
    Wt_kN = tangential_load(input_torque_Nm, d_sun, N) / 1000.0

    # Planet carrier speed ≈ input speed / (1 + Zr/Zs)
    i1 = s1["stage_ratio"]
    n_planet_carrier = INPUT_SPEED_RPM / i1

    C_kN  = 2000.0   # [kN] assumed — TODO: select from catalogue based on d_pin
    return bearing_l10_life(C_kN, Wt_kN, n_planet_carrier)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="GearPro epicyclic gearbox design calculator")
    parser.add_argument("--output", default=".", help="Output directory for report.json")
    args = parser.parse_args()

    input_torque_Nm = INPUT_TORQUE_MNM * 1e6   # N·m

    # Analyse all stages
    torque = input_torque_Nm
    stage_ratios = []
    analysed_stages = []
    for sd in STAGE_DESIGNS:
        s = analyse_stage(sd, torque)
        analysed_stages.append(s)
        stage_ratios.append(s["stage_ratio"])
        torque /= s["stage_ratio"]   # torque reduces at each stage

    overall_ratio = 1.0
    for r in stage_ratios:
        overall_ratio *= r

    ratio_error_pct = abs(overall_ratio - GEAR_RATIO_TARGET) / GEAR_RATIO_TARGET * 100.0
    output_speed    = INPUT_SPEED_RPM * overall_ratio
    eta_pct         = overall_efficiency(analysed_stages)
    l10_hr          = estimate_bearing_life(analysed_stages, input_torque_Nm)

    # Clean up internal fields for JSON output
    output_stages = []
    for s in analysed_stages:
        output_stages.append({
            "stage":           s["stage"],
            "sun_teeth":       s["sun_teeth"],
            "planet_teeth":    s["planet_teeth"],
            "ring_teeth":      s["ring_teeth"],
            "module_mm":       s["module_mm"],
            "face_width_mm":   s["face_width_mm"],
            "num_planets":     s["num_planets"],
            "helix_angle_deg": s["helix_angle_deg"],
            "agma_bending_sf": s["agma_bending_sf"],
            "agma_contact_sf": s["agma_contact_sf"],
            "mesh_condition_ok":     s["mesh_condition_ok"],
            "assembly_condition_ok": s["assembly_condition_ok"],
        })

    report = {
        "overall_gear_ratio":    round(overall_ratio, 4),
        "ratio_error_pct":       round(ratio_error_pct, 3),
        "stage_ratios":          [round(r, 4) for r in stage_ratios],
        "stages":                output_stages,
        "overall_efficiency_pct": round(eta_pct, 3),
        "bearing_l10_life_hr":   round(l10_hr, 0),
        "output_speed_rpm":      round(output_speed, 2),
        "input_torque_MNm":      INPUT_TORQUE_MNM,
        "agma_standard":         AGMA_STANDARD,
    }

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, "report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"GearPro report written to: {out_path}")
    print(f"  Overall ratio    : {overall_ratio:.4f}  (target 100, error {ratio_error_pct:.3f}%)")
    print(f"  Output speed     : {output_speed:.1f} RPM  (target {OUTPUT_SPEED_TARGET})")
    print(f"  Efficiency       : {eta_pct:.3f}%  (target >{EFF_TARGET_PCT}%)")
    print(f"  Bearing L10 life : {l10_hr:,.0f} hr  (design life {DESIGN_LIFE_HR:,.0f} hr)")
    for s in analysed_stages:
        print(f"  Stage {s['stage']}: ratio {s['stage_ratio']:.2f}  "
              f"SF_b={s['agma_bending_sf']:.2f}  SF_c={s['agma_contact_sf']:.2f}  "
              f"assem_ok={s['assembly_condition_ok']}  mesh_ok={s['mesh_condition_ok']}")


if __name__ == "__main__":
    main()
