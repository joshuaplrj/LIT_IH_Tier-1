"""
RadarForge — Evaluation Script
================================
Submission JSON schema expected at <submission_path>:
{
  "system_design": {
    "center_freq_hz": <float>,          -- must be 24e9 ± 100 MHz
    "bandwidth_hz": <float>,            -- required >= 150e6 for 1 m range res
    "chirp_duration_s": <float>,        -- required >= 3.33e-6 (500 m unambiguous)
    "num_chirps": <int>,                -- required for velocity resolution check
    "tx_power_dbm": <float>,            -- must be <= 36 dBm (ISM EIRP limit)
    "tx_rx_elements": {"tx": int, "rx": int},
    "mimo_virtual_elements": <int>      -- tx * rx
  },
  "performance": {
    "range_resolution_m": <float>,      -- must be <= 1.0
    "velocity_resolution_mps": <float>, -- must be <= 0.5
    "max_range_m": <float>,             -- must be >= 500.0
    "max_velocity_mps": <float>,        -- must be >= some drone speed
    "angular_resolution_deg": <float>,  -- must be <= 5.0
    "snr_at_500m_db": <float>,          -- must be >= 13.0 dB
    "detection_probability_pct": <float>, -- must be >= 90.0
    "cfar_threshold_db": <float>
  },
  "signal_processing": {
    "range_fft_size": <int>,
    "doppler_fft_size": <int>,
    "cfar_type": <str>,
    "angle_method": <str>
  },
  "simulation_results": {
    "detected_range_m": <float>,
    "detected_velocity_mps": <float>,
    "estimated_snr_db": <float>,
    "estimated_azimuth_deg": <float>,
    "range_error_m": <float>,          -- |detected - true| must be <= 1.0
    "velocity_error_mps": <float>,     -- |detected - true| must be <= 0.5
    "angle_error_deg": <float>         -- |detected - true| must be <= 5.0
  }
}

Scoring:
  Range accuracy   (30 pts): based on range_error_m and range_resolution_m
  Velocity accuracy(25 pts): based on velocity_error_mps and velocity_resolution_mps
  Angular resolution(25 pts): based on angular_resolution_deg and angle_error_deg
  SNR / link budget(20 pts): based on snr_at_500m_db and detection_probability_pct

Usage:
    python evaluate.py --submission submission.json
    python evaluate.py --submission submission.json --verbose
"""

import argparse
import json
import sys

C = 3e8

# ── Requirement constants ────────────────────────────────────────────────────
REQ_CENTER_FREQ_HZ = 24e9
REQ_RANGE_RES_M = 1.0
REQ_VEL_RES_MPS = 0.5
REQ_MAX_RANGE_M = 500.0
REQ_ANG_RES_DEG = 5.0
REQ_SNR_DB = 13.0           # minimum for Pd >= 90% at Pfa=1e-6
REQ_PD_PCT = 90.0
REQ_EIRP_MAX_DBM = 36.0     # ISM 24 GHz EIRP limit
REQ_FRAME_MAX_MS = 100.0    # 10 Hz update rate


def load_submission(path: str):
    try:
        with open(path) as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"Submission file not found: {path}"
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in submission: {e}"


def clamp(val, lo=0.0, hi=100.0):
    return max(lo, min(hi, val))


def score_range_accuracy(sub: dict) -> tuple:
    """Score range accuracy (30 pts)."""
    errors = []
    score = 0.0
    try:
        perf = sub["performance"]
        sim = sub.get("simulation_results", {})
        design = sub["system_design"]

        # 1. Range resolution meets requirement (15 pts)
        rr = float(perf["range_resolution_m"])
        bw = float(design["bandwidth_hz"])
        bw_derived_rr = C / (2 * bw)
        if rr <= REQ_RANGE_RES_M and abs(rr - bw_derived_rr) < 0.1:
            score += 15.0
        elif rr <= REQ_RANGE_RES_M:
            score += 10.0
            errors.append(f"range_resolution_m ({rr:.3f}) meets spec but is inconsistent with bandwidth ({bw/1e6:.1f} MHz).")
        else:
            errors.append(f"range_resolution_m ({rr:.3f} m) exceeds limit ({REQ_RANGE_RES_M} m).")

        # 2. Simulation range error (15 pts)
        range_err = sim.get("range_error_m", None)
        if range_err is None:
            errors.append("simulation_results.range_error_m missing.")
            score += 0
        else:
            range_err = float(range_err)
            if range_err <= 0.5:
                score += 15.0
            elif range_err <= 1.0:
                score += 10.0
            elif range_err <= 2.0:
                score += 5.0
            else:
                errors.append(f"range_error_m ({range_err:.2f}) exceeds 2 m.")
    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"range_accuracy: parse error — {e}")
    return clamp(score, 0, 30), errors


