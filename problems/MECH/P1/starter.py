"""
AeroBot — VTOL UAV Airframe and Propulsion Design
MECH-P1 Starter Script

Run:
    python starter.py                      # outputs report.json in current directory
    python starter.py --output ./my_dir/   # outputs to specified directory

report.json schema (all fields required for evaluation):
{
    "configuration": str,
    "mtow_kg": float,
    "wing_area_m2": float,
    "aspect_ratio": float,
    "airfoil": str,
    "cruise_cl": float,
    "cruise_cd": float,
    "ld_ratio": float,
    "power_cruise_W": float,
    "battery_capacity_Wh": float,
    "endurance_hr": float,
    "range_km": float,
    "vtol_rotor_diameter_m": float,
    "vtol_disk_loading_kg_m2": float,
    "hover_power_W": float,
    "static_margin_percent": float,
    "wing_spar_safety_factor": float,
    "bom": [{"item": str, "mass_kg": float, "cost_usd": float}]
}
"""

import argparse
import json
import math
import os

import numpy as np

# ---------------------------------------------------------------------------
# Physical constants & atmospheric model (ISA sea level)
# ---------------------------------------------------------------------------
RHO_AIR = 1.225          # kg/m³  — air density at sea level
G       = 9.81           # m/s²   — gravitational acceleration

# ---------------------------------------------------------------------------
# Mission requirements (do not change — these are the problem constraints)
# ---------------------------------------------------------------------------
PAYLOAD_MASS_KG   = 2.0       # kg
CRUISE_SPEED_MS   = 20.0      # m/s
ENDURANCE_TARGET_HR = 2.0     # hours
RANGE_TARGET_KM   = 100.0     # km round trip
MAX_WIND_MS       = 10.0      # m/s
MTOW_LIMIT_KG     = 15.0      # kg

# ---------------------------------------------------------------------------
# Design choices (students should adjust these)
# ---------------------------------------------------------------------------
CONFIGURATION     = "quad-plane"   # quad-plane | tilt-rotor | tail-sitter | hybrid
AIRFOIL           = "NACA 4412"
CRUISE_CL         = 0.80           # lift coefficient at cruise — TODO: optimise
ASPECT_RATIO      = 9.0            # wing aspect ratio          — TODO: optimise
CD0               = 0.025          # zero-lift drag coefficient  — TODO: refine
OSWALD_E          = 0.80           # Oswald span efficiency      — TODO: refine
ETA_PROP          = 0.80           # propeller efficiency
ETA_MOTOR         = 0.90           # motor efficiency
BATTERY_SPEC_ENERGY_WH_KG = 200.0  # Wh/kg (LiPo 6S typical)
NUM_VTOL_ROTORS   = 4
VTOL_DISK_LOADING_KG_M2 = 12.0     # kg/m² — keep < 15 for efficiency

# ---------------------------------------------------------------------------
# Mass budget (kg) — must sum to <= MTOW_LIMIT_KG
# ---------------------------------------------------------------------------
MASS_BUDGET = {
    "payload":    2.0,
    "battery":    3.5,   # TODO: recalculate from energy requirement
    "structure":  3.5,
    "propulsion": 2.0,
    "avionics":   1.0,
}


# ---------------------------------------------------------------------------
# Aerodynamic calculations
# ---------------------------------------------------------------------------

def compute_mtow(mass_budget: dict) -> float:
    """Return total MTOW from mass budget dictionary (kg)."""
    return sum(mass_budget.values())


def compute_wing_area(mtow_kg: float, rho: float, v: float, cl: float) -> float:
    """
    Size wing area from steady-level-flight lift equation.
        L = W  =>  S = W / (0.5 * rho * V^2 * CL)

    Parameters
    ----------
    mtow_kg : total aircraft mass [kg]
    rho     : air density [kg/m³]
    v       : cruise speed [m/s]
    cl      : cruise lift coefficient [-]

    Returns
    -------
    S : wing reference area [m²]
    """
    # TODO: implement
    W = mtow_kg * G
    S = W / (0.5 * rho * v**2 * cl)
    return S


