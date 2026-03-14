"""
MIMO-Sat — Evaluation Script
==============================
Submission JSON schema expected at <submission_path>:
{
  "link_budget": {
    "downlink": {
      "eirp_dbw": <float>,
      "fspl_db": <float>,
      "rain_attenuation_db": <float>,
      "atmospheric_abs_db": <float>,
      "g_over_t_db_per_k": <float>,
      "received_c_over_n0_dbhz": <float>,
      "eb_n0_db": <float>          -- key metric: must meet required Eb/N0
    },
    "uplink": { ... same fields ... }
  },
  "modcod": {
    "downlink": {
      "modulation": "<QPSK|8PSK|16APSK|32APSK>",
      "fec_code": "<LDPC|Turbo|Polar>",
      "code_rate": "<str>",
      "spectral_efficiency_bps_per_hz": <float>,
      "required_eb_n0_db": <float>,
      "margin_db": <float>         -- must be >= 0.5 dB for any margin credit
    },
    "uplink": { ... same fields ... }
  },
  "beamforming": {
    "array_elements": <int>,         -- should be 256
    "beam_gain_zenith_db": <float>,  -- phased array gain at boresight
    "scan_loss_db_at_scan_angle": <float>,
    "half_power_beamwidth_deg": <float>,
    "scan_elevation_deg": <float>
  },
  "doppler": {
    "max_doppler_shift_hz_dl": <float>,   -- must be > 200000 Hz at low elevation
    "compensation_method": <str>,
    "residual_frequency_error_hz": <float>
  },
  "availability": {
    "link_margin_db": <float>,       -- must be > 0 for availability > 50%
    "availability_pct": <float>      -- must be >= 99.9 for full credit
  },
  "geometry": {
    "altitude_km": <float>,          -- must be 550 ± 50 km
    "elevation_deg": <float>,
    "slant_range_km": <float>
  }
}

Scoring (100 pts):
  Link budget accuracy  (30 pts): DL+UL budgets, FSPL consistency, Eb/N0 margins
  Array/MIMO capacity   (30 pts): phased array gain, spectral efficiency, throughput verification
  Beamforming design    (25 pts): scan loss, HPBW, Doppler analysis
  Documentation quality (15 pts): availability analysis, modcod selection rationale

Usage:
    python evaluate.py --submission submission.json
    python evaluate.py --submission submission.json --verbose
"""

import argparse
import json
import math
import sys

C = 3e8
K_B = 1.38e-23
RE = 6371e3
GM = 3.986e14

# Requirements
REQ_DL_DATA_RATE_MBPS = 100.0
REQ_UL_DATA_RATE_MBPS = 10.0
REQ_BER = 1e-6
REQ_AVAILABILITY_PCT = 99.9
REQ_ALTITUDE_KM = 550.0
REQ_ARRAY_ELEMENTS = 256
DL_FREQ = 12e9
UL_FREQ = 14e9


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


def fspl_db(slant_range_m, freq_hz):
    lam = C / freq_hz
    return 20 * math.log10(4 * math.pi * slant_range_m / lam)


