"""
PhotonLink — Free-Space Optical Communication System Starter
=============================================================
Problem: Design a 1550 nm FSO link over 5 km at 10 Gbps, BER 1e-9, 99.9% availability.

Atmospheric challenges:
    Fog         : visibility can drop to 50 m  → use Kim model
    Rain        : up to 50 mm/hr              → ITU-R P.838 for optical
    Scintillation: Cn2 turbulence parameter   → Rytov variance, gamma-gamma distribution
    Pointing    : ±1 mrad building sway       → pointing loss

Usage:
    python starter.py --output submission.json
    python starter.py --scenario scenario.json --output submission.json
"""

import argparse
import json
import os
import numpy as np
from scipy.special import erfc, gamma as gamma_func

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

# ─── Constants ────────────────────────────────────────────────────────────────
C = 3e8
LAMBDA_M = 1550e-9      # wavelength (m)
LINK_RANGE_M = 5000.0   # link distance (m)
DATA_RATE_BPS = 10e9    # 10 Gbps
K_WAVE = 2 * np.pi / LAMBDA_M  # wave number


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ATMOSPHERIC ATTENUATION MODELS
# ═════════════════════════════════════════════════════════════════════════════

def fog_attenuation_kim_model(visibility_m: float,
                               wavelength_nm: float = 1550.0,
                               range_km: float = 5.0) -> float:
    """
    Compute fog/haze attenuation using the Kim empirical model.

    Kim model: specific attenuation alpha = (3.91/V) * (lambda/550)^(-q)  dB/km
    where V is visibility in km, q is a visibility-dependent coefficient.

    Args:
        visibility_m  : meteorological visibility (metres)
        wavelength_nm : optical wavelength (nm), default 1550
        range_km      : link range (km)

    Returns:
        fog_attenuation_db : total path attenuation due to fog/haze (dB)
    """
    V = visibility_m / 1000.0   # convert to km

    # ── TODO 1: Implement Kim model q-factor piecewise selection
    #   q = 1.6           for V > 50 km
    #   q = 1.3           for 6 km < V <= 50 km
    #   q = 0.16*V + 0.34 for 1 km < V <= 6 km   (PLACEHOLDER)
    #   q = V - 0.5       for 0.5 km < V <= 1 km
    #   q = 0             for V <= 0.5 km (dense fog)
    if V > 50:
        q = 1.6
    elif V > 6:
        q = 1.3
    elif V > 1:
        q = 0.16 * V + 0.34      # PLACEHOLDER
    elif V > 0.5:
        q = V - 0.5
    else:
        q = 0.0

    # ── TODO 2: Compute specific attenuation (dB/km)
    alpha = (3.91 / V) * (wavelength_nm / 550.0) ** (-q)   # PLACEHOLDER
    total_attenuation = alpha * range_km
    return float(total_attenuation)


def rain_attenuation_fso(rain_rate_mmhr: float, range_km: float = 5.0) -> float:
    """
    Optical rain attenuation using empirical model.
    At 1550 nm, specific rain attenuation ~ 0.01 * rain_rate^0.6  dB/km (approximate).

    Args:
        rain_rate_mmhr : rain rate (mm/hr)
        range_km       : link range (km)

    Returns:
        rain_attenuation_db : total rain-induced attenuation (dB)
    """
    # ── TODO 3: Use more accurate FSO rain model
    #   Approximate: alpha_rain ≈ 0.01 * R^0.6 dB/km (varies by drop size distribution)
    alpha_rain = 0.01 * (rain_rate_mmhr ** 0.6)   # PLACEHOLDER
    return float(alpha_rain * range_km)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — TURBULENCE / SCINTILLATION MODEL
# ═════════════════════════════════════════════════════════════════════════════

