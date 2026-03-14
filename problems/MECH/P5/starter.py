"""
HyperCool — Two-Phase Cooling System for Data Center Servers
MECH-P5 Starter Script

Run:
    python starter.py                      # outputs report.json in current directory
    python starter.py --output ./my_dir/   # outputs to specified directory

report.json schema (all fields required for evaluation):
{
    "coolant_selected":              str   -- "water" | "novec_7100" | "R134a" | other
    "cooling_technology":            str   -- "microchannel_cold_plate" | "immersion" | "heat_pipe"
    "chip_heat_flux_W_cm2":          float -- heat flux [W/cm²]; problem spec is 100
    "die_area_cm2":                  float -- chip die area [cm²]
    "q_total_kW":                    float -- total rack heat load [kW]; must be ~50
    "evaporator_channel_width_um":   float -- microchannel width [μm]
    "evaporator_channel_height_um":  float -- microchannel height [μm]
    "evaporator_htc_W_m2K":          float -- flow boiling HTC [W/(m²·K)]; target > 20000
    "evaporator_pressure_drop_kPa":  float -- two-phase pressure drop per cold plate [kPa]
    "condenser_area_m2":             float -- total condenser surface area [m²]
    "condenser_type":                str   -- "air" | "liquid"
    "thermal_resistance_total_K_W":  float -- junction-to-saturation thermal resistance [K/W]
    "junction_temp_C":               float -- predicted junction temperature [°C]; must be < 85
    "saturation_temp_C":             float -- coolant saturation temperature [°C]
    "critical_heat_flux_W_cm2":      float -- CHF at design conditions [W/cm²]
    "chf_safety_factor":             float -- CHF / chip heat flux; must be >= 1.5
    "pump_power_W":                  float -- total pump electrical power [W]
    "system_cop":                    float -- COP = Q_total / W_pump
}
"""

import argparse
import json
import math
import os

import numpy as np

# ---------------------------------------------------------------------------
# Problem requirements (do not change)
# ---------------------------------------------------------------------------
Q_CHIP_W_CM2       = 100.0      # W/cm²  chip heat flux
Q_RACK_KW          = 50.0       # kW     total rack heat load
N_SERVERS          = 10         # servers per rack
N_CHIPS_PER_SERVER = 2          # GPUs/CPUs per server (assumed)
TJ_LIMIT_C         = 85.0       # °C     junction temperature limit
T_AMBIENT_C        = 40.0       # °C     worst-case ambient (also coolant inlet)
T_INLET_C          = 25.0       # °C     nominal coolant inlet

# ---------------------------------------------------------------------------
# Coolant selection and properties — Novec 7100 at saturation (61°C, 1 atm)
# ---------------------------------------------------------------------------
COOLANT             = "novec_7100"
COOLING_TECH        = "microchannel_cold_plate"
T_SAT_C             = 61.0      # °C  saturation temperature at 1 atm

# Novec 7100 liquid properties at ~61°C
RHO_L_KG_M3        = 1390.0    # kg/m³
RHO_V_KG_M3        = 9.9       # kg/m³
MU_L_PA_S          = 3.0e-4    # Pa·s dynamic viscosity
K_L_W_MK            = 0.069    # W/(m·K) thermal conductivity
H_FG_J_KG          = 111_600.0 # J/kg  latent heat of vaporisation
CP_L_J_KG_K        = 1,183.0   # J/(kg·K)  liquid specific heat (unused in 2-phase region)
PR_L               = 5.15      # Prandtl number (liquid)
SIGMA_N_M          = 0.0095    # N/m   surface tension

# Die / cold plate geometry
DIE_AREA_CM2       = 1.0       # cm²   chip die area (10 mm × 10 mm)
COLD_PLATE_L_M     = 0.010     # m     channel length (= die dimension)

# Microchannel geometry (per chip)
CH_WIDTH_UM        = 200.0     # μm    channel width
CH_HEIGHT_UM       = 500.0     # μm    channel height
FIN_WIDTH_UM       = 100.0     # μm    fin (wall) width

# Two-phase exit quality target
X_EXIT             = 0.30      # [-]   vapour quality at evaporator exit

# Pump efficiency
ETA_PUMP           = 0.50      # [-]