def compute_drag_polar(cl: float, cd0: float, ar: float, e: float) -> float:
    """
    Parabolic (low-speed) drag polar.
        CD = CD0 + CL^2 / (pi * AR * e)

    Returns CD (induced + parasitic).
    """
    # TODO: add compressibility correction if needed
    cd_induced = cl**2 / (math.pi * ar * e)
    return cd0 + cd_induced


def compute_ld_ratio(cl: float, cd: float) -> float:
    """Return lift-to-drag ratio."""
    return cl / cd


def compute_cruise_power(mtow_kg: float, ld_ratio: float, v: float,
                          eta_prop: float, eta_motor: float) -> float:
    """
    Electrical power required during cruise.
        P_shaft = (W / (L/D)) * V
        P_elec  = P_shaft / (eta_prop * eta_motor)

    Returns electrical power [W].
    """
    # TODO: add accessory power (avionics ~10 W)
    w = mtow_kg * G
    p_shaft = (w / ld_ratio) * v
    p_elec = p_shaft / (eta_prop * eta_motor)
    return p_elec


def compute_battery_capacity(power_cruise_W: float, endurance_hr: float,
                              hover_energy_Wh: float = 15.0) -> float:
    """
    Battery capacity = cruise energy + hover energy buffer.
    Add 10% reserve on top.

    Returns capacity [Wh].
    """
    # TODO: compute hover energy from hover power and assumed hover time (1 min pre + 1 min post)
    cruise_energy = power_cruise_W * endurance_hr
    total = (cruise_energy + hover_energy_Wh) * 1.10   # 10% reserve
    return total


def compute_endurance(battery_Wh: float, power_W: float) -> float:
    """Return endurance [hours] given battery capacity and cruise power."""
    return (battery_Wh * 0.90) / power_W   # 90% usable


def compute_range(endurance_hr: float, cruise_speed_ms: float) -> float:
    """Return range [km]."""
    return endurance_hr * cruise_speed_ms * 3.6   # 3.6 converts m/s*hr to km


# ---------------------------------------------------------------------------
# VTOL / hover calculations
# ---------------------------------------------------------------------------

def compute_vtol_rotor_diameter(mtow_kg: float, num_rotors: int,
                                 disk_loading: float) -> float:
    """
    From disk loading = W / (N * A_disk):
        A_disk = (W / N) / disk_loading
        D = 2 * sqrt(A_disk / pi)

    Returns rotor diameter [m].
    """
    # TODO: verify units consistency
    w_per_rotor = mtow_kg / num_rotors
    a_disk = w_per_rotor / disk_loading
    return 2.0 * math.sqrt(a_disk / math.pi)


def compute_hover_power(mtow_kg: float, num_rotors: int, rotor_diameter_m: float,
                         rho: float = RHO_AIR) -> float:
    """
    Actuator disk theory hover power:
        P = T * sqrt(T / (2 * rho * A))
    where T = W/N per rotor.

    Returns total electrical hover power [W] (assuming eta_motor = 0.85).
    """
    # TODO: add figure-of-merit correction (FM ~ 0.65–0.75 for small rotors)
    t_per_rotor = (mtow_kg * G) / num_rotors
    a_disk = math.pi * (rotor_diameter_m / 2.0)**2
    p_ideal = t_per_rotor * math.sqrt(t_per_rotor / (2.0 * rho * a_disk))
    p_total_ideal = p_ideal * num_rotors
    return p_total_ideal / 0.85   # electrical power


# ---------------------------------------------------------------------------
# Structural analysis — wing spar (simplified cantilever beam)
# ---------------------------------------------------------------------------

