"""
PhotonLink — Evaluation Script
================================
Submission JSON schema expected at <submission_path>:
{
  "link_budget": {
    "tx_power_dbm": <float>,             -- must be <= 23 dBm (200 mW, eye-safe)
    "beam_divergence_mrad": <float>,     -- typical range: 0.05–5 mrad
    "rx_aperture_diameter_m": <float>,   -- must be > 0
    "geometric_loss_db": <float>,        -- must be > 0
    "fog_attenuation_db": <float>,       -- must reflect visibility model
    "rain_attenuation_db": <float>,
    "scintillation_fade_margin_db": <float>,
    "pointing_loss_db": <float>,
    "total_loss_db": <float>,
    "received_power_dbm": <float>,
    "receiver_sensitivity_dbm": <float>,
    "link_margin_db": <float>           -- positive = link closes under given conditions
  },
  "channel_model": {
    "visibility_m": <float>,
    "rain_rate_mmhr": <float>,
    "Cn2_m_neg2_thirds": <float>,       -- typical range: 1e-17 (weak) to 1e-13 (strong)
    "rytov_variance": <float>,          -- must be > 0
    "turbulence_regime": "<weak|moderate|strong>",
    "fried_parameter_r0_m": <float>    -- r0 > 0
  },
  "diversity": {
    "n_tx_apertures": <int>,
    "n_rx_apertures": <int>,
    "diversity_gain_db": <float>        -- must be > 0 for aperture diversity credit
  },
  "adaptive_optics": {
    "n_actuators": <int>,               -- must be > 0
    "wavefront_sensor": <str>,
    "correction_bandwidth_hz": <float>, -- should relate to wind/turbulence
    "residual_wavefront_error_nm": <float>
  },
  "performance": {
    "ber_clear_sky": <float>,          -- must be <= 1e-9 for full credit
    "ber_with_fog_attenuation": <float>,
    "availability_pct": <float>,        -- must be >= 99.9 for full credit
    "modulation": <str>,
    "data_rate_gbps": <float>           -- must be 10.0
  }
}

Scoring:
  BER performance           (35 pts): clear-sky BER target, SNR margin, modulation choice
  Atmospheric model accuracy(30 pts): fog model, rain model, Rytov variance, r0 consistency
  Adaptive compensation     (25 pts): AO design, diversity gain, pointing loss
  Link budget completeness  (10 pts): all terms present, budget closes under clear-sky

Usage:
    python evaluate.py --submission submission.json
    python evaluate.py --submission submission.json --verbose
"""

import argparse
import json
import math
import sys

C = 3e8
LAMBDA_M = 1550e-9
LINK_RANGE_M = 5000.0
K_WAVE = 2 * math.pi / LAMBDA_M

REQ_BER = 1e-9
REQ_AVAIL_PCT = 99.9
REQ_DATA_RATE_GBPS = 10.0
MAX_TX_POWER_DBM = 23.0   # 200 mW eye-safe at 1550 nm