# ---------------------------------------------------------------------------
# Derived geometry
# ---------------------------------------------------------------------------

def microchannel_geometry(ch_width_um: float, ch_height_um: float,
                           fin_width_um: float, die_width_mm: float = 10.0) -> dict:
    """
    Compute number of channels, hydraulic diameter, flow area.

    Returns dict with geometry parameters.
    """
    # TODO: add fin efficiency calculation for wetted area
    w = ch_width_um * 1e-6   # m
    h = ch_height_um * 1e-6  # m
    t = fin_width_um * 1e-6  # m
    pitch = w + t             # m per channel
    N_ch = int((die_width_mm * 1e-3) / pitch)

    D_h = 2.0 * w * h / (w + h)    # hydraulic diameter [m]
    A_flow = N_ch * w * h            # total flow area per cold plate [m²]
    A_base = (die_width_mm * 1e-3) ** 2   # base area [m²]

    return {
        "N_channels":   N_ch,
        "D_h_m":        D_h,
        "A_flow_m2":    A_flow,
        "A_base_m2":    A_base,
        "A_wetted_m2":  N_ch * 2.0 * (w + h) * COLD_PLATE_L_M,  # approx
    }


# ---------------------------------------------------------------------------
# Single-phase HTC (Dittus-Boelter)
# ---------------------------------------------------------------------------

def single_phase_htc(G: float, D_h: float, k_l: float, mu_l: float,
                      Pr: float) -> float:
    """
    Dittus-Boelter for turbulent internal flow:
        h = 0.023 * Re^0.8 * Pr^0.4 * k / D_h

    Returns h [W/(m²·K)].
    """
    Re = G * D_h / mu_l
    if Re < 2300:
        # Laminar: Nu = 4.36 (uniform heat flux, fully developed)
        Nu = 4.36
    else:
        Nu = 0.023 * Re**0.8 * Pr**0.4
    return Nu * k_l / D_h


# ---------------------------------------------------------------------------
# Two-phase HTC (simplified enhancement factor approach)
# ---------------------------------------------------------------------------

def two_phase_htc(h_lo: float, G: float, x: float, D_h: float,
                   rho_l: float, rho_v: float, h_fg: float,
                   q_flux_W_m2: float) -> float:
    """
    Simplified two-phase HTC using Chen correlation (convective + nucleate boiling):
        h_tp = h_conv + h_nb
    where:
        h_conv = F * h_lo    (F: enhancement factor, 1–100)
        h_nb   = S * h_pool  (S: suppression factor, 0–1)

    For quick estimate: h_tp ≈ F * h_lo with F based on Martinelli parameter.
    """
    # TODO: implement full Chen/Kandlikar correlation
    if x <= 0:
        return h_lo

    # Martinelli parameter
    X_tt = ((1 - x) / x) ** 0.9 * (rho_v / rho_l) ** 0.5 * (1.0) ** 0.1  # mu ratio ~1
    # Enhancement factor (Dittus-Boelter turbulent liquid only)
    F = max(1.0, (1.0 + 1.0 / X_tt) ** 0.736)
    h_conv = F * h_lo

    # Nucleate boiling contribution (simplified Forster-Zuber)
    # TODO: replace with accurate pool boiling correlation for Novec 7100
    delta_T_sat = q_flux_W_m2 / (h_conv + 1e-12)   # initial estimate
    h_nb_approx = 0.00122 * (k_l**0.79 / (h_fg * rho_v) ** 0.24) * delta_T_sat * 1e3
    S = 1.0 / (1.0 + 2.56e-6 * (Re_tp := G * D_h / MU_L_PA_S * F) ** 1.17)

    return h_conv + S * max(0, h_nb_approx)


# ---------------------------------------------------------------------------
# Critical Heat Flux (CHF) — Katto-Ohno simplified
# ---------------------------------------------------------------------------

def critical_heat_flux(G: float, D_h: float, L: float,
                        h_fg: float, rho_l: float, rho_v: float) -> float:
    """
    Katto-Ohno CHF correlation (simplified form):
        q_CHF = C * (rho_v/rho_l)^0.043 * h_fg * G * (L/D_h)^(-0.54)
    C ≈ 0.25 for rectangular microchannels.

    Returns q_CHF [W/m²].
    """
    # TODO: use geometry-specific CHF correlation; this is conservative
    C = 0.25
    return C * (rho_v / rho_l) ** 0.043 * h_fg * G * (L / D_h) ** (-0.54)