def score_link_budget(sub):
    score = 0.0
    errors = []
    try:
        lb = sub["link_budget"]
        geo = sub.get("geometry", {})

        # 1. Altitude plausibility (3 pts)
        alt = float(geo.get("altitude_km", 550.0))
        if abs(alt - REQ_ALTITUDE_KM) <= 50:
            score += 3.0
        else:
            errors.append(f"altitude_km ({alt}) should be 550 ± 50 km.")

        # 2. Downlink FSPL consistency (6 pts)
        dl = lb["downlink"]
        slant_km = float(geo.get("slant_range_km", 550.0 / math.sin(math.radians(45))))
        expected_fspl = fspl_db(slant_km * 1e3, DL_FREQ)
        reported_fspl = float(dl["fspl_db"])
        if abs(reported_fspl - expected_fspl) < 3.0:
            score += 6.0
        elif abs(reported_fspl - expected_fspl) < 6.0:
            score += 3.0
            errors.append(f"DL FSPL ({reported_fspl:.1f} dB) differs from calculated ({expected_fspl:.1f} dB) by > 3 dB.")
        else:
            errors.append(f"DL FSPL ({reported_fspl:.1f} dB) inconsistent with geometry (expected ~{expected_fspl:.1f} dB).")

        # 3. Downlink Eb/N0 > required for chosen modcod (7 pts)
        modcod_dl = sub.get("modcod", {}).get("downlink", {})
        req_eb_n0 = float(modcod_dl.get("required_eb_n0_db", 7.0))
        avail_eb_n0 = float(dl["eb_n0_db"])
        margin = avail_eb_n0 - req_eb_n0
        if margin >= 3.0:
            score += 7.0
        elif margin >= 0.5:
            score += 5.0
        elif margin >= 0.0:
            score += 2.0
        else:
            errors.append(f"DL Eb/N0 ({avail_eb_n0:.1f} dB) below required ({req_eb_n0:.1f} dB) for chosen ModCod.")

        # 4. Uplink budget present and consistent (7 pts)
        ul = lb["uplink"]
        ul_fspl = float(ul["fspl_db"])
        expected_ul_fspl = fspl_db(slant_km * 1e3, UL_FREQ)
        if abs(ul_fspl - expected_ul_fspl) < 4.0:
            score += 4.0
        else:
            errors.append(f"UL FSPL ({ul_fspl:.1f} dB) inconsistent (expected ~{expected_ul_fspl:.1f} dB).")

        ul_eb_n0 = float(ul["eb_n0_db"])
        if ul_eb_n0 > 0:
            score += 3.0
        else:
            errors.append(f"UL Eb/N0 ({ul_eb_n0:.1f} dB) is non-positive; check uplink design.")

        # 5. Rain attenuation realistic (7 pts)
        rain_dl = float(dl["rain_attenuation_db"])
        if 3.0 <= rain_dl <= 30.0:
            score += 7.0
        elif rain_dl > 0:
            score += 3.0
            errors.append(f"DL rain_attenuation_db ({rain_dl:.1f}) seems unrealistic for tropical/Ku-band (expect 5-20 dB).")
        else:
            errors.append("DL rain_attenuation_db is zero or negative; include ITU-R rain model.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"link_budget: parse error — {e}")
    return clamp(score, 0, 30), errors


def score_array_capacity(sub):
    score = 0.0
    errors = []
    try:
        bf = sub["beamforming"]
        modcod_dl = sub.get("modcod", {}).get("downlink", {})

        # 1. Array element count correct (5 pts)
        n_elem = int(bf.get("array_elements", 0))
        if n_elem == REQ_ARRAY_ELEMENTS:
            score += 5.0
        else:
            errors.append(f"array_elements ({n_elem}) should be {REQ_ARRAY_ELEMENTS}.")

        # 2. Array gain plausible (8 pts)
        gain = float(bf.get("beam_gain_zenith_db", 0.0))
        # 256-element array with 0.5W per element: theoretical ~35 dBi
        if 28.0 <= gain <= 42.0:
            score += 8.0
        elif 22.0 <= gain < 28.0:
            score += 4.0
            errors.append(f"beam_gain_zenith_db ({gain:.1f}) seems low for 256-element array (expect ~30-38 dBi).")
        else:
            errors.append(f"beam_gain_zenith_db ({gain:.1f}) outside plausible range.")

        # 3. Spectral efficiency supports required data rate (10 pts)
        spec_eff = float(modcod_dl.get("spectral_efficiency_bps_per_hz", 0.0))
        # 100 Mbps in 36 MHz requires >= 2.78 bps/Hz
        if spec_eff >= 2.78:
            score += 10.0
        elif spec_eff >= 1.5:
            score += 6.0
            errors.append(f"spectral_efficiency ({spec_eff:.2f} bps/Hz) may be insufficient for 100 Mbps in 36 MHz. "
                          f"Need >= 2.78 bps/Hz.")
        else:
            errors.append(f"spectral_efficiency ({spec_eff:.2f} bps/Hz) too low for required throughput.")

        # 4. Uplink modcod supports 10 Mbps (7 pts)
        modcod_ul = sub.get("modcod", {}).get("uplink", {})
        ul_spec_eff = float(modcod_ul.get("spectral_efficiency_bps_per_hz", 0.0))
        if ul_spec_eff > 0:
            score += 7.0
        else:
            errors.append("uplink modcod spectral_efficiency missing or zero.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"array_capacity: parse error — {e}")
    return clamp(score, 0, 30), errors


def score_beamforming_design(sub):
    score = 0.0
    errors = []
    try:
        bf = sub["beamforming"]
        dop = sub.get("doppler", {})

        # 1. Scan loss computed and non-zero (7 pts)
        scan_loss = float(bf.get("scan_loss_db_at_scan_angle", 0.0))
        if 0.1 <= scan_loss <= 15.0:
            score += 7.0
        elif scan_loss == 0.0:
            errors.append("scan_loss_db_at_scan_angle is zero — scan loss must be included for non-zenith beams.")
        else:
            score += 3.0
            errors.append(f"scan_loss_db ({scan_loss:.1f} dB) outside expected range (0.1–15 dB).")

        # 2. HPBW plausible for 256-element array (6 pts)
        hpbw = float(bf.get("half_power_beamwidth_deg", 0.0))
        # 16x16 array at lambda/2 spacing: HPBW ~ 3-8 deg
        if 2.0 <= hpbw <= 10.0:
            score += 6.0
        elif hpbw > 0:
            score += 3.0
            errors.append(f"half_power_beamwidth_deg ({hpbw:.2f}) outside expected range (2–10 deg) for 256-element array.")
        else:
            errors.append("half_power_beamwidth_deg missing or zero.")

        # 3. Doppler shift computed correctly (7 pts)
        max_dop = float(dop.get("max_doppler_shift_hz_dl", 0.0))
        # v_sat ~ 7.6 km/s, f=12 GHz → max Doppler ~ 304 kHz (LOS component at horizon)
        if max_dop >= 150e3:
            score += 7.0
        elif max_dop >= 50e3:
            score += 4.0
            errors.append(f"max_doppler_shift_hz_dl ({max_dop/1e3:.1f} kHz) seems low — at low elevation Doppler can exceed 200 kHz.")
        else:
            errors.append(f"max_doppler_shift_hz_dl ({max_dop:.0f} Hz) too low; check orbital geometry.")

        # 4. Compensation method described (5 pts)
        method = dop.get("compensation_method", "")
        if len(str(method)) > 5:
            score += 5.0
        else:
            errors.append("doppler.compensation_method is empty or very brief.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"beamforming_design: parse error — {e}")
    return clamp(score, 0, 25), errors


def score_documentation(sub):
    score = 0.0
    errors = []
    try:
        avail = sub.get("availability", {})

        # 1. Availability >= 99.9% (8 pts)
        avail_pct = float(avail.get("availability_pct", 0.0))
        if avail_pct >= REQ_AVAILABILITY_PCT:
            score += 8.0
        elif avail_pct >= 99.0:
            score += 5.0
            errors.append(f"availability_pct ({avail_pct:.3f}%) is below 99.9% requirement.")
        else:
            errors.append(f"availability_pct ({avail_pct:.3f}%) is well below 99.9% requirement.")

        # 2. Link margin positive (4 pts)
        margin = float(avail.get("link_margin_db", -999.0))
        if margin >= 3.0:
            score += 4.0
        elif margin >= 0.0:
            score += 2.0
            errors.append(f"link_margin_db ({margin:.1f} dB) is positive but less than 3 dB — marginal design.")
        else:
            errors.append(f"link_margin_db ({margin:.1f} dB) is negative — link does not close.")

        # 3. Both uplink and downlink modcod selected (3 pts)
        mc = sub.get("modcod", {})
        if "downlink" in mc and "uplink" in mc:
            score += 3.0
        elif "downlink" in mc:
            score += 1.0
            errors.append("Uplink ModCod not selected.")
        else:
            errors.append("ModCod selection missing for both directions.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"documentation: parse error — {e}")
    return clamp(score, 0, 15), errors


def main():
    parser = argparse.ArgumentParser(description="MIMO-Sat evaluation script")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    sub, err = load_submission(args.submission)
    if err:
        print(json.dumps({"total": 0, "breakdown": {}, "errors": [err]}, indent=2))
        sys.exit(1)

    lb_score, lb_errs = score_link_budget(sub)
    ac_score, ac_errs = score_array_capacity(sub)
    bf_score, bf_errs = score_beamforming_design(sub)
    doc_score, doc_errs = score_documentation(sub)

    all_errors = lb_errs + ac_errs + bf_errs + doc_errs
    total = lb_score + ac_score + bf_score + doc_score

    result = {
        "total": round(total, 1),
        "breakdown": {
            "link_budget_accuracy": {"score": round(lb_score, 1), "max": 30},
            "array_mimo_capacity":  {"score": round(ac_score, 1), "max": 30},
            "beamforming_design":   {"score": round(bf_score, 1), "max": 25},
            "documentation_analysis": {"score": round(doc_score, 1), "max": 15},
        },
        "errors": all_errors,
    }
    print(json.dumps(result, indent=2))

    if args.verbose:
        print(f"\nTotal: {total:.1f} / 100")
        for k, v in result["breakdown"].items():
            print(f"  {k:30s}: {v['score']:5.1f} / {v['max']}")
        if all_errors:
            print("\nIssues:")
            for e in all_errors:
                print(f"  - {e}")


if __name__ == "__main__":
    main()