def load_submission(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def score_ber_performance(sub):
    score = 0.0
    errors = []
    try:
        perf = sub["performance"]
        lb = sub["link_budget"]

        # 1. Data rate correct (5 pts)
        dr = float(perf.get("data_rate_gbps", 0))
        if abs(dr - REQ_DATA_RATE_GBPS) < 0.1:
            score += 5.0
        else:
            errors.append(f"data_rate_gbps ({dr}) must be 10.0 Gbps.")

        # 2. Clear-sky BER target (15 pts)
        ber_clear = float(perf.get("ber_clear_sky", 1.0))
        if ber_clear <= REQ_BER:
            score += 15.0
        elif ber_clear <= 1e-6:
            score += 8.0
            errors.append(f"ber_clear_sky ({ber_clear:.1e}) exceeds BER target ({REQ_BER:.1e}).")
        elif ber_clear <= 1e-3:
            score += 3.0
            errors.append(f"ber_clear_sky ({ber_clear:.1e}) well above BER target.")
        else:
            errors.append(f"ber_clear_sky ({ber_clear:.1e}) is unacceptably high.")

        # 3. Link margin positive under clear sky (10 pts)
        margin = float(lb.get("link_margin_db", -999))
        if margin >= 5.0:
            score += 10.0
        elif margin >= 0.0:
            score += 6.0
            errors.append(f"link_margin_db ({margin:.1f}) is positive but < 5 dB — marginal.")
        else:
            errors.append(f"link_margin_db ({margin:.1f} dB) is negative — link does not close.")

        # 4. Modulation appropriate for turbulence channel (5 pts)
        mod = str(perf.get("modulation", "")).upper()
        if any(m in mod for m in ["OOK", "PPM", "DPSK", "BPSK", "DPIM", "OFDM"]):
            score += 5.0
        else:
            errors.append(f"modulation '{mod}' not recognised. Use OOK, PPM, DPSK, or similar.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"ber_performance: parse error — {e}")
    return clamp(score, 0, 35), errors


def score_atmospheric_model(sub):
    score = 0.0
    errors = []
    try:
        ch = sub["channel_model"]
        lb = sub["link_budget"]

        # 1. Cn2 in plausible range (5 pts)
        Cn2 = float(ch.get("Cn2_m_neg2_thirds", 0))
        if 1e-17 <= Cn2 <= 1e-12:
            score += 5.0
        elif Cn2 > 0:
            score += 2.0
            errors.append(f"Cn2 ({Cn2:.1e}) outside typical range (1e-17 to 1e-12 m^(-2/3)).")
        else:
            errors.append("Cn2 is zero or missing.")

        # 2. Rytov variance consistent with Cn2 (8 pts)
        sigma_R2 = float(ch.get("rytov_variance", 0))
        # Verify: sigma_R2 = 0.5 * Cn2 * k^(7/6) * L^(11/6)
        expected_sigma_R2 = 0.5 * Cn2 * (K_WAVE ** (7 / 6)) * (LINK_RANGE_M ** (11 / 6))
        if sigma_R2 > 0 and abs(math.log10(max(sigma_R2, 1e-30)) - math.log10(max(expected_sigma_R2, 1e-30))) < 0.5:
            score += 8.0
        elif sigma_R2 > 0:
            score += 4.0
            errors.append(f"rytov_variance ({sigma_R2:.4f}) inconsistent with Cn2 (expected ~{expected_sigma_R2:.4f}).")
        else:
            errors.append("rytov_variance is zero or missing.")

        # 3. Fried parameter r0 consistent with Cn2 (7 pts)
        r0 = float(ch.get("fried_parameter_r0_m", 0))
        expected_r0 = (0.423 * K_WAVE ** 2 * Cn2 * LINK_RANGE_M) ** (-3 / 5) if Cn2 > 0 else 0
        if r0 > 0 and expected_r0 > 0:
            ratio = r0 / expected_r0
            if 0.5 <= ratio <= 2.0:
                score += 7.0
            else:
                score += 3.0
                errors.append(f"fried_parameter_r0_m ({r0:.4f}) inconsistent with Cn2 (expected ~{expected_r0:.4f}).")
        else:
            errors.append("fried_parameter_r0_m missing or zero.")

        # 4. Fog attenuation included and non-zero (5 pts)
        fog_db = float(lb.get("fog_attenuation_db", -1))
        if fog_db > 0:
            score += 5.0
        elif fog_db == 0:
            errors.append("fog_attenuation_db is zero — fog is the dominant FSO impairment; must be modelled.")
        else:
            errors.append("fog_attenuation_db is negative or missing.")

        # 5. Turbulence regime label consistent with Rytov variance (5 pts)
        regime = str(ch.get("turbulence_regime", "")).lower()
        if sigma_R2 < 0.3 and "weak" in regime:
            score += 5.0
        elif 0.3 <= sigma_R2 < 1.0 and "moderate" in regime:
            score += 5.0
        elif sigma_R2 >= 1.0 and "strong" in regime:
            score += 5.0
        else:
            score += 2.0
            errors.append(f"turbulence_regime '{regime}' inconsistent with sigma_R2={sigma_R2:.4f}.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"atmospheric_model: parse error — {e}")
    return clamp(score, 0, 30), errors


def score_adaptive_compensation(sub):
    score = 0.0
    errors = []
    try:
        ao = sub.get("adaptive_optics", {})
        div = sub.get("diversity", {})
        lb = sub["link_budget"]

        # 1. Adaptive optics n_actuators > 0 (8 pts)
        n_act = int(ao.get("n_actuators", 0))
        r0 = float(sub.get("channel_model", {}).get("fried_parameter_r0_m", 0.01))
        D = float(lb.get("rx_aperture_diameter_m", 0.2))
        if n_act > 0:
            expected_n_act = max(1, int((D / r0) ** 2))
            if abs(n_act - expected_n_act) / max(expected_n_act, 1) < 5.0:
                score += 8.0
            else:
                score += 4.0
                errors.append(f"n_actuators ({n_act}) inconsistent with D/r0 ratio (expected ~{expected_n_act}).")
        else:
            errors.append("adaptive_optics.n_actuators is zero or missing.")

        # 2. Residual wavefront error is positive and < lambda/14 (Marechal) (5 pts)
        rwe = float(ao.get("residual_wavefront_error_nm", -1))
        lambda_nm = LAMBDA_M * 1e9
        if 0 < rwe < lambda_nm / 14:
            score += 5.0
        elif rwe > 0:
            score += 2.0
            errors.append(f"residual_wavefront_error_nm ({rwe:.1f}) exceeds lambda/14 ({lambda_nm/14:.1f} nm) — diffraction limit not met.")
        else:
            errors.append("residual_wavefront_error_nm missing or non-positive.")

        # 3. Pointing loss included (6 pts)
        pt_loss = float(lb.get("pointing_loss_db", -1))
        if pt_loss > 0:
            score += 6.0
        elif pt_loss == 0:
            errors.append("pointing_loss_db is zero — 1 mrad building sway must produce measurable pointing loss.")
        else:
            errors.append("pointing_loss_db is negative or missing.")

        # 4. Spatial diversity n > 1 (6 pts)
        n_tx = int(div.get("n_tx_apertures", 0))
        n_rx = int(div.get("n_rx_apertures", 0))
        if n_tx >= 2 or n_rx >= 2:
            score += 6.0
        elif n_tx == 1 and n_rx == 1:
            score += 2.0
            errors.append("Only 1 TX and 1 RX aperture — spatial diversity requires multiple apertures.")
        else:
            errors.append("diversity.n_tx_apertures and n_rx_apertures missing.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"adaptive_compensation: parse error — {e}")
    return clamp(score, 0, 25), errors


def score_link_budget_completeness(sub):
    score = 0.0
    errors = []
    required_fields = [
        "tx_power_dbm", "beam_divergence_mrad", "rx_aperture_diameter_m",
        "geometric_loss_db", "fog_attenuation_db", "rain_attenuation_db",
        "scintillation_fade_margin_db", "pointing_loss_db",
        "total_loss_db", "received_power_dbm", "receiver_sensitivity_dbm",
        "link_margin_db"
    ]
    try:
        lb = sub["link_budget"]
        present = sum(1 for f in required_fields if f in lb and lb[f] is not None)
        score = (present / len(required_fields)) * 8.0

        # TX power within eye-safe limit (2 pts)
        tx_pow = float(lb.get("tx_power_dbm", 999))
        if tx_pow <= MAX_TX_POWER_DBM:
            score += 2.0
        else:
            errors.append(f"tx_power_dbm ({tx_pow:.1f}) exceeds eye-safe limit ({MAX_TX_POWER_DBM} dBm / 200 mW).")

        missing = [f for f in required_fields if f not in lb]
        if missing:
            errors.append(f"Missing link budget fields: {missing}")

    except (KeyError, TypeError) as e:
        errors.append(f"link_budget_completeness: parse error — {e}")
    return clamp(score, 0, 10), errors


def main():
    parser = argparse.ArgumentParser(description="PhotonLink evaluation script")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    sub, err = load_submission(args.submission)
    if err:
        print(json.dumps({"total": 0, "breakdown": {}, "errors": [err]}, indent=2))
        sys.exit(1)

    ber_score, ber_errs = score_ber_performance(sub)
    atm_score, atm_errs = score_atmospheric_model(sub)
    ao_score, ao_errs = score_adaptive_compensation(sub)
    lb_score, lb_errs = score_link_budget_completeness(sub)

    # Availability check (bonus deduction if < 99.9%)
    avail = float(sub.get("performance", {}).get("availability_pct", 0))
    avail_penalty = 0.0
    avail_note = ""
    if avail < REQ_AVAIL_PCT:
        avail_penalty = 5.0
        avail_note = f"availability_pct ({avail:.3f}%) below 99.9% requirement (-5 pts)."

    all_errors = ber_errs + atm_errs + ao_errs + lb_errs
    if avail_note:
        all_errors.append(avail_note)
    total = max(0.0, ber_score + atm_score + ao_score + lb_score - avail_penalty)

    result = {
        "total": round(total, 1),
        "breakdown": {
            "ber_performance":      {"score": round(ber_score, 1), "max": 35},
            "atmospheric_model":    {"score": round(atm_score, 1), "max": 30},
            "adaptive_compensation":{"score": round(ao_score, 1),  "max": 25},
            "link_budget_complete": {"score": round(lb_score, 1),  "max": 10},
        },
        "errors": all_errors,
    }
    print(json.dumps(result, indent=2))

    if args.verbose:
        print(f"\nTotal: {total:.1f} / 100")
        for k, v in result["breakdown"].items():
            print(f"  {k:28s}: {v['score']:5.1f} / {v['max']}")
        if all_errors:
            print("\nIssues:")
            for e in all_errors:
                print(f"  - {e}")


if __name__ == "__main__":
    main()