def compute_spar_safety_factor(mtow_kg: float, wing_area_m2: float,
                                aspect_ratio: float) -> float:
    """
    Simplified spar bending check.
    Model: elliptic lift distribution, root bending moment = (W/2) * (b/4).
    Assume CFRP circular tube: OD = 25 mm, t = 2 mm.
    Allowable bending stress = 400 MPa (conservative for CFRP).

    Returns safety factor SF = sigma_allow / sigma_actual.
    """
    # TODO: replace with proper FEA results or full hand-calc with load factor n=3.8
    span = math.sqrt(aspect_ratio * wing_area_m2)
    half_span = span / 2.0
    lift = mtow_kg * G * 3.8   # 3.8g load factor (FAA small UAV typical)
    M_root = (lift / 2.0) * (half_span / 2.0)   # simplified elliptic: centroid at b/4

    # CFRP tube section modulus  Z = pi*(OD^4 - ID^4) / (32 * OD)
    od = 0.025   # m
    t  = 0.002   # m
    id_ = od - 2 * t
    Z = math.pi * (od**4 - id_**4) / (32 * od)

    sigma_actual = M_root / Z
    sigma_allow  = 400e6   # Pa
    return sigma_allow / sigma_actual


# ---------------------------------------------------------------------------
# Stability — static margin (simplified)
# ---------------------------------------------------------------------------

def compute_static_margin(cg_fraction_mac: float = 0.28,
                           neutral_point_fraction_mac: float = 0.38) -> float:
    """
    Static margin = (x_NP - x_CG) / MAC  * 100 [%].
    Positive = stable.
    Target: 8–15%.

    Parameters
    ----------
    cg_fraction_mac : CG position as fraction of MAC from leading edge
    neutral_point_fraction_mac : aerodynamic neutral point as fraction of MAC
    """
    # TODO: compute NP from full tail contribution using tail volume coefficient
    sm = (neutral_point_fraction_mac - cg_fraction_mac) * 100.0
    return sm


# ---------------------------------------------------------------------------
# Bill of Materials (placeholder)
# ---------------------------------------------------------------------------