def score_velocity_accuracy(sub: dict) -> tuple:
    """Score velocity accuracy (25 pts)."""
    errors = []
    score = 0.0
    try:
        perf = sub["performance"]
        sim = sub.get("simulation_results", {})
        design = sub["system_design"]

        # 1. Velocity resolution (13 pts)
        vr = float(perf["velocity_resolution_mps"])
        if vr <= REQ_VEL_RES_MPS:
            score += 13.0
        else:
            errors.append(f"velocity_resolution_mps ({vr:.3f}) exceeds limit ({REQ_VEL_RES_MPS}).")

        # Consistency check: lambda / (2 * N * T)
        import math
        lam = C / float(design["center_freq_hz"])
        N = int(design["num_chirps"])
        T = float(design["chirp_duration_s"])
        vr_calc = lam / (2 * N * T)
        if abs(vr - vr_calc) > 0.05:
            errors.append(f"velocity_resolution inconsistency: reported {vr:.4f} m/s, calculated {vr_calc:.4f} m/s.")
            score = max(0.0, score - 3.0)

        # 2. Simulation velocity error (12 pts)
        vel_err = sim.get("velocity_error_mps", None)
        if vel_err is None:
            errors.append("simulation_results.velocity_error_mps missing.")
        else:
            vel_err = float(vel_err)
            if vel_err <= 0.25:
                score += 12.0
            elif vel_err <= 0.5:
                score += 8.0
            elif vel_err <= 1.0:
                score += 4.0
            else:
                errors.append(f"velocity_error_mps ({vel_err:.3f}) exceeds 1 m/s.")
    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"velocity_accuracy: parse error — {e}")
    return clamp(score, 0, 25), errors


def score_angular_resolution(sub: dict) -> tuple:
    """Score angular resolution (25 pts)."""
    errors = []
    score = 0.0
    try:
        perf = sub["performance"]
        sim = sub.get("simulation_results", {})
        design = sub["system_design"]
        sp = sub.get("signal_processing", {})

        # 1. Angular resolution meets spec (13 pts)
        ar = float(perf["angular_resolution_deg"])
        n_virt = int(design["mimo_virtual_elements"])
        n_tx = int(design["tx_rx_elements"]["tx"])
        n_rx = int(design["tx_rx_elements"]["rx"])
        if n_virt != n_tx * n_rx:
            errors.append(f"mimo_virtual_elements ({n_virt}) != tx*rx ({n_tx*n_rx}).")
        if ar <= REQ_ANG_RES_DEG:
            score += 13.0
        else:
            errors.append(f"angular_resolution_deg ({ar:.2f}) exceeds limit ({REQ_ANG_RES_DEG} deg).")

        # 2. Angle estimation method named (4 pts)
        method = sp.get("angle_method", "")
        if any(m in method.upper() for m in ["MUSIC", "ESPRIT", "BEAMFORMING", "CAPON"]):
            score += 4.0
        else:
            errors.append(f"angle_method '{method}' not recognised. Use MUSIC, ESPRIT, or Beamforming.")

        # 3. Simulation angle error (8 pts)
        ang_err = sim.get("angle_error_deg", None)
        if ang_err is None:
            errors.append("simulation_results.angle_error_deg missing.")
        else:
            ang_err = float(ang_err)
            if ang_err <= 1.0:
                score += 8.0
            elif ang_err <= 2.5:
                score += 5.0
            elif ang_err <= 5.0:
                score += 2.0
            else:
                errors.append(f"angle_error_deg ({ang_err:.2f}) exceeds 5 deg.")
    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"angular_resolution: parse error — {e}")
    return clamp(score, 0, 25), errors