def rytov_variance(Cn2: float, L: float = LINK_RANGE_M,
                   wavelength: float = LAMBDA_M) -> float:
    """
    Compute Rytov variance (spherical wave approximation).

    sigma_R^2 = 0.5 * Cn2 * k^(7/6) * L^(11/6)

    Args:
        Cn2        : refractive index structure parameter (m^(-2/3))
        L          : propagation distance (m)
        wavelength : optical wavelength (m)

    Returns:
        sigma_R2 : Rytov variance (dimensionless)
    """
    k = 2 * np.pi / wavelength
    # ── TODO 4: Implement Rytov variance formula
    sigma_R2 = 0.5 * Cn2 * (k ** (7 / 6)) * (L ** (11 / 6))   # PLACEHOLDER
    return float(sigma_R2)


def fried_parameter_r0(Cn2: float, L: float = LINK_RANGE_M,
                        wavelength: float = LAMBDA_M) -> float:
    """
    Compute Fried coherence parameter r0 (m).
    r0 = (0.423 * k^2 * Cn2 * L)^(-3/5)

    Larger r0 = better seeing (less turbulence).
    """
    k = 2 * np.pi / wavelength
    # ── TODO 5: Implement Fried parameter
    r0 = (0.423 * k ** 2 * Cn2 * L) ** (-3 / 5)   # PLACEHOLDER
    return float(r0)


def aperture_averaging_factor(D_rx: float, L: float = LINK_RANGE_M,
                               wavelength: float = LAMBDA_M) -> float:
    """
    Compute aperture averaging factor A (Churnside approximation).
    A = [1 + 1.1 * (D^2 / (lambda * L))^(7/6)]^(-1)
    Reduces scintillation index for finite receiver aperture.
    """
    # ── TODO 6: Implement aperture averaging factor
    x = (D_rx ** 2) / (wavelength * L)
    A = 1.0 / (1.0 + 1.1 * x ** (7 / 6))   # PLACEHOLDER
    return float(A)


def gamma_gamma_ber_ook(mean_snr_linear: float, sigma_R2: float,
                         n_samples: int = 100000) -> float:
    """
    Estimate BER for OOK modulation over a gamma-gamma turbulence channel
    using Monte Carlo integration.

    The irradiance I follows a gamma-gamma distribution parameterised by
    alpha (large-scale) and beta (small-scale) scintillation indices.

    Args:
        mean_snr_linear : mean electrical SNR (linear)
        sigma_R2        : Rytov variance
        n_samples       : Monte Carlo samples

    Returns:
        ber : bit error rate
    """
    # ── TODO 7: Derive alpha, beta from sigma_R2
    #   Simplified (log-normal for weak turbulence):
    #   sigma_ln_I^2 = sigma_R^2 (weak regime)
    #   For gamma-gamma: alpha = exp(sigma_ln_x^2) - 1)^(-1)
    if sigma_R2 < 0.3:
        # Log-normal approximation (weak turbulence)
        sigma_ln = np.sqrt(0.307 * sigma_R2)  # PLACEHOLDER
        ln_I_samples = np.random.normal(-0.5 * sigma_ln ** 2, sigma_ln, n_samples)
        I_samples = np.exp(ln_I_samples)
    else:
        # Gamma-gamma Monte Carlo
        # Parameters (approximate)
        alpha_gg = max(1.01, (np.exp(0.49 * sigma_R2 / (1 + 1.11 * sigma_R2 ** (6 / 5)) ** (7 / 6)) - 1) ** (-1))
        beta_gg = max(1.01, (np.exp(0.51 * sigma_R2 / (1 + 0.69 * sigma_R2 ** (6 / 5)) ** (5 / 6)) - 1) ** (-1))
        # Draw samples: I = Ix * Iy, Ix ~ Gamma(alpha), Iy ~ Gamma(beta)
        Ix = np.random.gamma(alpha_gg, 1.0 / alpha_gg, n_samples)
        Iy = np.random.gamma(beta_gg, 1.0 / beta_gg, n_samples)
        I_samples = Ix * Iy

    # BER for OOK (direct detection): BER = 0.5 * erfc(sqrt(SNR * I / 2))
    snr_per_sample = mean_snr_linear * I_samples
    ber_samples = 0.5 * erfc(np.sqrt(np.maximum(snr_per_sample / 2.0, 0)))
    return float(np.mean(ber_samples))


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — POINTING LOSS
# ═════════════════════════════════════════════════════════════════════════════

