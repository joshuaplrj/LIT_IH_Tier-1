"""
WaveCraft — Evaluation Script
================================
Submission JSON schema expected at <submission_path>:
{
  "architecture": {
    "topology": "<direct_conversion|superheterodyne|direct_sampling>",
    "adc_sampling_rate_msps": <float>,  -- must support widest standard's bandwidth
    "adc_enob": <float>,                -- must be >= 10 bits for > 60 dB DR
    "rf_bandwidth_mhz": <float>,
    "image_rejection_db": <float>,      -- must be >= 30 dB
    "iq_imbalance_correction": <bool>
  },
  "analog_frontend": {
    "lna_noise_figure_db": <float>,     -- must be <= 5 dB (target: < 3 dB)
    "lna_gain_db": <float>,
    "frequency_range_mhz": {"min": <float>, "max": <float>},
    "lo_frequency_mhz": <float>,
    "phase_noise_dbc_per_hz_at_1khz": <float>
  },
  "digital_frontend": {
    "ddc_implemented": <bool>,
    "channelization_type": "<polyphase|fft|single_channel>",
    "sample_rate_conversion": <bool>
  },
  "standards_implemented": [
    {
      "name": "<FM|DAB+|LTE|GPS|WiFi>",
      "center_freq_mhz": <float>,
      "bandwidth_mhz": <float>,
      "demodulation": <str>,            -- description of demod method
      "sensitivity_dbm": <float>,       -- minimum detectable signal
      "selectivity_db": <float>,        -- adjacent channel rejection
      "ber_at_sensitivity": <float>     -- BER at minimum signal level
    }
    ...                                 -- at least 2 entries required
  ],
  "performance": {
    "n_standards_implemented": <int>,   -- must be >= 2 for full coverage score
    "dynamic_range_db": <float>,
    "noise_figure_system_db": <float>
  }
}

Scoring (100 pts):
  Standard coverage   (35 pts): number of standards implemented with working demodulators
  Receiver sensitivity(30 pts): sensitivity per standard vs theoretical minimum
  Selectivity         (20 pts): adjacent channel rejection per standard
  Architecture quality(15 pts): topology choice justification, ADC sizing, digital front-end

VALID_STANDARDS  = {FM, DAB+, LTE, GPS, WiFi}
SENSITIVITY_REFS = {FM: -96, DAB+: -95, LTE: -100, GPS: -130, WiFi: -82}  (dBm, approximate)

Usage:
    python evaluate.py --submission submission.json
    python evaluate.py --submission submission.json --verbose
"""

import argparse
import json
import sys
import math

K_B = 1.38e-23
T0 = 290.0

VALID_STANDARDS = {"FM", "DAB+", "LTE", "GPS", "WiFi"}

# Expected sensitivity ranges (dBm) for each standard with a good receiver
# (lower dBm = more sensitive; listed as [max acceptable, ideal])
SENSITIVITY_REF = {
    "FM":   {"bw_hz": 200e3,  "snr_min": 10.0},
    "DAB+": {"bw_hz": 1.5e6, "snr_min": 8.0},
    "LTE":  {"bw_hz": 10e6,  "snr_min": 7.0},
    "GPS":  {"bw_hz": 2.046e6, "snr_min": 14.0},
    "WiFi": {"bw_hz": 80e6,  "snr_min": 15.0},
}

REQ_MIN_STANDARDS = 2
REQ_IMAGE_REJECTION_DB = 30.0
REQ_LNA_NF_DB = 5.0
REQ_ADC_ENOB = 10.0


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


def theoretical_sensitivity(std_name, nf_db):
    """Compute theoretical MDS for a standard."""
    if std_name not in SENSITIVITY_REF:
        return -80.0
    ref = SENSITIVITY_REF[std_name]
    ktb_dbm = 10 * math.log10(K_B * T0 * ref["bw_hz"]) + 30
    return ktb_dbm + nf_db + ref["snr_min"]