def score_snr_link_budget(sub: dict) -> tuple:
    """Score SNR and link budget (20 pts)."""
    errors = []
    score = 0.0
    try:
        perf = sub["performance"]
        design = sub["system_design"]

        # 1. SNR at 500 m (10 pts)
        snr = float(perf["snr_at_500m_db"])
        if snr >= REQ_SNR_DB + 3:
            score += 10.0
        elif snr >= REQ_SNR_DB:
            score += 7.0
        elif snr >= REQ_SNR_DB - 3:
            score += 3.0
        else:
            errors.append(f"snr_at_500m_db ({snr:.1f}) is below minimum ({REQ_SNR_DB} dB).")

        # 2. Detection probability (7 pts)
        pd = float(perf["detection_probability_pct"])
        if pd >= REQ_PD_PCT:
            score += 7.0
        elif pd >= 80.0:
            score += 4.0
        else:
            errors.append(f"detection_probability_pct ({pd:.1f}%) below requirement (90%).")

        # 3. EIRP within ISM limits (3 pts)
        tx_dbm = float(design["tx_power_dbm"])
        if tx_dbm <= REQ_EIRP_MAX_DBM:
            score += 3.0
        else:
            errors.append(f"tx_power_dbm ({tx_dbm:.1f}) exceeds ISM EIRP limit ({REQ_EIRP_MAX_DBM} dBm).")
    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"snr_link_budget: parse error — {e}")
    return clamp(score, 0, 20), errors


def validate_constraints(sub: dict) -> list:
    """Check hard constraints that can zero-out sections."""
    warnings = []
    try:
        design = sub["system_design"]
        freq = float(design["center_freq_hz"])
        if abs(freq - REQ_CENTER_FREQ_HZ) > 200e6:
            warnings.append(f"center_freq_hz ({freq/1e9:.2f} GHz) is not 24 GHz ± 200 MHz.")
        frame_ms = float(sub["performance"].get("max_range_m", 0)) * 0  # placeholder
        # Frame duration check
        N = int(design["num_chirps"])
        T = float(design["chirp_duration_s"])
        frame_ms_actual = N * T * 1e3
        if frame_ms_actual > REQ_FRAME_MAX_MS:
            warnings.append(f"Frame duration {frame_ms_actual:.1f} ms exceeds 100 ms (10 Hz update rate).")
    except (KeyError, TypeError):
        pass
    return warnings


def main():
    parser = argparse.ArgumentParser(description="RadarForge evaluation script")
    parser.add_argument("--submission", required=True, help="Path to submission.json")
    parser.add_argument("--verbose", action="store_true", help="Print detailed feedback")
    args = parser.parse_args()

    sub, load_err = load_submission(args.submission)
    if load_err:
        result = {
            "total": 0,
            "breakdown": {},
            "errors": [load_err]
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    all_errors = []
    warnings = validate_constraints(sub)
    all_errors.extend(warnings)

    r_score, r_errs = score_range_accuracy(sub)
    v_score, v_errs = score_velocity_accuracy(sub)
    a_score, a_errs = score_angular_resolution(sub)
    s_score, s_errs = score_snr_link_budget(sub)

    all_errors.extend(r_errs + v_errs + a_errs + s_errs)
    total = r_score + v_score + a_score + s_score

    result = {
        "total": round(total, 1),
        "breakdown": {
            "range_accuracy": {"score": round(r_score, 1), "max": 30},
            "velocity_accuracy": {"score": round(v_score, 1), "max": 25},
            "angular_resolution": {"score": round(a_score, 1), "max": 25},
            "snr_link_budget": {"score": round(s_score, 1), "max": 20},
        },
        "errors": all_errors,
    }

    print(json.dumps(result, indent=2))

    if args.verbose:
        print("\n--- Evaluation Summary ---")
        print(f"Total score: {total:.1f} / 100")
        for metric, data in result["breakdown"].items():
            print(f"  {metric:25s}: {data['score']:5.1f} / {data['max']}")
        if all_errors:
            print("\nIssues found:")
            for e in all_errors:
                print(f"  - {e}")


if __name__ == "__main__":
    main()
