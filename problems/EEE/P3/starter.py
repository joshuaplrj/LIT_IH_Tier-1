"""
MotorForge — 10 kW BLDC Motor Design Simulation Scaffold
Starter skeleton for EEE-P3.

Usage:
    python starter.py [--output submission/motor_design_report.json]

This script encodes all key BLDC motor design equations and produces a
structured JSON design report. Adjust the DESIGN PARAMETERS section at the
top to iterate toward a solution that meets all requirements.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

# ─────────────────────────────────────────────
# REQUIREMENTS (DO NOT CHANGE)
# ─────────────────────────────────────────────

REQ_RATED_POWER_W    = 10_000.0   # W
REQ_RATED_SPEED_RPM  = 4_000.0   # RPM
REQ_PEAK_TORQUE_NM   = 40.0      # Nm
REQ_EFFICIENCY_MIN   = 0.92      # 92 %
REQ_VOLTAGE_DC       = 72.0      # V DC bus
REQ_OD_MAX_MM        = 200.0     # mm
REQ_LENGTH_MAX_MM    = 150.0     # mm
REQ_WEIGHT_MAX_KG    = 12.0      # kg
T_AMBIENT_C          = 40.0      # °C (worst-case ambient)
T_INSULATION_MAX_C   = 155.0     # °C (Class F insulation limit)

# ─────────────────────────────────────────────
# DESIGN PARAMETERS — ADJUST THESE
# ─────────────────────────────────────────────

# Topology
N_POLES         = 10       # number of magnetic poles (must be even)
N_SLOTS         = 12       # number of stator slots

# Geometry (meters)
D_BORE_M        = 0.120    # stator bore diameter (m) — initial guess, iterate
L_STACK_M       = 0.080    # axial stack length (m)
AIR_GAP_M       = 0.001    # mechanical air gap (m)
OD_STATOR_M     = 0.190    # stator outer diameter (m) — must be ≤ 0.200 m

# Winding
N_TURNS_PER_PHASE = 48     # series turns per phase — iterate to match Ke target
WIRE_DIAMETER_MM  = 1.2    # conductor wire diameter (mm)
PARALLEL_PATHS    = 2      # number of parallel conductors per phase

# Magnet
MAGNET_GRADE      = "N42"  # NdFeB grade
B_REM_T           = 1.28   # remanence flux density (T) — N42 at 20°C
MU_R_MAGNET       = 1.05   # relative permeability of magnet
T_MAGNET_M        = 0.006  # magnet thickness (m) — radial direction

# Materials
DENSITY_COPPER_KG_M3  = 8_960.0
DENSITY_IRON_KG_M3    = 7_650.0   # laminated silicon steel (stacking factor 0.95)
DENSITY_MAGNET_KG_M3  = 7_500.0
RHO_COPPER_OHM_M      = 1.72e-8   # at 20°C; use 2.1e-8 at 100°C

# Iron loss coefficients (M19 26-gauge silicon steel)
K_H_IRON          = 0.0275   # hysteresis coefficient
K_E_IRON          = 1.83e-5  # eddy current coefficient
B_STEINMETZ_EXP   = 2.0      # Steinmetz exponent for B

# Thermal
H_CONV_W_M2K      = 25.0    # natural convection coefficient (W/m²K)
R_TH_EXTRA_K_W    = 0.05    # extra thermal resistance (winding to lamination, K/W)

# ─────────────────────────────────────────────
# 1. ELECTROMAGNETIC CALCULATIONS
# ─────────────────────────────────────────────

def calc_electromagnetic(
    n_poles, n_slots, d_bore_m, l_stack_m, air_gap_m,
    b_rem_t, mu_r_magnet, t_magnet_m,
    n_turns_per_phase, parallel_paths, wire_diameter_mm,
    rated_speed_rpm, rated_power_w, peak_torque_nm,
    rho_cu_ohm_m
):
    """Compute all electromagnetic parameters and return a dict."""
    p = n_poles // 2  # pole pairs
    f_elec_hz = p * rated_speed_rpm / 60.0  # electrical frequency at rated speed

    # Winding factor (simplified for fractional-pitch)
    # For 10p/12s: k_w ≈ 0.933 (tabulated); for 8p/12s: k_w ≈ 0.866
    # General approximation: k_w = k_p × k_d (pitch × distribution factors)
    k_pitch = math.sin(math.pi / 2 * (n_slots / n_poles))  # simplified
    k_dist  = math.sin(math.pi / 6) / (3 * math.sin(math.pi / 18))  # approx 3-phase
    k_w     = min(k_pitch * k_dist, 0.966)  # clamp to physical max

    # Pole pitch and magnet coverage
    tau_p   = math.pi * d_bore_m / n_poles  # pole pitch at bore surface (m)
    alpha_m = 0.85  # magnet pole-arc to pole-pitch ratio (typical)

    # Air-gap flux density using magnetic circuit (Carter factor ≈ 1.1)
    k_c     = 1.10  # Carter factor (accounts for slot opening)
    g_eff   = k_c * air_gap_m + t_magnet_m / mu_r_magnet
    b_gap   = b_rem_t / (1 + k_c * air_gap_m * mu_r_magnet / t_magnet_m)

    # Magnet flux per pole
    phi_m   = b_gap * alpha_m * tau_p * l_stack_m

    # Back-EMF constant Ke (V·s/rad)
    ke      = (n_turns_per_phase * k_w * p * phi_m) / (math.pi)
    # Torque constant Kt (N·m/A) — equals Ke in SI
    kt      = 1.5 * p * phi_m * n_turns_per_phase * k_w

    # Rated operating point
    omega_rated = 2 * math.pi * rated_speed_rpm / 60.0  # rad/s
    t_rated     = rated_power_w / omega_rated

    # Required current for rated torque
    i_rated     = t_rated / kt
    i_peak      = peak_torque_nm / kt  # for peak torque at low speed

    # Phase inductance (simplified: Ld = Lq for surface-mount BLDC)
    mu_0        = 4 * math.pi * 1e-7
    l_phase_h   = (mu_0 * (n_turns_per_phase**2) * k_w**2 *
                   math.pi * (d_bore_m/2)**2 * l_stack_m /
                   (p**2 * g_eff * 2))

    # Phase resistance
    r_conductor = math.pi * (wire_diameter_mm * 1e-3 / 2)**2  # m²
    l_turn_avg  = math.pi * (d_bore_m + (0.190 - d_bore_m) / 2) + 2 * l_stack_m  # approx
    r_phase     = (rho_cu_ohm_m * l_turn_avg * n_turns_per_phase /
                   (r_conductor * parallel_paths))

    # Back-EMF at rated speed (peak line-to-neutral)
    v_bemf_peak = ke * omega_rated
    # Check voltage margin
    v_phase_needed = math.sqrt(v_bemf_peak**2 + (i_rated * r_phase)**2 +
                               (i_rated * l_phase_h * 2*math.pi*f_elec_hz)**2)
    v_phase_avail  = REQ_VOLTAGE_DC / math.sqrt(3)

    # Current density check
    i_per_conductor = i_peak / parallel_paths
    j_current_density = i_per_conductor / (r_conductor * 1e6)  # A/mm²

    return {
        "pole_pairs": p,
        "electrical_frequency_hz": round(f_elec_hz, 1),
        "winding_factor": round(k_w, 4),
        "air_gap_flux_density_T": round(b_gap, 4),
        "magnet_flux_per_pole_Wb": round(phi_m * 1e3, 4),  # mWb
        "back_emf_constant_V_s_rad": round(ke, 4),
        "torque_constant_Nm_A": round(kt, 4),
        "rated_torque_Nm": round(t_rated, 2),
        "rated_current_A_rms": round(i_rated, 2),
        "peak_current_A": round(i_peak, 2),
        "phase_resistance_ohm": round(r_phase, 4),
        "phase_inductance_mH": round(l_phase_h * 1e3, 4),
        "v_bemf_peak_V": round(v_bemf_peak, 2),
        "v_phase_needed_V": round(v_phase_needed, 2),
        "v_phase_available_V": round(v_phase_avail, 2),
        "voltage_margin_ok": bool(v_phase_needed <= v_phase_avail * 1.05),
        "current_density_A_mm2": round(j_current_density, 2),
        "current_density_ok": bool(j_current_density <= 6.0),
    }


# ─────────────────────────────────────────────
# 2. LOSS ESTIMATION
# ─────────────────────────────────────────────

def calc_losses(em: dict, n_poles, n_slots, d_bore_m, l_stack_m, od_stator_m,
                rated_power_w, rated_speed_rpm,
                b_gap, f_elec_hz, k_h, k_e, b_exp,
                wire_dia_mm, n_turns, parallel_paths, rho_cu_ohm_m):
    """Return a dict of all loss components in Watts."""
    omega    = 2 * math.pi * rated_speed_rpm / 60.0
    i_rms    = em["rated_current_A_rms"]
    r_phase  = em["phase_resistance_ohm"]

    # Copper losses (3 phases)
    p_copper = 3 * i_rms**2 * r_phase

    # Iron mass (rough estimate: stator yoke + teeth)
    stator_area = math.pi * ((od_stator_m/2)**2 - (d_bore_m/2)**2)
    m_iron = stator_area * l_stack_m * DENSITY_IRON_KG_M3 * 0.95  # stacking factor

    # Iron losses (Steinmetz)
    b_pk_stator = 1.4  # typical peak flux in stator yoke (T)
    p_iron_w_kg = k_h * f_elec_hz * b_pk_stator**b_exp + k_e * f_elec_hz**2 * b_pk_stator**2
    p_iron = p_iron_w_kg * m_iron

    # Magnet eddy-current losses (simplified formula)
    sigma_magnet   = 6.25e5   # S/m for NdFeB
    l_magnet_chord = math.pi * d_bore_m / n_poles * 0.85  # magnet arc length
    p_magnet_eddy  = (sigma_magnet * (2*math.pi*f_elec_hz)**2 *
                      b_gap**2 * l_magnet_chord**2 *
                      T_MAGNET_M * math.pi * d_bore_m * l_stack_m / 48)

    # Mechanical losses (bearing + windage, empirical)
    p_mech = 0.005 * rated_power_w  # ~0.5% of rated power

    p_total = p_copper + p_iron + p_magnet_eddy + p_mech
    efficiency = rated_power_w / (rated_power_w + p_total)

    return {
        "copper_W": round(p_copper, 1),
        "iron_W": round(p_iron, 1),
        "magnet_eddy_W": round(p_magnet_eddy, 1),
        "mechanical_W": round(p_mech, 1),
        "total_loss_W": round(p_total, 1),
        "efficiency_pct": round(efficiency * 100, 2),
    }


# ─────────────────────────────────────────────
# 3. THERMAL ANALYSIS
# ─────────────────────────────────────────────

def calc_thermal(losses: dict, d_bore_m, l_stack_m, od_stator_m):
    """Simple lumped-parameter thermal model."""
    # Thermal resistance: housing surface → ambient (natural convection)
    surface_area = math.pi * od_stator_m * l_stack_m + 2 * math.pi * (od_stator_m/2)**2
    r_th_surface = 1.0 / (H_CONV_W_M2K * surface_area)

    # Total winding-to-ambient thermal resistance
    r_th_total = r_th_surface + R_TH_EXTRA_K_W

    p_total = losses["total_loss_W"]
    delta_t = p_total * r_th_total
    t_winding = T_AMBIENT_C + delta_t

    return {
        "r_th_surface_K_W": round(r_th_surface, 4),
        "r_th_total_K_W": round(r_th_total, 4),
        "delta_T_K": round(delta_t, 1),
        "winding_temp_C": round(t_winding, 1),
        "ambient_temp_C": T_AMBIENT_C,
        "insulation_class": "F (155°C limit)",
        "thermal_ok": bool(t_winding <= T_INSULATION_MAX_C),
    }


# ─────────────────────────────────────────────
# 4. WEIGHT ESTIMATE
# ─────────────────────────────────────────────

def calc_weight(d_bore_m, l_stack_m, od_stator_m,
                wire_dia_mm, n_turns, parallel_paths, n_slots,
                t_magnet_m, n_poles):
    """Rough weight estimate by volume × density."""
    # Stator iron
    stator_area = math.pi * ((od_stator_m/2)**2 - (d_bore_m/2)**2)
    m_stator = stator_area * l_stack_m * DENSITY_IRON_KG_M3 * 0.95

    # Copper (total conductor volume)
    r_cond = math.pi * (wire_dia_mm * 1e-3 / 2)**2  # m²
    l_turn = math.pi * (d_bore_m + (od_stator_m - d_bore_m)/2) + 2 * l_stack_m
    v_copper = r_cond * l_turn * n_turns * 3 * parallel_paths
    m_copper = v_copper * DENSITY_COPPER_KG_M3

    # Magnets
    tau_p   = math.pi * d_bore_m / n_poles
    v_magnet = tau_p * 0.85 * t_magnet_m * l_stack_m * n_poles
    m_magnet = v_magnet * DENSITY_MAGNET_KG_M3

    # Rotor back-iron (estimate as 30% of stator iron mass)
    m_rotor_iron = 0.3 * m_stator

    # Housing (estimate as 20% of stator iron)
    m_housing = 0.2 * m_stator

    total = m_stator + m_copper + m_magnet + m_rotor_iron + m_housing

    return {
        "m_stator_kg": round(m_stator, 2),
        "m_copper_kg": round(m_copper, 2),
        "m_magnets_kg": round(m_magnet, 2),
        "m_rotor_iron_kg": round(m_rotor_iron, 2),
        "m_housing_kg": round(m_housing, 2),
        "total_kg": round(total, 2),
        "weight_ok": bool(total <= REQ_WEIGHT_MAX_KG),
    }


# ─────────────────────────────────────────────
# 5. FOC CONTROLLER DESIGN
# ─────────────────────────────────────────────

def design_foc(em: dict):
    """Design PI gains for inner current loop and outer speed loop."""
    r = em["phase_resistance_ohm"]
    l = em["phase_inductance_mH"] * 1e-3  # H
    kt = em["torque_constant_Nm_A"]
    rated_speed_rpm = REQ_RATED_SPEED_RPM
    j_rotor = 0.005  # kg·m² — estimated rotor inertia

    # Inner current loop: bandwidth ω_ci = 1000 rad/s (≈160 Hz)
    omega_ci = 1000.0
    kp_current = l * omega_ci
    ki_current = r * omega_ci

    # Outer speed loop: bandwidth ω_cs = 100 rad/s (≈16 Hz)
    omega_cs = 100.0
    kp_speed = j_rotor * omega_cs / kt
    ki_speed = kp_speed * omega_cs / 10.0  # typical integral ratio

    return {
        "topology": "Field-Oriented Control (FOC) with d-axis current = 0 (MTPA at low speed)",
        "current_loop_bandwidth_Hz": round(omega_ci / (2*math.pi), 1),
        "Kp_current": round(kp_current, 4),
        "Ki_current": round(ki_current, 4),
        "speed_loop_bandwidth_Hz": round(omega_cs / (2*math.pi), 1),
        "Kp_speed": round(kp_speed, 4),
        "Ki_speed": round(ki_speed, 4),
        "pwm_frequency_kHz": 20,
        "simulation_notes": (
            "Implement d-q frame current controllers. "
            "Use anti-windup clamping on integral terms. "
            "Add space vector modulation (SVM) for DC bus utilization > 0.866."
        ),
    }


# ─────────────────────────────────────────────
# 6. TORQUE-SPEED CURVE AND EFFICIENCY MAP
# ─────────────────────────────────────────────

def build_torque_speed_curve(em: dict, losses_at_rated: dict):
    """Generate torque-speed curve data points."""
    kt         = em["torque_constant_Nm_A"]
    r_phase    = em["phase_resistance_ohm"]
    v_dc       = REQ_VOLTAGE_DC
    ke         = em["back_emf_constant_V_s_rad"]

    curve = []
    for speed_rpm in range(0, 5200, 200):
        omega = 2 * math.pi * speed_rpm / 60.0
        # Max torque limited by voltage: T_max = (V_dc/sqrt(3) - ke*omega) * kt / r_phase
        v_phase = v_dc / math.sqrt(3)
        bemf    = ke * omega
        if bemf >= v_phase:
            t_max = 0.0
        else:
            i_max = (v_phase - bemf) / r_phase
            t_max = kt * min(i_max, em["peak_current_A"])
        t_max = max(0.0, min(t_max, REQ_PEAK_TORQUE_NM))
        curve.append({"speed_rpm": speed_rpm, "max_torque_Nm": round(t_max, 2)})

    return curve


def build_efficiency_map(em: dict):
    """Build a sparse efficiency map over speed × torque grid."""
    kt          = em["torque_constant_Nm_A"]
    r_phase     = em["phase_resistance_ohm"]
    ke          = em["back_emf_constant_V_s_rad"]
    l_phase     = em["phase_inductance_mH"] * 1e-3
    f_base_hz   = em["electrical_frequency_hz"]  # at rated speed
    rated_omega = 2 * math.pi * REQ_RATED_SPEED_RPM / 60.0

    eff_map = []
    for speed_rpm in range(500, 5000, 500):
        omega = 2 * math.pi * speed_rpm / 60.0
        f_hz  = speed_rpm / 60.0 * (N_POLES // 2)

        for torque_nm in [5, 10, 15, 20, 25, 30, 35, 40]:
            if torque_nm > REQ_PEAK_TORQUE_NM:
                continue
            i_q = torque_nm / kt if kt > 0 else 0
            p_out = torque_nm * omega
            if p_out <= 0:
                continue

            # Losses
            p_cu   = 3 * i_q**2 * r_phase
            b_ratio = torque_nm / REQ_PEAK_TORQUE_NM
            p_iron = (K_H_IRON * f_hz * (1.0 * b_ratio)**B_STEINMETZ_EXP +
                      K_E_IRON * f_hz**2 * (1.0 * b_ratio)**2) * 10  # rough iron mass
            p_mech = 0.005 * REQ_RATED_POWER_W * (speed_rpm / REQ_RATED_SPEED_RPM)

            eff = p_out / (p_out + p_cu + p_iron + p_mech)
            eff_map.append({
                "speed_rpm": speed_rpm,
                "torque_Nm": torque_nm,
                "efficiency_pct": round(min(eff * 100, 99.9), 1),
            })

    return eff_map


# ─────────────────────────────────────────────
# 7. MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MotorForge Design Calculator")
    parser.add_argument("--output", default="submission/motor_design_report.json",
                        help="Output design report JSON path")
    args = parser.parse_args()

    print("=" * 60)
    print("MotorForge — BLDC Motor Design Worksheet")
    print("=" * 60)

    # TODO: iterate the design parameters above until all requirements are met

    # ── Electromagnetic design ──
    em = calc_electromagnetic(
        N_POLES, N_SLOTS, D_BORE_M, L_STACK_M, AIR_GAP_M,
        B_REM_T, MU_R_MAGNET, T_MAGNET_M,
        N_TURNS_PER_PHASE, PARALLEL_PATHS, WIRE_DIAMETER_MM,
        REQ_RATED_SPEED_RPM, REQ_RATED_POWER_W, REQ_PEAK_TORQUE_NM,
        RHO_COPPER_OHM_M
    )
    print(f"\n[EM] Torque constant:   {em['torque_constant_Nm_A']:.4f} Nm/A")
    print(f"[EM] Back-EMF (peak):   {em['v_bemf_peak_V']:.1f} V  "
          f"(available: {em['v_phase_available_V']:.1f} V)")
    print(f"[EM] Rated current:     {em['rated_current_A_rms']:.1f} A rms")
    print(f"[EM] Peak current:      {em['peak_current_A']:.1f} A")
    print(f"[EM] Current density:   {em['current_density_A_mm2']:.1f} A/mm² "
          f"({'OK' if em['current_density_ok'] else 'HIGH - reduce J'})")
    print(f"[EM] Voltage margin:    {'OK' if em['voltage_margin_ok'] else 'INSUFFICIENT'}")

    # ── Losses ──
    losses = calc_losses(
        em, N_POLES, N_SLOTS, D_BORE_M, L_STACK_M, OD_STATOR_M,
        REQ_RATED_POWER_W, REQ_RATED_SPEED_RPM,
        em["air_gap_flux_density_T"], em["electrical_frequency_hz"],
        K_H_IRON, K_E_IRON, B_STEINMETZ_EXP,
        WIRE_DIAMETER_MM, N_TURNS_PER_PHASE, PARALLEL_PATHS, RHO_COPPER_OHM_M
    )
    print(f"\n[LOSS] Copper:          {losses['copper_W']:.0f} W")
    print(f"[LOSS] Iron:            {losses['iron_W']:.0f} W")
    print(f"[LOSS] Magnet eddy:     {losses['magnet_eddy_W']:.0f} W")
    print(f"[LOSS] Mechanical:      {losses['mechanical_W']:.0f} W")
    print(f"[LOSS] Efficiency:      {losses['efficiency_pct']:.1f} %  "
          f"(target > {REQ_EFFICIENCY_MIN*100:.0f} %)")

    # ── Thermal ──
    thermal = calc_thermal(losses, D_BORE_M, L_STACK_M, OD_STATOR_M)
    print(f"\n[THERMAL] ΔT:           {thermal['delta_T_K']:.0f} K")
    print(f"[THERMAL] T_winding:    {thermal['winding_temp_C']:.0f} °C  "
          f"(limit {T_INSULATION_MAX_C:.0f} °C) "
          f"{'OK' if thermal['thermal_ok'] else 'EXCEEDED'}")

    # ── Weight ──
    weight = calc_weight(
        D_BORE_M, L_STACK_M, OD_STATOR_M,
        WIRE_DIAMETER_MM, N_TURNS_PER_PHASE, PARALLEL_PATHS, N_SLOTS,
        T_MAGNET_M, N_POLES
    )
    print(f"\n[WEIGHT] Total:         {weight['total_kg']:.2f} kg  "
          f"(limit {REQ_WEIGHT_MAX_KG:.0f} kg) "
          f"{'OK' if weight['weight_ok'] else 'EXCEEDED'}")

    # ── FOC Controller ──
    foc = design_foc(em)
    print(f"\n[FOC] Kp_current={foc['Kp_current']}, Ki_current={foc['Ki_current']}")
    print(f"[FOC] Kp_speed={foc['Kp_speed']}, Ki_speed={foc['Ki_speed']}")

    # ── Performance summary ──
    torque_density = em["rated_torque_Nm"] / weight["total_kg"]
    perf = {
        "efficiency_pct": losses["efficiency_pct"],
        "efficiency_ok": bool(losses["efficiency_pct"] >= REQ_EFFICIENCY_MIN * 100),
        "peak_torque_Nm": em["rated_torque_Nm"],
        "torque_density_Nm_kg": round(torque_density, 3),
        "weight_kg": weight["total_kg"],
        "weight_ok": weight["weight_ok"],
        "od_mm": OD_STATOR_M * 1000,
        "od_ok": bool(OD_STATOR_M * 1000 <= REQ_OD_MAX_MM),
        "length_mm": L_STACK_M * 1000,
        "length_ok": bool(L_STACK_M * 1000 <= REQ_LENGTH_MAX_MM),
        "thermal_ok": thermal["thermal_ok"],
    }

    # ── Curves ──
    ts_curve = build_torque_speed_curve(em, losses)
    eff_map  = build_efficiency_map(em)

    # ── Assemble report ──
    report = {
        "motor_parameters": {
            "poles": N_POLES,
            "slots": N_SLOTS,
            "bore_diameter_mm": round(D_BORE_M * 1000, 1),
            "stack_length_mm": round(L_STACK_M * 1000, 1),
            "outer_diameter_mm": round(OD_STATOR_M * 1000, 1),
            "air_gap_mm": round(AIR_GAP_M * 1000, 2),
            "turns_per_phase": N_TURNS_PER_PHASE,
            "parallel_paths": PARALLEL_PATHS,
            "wire_diameter_mm": WIRE_DIAMETER_MM,
            "magnet_grade": MAGNET_GRADE,
            "magnet_thickness_mm": round(T_MAGNET_M * 1000, 1),
        },
        "magnetic_analysis": em,
        "loss_breakdown": losses,
        "thermal_analysis": thermal,
        "performance_verification": perf,
        "foc_controller": foc,
        "simulation_results": {
            "torque_speed_curve": ts_curve,
            "efficiency_map": eff_map,
        },
        "weight_breakdown": weight,
        # TODO: add FEA validation summary, sensitivity analysis, drive-cycle results
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n[INFO] Design report saved to {out_path}")

    # Final gate check
    all_ok = all([
        perf["efficiency_ok"],
        perf["weight_ok"],
        perf["od_ok"],
        perf["length_ok"],
        perf["thermal_ok"],
        em["voltage_margin_ok"],
        em["current_density_ok"],
    ])
    if all_ok:
        print("[PASS] All requirements satisfied. Proceed to FEA validation.")
    else:
        print("[FAIL] Some requirements NOT met — check parameters above and iterate.")


if __name__ == "__main__":
    main()
