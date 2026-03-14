"""
RadarForge — FMCW Radar System Design Starter
==============================================
Problem: Design a 24 GHz FMCW radar to detect drones (RCS ~ 0.01 m2) at up to 500 m.

Requirements:
    - Range resolution  : <= 1 m
    - Velocity resolution: <= 0.5 m/s
    - Angular resolution: <= 5 deg azimuth
    - Detection probability: >= 90% at 500 m, Pfa = 1e-6
    - Update rate       : >= 10 Hz (frame <= 100 ms)

Run as-is to generate a placeholder submission.json, then fill in the TODOs.

Usage:
    python starter.py --output submission.json
    python starter.py --scenario scenario.json --output submission.json
"""

import argparse
import json
import os
import numpy as np
from scipy import signal
from scipy.linalg import eigh

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

# ─── Physical constants ──────────────────────────────────────────────────────
C = 3e8          # speed of light (m/s)
K_B = 1.38e-23   # Boltzmann constant (J/K)
T0 = 290.0       # reference temperature (K)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — SYSTEM DESIGN
# ═════════════════════════════════════════════════════════════════════════════

def design_radar_system() -> dict:
    """
    Calculate all FMCW radar waveform and hardware parameters.

    Returns a dict with keys:
        center_freq_hz, bandwidth_hz, chirp_duration_s, num_chirps,
        tx_power_dbm, tx_elements, rx_elements, mimo_virtual_elements,
        lambda_m, sweep_rate_hz_per_s, frame_duration_s,
        range_resolution_m, velocity_resolution_mps,
        max_range_m, max_velocity_mps, angular_resolution_deg,
        array_element_spacing_m
    """
    center_freq = 24e9          # Hz
    lam = C / center_freq       # wavelength (m)

    # ── TODO 1: Compute bandwidth from desired range resolution (delta_R = 1 m)
    #   Formula: B = c / (2 * delta_R)
    bandwidth = C / (2 * 1.0)   # PLACEHOLDER — replace with your calculation

    # ── TODO 2: Compute chirp duration such that max unambiguous range >= 500 m
    #   Formula: R_max = c * T_chirp / 2  →  T_chirp >= 2 * 500 / c
    chirp_duration = 2 * 500 / C * 1.5  # PLACEHOLDER — add safety margin

    # ── TODO 3: Compute number of chirps for velocity resolution <= 0.5 m/s
    #   Formula: delta_v = lambda / (2 * N * T_chirp)  →  N >= lambda / (2 * delta_v * T_chirp)
    num_chirps = int(np.ceil(lam / (2 * 0.5 * chirp_duration)))
    # Round up to next power of 2 for FFT efficiency
    num_chirps = int(2 ** np.ceil(np.log2(max(num_chirps, 64))))

    # ── TODO 4: Verify frame duration <= 100 ms
    frame_duration = num_chirps * chirp_duration

    # ── TODO 5: Determine TX/RX element count for 5 deg angular resolution
    #   Virtual aperture length L = N_virt * d  where d = lambda/2
    #   Resolution: theta_res = lambda / L  (radians)  →  N_virt >= lambda / (d * sin(5 deg))
    n_tx = 2    # PLACEHOLDER
    n_rx = 4    # PLACEHOLDER
    n_virt = n_tx * n_rx
    d_element = lam / 2     # half-wavelength spacing

    # ── TODO 6: Compute required transmit power via radar range equation
    #   SNR = (Pt * Gt * Gr * lambda^2 * sigma) / ((4pi)^3 * R^4 * k * T * Bn * F * L)
    #   Target: SNR >= 13 dB for Pd = 90%, Pfa = 1e-6 (Albersheim / Shnidman)
    tx_power_w = 0.1        # PLACEHOLDER (W) — compute from radar range equation
    tx_power_dbm = 10 * np.log10(tx_power_w * 1000)

    # Derived metrics
    range_res = C / (2 * bandwidth)
    vel_res = lam / (2 * num_chirps * chirp_duration)
    v_max = lam / (4 * chirp_duration)
    ang_res_rad = lam / (n_virt * d_element)
    ang_res_deg = np.degrees(ang_res_rad)

    return {
        "center_freq_hz": center_freq,
        "bandwidth_hz": bandwidth,
        "chirp_duration_s": chirp_duration,
        "num_chirps": num_chirps,
        "frame_duration_s": frame_duration,
        "tx_power_dbm": round(tx_power_dbm, 2),
        "tx_elements": n_tx,
        "rx_elements": n_rx,
        "mimo_virtual_elements": n_virt,
        "lambda_m": lam,
        "sweep_rate_hz_per_s": bandwidth / chirp_duration,
        "range_resolution_m": round(range_res, 4),
        "velocity_resolution_mps": round(vel_res, 4),
        "max_range_m": round(C * chirp_duration / 2, 1),
        "max_velocity_mps": round(v_max, 2),
        "angular_resolution_deg": round(ang_res_deg, 2),
        "array_element_spacing_m": d_element,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — IF SIGNAL SIMULATION
# ═════════════════════════════════════════════════════════════════════════════

def generate_if_signal(params: dict, target: dict) -> np.ndarray:
    """
    Generate the complex IF (beat) signal for a single point target.

    Args:
        params  : output of design_radar_system()
        target  : {"range_m": float, "velocity_mps": float,
                   "azimuth_deg": float, "rcs_m2": float}

    Returns:
        if_matrix : shape (num_chirps, N_fast) complex array
    """
    B = params["bandwidth_hz"]
    T = params["chirp_duration_s"]
    N = params["num_chirps"]
    lam = params["lambda_m"]
    f0 = params["center_freq_hz"]
    N_fast = 512   # ADC samples per chirp — adjust to your design

    t_fast = np.linspace(0, T, N_fast, endpoint=False)

    R0 = target.get("range_m", 100.0)
    v = target.get("velocity_mps", 10.0)
    sigma = target.get("rcs_m2", 0.01)

    # ── TODO 7: Compute IF beat frequency and Doppler shift
    #   f_beat = 2 * B * R / (c * T)
    #   f_doppler = 2 * v / lambda
    f_beat = 2 * B * R0 / (C * T)              # PLACEHOLDER
    f_doppler = 2 * v / lam                    # PLACEHOLDER

    # ── TODO 8: Compute received signal amplitude from radar range equation
    #   Amplitude proportional to sqrt(Pt * Gt * Gr * lambda^2 * sigma) / ((4pi)^(3/2) * R^2)
    amplitude = 1.0 / (R0 ** 2)               # PLACEHOLDER — normalised amplitude

    # Noise power (thermal noise floor)
    noise_figure_db = 10.0
    bandwidth_noise = 1 / T
    noise_power = K_B * T0 * bandwidth_noise * 10 ** (noise_figure_db / 10)
    noise_std = np.sqrt(noise_power / 2)

    if_matrix = np.zeros((N, N_fast), dtype=complex)
    for m in range(N):
        # Phase progression across chirps (Doppler)
        doppler_phase = 2 * np.pi * f_doppler * m * T
        # Beat signal for this chirp
        beat = amplitude * np.exp(1j * 2 * np.pi * (f_beat * t_fast + doppler_phase))
        noise = noise_std * (np.random.randn(N_fast) + 1j * np.random.randn(N_fast))
        if_matrix[m, :] = beat + noise

    return if_matrix


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — RANGE-DOPPLER PROCESSING
# ═════════════════════════════════════════════════════════════════════════════

def range_doppler_processing(if_matrix: np.ndarray, params: dict) -> dict:
    """
    Apply 2D FFT to produce a range-Doppler map and extract peak detections.

    Args:
        if_matrix : (num_chirps, N_fast) complex IF signal
        params    : system design parameters

    Returns:
        dict with keys: range_doppler_map (2D array), range_axis, velocity_axis,
                        detected_range_m, detected_velocity_mps
    """
    N_chirps, N_fast = if_matrix.shape
    B = params["bandwidth_hz"]
    T = params["chirp_duration_s"]
    lam = params["lambda_m"]

    # ── TODO 9: Apply 2D window (Hanning along range, Hanning along Doppler)
    win_fast = np.hanning(N_fast)
    win_slow = np.hanning(N_chirps)
    window2d = np.outer(win_slow, win_fast)
    windowed = if_matrix * window2d     # PLACEHOLDER — apply window

    # ── TODO 10: Compute 2D FFT and shift
    rd_map = np.fft.fftshift(np.fft.fft2(windowed))   # PLACEHOLDER — verify axes
    rd_map_db = 20 * np.log10(np.abs(rd_map) + 1e-12)

    # Calibration axes
    range_res = C / (2 * B)
    vel_res = lam / (2 * N_chirps * T)
    range_axis = np.arange(N_fast) * range_res
    velocity_axis = (np.arange(N_chirps) - N_chirps // 2) * vel_res

    # ── TODO 11: Implement CA-CFAR detection on the RD map
    #   For now, just find the peak
    peak_idx = np.unravel_index(np.argmax(np.abs(rd_map)), rd_map.shape)
    detected_range = range_axis[peak_idx[1] % N_fast]
    detected_velocity = velocity_axis[peak_idx[0] % N_chirps]

    # SNR estimate
    peak_power = np.abs(rd_map[peak_idx]) ** 2
    noise_floor = np.median(np.abs(rd_map) ** 2)
    snr_db = 10 * np.log10(peak_power / (noise_floor + 1e-30))

    return {
        "range_doppler_map": rd_map_db,
        "range_axis": range_axis,
        "velocity_axis": velocity_axis,
        "detected_range_m": float(detected_range),
        "detected_velocity_mps": float(detected_velocity),
        "estimated_snr_db": float(snr_db),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — CFAR DETECTION
# ═════════════════════════════════════════════════════════════════════════════

def ca_cfar_1d(power_spectrum: np.ndarray, n_ref: int = 16,
               n_guard: int = 4, pfa: float = 1e-6) -> np.ndarray:
    """
    Cell-Averaging CFAR detector (1D, applied row-by-row to RD map).

    Args:
        power_spectrum : 1D power array
        n_ref          : number of reference cells per side
        n_guard        : number of guard cells per side
        pfa            : desired false-alarm probability

    Returns:
        detections : boolean array, True where target detected
    """
    N = len(power_spectrum)
    detections = np.zeros(N, dtype=bool)

    # ── TODO 12: Implement CA-CFAR sliding window
    #   alpha = n_ref * (pfa ** (-1/n_ref) - 1)   for Rayleigh clutter
    alpha = n_ref * (pfa ** (-1.0 / n_ref) - 1.0)   # PLACEHOLDER
    half = n_ref + n_guard

    for i in range(half, N - half):
        left_ref = power_spectrum[i - half: i - n_guard]
        right_ref = power_spectrum[i + n_guard + 1: i + half + 1]
        noise_est = np.mean(np.concatenate([left_ref, right_ref]))
        threshold = alpha * noise_est
        detections[i] = power_spectrum[i] > threshold

    return detections


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — ANGLE ESTIMATION (MUSIC)
# ═════════════════════════════════════════════════════════════════════════════

def music_angle_estimation(array_snapshot: np.ndarray, n_targets: int,
                           d_over_lambda: float = 0.5,
                           angle_range: tuple = (-90, 90),
                           n_angles: int = 1801) -> np.ndarray:
    """
    MUSIC spatial spectrum estimator for ULA.

    Args:
        array_snapshot : (M, K) complex array — M elements, K snapshots
        n_targets      : number of expected targets
        d_over_lambda   : element spacing / wavelength (default 0.5)
        angle_range    : (min_deg, max_deg)
        n_angles       : number of angle grid points

    Returns:
        angles_deg : array of peak angles in degrees
    """
    M, K = array_snapshot.shape

    # ── TODO 13: Compute covariance matrix and eigendecompose
    R = (array_snapshot @ array_snapshot.conj().T) / K   # PLACEHOLDER
    eigenvalues, eigenvectors = eigh(R)

    # Noise subspace: M - n_targets smallest eigenvectors
    E_n = eigenvectors[:, :M - n_targets]

    # ── TODO 14: Sweep steering vector and compute MUSIC pseudospectrum
    angles = np.linspace(angle_range[0], angle_range[1], n_angles)
    spectrum = np.zeros(n_angles)
    for i, theta in enumerate(angles):
        a = np.exp(1j * 2 * np.pi * d_over_lambda *
                   np.arange(M) * np.sin(np.radians(theta)))
        spectrum[i] = 1.0 / (np.abs(a.conj() @ E_n @ E_n.conj().T @ a) + 1e-30)

    # Find peaks
    peaks, _ = signal.find_peaks(spectrum, height=np.max(spectrum) * 0.1)
    peak_angles = angles[peaks[:n_targets]] if len(peaks) >= n_targets else angles[np.argsort(spectrum)[-n_targets:]]

    return peak_angles


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — LINK BUDGET / SNR CALCULATION
# ═════════════════════════════════════════════════════════════════════════════

def compute_snr_at_range(params: dict, range_m: float,
                         rcs_m2: float = 0.01,
                         noise_figure_db: float = 10.0,
                         system_loss_db: float = 3.0) -> float:
    """
    Compute single-pulse SNR using the radar range equation.

    SNR = (Pt * Gt * Gr * lambda^2 * sigma) /
          ((4*pi)^3 * R^4 * k * T0 * B * F * L)

    Returns SNR in dB.
    """
    pt_w = 10 ** ((params["tx_power_dbm"] - 30) / 10)
    lam = params["lambda_m"]
    B = params["bandwidth_hz"]

    # ── TODO 15: Calculate antenna gains from element count and efficiency
    #   Gt = eta * pi * N_tx * ... (phased array gain)
    gt_linear = 10.0    # PLACEHOLDER — compute from array geometry
    gr_linear = 10.0    # PLACEHOLDER

    numerator = pt_w * gt_linear * gr_linear * (lam ** 2) * rcs_m2
    denominator = ((4 * np.pi) ** 3 * (range_m ** 4) *
                   K_B * T0 * B *
                   10 ** (noise_figure_db / 10) *
                   10 ** (system_loss_db / 10))

    snr_linear = numerator / denominator
    return 10 * np.log10(snr_linear + 1e-30)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — DETECTION PROBABILITY (ALBERSHEIM APPROXIMATION)
# ═════════════════════════════════════════════════════════════════════════════

def albersheim_pd(snr_db: float, pfa: float = 1e-6) -> float:
    """
    Albersheim approximation for detection probability (single pulse, Swerling 0).
    Returns Pd as a fraction (0–1).
    """
    # ── TODO 16: Implement Albersheim's equation
    #   A = ln(0.62 / Pfa)
    #   B_alb = ln(Pd / (1 - Pd))
    #   SNR_min = A + 0.12 * A * B_alb + 1.7 * B_alb
    #   Invert to get Pd from SNR
    A = np.log(0.62 / pfa)
    snr_lin = 10 ** (snr_db / 10)
    # Iterative inversion (Newton's method) — PLACEHOLDER returns 0.5
    pd = 0.5    # TODO: replace with proper inversion
    return pd


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — VISUALISATION (OPTIONAL)
# ═════════════════════════════════════════════════════════════════════════════

def plot_range_doppler_map(rd_result: dict, output_dir: str = ".") -> None:
    if not HAS_PLOT:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    R = rd_result["range_axis"]
    V = rd_result["velocity_axis"]
    img = rd_result["range_doppler_map"]
    # Show only positive ranges
    half = len(V) // 2
    ax.imshow(img[half - 30: half + 30, :200],
              aspect="auto", origin="lower",
              extent=[R[0], R[min(200, len(R) - 1)],
                      V[half - 30], V[min(half + 29, len(V) - 1)]],
              cmap="viridis", vmin=-60, vmax=0)
    ax.set_xlabel("Range (m)")
    ax.set_ylabel("Velocity (m/s)")
    ax.set_title("Range-Doppler Map (dB, normalised)")
    plt.colorbar(ax.images[0], ax=ax, label="Power (dB)")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "range_doppler_map.png"), dpi=150)
    plt.close(fig)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="RadarForge FMCW radar design tool")
    parser.add_argument("--scenario", default=None,
                        help="JSON file with target scenario parameters")
    parser.add_argument("--output", default="submission.json",
                        help="Output submission JSON path")
    parser.add_argument("--plot", action="store_true",
                        help="Generate range-Doppler map plot")
    args = parser.parse_args()

    print("[RadarForge] Step 1: Designing radar system parameters...")
    params = design_radar_system()
    print(f"  Bandwidth       : {params['bandwidth_hz']/1e6:.1f} MHz")
    print(f"  Chirp duration  : {params['chirp_duration_s']*1e6:.2f} µs")
    print(f"  Num chirps      : {params['num_chirps']}")
    print(f"  Frame duration  : {params['frame_duration_s']*1e3:.1f} ms")
    print(f"  Range resolution: {params['range_resolution_m']:.3f} m")
    print(f"  Vel  resolution : {params['velocity_resolution_mps']:.3f} m/s")
    print(f"  Angular res     : {params['angular_resolution_deg']:.2f} deg")
    print(f"  MIMO virtual    : {params['mimo_virtual_elements']} elements")

    # Load scenario or use default
    if args.scenario and os.path.exists(args.scenario):
        with open(args.scenario) as f:
            target = json.load(f)
        print(f"[RadarForge] Loaded scenario: {target}")
    else:
        target = {"range_m": 200.0, "velocity_mps": 15.0,
                  "azimuth_deg": 10.0, "rcs_m2": 0.01}
        print(f"[RadarForge] Using default scenario: {target}")

    print("[RadarForge] Step 2: Generating IF signal simulation...")
    if_matrix = generate_if_signal(params, target)

    print("[RadarForge] Step 3: Range-Doppler processing...")
    rd_result = range_doppler_processing(if_matrix, params)
    print(f"  Detected range   : {rd_result['detected_range_m']:.2f} m (true: {target['range_m']} m)")
    print(f"  Detected velocity: {rd_result['detected_velocity_mps']:.2f} m/s (true: {target['velocity_mps']} m/s)")
    print(f"  Estimated SNR    : {rd_result['estimated_snr_db']:.1f} dB")

    print("[RadarForge] Step 4: Link budget at 500 m...")
    snr_500m = compute_snr_at_range(params, 500.0)
    pd_500m = albersheim_pd(snr_500m) * 100.0
    print(f"  SNR @ 500 m     : {snr_500m:.1f} dB")
    print(f"  Pd @ 500 m      : {pd_500m:.1f}%")

    print("[RadarForge] Step 5: Angle estimation (MUSIC) — placeholder snapshot...")
    n_virt = params["mimo_virtual_elements"]
    # Placeholder: generate a synthetic array snapshot
    az_true = np.radians(target["azimuth_deg"])
    snapshot = (np.exp(1j * 2 * np.pi * 0.5 * np.arange(n_virt) * np.sin(az_true))
                .reshape(-1, 1) + 0.1 * (np.random.randn(n_virt, 1) +
                                          1j * np.random.randn(n_virt, 1)))
    est_angles = music_angle_estimation(snapshot, n_targets=1)
    print(f"  Estimated azimuth: {est_angles[0]:.2f} deg (true: {target['azimuth_deg']} deg)")

    if args.plot:
        print("[RadarForge] Generating range-Doppler plot...")
        out_dir = os.path.dirname(os.path.abspath(args.output)) or "."
        plot_range_doppler_map(rd_result, out_dir)

    # ── Assemble submission JSON ─────────────────────────────────────────────
    submission = {
        "system_design": {
            "center_freq_hz": params["center_freq_hz"],
            "bandwidth_hz": params["bandwidth_hz"],
            "chirp_duration_s": params["chirp_duration_s"],
            "num_chirps": params["num_chirps"],
            "tx_power_dbm": params["tx_power_dbm"],
            "tx_rx_elements": {
                "tx": params["tx_elements"],
                "rx": params["rx_elements"]
            },
            "mimo_virtual_elements": params["mimo_virtual_elements"],
        },
        "performance": {
            "range_resolution_m": params["range_resolution_m"],
            "velocity_resolution_mps": params["velocity_resolution_mps"],
            "max_range_m": params["max_range_m"],
            "max_velocity_mps": params["max_velocity_mps"],
            "angular_resolution_deg": params["angular_resolution_deg"],
            "snr_at_500m_db": round(float(snr_500m), 2),
            "detection_probability_pct": round(float(pd_500m), 2),
            "cfar_threshold_db": 13.0,   # TODO: compute from CFAR design
        },
        "signal_processing": {
            "range_fft_size": if_matrix.shape[1],
            "doppler_fft_size": if_matrix.shape[0],
            "cfar_type": "CA-CFAR",
            "angle_method": "MUSIC",
        },
        "simulation_results": {
            "detected_range_m": rd_result["detected_range_m"],
            "detected_velocity_mps": rd_result["detected_velocity_mps"],
            "estimated_snr_db": rd_result["estimated_snr_db"],
            "estimated_azimuth_deg": float(est_angles[0]),
            "range_error_m": abs(rd_result["detected_range_m"] - target["range_m"]),
            "velocity_error_mps": abs(rd_result["detected_velocity_mps"] - target["velocity_mps"]),
            "angle_error_deg": abs(float(est_angles[0]) - target["azimuth_deg"]),
        },
    }

    out_path = args.output
    with open(out_path, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"\n[RadarForge] Submission saved to: {out_path}")
    print("[RadarForge] Done. Review the TODOs in this file to improve your design.")


if __name__ == "__main__":
    main()