# ---------------------------------------------------------------------------
# Pressure drop (two-phase, simplified Homogeneous model)
# ---------------------------------------------------------------------------

def pressure_drop_two_phase(G: float, D_h: float, L: float,
                              x_exit: float, rho_l: float, rho_v: float,
                              mu_l: float) -> float:
    """
    Two-phase pressure drop using homogeneous mixture model:
        delta_P = f_tp * (L/D_h) * G^2 / (2 * rho_m)
    where rho_m = 1 / (x/rho_v + (1-x)/rho_l)  and  f_tp = 64/Re_m (laminar)

    Returns pressure drop [Pa].
    """
    # TODO: use Lockhart-Martinelli or Friedel correlation for better accuracy
    x_avg = x_exit / 2.0
    rho_m = 1.0 / (x_avg / rho_v + (1.0 - x_avg) / rho_l)
    mu_m  = mu_l * (1.0 - x_avg) + (mu_l * rho_v / rho_l) * x_avg
    Re_m  = G * D_h / mu_m
    f     = 64.0 / Re_m if Re_m < 2300 else 0.316 * Re_m ** (-0.25)
    return f * (L / D_h) * G**2 / (2.0 * rho_m)


# ---------------------------------------------------------------------------
# Thermal resistance network
# ---------------------------------------------------------------------------

def thermal_resistance_total(h_tp: float, A_base: float,
                               R_jc: float = 0.008, R_TIM: float = 0.004,
                               R_spreading: float = 0.004) -> float:
    """
    Total thermal resistance from junction to saturation:
        R_total = R_jc + R_TIM + R_spreading + R_conv
    R_conv = 1 / (h_tp * A_base)

    Returns R_total [K/W].
    """
    # TODO: add R_spreading using Spreading resistance model (cylindrical source)
    R_conv = 1.0 / (h_tp * A_base)
    return R_jc + R_TIM + R_spreading + R_conv


# ---------------------------------------------------------------------------
# Condenser sizing (air-cooled, worst-case 40°C ambient)
# ---------------------------------------------------------------------------

