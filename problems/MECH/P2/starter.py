"""
ThermoCell — High-Temperature Thermal Energy Storage Design
MECH-P2 Starter Script

Run:
    python starter.py                      # outputs report.json in current directory
    python starter.py --output ./my_dir/   # outputs to specified directory

report.json schema (all fields required for evaluation):
{
    "technology_selected":       str   -- "molten_salt" | "PCM" | "thermochemical"
    "storage_medium":            str   -- e.g. "Solar Salt (60% NaNO3 + 40% KNO3)"
    "hot_tank_volume_m3":        float -- hot-side tank total volume [m³]
    "cold_tank_volume_m3":       float -- cold-side tank total volume [m³]
    "tank_material":             str   -- e.g. "304 Stainless Steel"
    "insulation_thickness_m":    float -- insulation wall thickness [m]
    "thermal_loss_rate_kW":      float -- steady-state combined heat loss both tanks [kW]
    "round_trip_efficiency_pct": float -- end-to-end round-trip efficiency [%]; target > 95
    "hx_area_m2":                float -- total heat exchanger surface area [m²]
    "hx_effectiveness":          float -- heat exchanger effectiveness [-]; target > 0.90
    "energy_density_kWh_m3":     float -- volumetric energy density [kWh/m³]
    "cycle_lifetime_cycles":     int   -- fatigue life in cycles; must be >= 10950
    "thermal_stress_MPa":        float -- peak cyclic thermal stress in tank shell [MPa]
    "cost_per_kWh_usd":          float -- capital cost per kWh stored [USD/kWh]; target < 20
    "total_salt_mass_kg":        float -- mass of storage medium [kg]
    "charge_time_hr":            float -- time to fully charge at rated charge power [hr]
    "discharge_time_hr":         float -- time to fully discharge at rated power [hr]
}
"""

import argparse
import json
import math
import os

# ---------------------------------------------------------------------------
# Problem requirements (do not change)
# ---------------------------------------------------------------------------
STORAGE_CAPACITY_MWH   = 1_000.0    # MWh thermal
DISCHARGE_POWER_MW     = 100.0      # MW thermal
CHARGE_POWER_MW        = 50.0       # MW thermal
T_HOT_C                = 565.0      # °C hot tank temperature
T_COLD_C               = 290.0      # °C cold tank temperature
T_AMBIENT_C            = 20.0       # °C ambient
DESIGN_LIFE_CYCLES     = 10_950     # cycles (30 years × 365 cycles/yr)
COST_TARGET_USD_KWH    = 20.0       # USD/kWh
ROUNDTRIP_EFF_TARGET   = 95.0       # %

# ---------------------------------------------------------------------------
# Solar Salt properties (60% NaNO3 + 40% KNO3)
# ---------------------------------------------------------------------------
SALT_CP_J_KG_K    = 1_520.0   # J/(kg·K) specific heat capacity
SALT_DENSITY_KG_M3 = 1_800.0  # kg/m³  at average temperature
SALT_SOLID_TEMP_C  = 238.0    # °C  freezing point — must stay above this!

# Tank material properties (304 SS at 565°C)
SHELL_E_PA          = 193e9    # Pa  Young's modulus
SHELL_ALPHA         = 17.2e-6  # /K  thermal expansion coefficient
SHELL_NU            = 0.29     # Poisson ratio
SHELL_SY_PA         = 205e6    # Pa  yield strength at 565°C

# Insulation (mineral wool)
INSULATION_K_W_MK   = 0.04    # W/(m·K)
INSULATION_THICK_M  = 0.50    # m   — TODO: optimise for cost vs. heat loss

# Heat exchanger parameters
HX_U_W_M2_K         = 800.0   # W/(m²·K) overall heat transfer coefficient (shell-and-tube)
HX_LMTD_K           = 50.0    # K  log-mean temperature difference   — TODO: calculate properly

# Cost parameters
SALT_COST_USD_KG     = 1.0     # USD/kg
TANK_COST_USD_M2     = 200.0   # USD/m² of tank surface (fabricated)
HX_COST_USD_M2       = 500.0   # USD/m² of heat exchanger surface

