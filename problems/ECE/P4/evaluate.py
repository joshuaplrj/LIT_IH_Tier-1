"""
ChipCraft — Evaluation Script
================================
Submission JSON schema expected at <submission_path>:
{
  "ecg_channel": {
    "ina_gain_db": <float>,
    "input_impedance_ohm": <float>,      -- must be >= 1e10 (10 GΩ)
    "cmrr_db": <float>,                  -- must be >= 100 dB
    "input_referred_noise_uvrms": <float>,-- must be <= 5.0 µVrms
    "bandwidth_hz": <float>,             -- must cover 0.05 – 150 Hz
    "power_uw": <float>
  },
  "ppg_channel": {
    "tia_transimpedance_kohm": <float>,
    "led_drive_current_ma": <float>,     -- should be 20 mA
    "snr_db": <float>,                   -- must be >= 60 dB
    "ambient_rejection_db": <float>,     -- must be >= 80 dB
    "power_uw": <float>
  },
  "sar_adc": {
    "resolution_bits": 16,
    "sampling_rate_ksps": 1.0,
    "enob_bits": <float>,                -- must be >= 14 bits
    "inl_lsb": <float>,                  -- must be <= 1.0 LSB
    "dnl_lsb": <float>,                  -- must be <= 0.5 LSB (no missing codes)
    "sndr_db": <float>,
    "power_uw_per_channel": <float>      -- must be <= 50 µW
  },
  "biasing": {
    "bandgap_voltage_v": <float>,        -- should be 1.0 – 1.3 V
    "reference_accuracy_ppm_per_c": <float>,
    "bias_current_na": <float>
  },
  "power_budget": {
    "ecg_total_uw": <float>,
    "ppg_total_uw": <float>,
    "adc_8ch_total_uw": <float>,
    "biasing_uw": <float>,
    "total_afe_uw": <float>             -- must be <= 500 µW
  }
}

Scoring (100 pts):
  ADC linearity     (30 pts): ENOB, INL, DNL, SNDR
  Power consumption (30 pts): per-channel ADC power, total AFE power, power budget breakdown
  Noise floor       (25 pts): ECG IRN, PPG SNR, bandgap accuracy
  Layout quality    (15 pts): topology choices, headroom analysis, design rationale

Usage:
    python evaluate.py --submission submission.json
    python evaluate.py --submission submission.json --verbose
"""

import argparse
import json
import sys

REQ_ENOB = 14.0
REQ_INL_LSB = 1.0
REQ_DNL_LSB = 0.5
REQ_ADC_POWER_UW = 50.0
REQ_TOTAL_POWER_UW = 500.0
REQ_CMRR_DB = 100.0
REQ_IRN_UVRMS = 5.0
REQ_INPUT_Z_OHM = 1e10
REQ_PPG_SNR_DB = 60.0
REQ_AMB_REJ_DB = 80.0


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


