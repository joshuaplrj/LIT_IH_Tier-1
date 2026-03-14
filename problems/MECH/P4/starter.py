"""
VibeKill — Active Vibration Control for CNC Milling Machine
MECH-P4 Starter Script

Run:
    python starter.py                      # outputs report.json in current directory
    python starter.py --output ./my_dir/   # outputs to specified directory

report.json schema (all fields required for evaluation):
{
    "actuator_type":                    str   -- e.g. "piezoelectric_stack"
    "sensor_type":                      str   -- e.g. "accelerometer"
    "control_algorithm":                str   -- "FxLMS" | "H_infinity" | "DVF" | "PID" | other
    "chatter_frequency_Hz":             float -- dominant chatter frequency [Hz]; must be in [250, 400]
    "attenuation_dB":                   float -- vibration attenuation at chatter freq [dB]; must be > 20
    "control_bandwidth_Hz":             float -- [Hz]; should be >= 500
    "static_stiffness_preservation_pct":float -- [%]; must be > 90
    "response_time_ms":                 float -- settling time to 5% of steady state [ms]
    "stability_margin_dB":              float -- gain margin [dB]; must be > 6
    "phase_margin_deg":                 float -- phase margin [deg]; must be > 30
    "actuator_force_N":                 float -- peak actuator force [N]
    "actuator_stroke_um":               float -- actuator stroke [μm]
    "controller_sampling_rate_Hz":      float -- digital controller sample rate [Hz]; must be >= 2000
    "open_loop_fn_Hz":                  list  -- identified natural frequencies without control [Hz]
    "closed_loop_fn_Hz":                list  -- effective natural frequencies with control [Hz]
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
CHATTER_FREQ_MIN_HZ   = 250.0    # Hz
CHATTER_FREQ_MAX_HZ   = 400.0    # Hz
ATTENUATION_TARGET_DB = 20.0     # dB minimum
STIFFNESS_PRES_TARGET = 90.0     # % of original static stiffness
BANDWIDTH_TARGET_HZ   = 500.0    # Hz

# Workpiece / process
KS_N_MM2       = 2000.0   # N/mm²  specific cutting force (Ti-6Al-4V)
N_TEETH        = 4        # number of cutter teeth

# ---------------------------------------------------------------------------
# Spindle structural model (1-DOF, identified by modal analysis)
# ---------------------------------------------------------------------------
SPINDLE_K_N_UM   = 50.0       # N/μm  static stiffness
SPINDLE_FN_HZ    = 300.0      # Hz    dominant chatter mode natural frequency
SPINDLE_ZETA_OL  = 0.02       # -     open-loop damping ratio (bare spindle)

# Derive mass and damping from k, fn, zeta
K_SI = SPINDLE_K_N_UM * 1e6   # N/m
M_SI = K_SI / (2 * math.pi * SPINDLE_FN_HZ) ** 2
C_SI = 2 * SPINDLE_ZETA_OL * math.sqrt(K_SI * M_SI)

# ---------------------------------------------------------------------------
# Control design
# ---------------------------------------------------------------------------
ACTUATOR_TYPE       = "piezoelectric_stack"
SENSOR_TYPE         = "accelerometer"
CONTROL_ALGORITHM   = "DVF"       # Direct Velocity Feedback

# Target closed-loop damping ratio (for 20 dB attenuation need ~10× increase)
ZETA_TARGET         = 0.20

# DVF gain: g_dvf = delta_c = 2 * (zeta_cl - zeta_ol) * sqrt(k * m)
DVF_GAIN_NS_M       = 2.0 * (ZETA_TARGET - SPINDLE_ZETA_OL) * math.sqrt(K_SI * M_SI)

# Actuator parameters (PI P-844.10 class)
ACTUATOR_FORCE_N    = 800.0    # N   rated force
ACTUATOR_STROKE_UM  = 15.0     # μm  stroke
CONTROLLER_FS_HZ    = 10_000.0 # Hz  sampling rate

# Low-pass filter cutoff to prevent spillover
LPF_CUTOFF_HZ       = 600.0    # Hz


# ---------------------------------------------------------------------------
# 1-DOF frequency response function
# ---------------------------------------------------------------------------

def frf(omega: np.ndarray, k: float, m: float, c: float) -> np.ndarray:
    """
    Receptance FRF for a 1-DOF system:
        G(jω) = 1 / (k - m*ω^2 + j*c*ω)

    Returns complex array.
    """
    # TODO: extend to multi-DOF using modal superposition
    denom = k - m * omega**2 + 1j * c * omega
    return 1.0 / denom


def frf_with_dvf(omega: np.ndarray, k: float, m: float, c: float,
                  g_dvf: float, lpf_cutoff: float) -> np.ndarray:
    """
    Closed-loop FRF with DVF controller and first-order low-pass filter.
    Controller: C(jω) = -g_dvf * jω / (1 + jω/ω_lpf)
    Closed-loop FRF:
        G_cl = G_ol / (1 - G_ol * C * H_act)
    Assuming ideal actuator (H_act = 1) and collocated sensor.
    """
    # TODO: add actuator dynamics (second-order resonance ~5 kHz)
    G_ol  = frf(omega, k, m, c)
    omega_lpf = 2 * math.pi * lpf_cutoff
    C_ctrl = -g_dvf * 1j * omega / (1.0 + 1j * omega / omega_lpf)
    G_cl  = G_ol / (1.0 - G_ol * C_ctrl)
    return G_cl


def compute_attenuation_dB(G_ol: np.ndarray, G_cl: np.ndarray,
                            fn_Hz: float, freqs_Hz: np.ndarray) -> float:
    """
    Attenuation at natural frequency = 20 * log10(|G_ol(fn)| / |G_cl(fn)|).
    """
    # Find index closest to fn
    idx = np.argmin(np.abs(freqs_Hz - fn_Hz))
    ratio = np.abs(G_ol[idx]) / np.abs(G_cl[idx])
    return 20.0 * math.log10(max(ratio, 1e-12))


def compute_settling_time(zeta: float, fn_Hz: float) -> float:
    """
    Time to settle within 5% of steady state (underdamped):
        t_s ≈ 3 / (zeta * omega_n)    [seconds]
    Returns settling time in ms.
    """
    omega_n = 2 * math.pi * fn_Hz
    return (3.0 / (zeta * omega_n)) * 1000.0   # ms


def compute_stability_margins(omega: np.ndarray, G_ol: np.ndarray,
                               g_dvf: float, lpf_cutoff: float) -> tuple:
    """
    Simplified gain and phase margin calculation for DVF loop.
    Loop transfer function: L(jω) = G_ol(jω) * C(jω)

    Returns (gain_margin_dB, phase_margin_deg).
    """
    # TODO: use proper Nyquist analysis or scipy.signal for bode margins
    omega_lpf = 2 * math.pi * lpf_cutoff
    C = -g_dvf * 1j * omega / (1.0 + 1j * omega / omega_lpf)
    L = G_ol * C

    # Phase crossover frequency (where phase = -180°)
    phase_L = np.angle(L, deg=True)
    # Find where phase crosses -180 (approximate)
    sign_changes = np.where(np.diff(np.sign(phase_L + 180.0)))[0]
    if len(sign_changes) > 0:
        idx_pc = sign_changes[0]
        gain_at_pc = np.abs(L[idx_pc])
        gain_margin_dB = -20.0 * math.log10(max(gain_at_pc, 1e-12))
    else:
        gain_margin_dB = 40.0   # no phase crossover — very stable

    # Gain crossover frequency (where |L| = 1 = 0 dB)
    mag_L = np.abs(L)
    sign_changes_gain = np.where(np.diff(np.sign(mag_L - 1.0)))[0]
    if len(sign_changes_gain) > 0:
        idx_gc = sign_changes_gain[0]
        phase_at_gc = np.angle(L[idx_gc], deg=True)
        phase_margin_deg = 180.0 + phase_at_gc
    else:
        phase_margin_deg = 90.0   # gain never crosses 0 dB

    return gain_margin_dB, phase_margin_deg


def compute_static_stiffness_preservation(k: float, g_dvf: float,
                                           lpf_cutoff: float) -> float:
    """
    At DC (ω=0), DVF controller output = 0 (derivative action).
    Static stiffness is unaffected by velocity feedback.
    Returns 100% for pure velocity feedback.

    NOTE: If an integral term were added, DC stiffness would change.
    """
    # TODO: verify with closed-loop DC gain of FRF
    return 100.0   # DVF does not affect static stiffness


def compute_actuator_force(g_dvf: float, fn_Hz: float,
                            vib_amplitude_um: float = 20.0) -> float:
    """
    Peak actuator force = g_dvf * v_max
    where v_max = A * omega_n (peak velocity from typical chatter amplitude).
    """
    A_m = vib_amplitude_um * 1e-6
    omega_n = 2 * math.pi * fn_Hz
    v_max = A_m * omega_n
    return g_dvf * v_max


def chatter_stability_limit(G_re_at_fn: float, N_teeth: int,
                              Ks_N_mm2: float) -> float:
    """
    Tlusty chatter stability limit (1D approximation):
        b_lim = -1 / (2 * N * Ks * G_re(omega_c))
    Returns b_lim [mm].
    """
    # TODO: extend to full stability lobe diagram with tooth pass frequency
    if G_re_at_fn >= 0:
        return float('inf')
    return -1.0 / (2.0 * N_teeth * Ks_N_mm2 * G_re_at_fn * 1e-6)  # Ks in N/m²


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="VibeKill active vibration control calculator")
    parser.add_argument("--output", default=".", help="Output directory for report.json")
    args = parser.parse_args()

    # Frequency array
    freqs_Hz  = np.linspace(1, 1000, 10000)
    omega     = 2 * math.pi * freqs_Hz

    # FRF analysis
    G_ol = frf(omega, K_SI, M_SI, C_SI)
    G_cl = frf_with_dvf(omega, K_SI, M_SI, C_SI, DVF_GAIN_NS_M, LPF_CUTOFF_HZ)

    attenuation_dB = compute_attenuation_dB(G_ol, G_cl, SPINDLE_FN_HZ, freqs_Hz)
    settling_ms    = compute_settling_time(ZETA_TARGET, SPINDLE_FN_HZ)

    gm_dB, pm_deg  = compute_stability_margins(omega, G_ol, DVF_GAIN_NS_M, LPF_CUTOFF_HZ)
    stiff_pct      = compute_static_stiffness_preservation(K_SI, DVF_GAIN_NS_M, LPF_CUTOFF_HZ)
    act_force      = compute_actuator_force(DVF_GAIN_NS_M, SPINDLE_FN_HZ)

    # Effective closed-loop natural frequency (shifts slightly with DVF)
    cl_damp_ratio = ZETA_TARGET
    fn_cl = SPINDLE_FN_HZ * math.sqrt(1 - cl_damp_ratio**2)

    report = {
        "actuator_type":                    ACTUATOR_TYPE,
        "sensor_type":                      SENSOR_TYPE,
        "control_algorithm":                CONTROL_ALGORITHM,
        "chatter_frequency_Hz":             SPINDLE_FN_HZ,
        "attenuation_dB":                   round(attenuation_dB, 2),
        "control_bandwidth_Hz":             LPF_CUTOFF_HZ,
        "static_stiffness_preservation_pct": round(stiff_pct, 1),
        "response_time_ms":                 round(settling_ms, 2),
        "stability_margin_dB":              round(gm_dB, 2),
        "phase_margin_deg":                 round(pm_deg, 2),
        "actuator_force_N":                 round(act_force, 2),
        "actuator_stroke_um":               ACTUATOR_STROKE_UM,
        "controller_sampling_rate_Hz":      CONTROLLER_FS_HZ,
        "open_loop_fn_Hz":                  [round(SPINDLE_FN_HZ, 1)],
        "closed_loop_fn_Hz":                [round(fn_cl, 1)],
    }

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, "report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"VibeKill report written to: {out_path}")
    print(f"  Chatter freq       : {SPINDLE_FN_HZ:.1f} Hz")
    print(f"  Attenuation        : {attenuation_dB:.2f} dB  (target > {ATTENUATION_TARGET_DB} dB)")
    print(f"  Static stiffness   : {stiff_pct:.1f}%  (target > {STIFFNESS_PRES_TARGET}%)")
    print(f"  Settling time      : {settling_ms:.2f} ms")
    print(f"  Gain margin        : {gm_dB:.2f} dB  (target > 6 dB)")
    print(f"  Phase margin       : {pm_deg:.2f}°  (target > 30°)")
    print(f"  Actuator force     : {act_force:.2f} N  (rated {ACTUATOR_FORCE_N} N)")
    print(f"  DVF gain           : {DVF_GAIN_NS_M:.1f} N·s/m")


if __name__ == "__main__":
    main()