# ---------------------------------------------------------------------------
# Technology selection
# ---------------------------------------------------------------------------
TECHNOLOGY       = "molten_salt"
STORAGE_MEDIUM   = "Solar Salt (60% NaNO3 + 40% KNO3)"
TANK_MATERIAL    = "304 Stainless Steel"


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def compute_salt_mass(capacity_MWh: float, cp: float, delta_T: float) -> float:
    """
    Mass of storage medium from sensible heat equation:
        Q = m * cp * delta_T
        m = Q / (cp * delta_T)

    Parameters
    ----------
    capacity_MWh : storage capacity [MWh]
    cp           : specific heat capacity [J/(kg·K)]
    delta_T      : temperature swing [K]

    Returns
    -------
    m : salt mass [kg]
    """
    # TODO: verify unit conversion (MWh -> J)
    Q_joules = capacity_MWh * 3.6e9   # 1 MWh = 3.6e9 J
    return Q_joules / (cp * delta_T)


def compute_tank_volume(salt_mass_kg: float, density: float,
                         ullage_fraction: float = 0.10) -> float:
    """
    Tank volume = salt volume + ullage.
    Two equal tanks (hot + cold), so each holds half the salt.

    Returns volume per tank [m³].
    """
    # TODO: add pump-out volume and minimum heel
    V_salt_total = salt_mass_kg / density
    V_per_tank   = (V_salt_total / 2.0) * (1.0 + ullage_fraction)
    return V_per_tank


def compute_tank_dimensions(volume_m3: float, h_to_d_ratio: float = 1.0) -> tuple:
    """
    Cylindrical tank dimensions from volume and H/D ratio.
        V = pi/4 * D^2 * H  and  H = h_to_d_ratio * D
        => D = (4*V / (pi * h_to_d_ratio))^(1/3)

    Returns (diameter_m, height_m).
    """
    # TODO: check for practical limits (D < 20 m for standard construction)
    D = (4.0 * volume_m3 / (math.pi * h_to_d_ratio)) ** (1.0 / 3.0)
    H = h_to_d_ratio * D
    return D, H


def compute_tank_surface_area(D: float, H: float) -> float:
    """External surface area of a closed cylinder [m²]."""
    return math.pi * D * H + 2.0 * math.pi * (D / 2.0)**2


def compute_thermal_loss(surface_area_m2: float, T_tank_C: float,
                          T_amb_C: float, k: float, thickness: float) -> float:
    """
    Steady-state conduction loss through flat insulation (conservative — ignores curvature):
        Q_loss = k * A * (T_inner - T_outer) / thickness

    Returns heat loss rate [W].
    """
    # TODO: add convection and radiation on outer surface; model as thermal resistance network
    return k * surface_area_m2 * (T_tank_C - T_amb_C) / thickness


def compute_roundtrip_efficiency(thermal_loss_both_tanks_W: float,
                                  discharge_time_hr: float,
                                  capacity_Wh: float,
                                  eta_hx_charge: float = 0.98,
                                  eta_hx_discharge: float = 0.98,
                                  eta_parasitic: float = 0.985) -> float:
    """
    Round-trip efficiency accounting for:
    - Heat exchanger effectiveness losses (charge and discharge)
    - Thermal standby losses during storage
    - Parasitic pump/auxiliary power

    Returns eta_rt [%].
    """
    # TODO: add transient startup losses
    standby_loss_Wh = thermal_loss_both_tanks_W * discharge_time_hr
    thermal_eff = (capacity_Wh - standby_loss_Wh) / capacity_Wh
    eta_rt = eta_hx_charge * thermal_eff * eta_hx_discharge * eta_parasitic * 100.0
    return eta_rt


def compute_hx_area(heat_transfer_W: float, U: float, LMTD: float) -> float:
    """
    Heat exchanger area from Q = U * A * LMTD.
    Use discharge power (largest duty).

    Returns A [m²].
    """
    # TODO: compute LMTD from actual hot/cold fluid temperatures
    return heat_transfer_W / (U * LMTD)


