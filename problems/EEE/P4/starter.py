"""
PowerShield — Solid-State Circuit Breaker Design and Simulation Scaffold
Starter skeleton for EEE-P4.

Usage:
    python starter.py [--output submission/sscb_design_report.json]

This script simulates the fault interruption transient, computes key design
metrics, and produces a structured JSON design report. Adjust the DESIGN
PARAMETERS section to match your chosen components.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

# ─────────────────────────────────────────────
# SYSTEM REQUIREMENTS (DO NOT CHANGE)
# ─────────────────────────────────────────────

V_DC                = 400.0    # V, DC bus voltage
I_RATED             = 200.0    # A, continuous rated current
I_FAULT_MAX         = 10_000.0 # A, maximum fault current
T_BREAK_MAX_US      = 100.0    # μs, maximum breaking time
V_CLAMP_MAX         = 600.0    # V, maximum clamping voltage
N_CYCLES_ENDURANCE  = 10_000   # switching cycle endurance
T_AMBIENT_C         = 40.0     # °C

# ─────────────────────────────────────────────
# DESIGN PARAMETERS — ADJUST THESE
# ─────────────────────────────────────────────

# ── Semiconductor ──
DEVICE_TYPE         = "SiC MOSFET"
DEVICE_PART         = "C3M0016120K"   # Wolfspeed 1200 V, 16 mΩ
V_DEVICE_RATED_V    = 1200.0          # V, device voltage rating
RDS_ON_MOHM         = 16.0            # mΩ per device at 25°C
I_DEVICE_RATED_A    = 115.0           # A per device
N_PARALLEL          = 4               # devices in parallel per current direction
N_SERIES            = 1               # devices in series per direction
N_DIRECTIONS        = 2               # 2 for bidirectional (back-to-back)
RDS_ON_TEMP_COEFF   = 1.5             # Rds_on scaling at 150°C vs 25°C
Q_GATE_NC           = 90.0            # gate charge (nC) per device

# ── Gate driver ──
V_GS_ON             = 20.0    # V, turn-on gate voltage
V_GS_OFF            = -5.0    # V, turn-off gate voltage (negative for fast turn-off)
R_GATE_OHM          = 4.7     # Ω, gate resistance (external)
I_GATE_DRIVER_A     = 4.0     # A, gate driver peak output current
GATE_DRIVER_DELAY_US = 0.3    # μs, driver propagation delay

# ── Clamping network ──
CLAMP_TYPE          = "MOV + RC snubber"
V_MOV_CLAMP_V       = 550.0   # V, MOV clamping voltage (must be < V_CLAMP_MAX)
MOV_ENERGY_J        = 150.0   # J, MOV energy rating
R_SNUBBER_OHM       = 2.0     # Ω
C_SNUBBER_NF        = 220.0   # nF

# ── Fault detection ──
DETECTION_METHOD    = "Rogowski coil + analog comparator"
I_THRESHOLD_A       = 500.0   # A, fault current threshold (2.5× rated)
T_DETECT_US         = 2.0     # μs, detection time

# ── Circuit parameters ──
L_FAULT_UH          = 100.0   # μH, fault loop stray inductance
R_FAULT_OHM         = 0.04    # Ω, fault path resistance
L_STRAY_BUS_NH      = 200.0   # nH, bus stray inductance (affects voltage spike)

# ── Thermal ──
R_TH_JC_DEG_W       = 0.5     # °C/W, junction-to-case (per device)
R_TH_CS_DEG_W       = 0.10    # °C/W, case-to-sink (thermal pad)
R_TH_SA_DEG_W       = 0.08    # °C/W, sink-to-ambient (forced-air heat sink)
T_J_MAX_C           = 150.0   # °C, maximum junction temperature

# ─────────────────────────────────────────────
# 1. SEMICONDUCTOR SIZING
# ─────────────────────────────────────────────

def calc_semiconductor(
    v_dc, i_rated, n_parallel, n_series, n_dir,
    rds_on_mohm, i_device_rated,
    v_device_rated
):
    """Compute effective device parameters for the switch stack."""
    rds_on_eff_mohm = rds_on_mohm / n_parallel * n_series
    rds_on_eff_ohm  = rds_on_eff_mohm * 1e-3

    i_total_rated = i_device_rated * n_parallel
    v_blocking    = v_device_rated * n_series

    # Safety margins
    voltage_margin = (v_blocking - v_dc) / v_dc
    current_margin = (i_total_rated - i_rated) / i_rated

    return {
        "device_type": DEVICE_TYPE,
        "device_part": DEVICE_PART,
        "n_parallel_per_direction": n_parallel,
        "n_series_per_direction": n_series,
        "n_directions": n_dir,
        "total_devices": n_parallel * n_series * n_dir,
        "rds_on_effective_mohm": round(rds_on_eff_mohm, 2),
        "i_rated_device_stack_A": round(i_total_rated, 0),
        "v_blocking_V": round(v_blocking, 0),
        "voltage_margin_pct": round(voltage_margin * 100, 1),
        "current_margin_pct": round(current_margin * 100, 1),
        "voltage_safety_ok": bool(voltage_margin >= 1.0),   # 2× margin
        "current_safety_ok": bool(current_margin >= 0.50),  # 50% margin
        "justification": (
            f"SiC MOSFETs chosen for sub-microsecond switching, lower Rds_on at high "
            f"voltage vs Si IGBT, and higher operating temperature capability. "
            f"{n_parallel} in parallel per direction reduces effective Rds_on to "
            f"{rds_on_eff_mohm:.1f} mΩ, meeting conduction loss budget."
        ),
    }


# ─────────────────────────────────────────────
# 2. CONDUCTION AND SWITCHING LOSSES
# ─────────────────────────────────────────────

def calc_losses(semi: dict, i_rated, v_dc, f_normal_hz=1000,
                rds_on_temp_coeff=RDS_ON_TEMP_COEFF,
                q_gate_nc=Q_GATE_NC, n_parallel=N_PARALLEL,
                n_dir=N_DIRECTIONS, n_series=N_SERIES):
    """Compute steady-state conduction and switching losses."""
    rds_eff = semi["rds_on_effective_mohm"] * 1e-3 * rds_on_temp_coeff  # at temperature

    # Conduction losses (bidirectional: only one direction conducts at a time)
    p_cond = i_rated**2 * rds_eff  # both directions in path, but only 1 active

    # Switching losses (normal operation, not fault interruption)
    # E_sw per cycle ≈ 0.5 × Q_gate × V_ds × N_devices
    q_gate_total = q_gate_nc * 1e-9 * n_parallel * n_series  # total charge
    e_sw_per_cycle_j = 0.5 * q_gate_total * v_dc
    p_sw = e_sw_per_cycle_j * f_normal_hz

    p_total = p_cond + p_sw

    efficiency = i_rated * v_dc / (i_rated * v_dc + p_total)

    return {
        "rds_on_at_temp_mohm": round(rds_eff * 1e3, 2),
        "conduction_loss_W": round(p_cond, 1),
        "switching_loss_W": round(p_sw, 2),
        "total_loss_W": round(p_total, 1),
        "efficiency_pct": round(efficiency * 100, 3),
    }


# ─────────────────────────────────────────────
# 3. FAULT INTERRUPTION SIMULATION
# ─────────────────────────────────────────────

def simulate_fault_interruption(
    v_dc, l_fault_uh, r_fault_ohm,
    t_detect_us, t_fall_us,
    v_clamp_v, l_stray_nh,
    dt_ns=10.0,
) -> dict:
    """
    Simulate fault current and switch voltage during interruption.

    Model:
      Phase 1 (0 → t_detect):  switch closed, RL fault charging
      Phase 2 (t_detect → t_detect+t_fall): MOSFET turning off (linear fall)
      Phase 3 (t_detect+t_fall onwards): clamp absorbing energy

    Returns dict with time, current, and switch voltage arrays.
    """
    L = l_fault_uh * 1e-6   # H
    R = r_fault_ohm           # Ω
    L_s = l_stray_nh * 1e-9  # H (stray inductance adds to voltage spike)
    t_det = t_detect_us * 1e-6
    t_fall = t_fall_us * 1e-6
    V_cl  = v_clamp_v
    dt    = dt_ns * 1e-9

    t_max = (t_det + t_fall + 50e-6)  # simulate a bit past current zero

    times    = []
    currents = []
    v_switch = []

    I = 0.0
    I_at_detect = None

    for step in range(int(t_max / dt)):
        t = step * dt

        if t < t_det:
            # Phase 1: switch closed, fault current rising
            dI = (v_dc - I * R) / L
            I += dI * dt
        elif t < t_det + t_fall:
            # Phase 2: MOSFET turning off (linearly reduce gate drive effect)
            if I_at_detect is None:
                I_at_detect = I
            frac = (t - t_det) / t_fall  # 0→1
            dI = -I_at_detect / t_fall   # linear ramp-down (simplified)
            I += dI * dt
            I = max(I, 0.0)
        else:
            # Phase 3: current zero or clamped energy dissipation
            if I <= 0:
                I = 0.0
                dI = 0.0
            else:
                dI = -(V_cl - v_dc) / (L + L_s)
                I += dI * dt
                I = max(I, 0.0)

        # Switch voltage: V_dc + L_stray × |dI/dt| during turn-off
        if t >= t_det and I > 0:
            di_dt = abs(dI) / dt if dt > 0 else 0
            v_sw = V_cl + L_s * di_dt  # overshoot above clamp
        else:
            v_sw = I * R  # forward drop when conducting

        times.append(t * 1e6)    # μs
        currents.append(round(I, 2))
        v_switch.append(round(min(v_sw, V_cl + 100), 1))

    # Find interrupt time
    t_interrupt_us = None
    for i, cur in enumerate(currents):
        if cur <= 0.0 and times[i] > t_det * 1e6:
            t_interrupt_us = times[i]
            break

    total_interrupt_us = (t_interrupt_us - 0) if t_interrupt_us else None

    # Sub-sample for output (every 10th point to keep JSON small)
    stride = max(1, len(times) // 200)
    return {
        "time_us":           [round(x, 3) for x in times[::stride]],
        "current_A":         currents[::stride],
        "switch_voltage_V":  v_switch[::stride],
        "I_at_detect_A":     round(I_at_detect or 0, 1),
        "t_interrupt_us":    round(t_interrupt_us, 2) if t_interrupt_us else None,
        "peak_voltage_V":    round(max(v_switch), 1),
        "interrupt_ok":      bool(total_interrupt_us and
                                  total_interrupt_us <= T_BREAK_MAX_US),
        "voltage_clamp_ok":  bool(max(v_switch) <= V_CLAMP_MAX),
    }


# ─────────────────────────────────────────────
# 4. GATE DRIVER TIMING
# ─────────────────────────────────────────────

def calc_gate_timing(q_gate_nc, i_driver_a, r_gate_ohm,
                     v_gs_on, v_gs_off, gate_driver_delay_us):
    """Estimate MOSFET turn-off fall time."""
    # Time to discharge gate: t_fall ≈ Q_gate × R_gate / (|V_gs_on| + |V_gs_off|)
    v_drive_diff = abs(v_gs_on) + abs(v_gs_off)
    t_fall_s = (q_gate_nc * 1e-9 * r_gate_ohm) / v_drive_diff
    t_fall_us = t_fall_s * 1e6

    return {
        "v_gs_on_V":         v_gs_on,
        "v_gs_off_V":        v_gs_off,
        "r_gate_ohm":        r_gate_ohm,
        "i_driver_peak_A":   i_driver_a,
        "gate_driver_delay_us": gate_driver_delay_us,
        "mosfet_fall_time_us": round(t_fall_us, 3),
        "note": ("Negative turn-off voltage (-5 V) accelerates gate discharge "
                 "and improves dv/dt immunity."),
    }


# ─────────────────────────────────────────────
# 5. MOV SIZING
# ─────────────────────────────────────────────

def size_mov(l_fault_uh, i_at_detect_a, v_clamp_v, v_dc):
    """Compute minimum MOV energy rating."""
    l = l_fault_uh * 1e-6
    e_min = 0.5 * l * i_at_detect_a**2  # energy to absorb
    e_with_margin = e_min * 3.0  # 3× safety margin

    return {
        "clamp_voltage_V":     v_clamp_v,
        "fault_energy_min_J":  round(e_min, 2),
        "mov_rating_J":        round(e_with_margin, 2),
        "i_at_detect_A":       round(i_at_detect_a, 1),
        "clamp_ok":            bool(v_clamp_v < V_CLAMP_MAX),
        "mov_energy_ok":       bool(MOV_ENERGY_J >= e_with_margin),
        "r_snubber_ohm":       R_SNUBBER_OHM,
        "c_snubber_nF":        C_SNUBBER_NF,
    }


# ─────────────────────────────────────────────
# 6. THERMAL ANALYSIS
# ─────────────────────────────────────────────

def calc_thermal(losses_w, n_parallel, n_dir,
                 r_th_jc, r_th_cs, r_th_sa, t_ambient):
    """Compute junction temperature for steady-state operation."""
    p_per_device = losses_w / (n_parallel * n_dir)
    r_th_total   = r_th_jc + r_th_cs + r_th_sa
    t_junction   = t_ambient + losses_w * (r_th_jc + r_th_cs) / (n_parallel * n_dir) + \
                   losses_w * r_th_sa

    # Simplified: all heat through common sink
    delta_t = losses_w * (r_th_sa + (r_th_jc + r_th_cs) / (n_parallel * n_dir))
    t_j     = t_ambient + delta_t

    return {
        "r_th_jc_per_device": r_th_jc,
        "r_th_cs_per_device": r_th_cs,
        "r_th_sa_total":      r_th_sa,
        "total_loss_W":       round(losses_w, 1),
        "t_junction_C":       round(t_j, 1),
        "t_ambient_C":        t_ambient,
        "t_j_max_C":          T_J_MAX_C,
        "thermal_ok":         bool(t_j <= T_J_MAX_C),
        "heat_sink_note": (
            f"Forced-air heat sink required (R_th_sa = {r_th_sa} °C/W). "
            f"Natural convection (~0.5 °C/W) is insufficient for {losses_w:.0f} W."
            if r_th_sa < 0.15 else
            f"Natural convection heat sink (R_th_sa = {r_th_sa} °C/W) may be sufficient."
        ),
    }


# ─────────────────────────────────────────────
# 7. BILL OF MATERIALS
# ─────────────────────────────────────────────

def build_bom(n_parallel, n_dir, n_series):
    n_mosfets = n_parallel * n_dir * n_series
    bom = [
        {"component": f"SiC MOSFET {DEVICE_PART}",
         "qty": n_mosfets, "unit_cost_usd": 18.50,
         "total_cost_usd": round(n_mosfets * 18.50, 2)},
        {"component": "Isolated gate driver (IXD_614 or equivalent)",
         "qty": n_parallel * n_dir, "unit_cost_usd": 5.20,
         "total_cost_usd": round(n_parallel * n_dir * 5.20, 2)},
        {"component": f"MOV, {V_MOV_CLAMP_V:.0f} V, {MOV_ENERGY_J:.0f} J",
         "qty": 1, "unit_cost_usd": 12.00, "total_cost_usd": 12.00},
        {"component": f"RC snubber (R={R_SNUBBER_OHM} Ω, C={C_SNUBBER_NF} nF)",
         "qty": 2, "unit_cost_usd": 3.50, "total_cost_usd": 7.00},
        {"component": "Rogowski coil current sensor",
         "qty": 1, "unit_cost_usd": 45.00, "total_cost_usd": 45.00},
        {"component": "Analog comparator + logic board",
         "qty": 1, "unit_cost_usd": 30.00, "total_cost_usd": 30.00},
        {"component": "DC-DC isolated power supply (gate driver bias)",
         "qty": n_parallel * n_dir, "unit_cost_usd": 8.00,
         "total_cost_usd": round(n_parallel * n_dir * 8.00, 2)},
        {"component": "Forced-air heat sink + fan",
         "qty": 1, "unit_cost_usd": 35.00, "total_cost_usd": 35.00},
        {"component": "Bus bar, connectors, PCB, enclosure",
         "qty": 1, "unit_cost_usd": 80.00, "total_cost_usd": 80.00},
    ]
    total = sum(item["total_cost_usd"] for item in bom)
    return {"items": bom, "total_bom_cost_usd": round(total, 2)}


# ─────────────────────────────────────────────
# 8. MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PowerShield SSCB Design Calculator")
    parser.add_argument("--output", default="submission/sscb_design_report.json",
                        help="Output design report JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("PowerShield — SSCB Design Worksheet")
    print("=" * 60)

    # ── Semiconductor sizing ──
    semi = calc_semiconductor(
        V_DC, I_RATED, N_PARALLEL, N_SERIES, N_DIRECTIONS,
        RDS_ON_MOHM, I_DEVICE_RATED_A, V_DEVICE_RATED_V
    )
    print(f"\n[SEMI] Rds_on effective:   {semi['rds_on_effective_mohm']:.1f} mΩ")
    print(f"[SEMI] Total devices:       {semi['total_devices']}")
    print(f"[SEMI] Voltage margin:      {semi['voltage_margin_pct']:.0f} %  "
          f"({'OK' if semi['voltage_safety_ok'] else 'INSUFFICIENT'})")
    print(f"[SEMI] Current margin:      {semi['current_margin_pct']:.0f} %  "
          f"({'OK' if semi['current_safety_ok'] else 'INSUFFICIENT'})")

    # ── Gate driver timing ──
    gate = calc_gate_timing(
        Q_GATE_NC, I_GATE_DRIVER_A, R_GATE_OHM,
        V_GS_ON, V_GS_OFF, GATE_DRIVER_DELAY_US
    )
    t_fall_us = gate["mosfet_fall_time_us"]
    print(f"\n[GATE] MOSFET fall time:    {t_fall_us:.3f} μs")
    print(f"[GATE] Driver delay:        {GATE_DRIVER_DELAY_US} μs")

    # ── Fault simulation ──
    sim = simulate_fault_interruption(
        V_DC, L_FAULT_UH, R_FAULT_OHM,
        T_DETECT_US, t_fall_us,
        V_MOV_CLAMP_V, L_STRAY_BUS_NH,
    )
    t_int = sim.get("t_interrupt_us") or 9999.0
    print(f"\n[SIM] Current at detect:    {sim['I_at_detect_A']:.0f} A")
    print(f"[SIM] Interrupt time:       {t_int:.1f} μs  "
          f"({'PASS' if sim['interrupt_ok'] else f'FAIL > {T_BREAK_MAX_US} μs'})")
    print(f"[SIM] Peak switch voltage:  {sim['peak_voltage_V']:.0f} V  "
          f"({'PASS' if sim['voltage_clamp_ok'] else f'FAIL > {V_CLAMP_MAX} V'})")

    # ── Losses and efficiency ──
    losses = calc_losses(semi, I_RATED, V_DC)
    print(f"\n[LOSS] Conduction:         {losses['conduction_loss_W']:.0f} W")
    print(f"[LOSS] Switching:          {losses['switching_loss_W']:.1f} W")
    print(f"[LOSS] Efficiency:         {losses['efficiency_pct']:.3f} %")

    # ── MOV sizing ──
    mov = size_mov(L_FAULT_UH, sim["I_at_detect_A"], V_MOV_CLAMP_V, V_DC)
    print(f"\n[MOV] Fault energy:        {mov['fault_energy_min_J']:.1f} J")
    print(f"[MOV] MOV rating needed:   {mov['mov_rating_J']:.1f} J  "
          f"({'OK' if mov['mov_energy_ok'] else 'UNDERSIZED'})")

    # ── Thermal ──
    thermal = calc_thermal(
        losses["total_loss_W"], N_PARALLEL, N_DIRECTIONS,
        R_TH_JC_DEG_W, R_TH_CS_DEG_W, R_TH_SA_DEG_W, T_AMBIENT_C
    )
    print(f"\n[THERMAL] T_junction:      {thermal['t_junction_C']:.0f} °C  "
          f"(limit {T_J_MAX_C:.0f} °C) "
          f"{'OK' if thermal['thermal_ok'] else 'EXCEEDED'}")

    # ── BOM ──
    bom = build_bom(N_PARALLEL, N_DIRECTIONS, N_SERIES)
    print(f"\n[BOM] Total estimated cost: ${bom['total_bom_cost_usd']:.0f}")

    # ── Timing summary ──
    timing = {
        "detection_us":          T_DETECT_US,
        "gate_driver_delay_us":  GATE_DRIVER_DELAY_US,
        "mosfet_fall_time_us":   t_fall_us,
        "energy_absorption_us":  round(t_int - T_DETECT_US - t_fall_us, 2)
                                  if t_int else None,
        "total_us":              round(t_int, 2) if t_int else None,
        "meets_100us_target":    sim["interrupt_ok"],
    }

    # ── Assemble report ──
    report = {
        "semiconductor_selection": semi,
        "topology": {
            "description": (
                "Back-to-back SiC MOSFETs in common-source configuration "
                f"({N_PARALLEL} in parallel per direction, {N_DIRECTIONS} directions). "
                "Series connection of devices (N_series=1) — single series level sufficient "
                "at 1200 V rating for 400 V DC bus with 3× margin."
            ),
            "n_total_devices": semi["total_devices"],
            "n_parallel": N_PARALLEL,
            "n_series": N_SERIES,
            "bidirectional": True,
        },
        "snubber_clamping": mov,
        "gate_driver": gate,
        "fault_detection": {
            "method": DETECTION_METHOD,
            "threshold_A": I_THRESHOLD_A,
            "detection_time_us": T_DETECT_US,
            "nuisance_trip_guard": (
                "Hysteresis band ±10% of threshold; 0.5 μs blanking time "
                "to reject switching transients."
            ),
        },
        "thermal_design": thermal,
        "loss_analysis": losses,
        "simulation_results": {
            "fault_interruption": sim,
            "description": (
                f"RL circuit model: V_dc={V_DC} V, L={L_FAULT_UH} μH, R={R_FAULT_OHM} Ω. "
                f"Fault detected at {T_DETECT_US} μs, MOSFET turn-off over {t_fall_us:.2f} μs, "
                f"MOV clamps at {V_MOV_CLAMP_V} V."
            ),
        },
        "bom": bom,
        "timing_breakdown": timing,
        # TODO: add full LTSpice / PLECS simulation results and waveform screenshots
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[INFO] Design report saved to {out_path}")

    # Gate check
    all_pass = all([
        semi["voltage_safety_ok"],
        semi["current_safety_ok"],
        sim["interrupt_ok"],
        sim["voltage_clamp_ok"],
        thermal["thermal_ok"],
        mov["mov_energy_ok"],
        mov["clamp_ok"],
    ])
    print(f"\n{'[PASS] All design requirements met.' if all_pass else '[FAIL] Some requirements not met — check parameters above.'}")


if __name__ == "__main__":
    main()
