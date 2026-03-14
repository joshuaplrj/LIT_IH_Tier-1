"""
E-Harvest — RF Energy Harvesting System Design Scaffold
Starter skeleton for EEE-P5.

Usage:
    python starter.py [--output submission/eharvest_design_report.json]
                      [--rectifier single_series|voltage_doubler|dickson]
                      [--freq1_ghz 0.915] [--freq2_ghz 2.4]

Computes link budget, rectifier PCE curves, capacitor sizing, and assembles
a structured JSON design report. Adjust DESIGN PARAMETERS to iterate.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

# ─────────────────────────────────────────────
# REQUIREMENTS (DO NOT CHANGE)
# ─────────────────────────────────────────────

FREQ1_GHZ           = 0.915    # GHz
FREQ2_GHZ           = 2.400    # GHz
P_IN_MIN_DBM        = -20.0    # dBm (-20 dBm = 10 μW)
P_IN_MAX_DBM        = -10.0    # dBm (-10 dBm = 100 μW)
V_OUT_TARGET_V      = 1.8      # V DC
V_OUT_TOL           = 0.05     # ± 5%
P_OUT_TARGET_W      = 100e-6   # W (100 μW)
PCE_TARGET          = 0.40     # 40% PCE at -10 dBm
R_SOURCE_OHM        = 50.0     # Ω (antenna port impedance)
PCB_AREA_MM         = 50       # mm (square)

# ─────────────────────────────────────────────
# DESIGN PARAMETERS — ADJUST THESE
# ─────────────────────────────────────────────

# ── Antenna ──
ANTENNA_TYPE        = "Dual-band PIFA"
ANT_GAIN_DBI_915    = 2.0      # dBi gain at 915 MHz
ANT_GAIN_DBI_24     = 3.0      # dBi gain at 2.4 GHz
ANT_S11_DB_915      = -12.0    # dB S11 at 915 MHz (< -10 dB = good match)
ANT_S11_DB_24       = -15.0    # dB S11 at 2.4 GHz
ANT_BANDWIDTH_MHZ_915 = 50     # MHz, -10 dB bandwidth at 915 MHz
ANT_BANDWIDTH_MHZ_24  = 200    # MHz, -10 dB bandwidth at 2.4 GHz
ANT_EFF_PCT         = 75.0     # % antenna efficiency (losses in substrate)

# ── Matching network ──
MATCH_TOPOLOGY      = "L-network (diplexed for dual-band)"
MATCH_IL_DB_915     = 0.5      # dB insertion loss at 915 MHz
MATCH_IL_DB_24      = 0.8      # dB insertion loss at 2.4 GHz
# L-network component values (tune to rectifier input impedance)
L_MATCH_NH_915      = 8.2      # nH series inductor at 915 MHz
C_MATCH_PF_915      = 15.0     # pF shunt capacitor at 915 MHz
L_MATCH_NH_24       = 3.3      # nH series inductor at 2.4 GHz
C_MATCH_PF_24       = 4.7      # pF shunt capacitor at 2.4 GHz

# ── Rectifier ──
RECTIFIER_TOPOLOGY  = "dickson"   # "single_series", "voltage_doubler", "dickson"
DIODE_PART          = "SMS7630-061"
DIODE_V_TH_V        = 0.08     # V, zero-bias forward voltage
DIODE_I_S_A         = 5e-6     # A, saturation current
DIODE_IDEALITY      = 1.05     # ideality factor
DIODE_C_J_PF        = 0.14     # pF, junction capacitance at 0 V bias
DICKSON_STAGES      = 9        # number of Dickson multiplier stages
R_LOAD_OHM          = 32400    # Ω (V_out² / P_out = 1.8² / 100e-6)

# ── Voltage regulator ──
REGULATOR_TYPE      = "LDO (TPS7A02 or equivalent)"
REGULATOR_IQ_UA     = 0.025    # μA quiescent current (25 nA)
REGULATOR_V_OUT_V   = 1.8      # V
REGULATOR_V_IN_MIN_V = 2.0     # V minimum input for LDO dropout
REGULATOR_EFF_PCT   = 90.0     # % (Vout/Vin × 100)

# ── Energy buffer ──
C_BUFFER_UF         = 47.0     # μF storage capacitor
C_BUFFER_V_RATING   = 4.0      # V
LOAD_BURST_MA       = 0.100    # mA load current during active burst
LOAD_BURST_MS       = 10.0     # ms burst duration
LOAD_PERIOD_S       = 10.0     # s between bursts (duty cycle = 0.1%)


# ─────────────────────────────────────────────
# 1. LINK BUDGET
# ─────────────────────────────────────────────

def dbm_to_w(dbm: float) -> float:
    return 10 ** (dbm / 10) * 1e-3


def w_to_dbm(w: float) -> float:
    return 10 * math.log10(w / 1e-3) if w > 0 else -999


def link_budget(p_in_dbm: float, ant_gain_dbi: float,
                ant_eff_pct: float, match_il_db: float) -> dict:
    """Compute power available at rectifier input."""
    p_ambient_w = dbm_to_w(p_in_dbm)

    ant_gain_linear = 10 ** (ant_gain_dbi / 10)
    ant_eff_linear  = ant_eff_pct / 100.0
    match_il_linear = 10 ** (-match_il_db / 10)

    # Effective isotropic radiated power capture
    p_captured_w = p_ambient_w * ant_eff_linear  # simplified: gain accounts for directivity
    p_rect_input = p_captured_w * match_il_linear

    return {
        "p_ambient_dbm":    round(p_in_dbm, 1),
        "p_ambient_w":      round(p_ambient_w * 1e6, 2),     # μW
        "ant_efficiency_pct": ant_eff_pct,
        "matching_il_db":   match_il_db,
        "p_rectifier_input_w": round(p_rect_input * 1e6, 3), # μW
        "p_rectifier_input_dbm": round(w_to_dbm(p_rect_input), 2),
    }


# ─────────────────────────────────────────────
# 2. RECTIFIER EFFICIENCY MODEL
# ─────────────────────────────────────────────

def pce_single_series(p_in_w: float, r_source: float, r_load: float,
                      v_th: float, i_s: float, eta: float,
                      c_j_pf: float, freq_ghz: float) -> tuple:
    """
    Analytical PCE estimate for single-series rectifier.
    Returns (pce, v_out_v).
    """
    if p_in_w <= 0:
        return 0.0, 0.0
    v_pk_source = math.sqrt(2 * p_in_w * r_source)
    # Voltage at rectifier after source impedance divider (approximate)
    omega = 2 * math.pi * freq_ghz * 1e9
    z_c   = 1 / (omega * c_j_pf * 1e-12)
    r_rect_approx = min(z_c, r_load / 2)
    v_pk_rect = v_pk_source * r_rect_approx / (r_rect_approx + r_source)

    if v_pk_rect < v_th:
        return 0.0, 0.0

    v_out = (v_pk_rect - v_th) * 0.9  # 90% rectification efficiency factor
    p_out = v_out**2 / r_load
    pce   = min(p_out / p_in_w, 0.95)
    return pce, v_out


def pce_voltage_doubler(p_in_w: float, r_source: float, r_load: float,
                        v_th: float, freq_ghz: float, c_j_pf: float) -> tuple:
    """Voltage doubler: 2× voltage but similar efficiency to single-series."""
    if p_in_w <= 0:
        return 0.0, 0.0
    v_pk_source = math.sqrt(2 * p_in_w * r_source)
    omega = 2 * math.pi * freq_ghz * 1e9
    z_c   = 1 / (omega * c_j_pf * 1e-12)
    r_rect_approx = min(z_c, r_load / 2)
    v_pk_rect = v_pk_source * r_rect_approx / (r_rect_approx + r_source)

    v_out = max(0, 2 * v_pk_rect - 2 * v_th) * 0.85
    p_out = v_out**2 / r_load
    pce   = min(p_out / p_in_w, 0.90)
    return pce, v_out


def pce_dickson(p_in_w: float, r_source: float, r_load: float,
                v_th: float, n_stages: int, freq_ghz: float,
                c_j_pf: float) -> tuple:
    """
    Dickson charge-pump multiplier.
    Output voltage: V_out ≈ N × (V_pk - V_th) - N × V_th (diode drops)
    """
    if p_in_w <= 0:
        return 0.0, 0.0
    v_pk_source = math.sqrt(2 * p_in_w * r_source)
    omega = 2 * math.pi * freq_ghz * 1e9
    z_c   = 1 / (omega * c_j_pf * 1e-12)
    r_rect_approx = min(z_c, r_load / 4)
    v_pk_rect = v_pk_source * r_rect_approx / (r_rect_approx + r_source)

    # Each stage: gain (V_pk - V_th), loss V_th at each diode
    v_stage = max(0, v_pk_rect - v_th)
    v_out   = max(0, n_stages * v_stage - n_stages * v_th * 0.5) * 0.80
    p_out   = v_out**2 / r_load
    # Dickson has higher overhead losses: cap pumping, higher stage count
    pce     = min(p_out / p_in_w, 0.85) * (1 - 0.03 * n_stages)
    pce     = max(pce, 0.0)
    return pce, v_out


RECTIFIER_FNS = {
    "single_series":   pce_single_series,
    "voltage_doubler": pce_voltage_doubler,
    "dickson":         pce_dickson,
}


def build_pce_curve(topology: str, freq_ghz: float,
                    p_range_dbm=None) -> list:
    """Return a list of {p_in_dbm, pce_pct, v_out_V} dicts."""
    if p_range_dbm is None:
        p_range_dbm = list(range(-30, 0))

    fn = RECTIFIER_FNS.get(topology, pce_single_series)
    results = []

    for p_dbm in p_range_dbm:
        p_w = dbm_to_w(p_dbm)
        if topology == "dickson":
            pce, v_out = fn(p_w, R_SOURCE_OHM, R_LOAD_OHM,
                            DIODE_V_TH_V, DICKSON_STAGES,
                            freq_ghz, DIODE_C_J_PF)
        else:
            pce, v_out = fn(p_w, R_SOURCE_OHM, R_LOAD_OHM,
                            DIODE_V_TH_V, DIODE_I_S_A,
                            DIODE_IDEALITY, DIODE_C_J_PF, freq_ghz)
        results.append({
            "p_in_dbm": p_dbm,
            "pce_pct": round(pce * 100, 2),
            "v_out_V": round(v_out, 4),
        })
    return results


# ─────────────────────────────────────────────
# 3. MATCHING NETWORK DESIGN
# ─────────────────────────────────────────────

def design_l_network(r_source: float, r_load_rect: float, freq_ghz: float) -> dict:
    """
    Design an L-network to transform r_source → r_load_rect.
    For r_load_rect > r_source (upward transformation).
    """
    if r_load_rect <= r_source:
        # Downward: swap roles
        r_high, r_low = r_source, r_load_rect
    else:
        r_high, r_low = r_load_rect, r_source

    Q  = math.sqrt(r_high / r_low - 1)
    omega = 2 * math.pi * freq_ghz * 1e9

    # Shunt element across high-impedance port
    x_shunt = r_high / Q
    # Series element at low-impedance port
    x_series = r_low * Q

    # Reactance to component
    l_series_nh = round(x_series / omega * 1e9, 2)  # nH
    c_shunt_pf  = round(1 / (omega * x_shunt) * 1e12, 2)  # pF

    return {
        "Q":              round(Q, 3),
        "l_series_nH":    l_series_nh,
        "c_shunt_pF":     c_shunt_pf,
        "r_source_ohm":   r_source,
        "r_load_ohm":     r_load_rect,
        "freq_ghz":       freq_ghz,
        "bandwidth_approx_mhz": round(freq_ghz * 1000 / Q, 1),
    }


# ─────────────────────────────────────────────
# 4. ENERGY BUFFER ANALYSIS
# ─────────────────────────────────────────────

def analyze_buffer(c_uf: float, c_v_rating: float,
                   v_out: float, load_ma: float, load_ms: float,
                   period_s: float, i_harvest_ua: float) -> dict:
    """Analyze charge/discharge cycle of storage capacitor."""
    c_f = c_uf * 1e-6
    i_load = load_ma * 1e-3
    t_active = load_ms * 1e-3

    # Voltage droop during load burst
    dv = i_load * t_active / c_f
    dv_pct = 100 * dv / v_out

    # Charge time to recover from droop
    q_depleted = i_load * t_active  # C
    i_charge   = i_harvest_ua * 1e-6
    t_charge_s = q_depleted / i_charge if i_charge > 0 else float("inf")

    # Startup time from 0 V
    t_startup_s = (c_f * v_out) / i_charge if i_charge > 0 else float("inf")

    duty_cycle_pct = 100 * t_active / period_s

    return {
        "capacitance_uF":         c_uf,
        "voltage_rating_V":       c_v_rating,
        "load_burst_mA":          load_ma,
        "load_burst_ms":          load_ms,
        "period_s":               period_s,
        "duty_cycle_pct":         round(duty_cycle_pct, 3),
        "voltage_droop_V":        round(dv, 4),
        "voltage_droop_pct":      round(dv_pct, 2),
        "droop_within_5pct_ok":   bool(dv_pct <= 5.0),
        "charge_recovery_time_s": round(t_charge_s, 2),
        "startup_time_from_0_s":  round(t_startup_s, 1),
        "harvest_current_ua":     i_harvest_ua,
    }


# ─────────────────────────────────────────────
# 5. MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="E-Harvest RF Energy Harvesting Designer")
    parser.add_argument("--output",    default="submission/eharvest_design_report.json")
    parser.add_argument("--rectifier", default=RECTIFIER_TOPOLOGY,
                        choices=["single_series", "voltage_doubler", "dickson"])
    parser.add_argument("--freq1_ghz", type=float, default=FREQ1_GHZ)
    parser.add_argument("--freq2_ghz", type=float, default=FREQ2_GHZ)
    args = parser.parse_args()

    topo  = args.rectifier
    f1    = args.freq1_ghz
    f2    = args.freq2_ghz

    print("=" * 60)
    print("E-Harvest — RF Energy Harvesting Design Worksheet")
    print("=" * 60)

    # ── Link budget at both frequencies ──
    lb1 = link_budget(P_IN_MAX_DBM, ANT_GAIN_DBI_915, ANT_EFF_PCT, MATCH_IL_DB_915)
    lb2 = link_budget(P_IN_MAX_DBM, ANT_GAIN_DBI_24,  ANT_EFF_PCT, MATCH_IL_DB_24)
    print(f"\n[LINK] @{f1} GHz: available={lb1['p_ambient_w']} μW → "
          f"rectifier input={lb1['p_rectifier_input_w']} μW")
    print(f"[LINK] @{f2} GHz: available={lb2['p_ambient_w']} μW → "
          f"rectifier input={lb2['p_rectifier_input_w']} μW")

    # ── Rectifier PCE curves ──
    p_range = list(range(-25, 0))
    curve1 = build_pce_curve(topo, f1, p_range)
    curve2 = build_pce_curve(topo, f2, p_range)

    pce_at_design_f1 = next((r["pce_pct"] for r in curve1 if r["p_in_dbm"] == -10), 0)
    pce_at_design_f2 = next((r["pce_pct"] for r in curve2 if r["p_in_dbm"] == -10), 0)
    v_out_f1 = next((r["v_out_V"] for r in curve1 if r["p_in_dbm"] == -10), 0)
    v_out_f2 = next((r["v_out_V"] for r in curve2 if r["p_in_dbm"] == -10), 0)

    print(f"\n[PCE ] @{f1} GHz, -10 dBm: {pce_at_design_f1:.1f} %  "
          f"(target >40 %) {'PASS' if pce_at_design_f1 >= 40 else 'FAIL'}")
    print(f"[PCE ] @{f2} GHz, -10 dBm: {pce_at_design_f2:.1f} %  "
          f"(target >40 %) {'PASS' if pce_at_design_f2 >= 40 else 'FAIL'}")
    print(f"[VOUT] @{f1} GHz: {v_out_f1:.3f} V (before regulator)")
    print(f"[VOUT] @{f2} GHz: {v_out_f2:.3f} V (before regulator)")

    # ── Matching network ──
    fn = RECTIFIER_FNS.get(topo, pce_single_series)
    p_design = dbm_to_w(-10)
    if topo == "dickson":
        _, v_out_temp = fn(p_design, R_SOURCE_OHM, R_LOAD_OHM,
                           DIODE_V_TH_V, DICKSON_STAGES, f1, DIODE_C_J_PF)
    else:
        _, v_out_temp = fn(p_design, R_SOURCE_OHM, R_LOAD_OHM,
                           DIODE_V_TH_V, DIODE_I_S_A, DIODE_IDEALITY, DIODE_C_J_PF, f1)

    r_rect_estimate = R_LOAD_OHM  # approximate rectifier input impedance
    match1 = design_l_network(R_SOURCE_OHM, r_rect_estimate, f1)
    match2 = design_l_network(R_SOURCE_OHM, r_rect_estimate, f2)
    print(f"\n[MATCH] @{f1} GHz: Q={match1['Q']:.2f}, "
          f"L={match1['l_series_nH']} nH, C={match1['c_shunt_pF']} pF")
    print(f"[MATCH] @{f2} GHz: Q={match2['Q']:.2f}, "
          f"L={match2['l_series_nH']} nH, C={match2['c_shunt_pF']} pF")

    # ── Energy buffer ──
    i_harvest_ua = pce_at_design_f1 / 100 * dbm_to_w(-15) * 1e6  # μA (avg, -15 dBm)
    buf = analyze_buffer(C_BUFFER_UF, C_BUFFER_V_RATING,
                         V_OUT_TARGET_V, LOAD_BURST_MA, LOAD_BURST_MS,
                         LOAD_PERIOD_S, max(i_harvest_ua, 0.1))
    print(f"\n[BUF ] Voltage droop: {buf['voltage_droop_V']*1000:.1f} mV "
          f"({buf['voltage_droop_pct']:.1f} %)  "
          f"{'OK' if buf['droop_within_5pct_ok'] else 'OVER 5%'}")
    print(f"[BUF ] Startup time: {buf['startup_time_from_0_s']:.1f} s")

    # ── Output voltage stability over input power range ──
    v_out_table = []
    for p_dbm in range(-20, -9):
        p_w = dbm_to_w(p_dbm)
        if topo == "dickson":
            _, v_rect = fn(p_w, R_SOURCE_OHM, R_LOAD_OHM,
                           DIODE_V_TH_V, DICKSON_STAGES, f1, DIODE_C_J_PF)
        else:
            _, v_rect = fn(p_w, R_SOURCE_OHM, R_LOAD_OHM,
                           DIODE_V_TH_V, DIODE_I_S_A, DIODE_IDEALITY, DIODE_C_J_PF, f1)
        # After regulator: clamped to V_OUT_TARGET if above V_IN_MIN
        v_reg = V_OUT_TARGET_V if v_rect >= REGULATOR_V_IN_MIN_V else v_rect * REGULATOR_EFF_PCT / 100
        v_out_table.append({
            "p_in_dbm": p_dbm,
            "v_rect_V": round(v_rect, 4),
            "v_out_V":  round(v_reg, 4),
            "stable":   bool(abs(v_reg - V_OUT_TARGET_V) / V_OUT_TARGET_V <= V_OUT_TOL),
        })

    stable_range = [r["p_in_dbm"] for r in v_out_table if r["stable"]]
    print(f"[VREG] Stable output range: {min(stable_range) if stable_range else 'N/A'} to "
          f"{max(stable_range) if stable_range else 'N/A'} dBm")

    # ── Assemble report ──
    report = {
        "antenna_design": {
            "type":              ANTENNA_TYPE,
            "freq1_ghz":         f1,
            "freq2_ghz":         f2,
            "gain_dbi_freq1":    ANT_GAIN_DBI_915,
            "gain_dbi_freq2":    ANT_GAIN_DBI_24,
            "s11_db_freq1":      ANT_S11_DB_915,
            "s11_db_freq2":      ANT_S11_DB_24,
            "bandwidth_mhz_freq1": ANT_BANDWIDTH_MHZ_915,
            "bandwidth_mhz_freq2": ANT_BANDWIDTH_MHZ_24,
            "efficiency_pct":    ANT_EFF_PCT,
            "pcb_size_mm":       PCB_AREA_MM,
            "substrate":         "FR4, εr=4.4, h=1.6 mm",
            "dimensions_note": (
                "PIFA: main element ≈ λ/4 at 915 MHz (~81 mm — folded to fit 50 mm). "
                "Secondary resonance tuned to 2.4 GHz by tuning stub length."
            ),
        },
        "matching_network": {
            "topology":   MATCH_TOPOLOGY,
            "freq1": {**match1, "insertion_loss_db": MATCH_IL_DB_915},
            "freq2": {**match2, "insertion_loss_db": MATCH_IL_DB_24},
            "diplexer_note": (
                "A diplexer (high-pass / low-pass filter pair) splits the antenna "
                "signal into 915 MHz and 2.4 GHz paths before their respective "
                "L-networks and rectifiers. This avoids mutual loading."
            ),
        },
        "rectifier_circuit": {
            "topology":           topo,
            "diode":              DIODE_PART,
            "v_threshold_V":      DIODE_V_TH_V,
            "c_junction_pF":      DIODE_C_J_PF,
            "n_stages":           DICKSON_STAGES if topo == "dickson" else 1,
            "r_load_ohm":         R_LOAD_OHM,
            "pce_curve_freq1":    curve1,
            "pce_curve_freq2":    curve2,
            "pce_at_neg10dbm_freq1_pct": pce_at_design_f1,
            "pce_at_neg10dbm_freq2_pct": pce_at_design_f2,
            "pce_target_met_freq1": bool(pce_at_design_f1 >= PCE_TARGET * 100),
            "pce_target_met_freq2": bool(pce_at_design_f2 >= PCE_TARGET * 100),
        },
        "voltage_regulator": {
            "type":             REGULATOR_TYPE,
            "iq_nA":            REGULATOR_IQ_UA * 1000,
            "v_out_V":          REGULATOR_V_OUT_V,
            "v_in_min_V":       REGULATOR_V_IN_MIN_V,
            "efficiency_pct":   REGULATOR_EFF_PCT,
            "note": (
                "Ultra-low quiescent current LDO (25 nA Iq) ensures regulator "
                "overhead is negligible vs 100 μW harvested power. "
                "Cold-start circuit (S-882Z) needed if V_rect starts below 1.8 V."
            ),
        },
        "energy_buffer": buf,
        "simulation_results": {
            "pce_vs_input_power_freq1": curve1,
            "pce_vs_input_power_freq2": curve2,
            "output_voltage_vs_input_power": v_out_table,
            "startup_waveform_note": (
                f"Capacitor {C_BUFFER_UF} μF charges from 0 V. "
                f"Estimated startup time: {buf['startup_time_from_0_s']:.1f} s "
                f"at {i_harvest_ua:.1f} μA harvest current. "
                "Full transient simulation recommended in LTSpice or ADS."
            ),
            "link_budget_freq1": lb1,
            "link_budget_freq2": lb2,
        },
        "pcb_layout_notes": {
            "layers":            "2-layer (signal + ground plane)",
            "trace_width_rf_mm": 2.8,  # 50 Ω microstrip on FR4 1.6 mm
            "ground_plane":      "Full bottom layer ground; RF components on top layer",
            "component_placement": (
                "Antenna in top-left quadrant. Matching network immediately adjacent "
                "to antenna feed to minimize parasitic inductance. Rectifier and output "
                "filter in top-right quadrant. Regulator and capacitor near load connector."
            ),
            "decoupling":        "100 pF + 10 nF at every power supply pin",
            "pcb_size_mm":       f"{PCB_AREA_MM} × {PCB_AREA_MM}",
        },
        # TODO: add S-parameter data from HFSS/ADS simulation
        # TODO: add full efficiency map from circuit simulator (Spectre/ADS HB)
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n[INFO] Design report saved to {out_path}")

    overall_ok = all([
        pce_at_design_f1 >= PCE_TARGET * 100,
        buf["droop_within_5pct_ok"],
        v_out_f1 >= REGULATOR_V_IN_MIN_V,
    ])
    print(f"\n{'[PASS] Core targets met.' if overall_ok else '[FAIL] Targets not met — iterate parameters.'}")


if __name__ == "__main__":
    main()
