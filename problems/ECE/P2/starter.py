"""
MIMO-Sat — LEO Satellite Communication Link Design Starter
==========================================================
Problem: Design a Ku-band LEO satellite link at 550 km altitude.
  Downlink: 100 Mbps at BER 1e-6  (12 GHz)
  Uplink  :  10 Mbps at BER 1e-6  (14 GHz)

Key parameters:
    Orbit altitude    : 550 km
    Downlink frequency: 12 GHz
    Uplink frequency  : 14 GHz
    Ground dish       : 1.2 m parabolic
    Satellite array   : 256-element phased array
    Rain zone         : Tropical (ITU-R worst-case)

Usage:
    python starter.py --output submission.json
    python starter.py --scenario scenario.json --output submission.json
"""

import argparse
import json
import os
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

# ─── Physical / system constants ─────────────────────────────────────────────
C = 3e8
K_B = 1.38e-23
T0 = 290.0
RE = 6371e3          # Earth radius (m)
GM = 3.986e14        # Earth gravitational parameter (m^3/s^2)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ORBITAL GEOMETRY
# ═════════════════════════════════════════════════════════════════════════════

def compute_orbital_geometry(altitude_m: float, elevation_deg: float) -> dict:
    """
    Compute satellite link geometry for a given elevation angle.

    Returns:
        slant_range_m     : actual path length from ground to satellite
        incidence_angle_deg: angle from satellite sub-point
        sat_velocity_mps  : orbital velocity at altitude
        los_velocity_mps  : line-of-sight component of satellite velocity
        doppler_hz_dl     : Doppler shift at 12 GHz downlink
        doppler_hz_ul     : Doppler shift at 14 GHz uplink
    """
    h = altitude_m
    el = np.radians(elevation_deg)

    # ── TODO 1: Compute slant range using geometry
    #   Exact formula: R = sqrt((Re+h)^2 - Re^2*cos^2(el)) - Re*sin(el)
    slant_range = np.sqrt((RE + h) ** 2 - RE ** 2 * np.cos(el) ** 2) - RE * np.sin(el)  # PLACEHOLDER

    # ── TODO 2: Compute orbital velocity at altitude h
    #   v_sat = sqrt(GM / (Re + h))
    v_sat = np.sqrt(GM / (RE + h))   # PLACEHOLDER

    # ── TODO 3: Compute LOS velocity component
    #   For a satellite pass, worst-case LOS velocity ~ v_sat * cos(elevation)
    v_los = v_sat * np.cos(el)       # PLACEHOLDER — simplified; exact depends on pass geometry

    f_dl = 12e9
    f_ul = 14e9
    doppler_dl = f_dl * v_los / C
    doppler_ul = f_ul * v_los / C

    return {
        "slant_range_m": float(slant_range),
        "elevation_deg": elevation_deg,
        "sat_velocity_mps": float(v_sat),
        "los_velocity_mps": float(v_los),
        "doppler_hz_dl": float(doppler_dl),
        "doppler_hz_ul": float(doppler_ul),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ATMOSPHERIC MODELS
# ═════════════════════════════════════════════════════════════════════════════

def itu_r_rain_attenuation(freq_hz: float, elevation_deg: float,
                           rain_rate_mmhr: float = 50.0) -> float:
    """
    Estimate rain attenuation using ITU-R P.838 specific attenuation +
    P.618 path length model (simplified tropical zone).

    Args:
        freq_hz       : carrier frequency (Hz)
        elevation_deg : elevation angle (degrees)
        rain_rate_mmhr: rain rate (mm/hr), default 50 mm/hr (tropical)

    Returns:
        rain_attenuation_db : slant-path rain attenuation (dB)
    """
    f_ghz = freq_hz / 1e9
    el_rad = np.radians(elevation_deg)

    # ── TODO 4: Look up ITU-R P.838 k and alpha coefficients for given frequency
    #   Approximate (horizontal polarisation at 12 GHz): k~0.0188, alpha~1.217
    #   Approximate (horizontal polarisation at 14 GHz): k~0.0367, alpha~1.154
    if f_ghz < 13:
        k_coef = 0.0188
        alpha_coef = 1.217
    else:
        k_coef = 0.0367
        alpha_coef = 1.154

    # Specific rain attenuation (dB/km)
    gamma_r = k_coef * (rain_rate_mmhr ** alpha_coef)   # PLACEHOLDER

    # ── TODO 5: Compute effective slant path length through rain layer
    #   Rain height h_rain ~ 4 km (tropical), effective path = h_rain / sin(el)
    h_rain = 4000.0   # m
    l_eff_km = (h_rain / np.sin(el_rad)) / 1000.0       # PLACEHOLDER

    rain_att = gamma_r * l_eff_km
    return float(rain_att)


def atmospheric_absorption_db(freq_hz: float, slant_range_m: float,
                               elevation_deg: float) -> float:
    """
    Approximate gaseous absorption (oxygen + water vapour) along slant path.
    Uses a simplified 0.05 dB/km model at Ku-band (replace with ITU-R P.676).
    """
    # ── TODO 6: Use ITU-R P.676 for accurate atmospheric absorption
    absorption_db_per_km = 0.05    # PLACEHOLDER (dB/km at Ku-band)
    path_km = slant_range_m / 1000.0
    return float(absorption_db_per_km * path_km)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ANTENNA MODELS
# ═════════════════════════════════════════════════════════════════════════════

def parabolic_dish_gain_db(diameter_m: float, freq_hz: float,
                            efficiency: float = 0.6) -> float:
    """Compute gain of a parabolic dish antenna (dBi)."""
    lam = C / freq_hz
    # ── TODO 7: G = eta * (pi * D / lambda)^2
    gain_lin = efficiency * (np.pi * diameter_m / lam) ** 2   # PLACEHOLDER
    return float(10 * np.log10(gain_lin))


def phased_array_gain_db(n_elements: int, freq_hz: float,
                          d_spacing: float = None,
                          scan_elevation_deg: float = 90.0,
                          efficiency: float = 0.6) -> float:
    """
    Compute phased array gain including scan loss.

    Args:
        n_elements        : number of radiating elements
        freq_hz           : carrier frequency (Hz)
        d_spacing         : element spacing (default lambda/2)
        scan_elevation_deg: elevation angle of beam pointing
        efficiency        : aperture efficiency

    Returns:
        gain_db : array gain in dBi including scan loss
    """
    lam = C / freq_hz
    if d_spacing is None:
        d_spacing = lam / 2.0

    # ── TODO 8: G_array = N * G_element * scan_loss
    #   Scan loss = cos(theta_scan) where theta_scan = 90 - elevation (zenith angle)
    theta_scan = np.radians(90.0 - scan_elevation_deg)
    scan_loss = np.cos(theta_scan)

    # Single element gain ~ 5 dBi for a patch (linear: ~3.16)
    g_element = 3.16
    gain_lin = efficiency * n_elements * g_element * scan_loss   # PLACEHOLDER
    return float(10 * np.log10(max(gain_lin, 1e-10)))


def system_noise_temp_k(t_sky_k: float = 30.0, t_lna_k: float = 50.0,
                         feed_loss_db: float = 0.5) -> float:
    """
    Compute system noise temperature.
    T_sys = T_sky + T_feed + T_LNA/L_feed  (simplified)
    """
    # ── TODO 9: T_sys = T_ant + T_feed*(1 - 1/L) + T_LNA/L
    feed_loss_lin = 10 ** (feed_loss_db / 10.0)
    t_feed = T0 * (1 - 1 / feed_loss_lin)
    t_sys = t_sky_k + t_feed + t_lna_k / feed_loss_lin   # PLACEHOLDER
    return float(t_sys)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — LINK BUDGET
# ═════════════════════════════════════════════════════════════════════════════

def link_budget(link_dir: str, geom: dict, params: dict) -> dict:
    """
    Compute link budget for downlink or uplink.

    Args:
        link_dir : "downlink" or "uplink"
        geom     : output of compute_orbital_geometry()
        params   : dict with 'data_rate_bps', 'tx_power_w_per_element',
                   'n_tx_elements', 'rx_dish_diam_m', 'rain_rate_mmhr'

    Returns:
        dict with EIRP, FSPL, rain_att, atm_abs, G_over_T,
             received_C_over_N0, Eb_N0, link_margin_db
    """
    if link_dir == "downlink":
        freq = 12e9
        tx_n_elem = params.get("n_tx_elements", 256)
        tx_power_per_elem_w = params.get("tx_power_w_per_element", 0.5)
        rx_dish_diam = params.get("rx_dish_diam_m", 1.2)
        data_rate = params.get("dl_data_rate_bps", 100e6)
        el = geom["elevation_deg"]

        # ── TODO 10: Compute satellite EIRP
        pt_total_w = tx_n_elem * tx_power_per_elem_w
        pt_dbw = 10 * np.log10(pt_total_w)
        g_tx_db = phased_array_gain_db(tx_n_elem, freq, scan_elevation_deg=el)
        eirp_dbw = pt_dbw + g_tx_db

        # RX side
        g_rx_db = parabolic_dish_gain_db(rx_dish_diam, freq)
        t_sys = system_noise_temp_k()
        g_over_t_db = g_rx_db - 10 * np.log10(t_sys)

    else:  # uplink
        freq = 14e9
        tx_power_w = params.get("ul_tx_power_w", 5.0)
        tx_dish_diam = params.get("ul_tx_dish_diam_m", 1.2)
        el = geom["elevation_deg"]

        g_tx_db = parabolic_dish_gain_db(tx_dish_diam, freq)
        pt_dbw = 10 * np.log10(tx_power_w)
        eirp_dbw = pt_dbw + g_tx_db

        # Satellite RX (256-element array)
        n_rx_elem = params.get("n_rx_elements", 256)
        g_rx_db = phased_array_gain_db(n_rx_elem, freq, scan_elevation_deg=el)
        t_sys = system_noise_temp_k(t_sky_k=50.0, t_lna_k=80.0)
        g_over_t_db = g_rx_db - 10 * np.log10(t_sys)
        data_rate = params.get("ul_data_rate_bps", 10e6)

    # ── TODO 11: Free-space path loss
    R = geom["slant_range_m"]
    lam = C / freq
    fspl_db = 20 * np.log10(4 * np.pi * R / lam)    # PLACEHOLDER

    # Atmospheric losses
    rain_att = itu_r_rain_attenuation(freq, el, params.get("rain_rate_mmhr", 50.0))
    atm_abs = atmospheric_absorption_db(freq, R, el)
    total_loss = fspl_db + rain_att + atm_abs

    # C/N0 (dBHz)
    k_db = 10 * np.log10(K_B)   # -228.6 dBW/Hz/K
    c_over_n0 = eirp_dbw - total_loss + g_over_t_db - k_db

    # Eb/N0
    eb_n0_db = c_over_n0 - 10 * np.log10(data_rate)

    return {
        "eirp_dbw": round(eirp_dbw, 2),
        "fspl_db": round(fspl_db, 2),
        "rain_attenuation_db": round(rain_att, 2),
        "atmospheric_abs_db": round(atm_abs, 2),
        "g_over_t_db_per_k": round(g_over_t_db, 2),
        "received_c_over_n0_dbhz": round(c_over_n0, 2),
        "eb_n0_db": round(eb_n0_db, 2),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — MODULATION AND CODING SELECTION
# ═════════════════════════════════════════════════════════════════════════════

# DVB-S2 ModCod table (simplified): {name: (spectral_eff, required_eb_n0_db)}
MODCOD_TABLE = {
    "QPSK_1/2":    (1.00,  1.0),
    "QPSK_3/4":    (1.50,  4.5),
    "8PSK_2/3":    (2.00,  6.6),
    "8PSK_3/4":    (2.25,  7.9),
    "16APSK_3/4":  (3.00, 10.2),
    "16APSK_4/5":  (3.20, 11.0),
    "32APSK_3/4":  (3.75, 12.7),
    "32APSK_4/5":  (4.00, 13.7),
}


def select_modcod(eb_n0_available_db: float, data_rate_bps: float,
                  bandwidth_hz: float = 36e6) -> dict:
    """
    Select best ModCod that fits within available Eb/N0.

    Returns:
        dict with modulation, fec_code, code_rate, spectral_efficiency,
             required_eb_n0_db, margin_db
    """
    # ── TODO 12: Select highest spectral efficiency ModCod whose
    #   required Eb/N0 <= available Eb/N0
    best = None
    best_eff = 0.0
    for name, (spec_eff, req_eb_n0) in MODCOD_TABLE.items():
        if eb_n0_available_db >= req_eb_n0 and spec_eff >= data_rate_bps / bandwidth_hz:
            if spec_eff > best_eff:
                best_eff = spec_eff
                best = (name, spec_eff, req_eb_n0)

    if best is None:
        # Fall back to most robust
        best = ("QPSK_1/2", 1.00, 1.0)

    name, spec_eff, req_eb_n0 = best
    mod, code_rate_str = name.split("_", 1)
    return {
        "modulation": mod,
        "fec_code": "LDPC",
        "code_rate": code_rate_str,
        "spectral_efficiency_bps_per_hz": spec_eff,
        "required_eb_n0_db": req_eb_n0,
        "margin_db": round(eb_n0_available_db - req_eb_n0, 2),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — BEAMFORMING DESIGN
# ═════════════════════════════════════════════════════════════════════════════

def design_beamforming(n_elements: int = 256, freq_hz: float = 12e9,
                       scan_az_deg: float = 0.0,
                       scan_el_deg: float = 45.0) -> dict:
    """
    Design phased array beam: compute gain, HPBW, scan loss, beam hopping schedule.

    Returns:
        dict with beam_gain_db, hpbw_deg, scan_loss_db, beam_hopping_schedule
    """
    lam = C / freq_hz
    n_side = int(np.sqrt(n_elements))     # assume square array
    d = lam / 2.0

    # ── TODO 13: Array gain, HPBW, scan loss
    theta_scan = np.radians(90.0 - scan_el_deg)
    scan_loss_lin = np.cos(theta_scan)
    scan_loss_db = -10 * np.log10(max(scan_loss_lin, 1e-6))

    gain_zenith_db = 10 * np.log10(0.6 * n_elements * 3.16)
    gain_scan_db = gain_zenith_db - scan_loss_db

    # HPBW (radians): 0.886 * lambda / (N_side * d)
    hpbw_rad = 0.886 * lam / (n_side * d)
    hpbw_deg = np.degrees(hpbw_rad)

    # ── TODO 14: Beam hopping schedule
    #   Number of beam spots in coverage zone: approximate
    coverage_half_angle = 60.0  # degrees (satellite footprint)
    n_beams = max(1, int((coverage_half_angle / (hpbw_deg / 2)) ** 2))
    dwell_ms = 100.0 / n_beams   # 100 ms frame, share among beams

    return {
        "array_elements": n_elements,
        "beam_gain_zenith_db": round(gain_zenith_db, 2),
        "beam_gain_at_scan_db": round(gain_scan_db, 2),
        "scan_loss_db_at_scan_angle": round(scan_loss_db, 2),
        "half_power_beamwidth_deg": round(hpbw_deg, 3),
        "scan_elevation_deg": scan_el_deg,
        "n_beam_spots": n_beams,
        "dwell_time_per_beam_ms": round(dwell_ms, 3),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — AVAILABILITY ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════

def compute_availability(link_margin_db: float,
                         rain_rate_exceeded_at_0_1pct: float = 50.0) -> float:
    """
    Estimate link availability using exponential rain exceedance model.

    The link is unavailable when rain attenuation > link_margin_db.
    For tropical zone, exceedance probability ~ exp(-A / a) where a ~ 2.5 dB
    for 12 GHz.

    Returns:
        availability_pct : availability as percentage
    """
    # ── TODO 15: Use ITU-R P.618 statistics for proper availability calculation
    #   Simple model: P(A > link_margin) = p0 * exp(-link_margin / a)
    p0 = 1.0    # tropical zone: 1% exceeded at light rain
    a = 2.5     # shape parameter (dB)
    p_outage = p0 * np.exp(-link_margin_db / a)
    availability = 100.0 * (1.0 - p_outage / 100.0)
    return float(availability)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — BER SIMULATION (OPTIONAL)
# ═════════════════════════════════════════════════════════════════════════════

def simulate_ber_curve(modulation: str = "QPSK",
                       eb_n0_range_db: np.ndarray = None) -> dict:
    """
    Compute theoretical BER vs Eb/N0 for selected modulation (AWGN channel).

    Returns:
        dict with eb_n0_db_list and ber_list
    """
    from scipy.special import erfc

    if eb_n0_range_db is None:
        eb_n0_range_db = np.linspace(0, 15, 50)

    eb_n0_lin = 10 ** (eb_n0_range_db / 10.0)

    # ── TODO 16: Implement BER formulas for each modulation
    if modulation == "QPSK":
        ber = 0.5 * erfc(np.sqrt(eb_n0_lin))
    elif modulation == "8PSK":
        # Approximate: BER ≈ (2/3) * erfc(sqrt(eb_n0 * sin^2(pi/8) * log2(8)))
        ber = (2.0 / 3.0) * erfc(np.sqrt(eb_n0_lin * np.sin(np.pi / 8) ** 2 * 3))
    else:
        ber = 0.5 * erfc(np.sqrt(eb_n0_lin))   # PLACEHOLDER

    return {
        "eb_n0_db": eb_n0_range_db.tolist(),
        "ber": np.clip(ber, 1e-12, 1.0).tolist(),
        "modulation": modulation,
    }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="MIMO-Sat LEO link design tool")
    parser.add_argument("--scenario", default=None,
                        help="JSON file with scenario overrides")
    parser.add_argument("--output", default="submission.json",
                        help="Output submission JSON path")
    parser.add_argument("--plot", action="store_true",
                        help="Generate BER curve plot")
    args = parser.parse_args()

    # Default parameters
    scenario = {
        "altitude_m": 550e3,
        "elevation_deg": 45.0,
        "rain_rate_mmhr": 50.0,
        "n_tx_elements": 256,
        "tx_power_w_per_element": 0.5,
        "rx_dish_diam_m": 1.2,
        "dl_data_rate_bps": 100e6,
        "ul_data_rate_bps": 10e6,
        "ul_tx_power_w": 5.0,
        "ul_tx_dish_diam_m": 1.2,
        "n_rx_elements": 256,
        "transponder_bandwidth_hz": 36e6,
    }
    if args.scenario and os.path.exists(args.scenario):
        with open(args.scenario) as f:
            scenario.update(json.load(f))

    print("[MIMO-Sat] Step 1: Computing orbital geometry...")
    geom = compute_orbital_geometry(scenario["altitude_m"], scenario["elevation_deg"])
    print(f"  Slant range   : {geom['slant_range_m']/1e3:.1f} km")
    print(f"  Sat velocity  : {geom['sat_velocity_mps']/1e3:.2f} km/s")
    print(f"  Max Doppler DL: {geom['doppler_hz_dl']/1e3:.1f} kHz")
    print(f"  Max Doppler UL: {geom['doppler_hz_ul']/1e3:.1f} kHz")

    print("[MIMO-Sat] Step 2: Downlink link budget...")
    dl_budget = link_budget("downlink", geom, scenario)
    for k, v in dl_budget.items():
        print(f"  {k:35s}: {v}")

    print("[MIMO-Sat] Step 3: Uplink link budget...")
    ul_budget = link_budget("uplink", geom, scenario)
    for k, v in ul_budget.items():
        print(f"  {k:35s}: {v}")

    print("[MIMO-Sat] Step 4: Modulation and coding selection...")
    dl_modcod = select_modcod(dl_budget["eb_n0_db"], scenario["dl_data_rate_bps"],
                               scenario["transponder_bandwidth_hz"])
    ul_modcod = select_modcod(ul_budget["eb_n0_db"], scenario["ul_data_rate_bps"],
                               scenario["transponder_bandwidth_hz"])
    print(f"  DL ModCod: {dl_modcod['modulation']}-{dl_modcod['code_rate']} "
          f"(margin: {dl_modcod['margin_db']:.1f} dB)")
    print(f"  UL ModCod: {ul_modcod['modulation']}-{ul_modcod['code_rate']} "
          f"(margin: {ul_modcod['margin_db']:.1f} dB)")

    print("[MIMO-Sat] Step 5: Beamforming design...")
    bf = design_beamforming(n_elements=256, freq_hz=12e9,
                             scan_el_deg=scenario["elevation_deg"])
    print(f"  Beam gain @ zenith : {bf['beam_gain_zenith_db']:.1f} dBi")
    print(f"  Scan loss          : {bf['scan_loss_db_at_scan_angle']:.1f} dB")
    print(f"  HPBW               : {bf['half_power_beamwidth_deg']:.3f} deg")

    print("[MIMO-Sat] Step 6: Availability analysis...")
    link_margin = dl_budget.get("eb_n0_db", 5.0) - dl_modcod["required_eb_n0_db"]
    avail = compute_availability(max(link_margin, 0.0))
    print(f"  Link margin   : {link_margin:.1f} dB")
    print(f"  Availability  : {avail:.3f}%")

    if args.plot:
        ber_data = simulate_ber_curve(dl_modcod["modulation"])
        if HAS_PLOT:
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.semilogy(ber_data["eb_n0_db"], ber_data["ber"])
            ax.axvline(dl_modcod["required_eb_n0_db"], color="r", linestyle="--",
                       label=f"Required Eb/N0 = {dl_modcod['required_eb_n0_db']} dB")
            ax.set_xlabel("Eb/N0 (dB)")
            ax.set_ylabel("BER")
            ax.set_title(f"BER vs Eb/N0 — {dl_modcod['modulation']}")
            ax.legend()
            ax.grid(True, which="both")
            fig.tight_layout()
            out_dir = os.path.dirname(os.path.abspath(args.output)) or "."
            fig.savefig(os.path.join(out_dir, "ber_curve.png"), dpi=150)
            plt.close(fig)

    # ── Assemble submission JSON ─────────────────────────────────────────────
    submission = {
        "link_budget": {
            "downlink": dl_budget,
            "uplink": ul_budget,
        },
        "modcod": {
            "downlink": dl_modcod,
            "uplink": ul_modcod,
        },
        "beamforming": bf,
        "doppler": {
            "max_doppler_shift_hz_dl": geom["doppler_hz_dl"],
            "max_doppler_shift_hz_ul": geom["doppler_hz_ul"],
            "compensation_method": "Pre-correction via ephemeris + closed-loop AFC",
            "residual_frequency_error_hz": 100.0,   # TODO: compute from tracking loop bandwidth
        },
        "availability": {
            "link_margin_db": round(link_margin, 2),
            "availability_pct": round(avail, 4),
        },
        "geometry": {
            "altitude_km": scenario["altitude_m"] / 1e3,
            "elevation_deg": scenario["elevation_deg"],
            "slant_range_km": round(geom["slant_range_m"] / 1e3, 2),
        },
    }

    with open(args.output, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"\n[MIMO-Sat] Submission saved to: {args.output}")


if __name__ == "__main__":
    main()