def build_bom(mass_budget: dict, battery_Wh: float) -> list:
    """Return a list of BOM line items as dicts."""
    # TODO: populate with actual component selections and market prices
    bom = [
        {"item": "Wing (CFRP + foam core)",       "mass_kg": mass_budget["structure"] * 0.45, "cost_usd": 120.0},
        {"item": "Fuselage (CFRP monocoque)",      "mass_kg": mass_budget["structure"] * 0.35, "cost_usd": 95.0},
        {"item": "Tail surfaces (CFRP)",           "mass_kg": mass_budget["structure"] * 0.20, "cost_usd": 45.0},
        {"item": "VTOL motors x4 (T-Motor MN4014)","mass_kg": mass_budget["propulsion"] * 0.40, "cost_usd": 240.0},
        {"item": "VTOL props x4 (15 inch folding)","mass_kg": mass_budget["propulsion"] * 0.10, "cost_usd": 60.0},
        {"item": "Cruise motor (T-Motor AT2826)",  "mass_kg": mass_budget["propulsion"] * 0.15, "cost_usd": 55.0},
        {"item": "Cruise prop (10x4.7 folding)",   "mass_kg": mass_budget["propulsion"] * 0.05, "cost_usd": 15.0},
        {"item": "ESC set (5x 40A)",               "mass_kg": mass_budget["propulsion"] * 0.30, "cost_usd": 120.0},
        {"item": f"LiPo battery ({battery_Wh:.0f} Wh)", "mass_kg": mass_budget["battery"], "cost_usd": 180.0},
        {"item": "Flight controller + GPS",        "mass_kg": mass_budget["avionics"] * 0.30, "cost_usd": 350.0},
        {"item": "Payload (camera + LiDAR + GPS)", "mass_kg": PAYLOAD_MASS_KG,                 "cost_usd": 1500.0},
    ]
    return bom


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AeroBot VTOL UAV design calculator")
    parser.add_argument("--output", default=".", help="Output directory for report.json")
    args = parser.parse_args()

    # --- mass budget ---
    mtow = compute_mtow(MASS_BUDGET)
    assert mtow <= MTOW_LIMIT_KG, f"MTOW {mtow:.2f} kg exceeds limit {MTOW_LIMIT_KG} kg!"

    # --- aerodynamics ---
    wing_area   = compute_wing_area(mtow, RHO_AIR, CRUISE_SPEED_MS, CRUISE_CL)
    cruise_cd   = compute_drag_polar(CRUISE_CL, CD0, ASPECT_RATIO, OSWALD_E)
    ld          = compute_ld_ratio(CRUISE_CL, cruise_cd)
    power_cruise = compute_cruise_power(mtow, ld, CRUISE_SPEED_MS, ETA_PROP, ETA_MOTOR)

    # --- VTOL ---
    rotor_diam  = compute_vtol_rotor_diameter(mtow, NUM_VTOL_ROTORS, VTOL_DISK_LOADING_KG_M2)
    hover_power = compute_hover_power(mtow, NUM_VTOL_ROTORS, rotor_diam)
    hover_energy_Wh = hover_power * (2.0 / 60.0)   # 2 min total hover budget

    # --- battery & performance ---
    batt_cap    = compute_battery_capacity(power_cruise, ENDURANCE_TARGET_HR, hover_energy_Wh)
    batt_mass   = batt_cap / BATTERY_SPEC_ENERGY_WH_KG
    # update budget with calculated battery mass
    MASS_BUDGET["battery"] = round(batt_mass, 3)
    mtow = compute_mtow(MASS_BUDGET)

    endurance   = compute_endurance(batt_cap, power_cruise)
    range_km    = compute_range(endurance, CRUISE_SPEED_MS)

    # --- structure & stability ---
    spar_sf     = compute_spar_safety_factor(mtow, wing_area, ASPECT_RATIO)
    sm          = compute_static_margin()

    # --- BOM ---
    bom = build_bom(MASS_BUDGET, batt_cap)

    report = {
        "configuration":          CONFIGURATION,
        "mtow_kg":                round(mtow, 3),
        "wing_area_m2":           round(wing_area, 4),
        "aspect_ratio":           ASPECT_RATIO,
        "airfoil":                AIRFOIL,
        "cruise_cl":              CRUISE_CL,
        "cruise_cd":              round(cruise_cd, 5),
        "ld_ratio":               round(ld, 2),
        "power_cruise_W":         round(power_cruise, 1),
        "battery_capacity_Wh":    round(batt_cap, 1),
        "endurance_hr":           round(endurance, 3),
        "range_km":               round(range_km, 2),
        "vtol_rotor_diameter_m":  round(rotor_diam, 3),
        "vtol_disk_loading_kg_m2": VTOL_DISK_LOADING_KG_M2,
        "hover_power_W":          round(hover_power, 1),
        "static_margin_percent":  round(sm, 2),
        "wing_spar_safety_factor": round(spar_sf, 2),
        "bom":                    bom,
    }

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, "report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"AeroBot report written to: {out_path}")
    print(f"  MTOW            : {mtow:.2f} kg  (limit {MTOW_LIMIT_KG} kg)")
    print(f"  Wing area       : {wing_area:.4f} m²   AR = {ASPECT_RATIO}")
    print(f"  L/D             : {ld:.2f}")
    print(f"  Cruise power    : {power_cruise:.1f} W")
    print(f"  Battery         : {batt_cap:.1f} Wh  ({batt_mass:.2f} kg)")
    print(f"  Endurance       : {endurance:.3f} hr  (target {ENDURANCE_TARGET_HR} hr)")
    print(f"  Range           : {range_km:.1f} km  (target {RANGE_TARGET_KM} km)")
    print(f"  Rotor diameter  : {rotor_diam:.3f} m  (disk loading {VTOL_DISK_LOADING_KG_M2} kg/m²)")
    print(f"  Hover power     : {hover_power:.1f} W")
    print(f"  Static margin   : {sm:.1f}%")
    print(f"  Spar SF         : {spar_sf:.2f}")


if __name__ == "__main__":
    main()