def pointing_loss_db(pointing_error_rad: float, beam_radius_at_rx_m: float) -> float:
    """
    Compute pointing loss for a Gaussian beam.
    L_point = -10 * log10(exp(-2 * (r / w)^2))
    where r is pointing error displacement at receiver plane.

    Args:
        pointing_error_rad  : RMS pointing error (radians)
        beam_radius_at_rx_m : 1/e^2 Gaussian beam radius at receiver (m)

    Returns:
        pointing_loss_db : loss in dB (positive value)
    """
    r = pointing_error_rad * LINK_RANGE_M   # displacement at receiver (m)
    # ── TODO 8: Compute pointing loss
    loss_lin = np.exp(-2.0 * (r / beam_radius_at_rx_m) ** 2)
    loss_db = -10.0 * np.log10(max(loss_lin, 1e-20))
    return float(loss_db)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — GEOMETRIC LOSS
# ═════════════════════════════════════════════════════════════════════════════

def geometric_loss_db(beam_divergence_rad: float, rx_aperture_diam_m: float,
                       range_m: float = LINK_RANGE_M) -> float:
    """
    Compute geometric (diffraction) loss.
    For a Gaussian beam: w(L) = theta * L  (far field approximation)
    Loss = 20 * log10(2 * w(L) / D_rx)  when beam > aperture

    Args:
        beam_divergence_rad  : half-angle beam divergence (radians)
        rx_aperture_diam_m   : receiver aperture diameter (m)
        range_m              : link range (m)

    Returns:
        geo_loss_db : geometric path loss (dB)
    """
    # ── TODO 9: Compute beam radius at receiver and geometric loss
    w_L = beam_divergence_rad * range_m      # beam radius at receiver (m)
    D_rx = rx_aperture_diam_m
    if w_L > D_rx / 2:
        # Fraction of power collected = (D_rx / (2*w_L))^2
        fraction = (D_rx / (2.0 * w_L)) ** 2
        loss_db = -10.0 * np.log10(max(fraction, 1e-20))
    else:
        loss_db = 0.0   # aperture captures full beam
    return float(loss_db)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — RECEIVER SENSITIVITY
# ═════════════════════════════════════════════════════════════════════════════

def receiver_sensitivity_dbm(data_rate_bps: float = DATA_RATE_BPS,
                               target_ber: float = 1e-9,
                               modulation: str = "OOK") -> float:
    """
    Estimate receiver sensitivity (minimum detectable power) for a given BER.
    Typical APD receiver at 10 Gbps, 1550 nm: ~-28 dBm for BER = 1e-9 with OOK.

    Args:
        data_rate_bps : data rate (bps)
        target_ber    : required BER
        modulation    : modulation format

    Returns:
        sensitivity_dbm : receiver sensitivity in dBm
    """
    # ── TODO 10: Compute sensitivity from noise model
    #   sensitivity = hf * Rb * SNR_req / (2 * quantum_efficiency)
    #   where SNR_req = 2 * erfinv(1 - 2*BER)^2  for OOK
    #   Simplified: use empirical rule ~-28 dBm at 10 Gbps for APD
    h_planck = 6.626e-34
    f_optical = C / LAMBDA_M
    from scipy.special import erfcinv
    snr_req = 2 * (erfcinv(2 * target_ber)) ** 2  # PLACEHOLDER
    # Minimum photon count per bit
    n_photons = snr_req   # very simplified
    p_min_w = n_photons * h_planck * f_optical * data_rate_bps
    # Add practical penalty (~20 dB for real receivers)
    p_min_w_practical = max(p_min_w * 100, 1.58e-8)   # floor at ~-48 dBm practical
    sensitivity_dbm = 10 * np.log10(p_min_w_practical * 1000)
    # Clamp to typical APD range
    sensitivity_dbm = max(sensitivity_dbm, -35.0)
    return float(sensitivity_dbm)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SPATIAL DIVERSITY