def score_standard_coverage(sub):
    score = 0.0
    errors = []
    try:
        stds = sub.get("standards_implemented", [])
        n_std = len(stds)
        n_valid = sum(1 for s in stds if s.get("name", "") in VALID_STANDARDS
                      and s.get("demodulation", "") and len(str(s.get("demodulation", ""))) > 5)

        # 1. Minimum 2 standards (15 pts)
        if n_valid >= 5:
            score += 15.0
        elif n_valid >= 4:
            score += 12.0
        elif n_valid >= 3:
            score += 9.0
        elif n_valid >= REQ_MIN_STANDARDS:
            score += 6.0
        elif n_valid == 1:
            score += 3.0
            errors.append(f"Only {n_valid} standard implemented. Minimum required: {REQ_MIN_STANDARDS}.")
        else:
            errors.append("No valid standard implementations found.")

        # 2. Demodulation method described for each (10 pts, 2 per standard, max 5)
        demod_pts = min(n_valid * 2.0, 10.0)
        score += demod_pts

        # 3. Standards span multiple bands (10 pts)
        freqs = [float(s.get("center_freq_mhz", 0)) for s in stds if s.get("name") in VALID_STANDARDS]
        if len(freqs) >= 2:
            freq_ratio = max(freqs) / max(min(freqs), 1.0)
            if freq_ratio >= 15.0:    # e.g., FM 98 MHz vs LTE 1800 MHz = 18x
                score += 10.0
            elif freq_ratio >= 5.0:
                score += 6.0
            elif freq_ratio >= 2.0:
                score += 3.0
            else:
                errors.append("Standards chosen cover a narrow frequency range (< 2x). "
                               "Choose standards from different frequency bands.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"standard_coverage: parse error — {e}")
    return clamp(score, 0, 35), errors


def score_sensitivity(sub):
    score = 0.0
    errors = []
    try:
        stds = sub.get("standards_implemented", [])
        nf = float(sub.get("performance", {}).get("noise_figure_system_db",
                   sub.get("analog_frontend", {}).get("lna_noise_figure_db", 10.0)))

        pts_per_std = 30.0 / max(len(stds), 1)
        for s in stds:
            name = s.get("name", "")
            if name not in VALID_STANDARDS:
                continue
            reported_sens = float(s.get("sensitivity_dbm", 0))
            theory_sens = theoretical_sensitivity(name, nf)

            # Within 3 dB of theory: full credit; within 10 dB: partial; worse: minimal
            gap = reported_sens - theory_sens   # positive = worse than theory
            if gap <= 3.0:
                score += pts_per_std
            elif gap <= 10.0:
                score += pts_per_std * 0.6
                errors.append(f"{name}: sensitivity {reported_sens:.1f} dBm is {gap:.1f} dB above theoretical "
                               f"minimum ({theory_sens:.1f} dBm).")
            elif gap <= 20.0:
                score += pts_per_std * 0.3
                errors.append(f"{name}: sensitivity {reported_sens:.1f} dBm is {gap:.1f} dB worse than theory.")
            else:
                errors.append(f"{name}: sensitivity {reported_sens:.1f} dBm is far worse than theoretical "
                               f"minimum ({theory_sens:.1f} dBm). Check NF and bandwidth.")

        # LNA NF check (bonus penalty if > 5 dB)
        lna_nf = float(sub.get("analog_frontend", {}).get("lna_noise_figure_db", 10.0))
        if lna_nf > REQ_LNA_NF_DB:
            errors.append(f"lna_noise_figure_db ({lna_nf:.1f} dB) exceeds 5 dB — sensitivity will be limited.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"sensitivity: parse error — {e}")
    return clamp(score, 0, 30), errors


def score_selectivity(sub):
    score = 0.0
    errors = []
    try:
        stds = sub.get("standards_implemented", [])
        pts_per_std = 20.0 / max(len(stds), 1)

        for s in stds:
            name = s.get("name", "")
            if name not in VALID_STANDARDS:
                continue
            sel = float(s.get("selectivity_db", 0))

            # Required selectivity varies by standard
            req_sel = {"FM": 25, "DAB+": 30, "LTE": 40, "GPS": 20, "WiFi": 35}.get(name, 25)
            if sel >= req_sel + 10:
                score += pts_per_std
            elif sel >= req_sel:
                score += pts_per_std * 0.7
            elif sel >= req_sel * 0.7:
                score += pts_per_std * 0.4
                errors.append(f"{name}: selectivity_db ({sel:.1f}) below requirement ({req_sel} dB).")
            else:
                errors.append(f"{name}: selectivity_db ({sel:.1f} dB) far below requirement — "
                               f"channel filtering inadequate.")

        # Image rejection check
        img_rej = float(sub.get("architecture", {}).get("image_rejection_db", 0))
        if img_rej >= REQ_IMAGE_REJECTION_DB:
            score = min(score + 2.0, 20.0)
        else:
            errors.append(f"image_rejection_db ({img_rej:.1f}) below {REQ_IMAGE_REJECTION_DB} dB.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"selectivity: parse error — {e}")
    return clamp(score, 0, 20), errors


def score_architecture_quality(sub):
    score = 0.0
    errors = []
    try:
        arch = sub.get("architecture", {})
        afe = sub.get("analog_frontend", {})
        dfe = sub.get("digital_frontend", {})
        perf = sub.get("performance", {})

        # 1. Topology named (3 pts)
        topo = str(arch.get("topology", "")).lower()
        if any(t in topo for t in ["direct", "super", "sampling"]):
            score += 3.0
        else:
            errors.append(f"topology '{topo}' not recognised. Use direct_conversion, superheterodyne, or direct_sampling.")

        # 2. ADC ENOB >= 10 bits (4 pts)
        enob = float(arch.get("adc_enob", 0))
        if enob >= 12.0:
            score += 4.0
        elif enob >= REQ_ADC_ENOB:
            score += 2.0
        else:
            errors.append(f"adc_enob ({enob:.1f}) below minimum ({REQ_ADC_ENOB} bits) for sufficient dynamic range.")

        # 3. ADC sample rate covers widest selected standard (4 pts)
        stds = sub.get("standards_implemented", [])
        max_bw = max((float(s.get("bandwidth_mhz", 0)) for s in stds), default=0)
        adc_fs = float(arch.get("adc_sampling_rate_msps", 0))
        if adc_fs >= max_bw * 2.0:
            score += 4.0
        elif adc_fs > 0:
            score += 2.0
            errors.append(f"adc_sampling_rate_msps ({adc_fs:.1f}) may be insufficient for {max_bw:.1f} MHz bandwidth "
                           f"(requires >= {max_bw*2:.1f} Msps).")
        else:
            errors.append("adc_sampling_rate_msps is zero or missing.")

        # 4. Digital front-end implemented (2 pts)
        ddc = bool(dfe.get("ddc_implemented", False))
        src = bool(dfe.get("sample_rate_conversion", False))
        if ddc and src:
            score += 2.0
        elif ddc or src:
            score += 1.0
        else:
            errors.append("digital_frontend: neither DDC nor sample rate conversion reported.")

        # 5. Dynamic range plausible (2 pts)
        dr = float(perf.get("dynamic_range_db", 0))
        if dr >= 60.0:
            score += 2.0
        else:
            errors.append(f"dynamic_range_db ({dr:.1f}) below 60 dB — inadequate for most standards.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"architecture_quality: parse error — {e}")
    return clamp(score, 0, 15), errors


def main():
    parser = argparse.ArgumentParser(description="WaveCraft evaluation script")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    sub, err = load_submission(args.submission)
    if err:
        print(json.dumps({"total": 0, "breakdown": {}, "errors": [err]}, indent=2))
        sys.exit(1)

    cov_score, cov_errs = score_standard_coverage(sub)
    sen_score, sen_errs = score_sensitivity(sub)
    sel_score, sel_errs = score_selectivity(sub)
    arc_score, arc_errs = score_architecture_quality(sub)

    all_errors = cov_errs + sen_errs + sel_errs + arc_errs
    total = cov_score + sen_score + sel_score + arc_score

    result = {
        "total": round(total, 1),
        "breakdown": {
            "standard_coverage":   {"score": round(cov_score, 1), "max": 35},
            "receiver_sensitivity": {"score": round(sen_score, 1), "max": 30},
            "selectivity":         {"score": round(sel_score, 1), "max": 20},
            "architecture_quality":{"score": round(arc_score, 1), "max": 15},
        },
        "errors": all_errors,
    }
    print(json.dumps(result, indent=2))

    if args.verbose:
        print(f"\nTotal: {total:.1f} / 100")
        for k, v in result["breakdown"].items():
            print(f"  {k:24s}: {v['score']:5.1f} / {v['max']}")
        if all_errors:
            print("\nIssues:")
            for e in all_errors:
                print(f"  - {e}")


if __name__ == "__main__":
    main()