def condenser_area(Q_total_W: float, T_sat_C: float, T_amb_C: float,
                    U_condenser: float = 50.0) -> float:
    """
    Required condenser area:
        A = Q / (U * LMTD)
    U = 50 W/(m²·K) for forced-air condenser.
    LMTD ≈ (T_sat - T_amb)  (steam-to-air condensation)

    Returns A [m²].
    """
    # TODO: compute actual LMTD from condenser inlet/outlet temperatures
    LMTD = T_sat_C - T_amb_C
    if LMTD <= 0:
        return float('inf')
    return Q_total_W / (U_condenser * LMTD)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HyperCool two-phase cooling system calculator")
    parser.add_argument("--output", default=".", help="Output directory for report.json")
    args = parser.parse_args()

    # Chip power
    Q_chip_W   = Q_CHIP_W_CM2 * DIE_AREA_CM2 * 1e4 * 1e-4 * 1e4   # 100 W/cm² * 1 cm² = wait...
    # Correct: Q_chip = 100 W/cm² * 1 cm² * (1 W / 1 W/cm² * 1 cm²) = 100 W
    # But problem says 500W per chip — re-read: "500W/chip" in problem header; die area 5 cm²
    # Use problem spec values from MECH-P5 header  (500 W/chip, die area = 5 cm²)
    Q_CHIP_W_ACTUAL = 500.0          # W  per chip (problem spec)
    DIE_AREA_ACTUAL = 5.0 * 1e-4     # m²  (5 cm²)
    Q_CHIP_FLUX_W_M2 = Q_CHIP_W_ACTUAL / DIE_AREA_ACTUAL   # W/m²

    # Geometry
    geo = microchannel_geometry(CH_WIDTH_UM, CH_HEIGHT_UM, FIN_WIDTH_UM,
                                 die_width_mm=math.sqrt(DIE_AREA_ACTUAL * 1e4) * 10)

    # Mass flow per chip
    m_dot = Q_CHIP_W_ACTUAL / (H_FG_J_KG * X_EXIT)   # kg/s
    G     = m_dot / geo["A_flow_m2"]                  # kg/(m²·s)

    # HTC
    h_lo = single_phase_htc(G, geo["D_h_m"], K_L_W_MK, MU_L_PA_S, PR_L)
    h_tp = two_phase_htc(h_lo, G, X_EXIT / 2.0, geo["D_h_m"],
                          RHO_L_KG_M3, RHO_V_KG_M3, H_FG_J_KG, Q_CHIP_FLUX_W_M2)

    # CHF
    q_CHF_W_m2    = critical_heat_flux(G, geo["D_h_m"], COLD_PLATE_L_M,
                                        H_FG_J_KG, RHO_L_KG_M3, RHO_V_KG_M3)
    q_CHF_W_cm2   = q_CHF_W_m2 / 1e4
    chf_sf        = q_CHF_W_cm2 / Q_CHIP_W_CM2

    # Pressure drop
    dP_Pa = pressure_drop_two_phase(G, geo["D_h_m"], COLD_PLATE_L_M,
                                     X_EXIT, RHO_L_KG_M3, RHO_V_KG_M3, MU_L_PA_S)
    dP_kPa = dP_Pa / 1000.0

    # Thermal resistance and junction temperature
    R_total = thermal_resistance_total(h_tp, geo["A_base_m2"])
    Tj_C    = T_SAT_C + R_total * Q_CHIP_W_ACTUAL

    # Condenser
    Q_total_W   = Q_RACK_KW * 1000.0
    cond_area   = condenser_area(Q_total_W, T_SAT_C, T_AMBIENT_C)

    # Pump power
    N_chips_total = N_SERVERS * N_CHIPS_PER_SERVER
    Q_vol_per_chip = m_dot / RHO_L_KG_M3
    W_pump = N_chips_total * (Q_vol_per_chip * dP_Pa) / ETA_PUMP

    # System COP
    COP = Q_total_W / max(W_pump, 0.001)

    report = {
        "coolant_selected":              COOLANT,
        "cooling_technology":            COOLING_TECH,
        "chip_heat_flux_W_cm2":          Q_CHIP_W_CM2,
        "die_area_cm2":                  DIE_AREA_CM2 * 5.0,  # 5 cm² die
        "q_total_kW":                    Q_RACK_KW,
        "evaporator_channel_width_um":   CH_WIDTH_UM,
        "evaporator_channel_height_um":  CH_HEIGHT_UM,
        "evaporator_htc_W_m2K":          round(h_tp, 0),
        "evaporator_pressure_drop_kPa":  round(dP_kPa, 2),
        "condenser_area_m2":             round(cond_area, 2),
        "condenser_type":                "air",
        "thermal_resistance_total_K_W":  round(R_total, 5),
        "junction_temp_C":               round(Tj_C, 2),
        "saturation_temp_C":             T_SAT_C,
        "critical_heat_flux_W_cm2":      round(q_CHF_W_cm2, 1),
        "chf_safety_factor":             round(chf_sf, 2),
        "pump_power_W":                  round(W_pump, 2),
        "system_cop":                    round(COP, 1),
    }

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, "report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"HyperCool report written to: {out_path}")
    print(f"  Channels per chip  : {geo['N_channels']}  D_h={geo['D_h_m']*1e6:.1f} μm")
    print(f"  Mass flow per chip : {m_dot*1e3:.3f} g/s   G={G:.1f} kg/(m²·s)")
    print(f"  Single-phase HTC   : {h_lo:.0f} W/(m²·K)")
    print(f"  Two-phase HTC      : {h_tp:.0f} W/(m²·K)")
    print(f"  Pressure drop      : {dP_kPa:.2f} kPa")
    print(f"  CHF                : {q_CHF_W_cm2:.1f} W/cm²  (SF={chf_sf:.2f})")
    print(f"  R_total            : {R_total:.5f} K/W")
    print(f"  Junction temp      : {Tj_C:.2f}°C  (limit {TJ_LIMIT_C}°C)")
    print(f"  Condenser area     : {cond_area:.2f} m²")
    print(f"  Pump power         : {W_pump:.2f} W")
    print(f"  System COP         : {COP:.1f}")


if __name__ == "__main__":
    main()