def compute_hx_effectiveness(NTU: float, Cr: float = 0.5) -> float:
    """
    NTU-effectiveness for a counter-flow heat exchanger:
        eps = (1 - exp(-NTU*(1-Cr))) / (1 - Cr*exp(-NTU*(1-Cr)))

    Parameters
    ----------
    NTU : number of transfer units = U*A/C_min
    Cr  : heat capacity ratio C_min/C_max
    """
    # TODO: calculate C_min from actual mass flow rates and cp
    if Cr < 1.0:
        eps = (1.0 - math.exp(-NTU * (1.0 - Cr))) / (1.0 - Cr * math.exp(-NTU * (1.0 - Cr)))
    else:
        eps = NTU / (1.0 + NTU)
    return eps


def compute_thermal_stress(E: float, alpha: float, delta_T: float, nu: float) -> float:
    """
    Biaxial thermal stress in a thin-walled vessel due to temperature change:
        sigma = E * alpha * delta_T / (2 * (1 - nu))

    Returns stress [Pa].
    """
    # TODO: this is a simplified estimate — perform detailed FEA for final design
    return E * alpha * delta_T / (2.0 * (1.0 - nu))


def estimate_cycle_life(sigma_range_Pa: float, S_y_Pa: float) -> int:
    """
    Simplified low-cycle fatigue life via Coffin-Manson (elastic-dominated):
        N_f ~ (S_y / sigma_range)^(1/0.12)
    Returns estimated cycle life (integer).

    NOTE: This is a placeholder — real LCF requires material S-N data at temperature.
    """
    # TODO: use actual Coffin-Manson constants from ASME VIII Div. 2 fatigue curves
    if sigma_range_Pa <= 0:
        return 999_999
    ratio = S_y_Pa / sigma_range_Pa
    if ratio >= 1.0:
        Nf = int(ratio ** (1.0 / 0.12))
    else:
        Nf = int(ratio ** (1.0 / 0.12))
    return min(Nf, 999_999)


def compute_cost(salt_mass_kg: float, tank_surface_m2_each: float,
                 hx_area_m2: float, capacity_MWh: float) -> float:
    """
    Simplified capital cost estimate [USD/kWh].
    Components: salt + tanks (2) + heat exchangers (2: charge + discharge).
    """
    # TODO: add civil works, piping, controls, contingency (~30%)
    salt_cost  = salt_mass_kg * SALT_COST_USD_KG
    tank_cost  = 2.0 * tank_surface_m2_each * TANK_COST_USD_M2
    hx_cost    = 2.0 * hx_area_m2 * HX_COST_USD_M2   # charge + discharge HX
    total_cost = (salt_cost + tank_cost + hx_cost) * 1.30   # 30% balance-of-plant
    return total_cost / (capacity_MWh * 1000.0)   # USD/kWh