# ═════════════════════════════════════════════════════════════════════════════

def compute_diversity_gain(n_tx: int, n_rx: int,
                            aperture_sep_m: float,
                            r0_m: float) -> dict:
    """
    Estimate spatial diversity gain.

    If aperture separation >> r0, apertures are decorrelated → MRC gain ≈ 10*log10(N).
    If separation < r0, gain is reduced.

    Args:
        n_tx         : number of transmit apertures
        n_rx         : number of receive apertures
        aperture_sep_m: separation between apertures (m)
        r0_m         : Fried parameter (m)

    Returns:
        dict with diversity_gain_db and correlation_coefficient
    """
    # ── TODO 11: Compute diversity gain based on aperture separation vs r0
    rho = np.exp(-aperture_sep_m / r0_m)   # simplified spatial correlation
    total_apertures = n_tx * n_rx
    effective_branches = total_apertures * (1 - rho ** 2)
    effective_branches = max(1.0, effective_branches)
    diversity_gain_db = 10.0 * np.log10(effective_branches)

    return {
        "n_tx_apertures": n_tx,
        "n_rx_apertures": n_rx,
        "aperture_separation_m": aperture_sep_m,
        "spatial_correlation": round(float(rho), 4),
        "diversity_gain_db": round(float(diversity_gain_db), 2),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — ADAPTIVE OPTICS
# ═════════════════════════════════════════════════════════════════════════════

def design_adaptive_optics(Cn2: float, wind_speed_mps: float = 5.0,
                            tx_aperture_diam_m: float = 0.1) -> dict:
    """
    Design a basic adaptive optics system (wavefront sensor + deformable mirror).

    Args:
        Cn2               : refractive index structure parameter (m^(-2/3))
        wind_speed_mps    : wind speed across beam path (m/s)
        tx_aperture_diam_m: transmit aperture diameter (m)

    Returns:
        dict with n_actuators, correction_bandwidth_hz, residual_wf_error_nm
    """
    r0 = fried_parameter_r0(Cn2, LINK_RANGE_M, LAMBDA_M)

    # ── TODO 12: Compute number of actuators needed
    #   N_act ≈ (D/r0)^2  (Marechal criterion for diffraction-limited correction)
    D = tx_aperture_diam_m
    n_act = max(1, int((D / r0) ** 2))    # PLACEHOLDER

    # Greenwood frequency (required AO bandwidth)
    f_G = 0.427 * wind_speed_mps / r0     # PLACEHOLDER

    # Residual wavefront error (simplified Marechal approximation)
    sigma_phi2 = 1.0 * (D / r0) ** (5 / 3) / max(n_act, 1) ** (5 / 6)
    sigma_phi_nm = np.sqrt(sigma_phi2) * LAMBDA_M / (2 * np.pi) * 1e9

    return {
        "n_actuators": n_act,
        "wavefront_sensor": "Shack-Hartmann",
        "correction_bandwidth_hz": round(float(f_G), 1),
        "residual_wavefront_error_nm": round(float(sigma_phi_nm), 1),
        "fried_parameter_r0_m": round(float(r0), 4),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — AVAILABILITY
# ═════════════════════════════════════════════════════════════════════════════

def compute_link_budget(params: dict, conditions: dict) -> dict:
    """
    Compute full FSO link budget for given atmospheric conditions.

    Args:
        params     : design parameters (tx_power_dbm, beam_divergence_rad, etc.)
        conditions : atmospheric conditions (visibility_m, rain_rate, Cn2, etc.)

    Returns:
        dict with all link budget components and link_margin_db
    """
    tx_power = params.get("tx_power_dbm", 20.0)
    beam_div = params.get("beam_divergence_rad", 0.2e-3)
    D_rx = params.get("rx_aperture_diam_m", 0.2)
    pointing_err = params.get("pointing_error_rad", 1e-3)

    vis = conditions.get("visibility_m", 1000.0)
    rain_rate = conditions.get("rain_rate_mmhr", 0.0)
    Cn2 = conditions.get("Cn2", 1e-14)

    # ── TODO 13: Assemble all loss terms
    geo_loss = geometric_loss_db(beam_div, D_rx)
    fog_att = fog_attenuation_kim_model(vis, 1550.0, LINK_RANGE_M / 1000.0)
    rain_att = rain_attenuation_fso(rain_rate, LINK_RANGE_M / 1000.0)

    w_L = beam_div * LINK_RANGE_M
    pt_loss = pointing_loss_db(pointing_err, w_L)

    # Scintillation margin (approximate — use sigma_I for fade margin)
    sigma_R2 = rytov_variance(Cn2)
    A = aperture_averaging_factor(D_rx)
    sigma_eff = A * sigma_R2
    scint_margin = 5.0 * np.sqrt(sigma_eff)   # ~5-sigma fade margin (dB), simplified

    total_loss = geo_loss + fog_att + rain_att + pt_loss + scint_margin
    p_rx_dbm = tx_power - total_loss

    sensitivity = receiver_sensitivity_dbm()
    link_margin = p_rx_dbm - sensitivity

    return {
        "tx_power_dbm": round(tx_power, 2),
        "beam_divergence_mrad": round(beam_div * 1e3, 4),
        "rx_aperture_diameter_m": D_rx,
        "geometric_loss_db": round(geo_loss, 2),
        "fog_attenuation_db": round(fog_att, 2),
        "rain_attenuation_db": round(rain_att, 2),
        "scintillation_fade_margin_db": round(float(scint_margin), 2),
        "pointing_loss_db": round(pt_loss, 2),
        "total_loss_db": round(total_loss, 2),
        "received_power_dbm": round(p_rx_dbm, 2),
        "receiver_sensitivity_dbm": round(sensitivity, 2),
        "link_margin_db": round(link_margin, 2),
        "scintillation_sigma_i2": round(float(sigma_eff), 4),
    }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="PhotonLink FSO communication design tool")
    parser.add_argument("--scenario", default=None, help="JSON with atmospheric scenario overrides")
    parser.add_argument("--output", default="submission.json", help="Output submission JSON path")
    parser.add_argument("--plot", action="store_true", help="Generate BER curve plot")
    args = parser.parse_args()

    # Default design parameters
    design_params = {
        "tx_power_dbm": 20.0,          # 100 mW — eye-safe class 1M at 1550 nm
        "beam_divergence_rad": 0.2e-3, # 0.2 mrad half-angle
        "rx_aperture_diam_m": 0.2,     # 20 cm aperture
        "pointing_error_rad": 1e-3,    # 1 mrad RMS
        "modulation": "OOK",
    }

    # Default atmospheric scenario (clear sky)
    conditions_clear = {
        "visibility_m": 10000.0,
        "rain_rate_mmhr": 0.0,
        "Cn2": 1e-14,
        "wind_speed_mps": 5.0,
    }
    if args.scenario and os.path.exists(args.scenario):
        with open(args.scenario) as f:
            conditions_clear.update(json.load(f))

    # Fog scenario for availability analysis
    conditions_fog = dict(conditions_clear, visibility_m=200.0, rain_rate_mmhr=0.0)

    print("[PhotonLink] Step 1: Clear-sky link budget...")
    budget_clear = compute_link_budget(design_params, conditions_clear)
    for k, v in budget_clear.items():
        print(f"  {k:35s}: {v}")

    print("\n[PhotonLink] Step 2: Fog scenario link budget...")
    budget_fog = compute_link_budget(design_params, conditions_fog)
    print(f"  Fog attenuation (200m vis): {budget_fog['fog_attenuation_db']:.1f} dB")
    print(f"  Link margin (fog)         : {budget_fog['link_margin_db']:.1f} dB")
    if budget_fog["link_margin_db"] < 0:
        print("  >> FSO link FAILS in fog — hybrid RF/FSO backup required.")

    print("\n[PhotonLink] Step 3: Turbulence / scintillation analysis...")
    Cn2 = conditions_clear["Cn2"]
    sig_R2 = rytov_variance(Cn2)
    r0 = fried_parameter_r0(Cn2)
    regime = ("weak" if sig_R2 < 0.3 else "moderate" if sig_R2 < 1.0 else "strong")
    print(f"  Rytov variance : {sig_R2:.4f}")
    print(f"  Fried r0       : {r0*100:.2f} cm")
    print(f"  Turbulence     : {regime}")

    print("\n[PhotonLink] Step 4: BER under clear-sky turbulence...")
    snr_clear = 10 ** ((budget_clear["link_margin_db"] + 10) / 10.0)
    ber_clear = gamma_gamma_ber_ook(snr_clear, sig_R2, n_samples=50000)
    print(f"  BER (clear sky): {ber_clear:.2e}")

    print("\n[PhotonLink] Step 5: Spatial diversity design...")
    div = compute_diversity_gain(n_tx=2, n_rx=2, aperture_sep_m=0.5, r0_m=r0)
    print(f"  Diversity gain : {div['diversity_gain_db']:.1f} dB")

    print("\n[PhotonLink] Step 6: Adaptive optics design...")
    ao = design_adaptive_optics(Cn2, conditions_clear.get("wind_speed_mps", 5.0),
                                  tx_aperture_diam_m=0.1)
    print(f"  N actuators    : {ao['n_actuators']}")
    print(f"  AO bandwidth   : {ao['correction_bandwidth_hz']:.1f} Hz")
    print(f"  Residual WF err: {ao['residual_wavefront_error_nm']:.1f} nm")

    # Availability estimate
    # FSO active when link margin > 0 (fog scenarios are the limiting factor)
    link_margin_clear = budget_clear["link_margin_db"]
    # Simplified: hybrid ensures 99.9% (60 GHz RF covers fog events)
    availability_pct = 99.9 if link_margin_clear > 0 else 95.0

    if args.plot and HAS_PLOT:
        snr_range_db = np.linspace(-5, 30, 100)
        ber_awgn = 0.5 * erfc(np.sqrt(10 ** (snr_range_db / 10.0) / 2.0))
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.semilogy(snr_range_db, ber_awgn, "b-", label="OOK AWGN (no turbulence)")
        ax.axhline(1e-9, color="r", linestyle="--", label="BER = 1e-9 requirement")
        ax.set_xlabel("SNR (dB)")
        ax.set_ylabel("BER")
        ax.set_title("BER vs SNR — PhotonLink OOK 1550 nm")
        ax.legend()
        ax.grid(True, which="both")
        fig.tight_layout()
        out_dir = os.path.dirname(os.path.abspath(args.output)) or "."
        fig.savefig(os.path.join(out_dir, "ber_curve_fso.png"), dpi=150)
        plt.close(fig)

    # ── Assemble submission JSON ─────────────────────────────────────────────
    submission = {
        "link_budget": budget_clear,
        "channel_model": {
            "visibility_m": conditions_clear["visibility_m"],
            "rain_rate_mmhr": conditions_clear["rain_rate_mmhr"],
            "Cn2_m_neg2_thirds": Cn2,
            "rytov_variance": round(float(sig_R2), 6),
            "turbulence_regime": regime,
            "fried_parameter_r0_m": round(float(r0), 4),
        },
        "diversity": div,
        "adaptive_optics": ao,
        "hybrid_backup": {
            "backup_freq_ghz": 60.0,
            "switching_criterion": "Optical Rx power below sensitivity threshold",
            "switchover_time_ms": 10.0,   # TODO: design switching protocol
        },
        "performance": {
            "ber_clear_sky": float(f"{ber_clear:.2e}"),
            "ber_with_fog_attenuation": 1.0 if budget_fog["link_margin_db"] < 0 else 0.5,
            "availability_pct": availability_pct,
            "modulation": design_params["modulation"],
            "data_rate_gbps": DATA_RATE_BPS / 1e9,
        },
    }

    with open(args.output, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"\n[PhotonLink] Submission saved to: {args.output}")


if __name__ == "__main__":
    main()