def score_adc_linearity(sub):
    score = 0.0
    errors = []
    try:
        adc = sub["sar_adc"]

        # 1. Resolution (2 pts)
        res = int(adc.get("resolution_bits", 0))
        if res == 16:
            score += 2.0
        else:
            errors.append(f"resolution_bits ({res}) must be 16.")

        # 2. ENOB >= 14 bits (12 pts)
        enob = float(adc["enob_bits"])
        if enob >= 15.0:
            score += 12.0
        elif enob >= REQ_ENOB:
            score += 9.0
        elif enob >= 13.0:
            score += 5.0
        elif enob >= 12.0:
            score += 2.0
        else:
            errors.append(f"enob_bits ({enob:.2f}) below minimum ({REQ_ENOB} bits).")

        # 3. INL <= 1 LSB (8 pts)
        inl = float(adc["inl_lsb"])
        if inl <= 0.5:
            score += 8.0
        elif inl <= REQ_INL_LSB:
            score += 5.0
        elif inl <= 2.0:
            score += 2.0
            errors.append(f"inl_lsb ({inl:.3f}) exceeds 1 LSB — linearity degraded.")
        else:
            errors.append(f"inl_lsb ({inl:.3f}) severely exceeds limit ({REQ_INL_LSB} LSB).")

        # 4. DNL <= 0.5 LSB (no missing codes) (8 pts)
        dnl = float(adc["dnl_lsb"])
        if dnl <= 0.25:
            score += 8.0
        elif dnl <= REQ_DNL_LSB:
            score += 5.0
        elif dnl <= 1.0:
            score += 2.0
            errors.append(f"dnl_lsb ({dnl:.3f}) > 0.5 LSB — risk of missing codes.")
        else:
            errors.append(f"dnl_lsb ({dnl:.3f}) > 1.0 LSB — missing codes present.")

        # 5. Sample rate correct (0 pts deducted, just flag)
        sr = float(adc.get("sampling_rate_ksps", 0))
        if abs(sr - 1.0) > 0.1:
            errors.append(f"sampling_rate_ksps ({sr}) should be 1.0 kSPS.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"adc_linearity: parse error — {e}")
    return clamp(score, 0, 30), errors


def score_power_consumption(sub):
    score = 0.0
    errors = []
    try:
        adc = sub["sar_adc"]
        pwr = sub["power_budget"]

        # 1. ADC power per channel <= 50 µW (12 pts)
        adc_pw = float(adc["power_uw_per_channel"])
        if adc_pw <= 10.0:
            score += 12.0
        elif adc_pw <= 25.0:
            score += 9.0
        elif adc_pw <= REQ_ADC_POWER_UW:
            score += 6.0
        elif adc_pw <= 100.0:
            score += 2.0
            errors.append(f"power_uw_per_channel ({adc_pw:.2f} µW) exceeds 50 µW limit.")
        else:
            errors.append(f"power_uw_per_channel ({adc_pw:.2f} µW) far exceeds limit.")

        # 2. Total AFE <= 500 µW (12 pts)
        total = float(pwr["total_afe_uw"])
        if total <= 300.0:
            score += 12.0
        elif total <= 400.0:
            score += 9.0
        elif total <= REQ_TOTAL_POWER_UW:
            score += 6.0
        elif total <= 700.0:
            score += 2.0
            errors.append(f"total_afe_uw ({total:.2f} µW) exceeds 500 µW limit.")
        else:
            errors.append(f"total_afe_uw ({total:.2f} µW) far exceeds limit — design not feasible.")

        # 3. Power budget adds up (6 pts)
        p_sum = (float(pwr.get("ecg_total_uw", 0)) +
                 float(pwr.get("ppg_total_uw", 0)) +
                 float(pwr.get("adc_8ch_total_uw", 0)) +
                 float(pwr.get("biasing_uw", 0)))
        if abs(p_sum - total) < total * 0.05:
            score += 6.0
        else:
            score += 2.0
            errors.append(f"Power budget doesn't add up: components sum to {p_sum:.2f} µW, total reported {total:.2f} µW.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"power_consumption: parse error — {e}")
    return clamp(score, 0, 30), errors


def score_noise_floor(sub):
    score = 0.0
    errors = []
    try:
        ecg = sub["ecg_channel"]
        ppg = sub["ppg_channel"]
        bias = sub.get("biasing", {})

        # 1. ECG CMRR >= 100 dB (8 pts)
        cmrr = float(ecg["cmrr_db"])
        if cmrr >= 120.0:
            score += 8.0
        elif cmrr >= REQ_CMRR_DB:
            score += 5.0
        elif cmrr >= 80.0:
            score += 2.0
            errors.append(f"cmrr_db ({cmrr:.1f}) below 100 dB requirement.")
        else:
            errors.append(f"cmrr_db ({cmrr:.1f}) severely below requirement.")

        # 2. ECG input-referred noise <= 5 µVrms (8 pts)
        irn = float(ecg["input_referred_noise_uvrms"])
        if irn <= 1.0:
            score += 8.0
        elif irn <= 3.0:
            score += 6.0
        elif irn <= REQ_IRN_UVRMS:
            score += 4.0
        elif irn <= 10.0:
            score += 1.0
            errors.append(f"input_referred_noise_uvrms ({irn:.3f}) exceeds 5 µVrms.")
        else:
            errors.append(f"input_referred_noise_uvrms ({irn:.3f}) far exceeds 5 µVrms.")

        # 3. ECG input impedance >= 10 GΩ (4 pts)
        zin = float(ecg["input_impedance_ohm"])
        if zin >= REQ_INPUT_Z_OHM:
            score += 4.0
        else:
            errors.append(f"input_impedance_ohm ({zin:.2e}) below 10 GΩ requirement.")

        # 4. PPG SNR >= 60 dB (3 pts)
        snr = float(ppg["snr_db"])
        if snr >= REQ_PPG_SNR_DB:
            score += 3.0
        else:
            errors.append(f"ppg snr_db ({snr:.1f}) below 60 dB requirement.")

        # 5. Ambient light rejection >= 80 dB (2 pts)
        amb = float(ppg["ambient_rejection_db"])
        if amb >= REQ_AMB_REJ_DB:
            score += 2.0
        else:
            errors.append(f"ambient_rejection_db ({amb:.1f}) below 80 dB requirement.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"noise_floor: parse error — {e}")
    return clamp(score, 0, 25), errors


def score_layout_quality(sub):
    score = 0.0
    errors = []
    try:
        ecg = sub["ecg_channel"]
        adc = sub["sar_adc"]
        bias = sub.get("biasing", {})
        ppg = sub["ppg_channel"]

        # 1. Bandgap reference plausible (4 pts)
        vbg = float(bias.get("bandgap_voltage_v", 0))
        if 0.9 <= vbg <= 1.35:
            score += 4.0
        else:
            errors.append(f"bandgap_voltage_v ({vbg:.4f}) outside 0.9–1.35 V range.")

        # 2. TC < 50 ppm/°C (4 pts)
        tc = float(bias.get("reference_accuracy_ppm_per_c", 999))
        if tc <= 10.0:
            score += 4.0
        elif tc <= 30.0:
            score += 2.0
            errors.append(f"reference_accuracy_ppm_per_c ({tc:.1f}) > 10 ppm/°C — trimming needed.")
        else:
            errors.append(f"reference_accuracy_ppm_per_c ({tc:.1f}) > 50 ppm/°C — reference too inaccurate.")

        # 3. INA gain appropriate for ECG signals (4 pts)
        gain = float(ecg.get("ina_gain_db", 0))
        # For 0.5–5 mV input to fill 1 V ADC range: gain ~ 200–2000 (46–66 dB)
        if 40.0 <= gain <= 70.0:
            score += 4.0
        elif 30.0 <= gain < 40.0 or 70.0 < gain <= 80.0:
            score += 2.0
            errors.append(f"ina_gain_db ({gain:.1f}) outside optimal range (40–70 dB for ECG).")
        else:
            errors.append(f"ina_gain_db ({gain:.1f}) appears inappropriate for ECG signal levels.")

        # 4. TIA bandwidth >= 1 kHz for PPG (3 pts)
        ztia = float(ppg.get("tia_transimpedance_kohm", 0))
        if ztia >= 1000.0:     # >= 1 MΩ TI resistance
            score += 3.0
        elif ztia > 0:
            score += 1.0
            errors.append(f"tia_transimpedance_kohm ({ztia:.1f}) seems low for 100 pA sensitivity.")
        else:
            errors.append("tia_transimpedance_kohm is zero or missing.")

    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"layout_quality: parse error — {e}")
    return clamp(score, 0, 15), errors


def main():
    parser = argparse.ArgumentParser(description="ChipCraft evaluation script")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    sub, err = load_submission(args.submission)
    if err:
        print(json.dumps({"total": 0, "breakdown": {}, "errors": [err]}, indent=2))
        sys.exit(1)

    adc_score, adc_errs = score_adc_linearity(sub)
    pwr_score, pwr_errs = score_power_consumption(sub)
    nse_score, nse_errs = score_noise_floor(sub)
    lyt_score, lyt_errs = score_layout_quality(sub)

    all_errors = adc_errs + pwr_errs + nse_errs + lyt_errs
    total = adc_score + pwr_score + nse_score + lyt_score

    result = {
        "total": round(total, 1),
        "breakdown": {
            "adc_linearity":   {"score": round(adc_score, 1), "max": 30},
            "power_consumption": {"score": round(pwr_score, 1), "max": 30},
            "noise_floor":     {"score": round(nse_score, 1), "max": 25},
            "layout_quality":  {"score": round(lyt_score, 1), "max": 15},
        },
        "errors": all_errors,
    }
    print(json.dumps(result, indent=2))

    if args.verbose:
        print(f"\nTotal: {total:.1f} / 100")
        for k, v in result["breakdown"].items():
            print(f"  {k:22s}: {v['score']:5.1f} / {v['max']}")
        if all_errors:
            print("\nIssues:")
            for e in all_errors:
                print(f"  - {e}")


if __name__ == "__main__":
    main()