def compute_energy_density(capacity_MWh: float, total_tank_volume_m3: float) -> float:
    """Return volumetric energy density [kWh/m³]."""
    return (capacity_MWh * 1000.0) / total_tank_volume_m3


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ThermoCell TES system design calculator")
    parser.add_argument("--output", default=".", help="Output directory for report.json")
    args = parser.parse_args()

    delta_T = T_HOT_C - T_COLD_C   # 275 K

    # --- salt mass ---
    m_salt = compute_salt_mass(STORAGE_CAPACITY_MWH, SALT_CP_J_KG_K, delta_T)

    # --- tank sizing ---
    V_per_tank  = compute_tank_volume(m_salt, SALT_DENSITY_KG_M3)
    D, H        = compute_tank_dimensions(V_per_tank)
    SA_per_tank = compute_tank_surface_area(D, H)

    # --- thermal losses ---
    Q_loss_hot_W  = compute_thermal_loss(SA_per_tank, T_HOT_C,  T_AMBIENT_C,
                                          INSULATION_K_W_MK, INSULATION_THICK_M)
    Q_loss_cold_W = compute_thermal_loss(SA_per_tank, T_COLD_C, T_AMBIENT_C,
                                          INSULATION_K_W_MK, INSULATION_THICK_M)
    Q_loss_total_W = Q_loss_hot_W + Q_loss_cold_W
    Q_loss_total_kW = Q_loss_total_W / 1000.0

    # --- charge/discharge times ---
    charge_time_hr    = STORAGE_CAPACITY_MWH / CHARGE_POWER_MW
    discharge_time_hr = STORAGE_CAPACITY_MWH / DISCHARGE_POWER_MW

    # --- round-trip efficiency ---
    eta_rt = compute_roundtrip_efficiency(
        Q_loss_total_W, discharge_time_hr,
        STORAGE_CAPACITY_MWH * 1e6    # Wh
    )

    # --- heat exchanger ---
    hx_area     = compute_hx_area(DISCHARGE_POWER_MW * 1e6, HX_U_W_M2_K, HX_LMTD_K)
    NTU         = HX_U_W_M2_K * hx_area / (DISCHARGE_POWER_MW * 1e6 / HX_LMTD_K)
    hx_eff      = compute_hx_effectiveness(NTU)

    # --- structural analysis ---
    sigma_Pa    = compute_thermal_stress(SHELL_E_PA, SHELL_ALPHA, delta_T, SHELL_NU)
    sigma_MPa   = sigma_Pa / 1e6
    N_cycles    = estimate_cycle_life(sigma_Pa, SHELL_SY_PA)

    # --- energy density ---
    total_vol   = 2.0 * V_per_tank
    energy_dens = compute_energy_density(STORAGE_CAPACITY_MWH, total_vol)

    # --- cost ---
    cost_kwh    = compute_cost(m_salt, SA_per_tank, hx_area, STORAGE_CAPACITY_MWH)

    report = {
        "technology_selected":       TECHNOLOGY,
        "storage_medium":            STORAGE_MEDIUM,
        "hot_tank_volume_m3":        round(V_per_tank, 1),
        "cold_tank_volume_m3":       round(V_per_tank, 1),
        "tank_material":             TANK_MATERIAL,
        "insulation_thickness_m":    INSULATION_THICK_M,
        "thermal_loss_rate_kW":      round(Q_loss_total_kW, 2),
        "round_trip_efficiency_pct": round(eta_rt, 2),
        "hx_area_m2":                round(hx_area, 1),
        "hx_effectiveness":          round(hx_eff, 4),
        "energy_density_kWh_m3":     round(energy_dens, 2),
        "cycle_lifetime_cycles":     N_cycles,
        "thermal_stress_MPa":        round(sigma_MPa, 1),
        "cost_per_kWh_usd":          round(cost_kwh, 2),
        "total_salt_mass_kg":        round(m_salt, 0),
        "charge_time_hr":            round(charge_time_hr, 2),
        "discharge_time_hr":         round(discharge_time_hr, 2),
    }

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, "report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"ThermoCell report written to: {out_path}")
    print(f"  Salt mass          : {m_salt/1e6:.3f} million kg")
    print(f"  Tank volume each   : {V_per_tank:.1f} m³  (D={D:.2f} m, H={H:.2f} m)")
    print(f"  Thermal loss       : {Q_loss_total_kW:.2f} kW")
    print(f"  Round-trip eff.    : {eta_rt:.2f}%  (target >95%)")
    print(f"  HX area            : {hx_area:.1f} m²   effectiveness {hx_eff:.3f}")
    print(f"  Thermal stress     : {sigma_MPa:.1f} MPa  (S_y = {SHELL_SY_PA/1e6:.0f} MPa)")
    print(f"  Cycle life         : {N_cycles:,} cycles  (target {DESIGN_LIFE_CYCLES:,})")
    print(f"  Energy density     : {energy_dens:.2f} kWh/m³")
    print(f"  Cost               : ${cost_kwh:.2f}/kWh  (target <${COST_TARGET_USD_KWH})")


if __name__ == "__main__":
    main()
