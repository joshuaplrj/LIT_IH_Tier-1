"""
VibeKill — Evaluation Script   (MECH-P4)
==========================================
Usage:
    python evaluate.py --submission <path-to-report.json>

Expected report.json schema
----------------------------
{
    "actuator_type":                    str   -- description of actuator
    "sensor_type":                      str   -- description of sensor
    "control_algorithm":                str   -- "FxLMS" | "H_infinity" | "DVF" | "PID" | other
    "chatter_frequency_Hz":             float -- dominant chatter frequency; must be in [250, 400]
    "attenuation_dB":                   float -- vibration attenuation [dB]; must be > 20
    "control_bandwidth_Hz":             float -- [Hz]; must be >= 500
    "static_stiffness_preservation_pct":float -- [%]; must be > 90
    "response_time_ms":                 float -- settling time [ms]; must be < 100
    "stability_margin_dB":              float -- gain margin [dB]; must be > 6
    "phase_margin_deg":                 float -- phase margin [deg]; must be > 30
    "actuator_force_N":                 float -- peak force [N]
    "actuator_stroke_um":               float -- stroke [μm]
    "controller_sampling_rate_Hz":      float -- [Hz]; must be >= 2000 (Nyquist for 1 kHz)
    "open_loop_fn_Hz":                  list  -- open-loop natural frequencies [Hz]
    "closed_loop_fn_Hz":                list  -- closed-loop natural frequencies [Hz]
}

Scoring rubric (total = 100 points):
    Attenuation Achieved    (40 pts): dB attenuation at chatter frequencies
    Control Stability       (25 pts): gain margin, phase margin, Nyquist-compliant sample rate
    Response Time           (20 pts): settling time
    Design Quality          (15 pts): completeness of actuator/sensor spec + bandwidth
"""

import argparse
import json
import sys

REQUIRED_FIELDS = [
    "actuator_type", "sensor_type", "control_algorithm", "chatter_frequency_Hz",
    "attenuation_dB", "control_bandwidth_Hz", "static_stiffness_preservation_pct",
    "response_time_ms", "stability_margin_dB", "phase_margin_deg",
    "actuator_force_N", "actuator_stroke_um", "controller_sampling_rate_Hz",
    "open_loop_fn_Hz", "closed_loop_fn_Hz",
]

ATTENUATION_TARGET_DB  = 20.0
STIFFNESS_TARGET_PCT   = 90.0
GAIN_MARGIN_MIN_DB     = 6.0
PHASE_MARGIN_MIN_DEG   = 30.0
CHATTER_BAND_MIN       = 250.0
CHATTER_BAND_MAX       = 400.0


def load_submission(path: str) -> tuple:
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, [f"File not found: {path}"]
    except json.JSONDecodeError as e:
        return None, [f"JSON parse error: {e}"]
    return data, []


def check_required_fields(data: dict) -> list:
    return [f for f in REQUIRED_FIELDS if f not in data]


# ---------------------------------------------------------------------------
# Attenuation scoring (40 pts)
# ---------------------------------------------------------------------------

def score_attenuation(data: dict) -> tuple:
    max_score = 40
    score     = 0
    details   = {}
    errors    = []

    # Chatter frequency in range (5 pts)
    fn = data.get("chatter_frequency_Hz", 0)
    if CHATTER_BAND_MIN <= fn <= CHATTER_BAND_MAX:
        fn_pts = 5
    else:
        fn_pts = 0
        errors.append(f"Chatter frequency {fn} Hz is outside required band [{CHATTER_BAND_MIN}, {CHATTER_BAND_MAX}] Hz.")
    details["chatter_frequency_Hz"] = {"value": fn, "points": fn_pts, "max": 5}
    score += fn_pts

    # Attenuation achieved (30 pts)
    att = data.get("attenuation_dB", 0)
    if att >= 40.0:
        att_pts = 30
    elif att >= 30.0:
        att_pts = 22
    elif att >= 20.0:
        att_pts = 15
    elif att >= 10.0:
        att_pts = 7
        errors.append(f"Attenuation {att:.1f} dB is below the 20 dB target.")
    else:
        att_pts = 0
        errors.append(f"Attenuation {att:.1f} dB is inadequate (< 10 dB).")
    details["attenuation_dB"] = {"value": att, "target": ATTENUATION_TARGET_DB,
                                  "points": att_pts, "max": 30}
    score += att_pts

    # Static stiffness preservation (5 pts)
    sp = data.get("static_stiffness_preservation_pct", 0)
    if sp >= 95.0:
        sp_pts = 5
    elif sp >= 90.0:
        sp_pts = 3
    else:
        sp_pts = 0
        errors.append(f"Static stiffness preservation {sp:.1f}% is below 90% target.")
    details["static_stiffness_preservation_pct"] = {"value": sp, "target": 90.0,
                                                      "points": sp_pts, "max": 5}
    score += sp_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Control Stability scoring (25 pts)
# ---------------------------------------------------------------------------

def score_stability(data: dict) -> tuple:
    max_score = 25
    score     = 0
    details   = {}
    errors    = []

    # Gain margin (10 pts)
    gm = data.get("stability_margin_dB", 0)
    if gm >= 12.0:
        gm_pts = 10
    elif gm >= 6.0:
        gm_pts = 7
    elif gm >= 3.0:
        gm_pts = 3
        errors.append(f"Gain margin {gm:.1f} dB is below recommended 6 dB minimum.")
    else:
        gm_pts = 0
        errors.append(f"Gain margin {gm:.1f} dB is critically low; system may be unstable.")
    details["stability_margin_dB"] = {"value": gm, "target": GAIN_MARGIN_MIN_DB,
                                       "points": gm_pts, "max": 10}
    score += gm_pts

    # Phase margin (10 pts)
    pm = data.get("phase_margin_deg", 0)
    if pm >= 45.0:
        pm_pts = 10
    elif pm >= 30.0:
        pm_pts = 7
    elif pm >= 15.0:
        pm_pts = 3
        errors.append(f"Phase margin {pm:.1f}° is below 30° minimum.")
    else:
        pm_pts = 0
        errors.append(f"Phase margin {pm:.1f}° is critically low.")
    details["phase_margin_deg"] = {"value": pm, "target": PHASE_MARGIN_MIN_DEG,
                                    "points": pm_pts, "max": 10}
    score += pm_pts

    # Sampling rate (5 pts) — must be >= 2 × bandwidth for Nyquist
    fs   = data.get("controller_sampling_rate_Hz", 0)
    bw   = data.get("control_bandwidth_Hz", 500)
    nyq  = 2.0 * bw
    if fs >= 10.0 * bw:
        fs_pts = 5
    elif fs >= nyq:
        fs_pts = 3
    else:
        fs_pts = 0
        errors.append(f"Sampling rate {fs} Hz is below Nyquist rate {nyq} Hz for bandwidth {bw} Hz.")
    details["controller_sampling_rate_Hz"] = {"value": fs, "nyquist_min": nyq,
                                               "points": fs_pts, "max": 5}
    score += fs_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Response Time scoring (20 pts)
# ---------------------------------------------------------------------------

def score_response_time(data: dict) -> tuple:
    max_score = 20
    score     = 0
    details   = {}
    errors    = []

    rt = data.get("response_time_ms", 9999)
    if rt <= 20.0:
        rt_pts = 20
    elif rt <= 50.0:
        rt_pts = 14
    elif rt <= 100.0:
        rt_pts = 7
    else:
        rt_pts = 0
        errors.append(f"Response time {rt:.1f} ms exceeds 100 ms maximum.")
    details["response_time_ms"] = {"value": rt, "points": rt_pts, "max": 20}
    score += rt_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Design Quality scoring (15 pts)
# ---------------------------------------------------------------------------

def score_design_quality(data: dict, missing_fields: list) -> tuple:
    max_score = 15
    score     = 0
    details   = {}
    errors    = []

    # All required fields (8 pts)
    n_miss = len(missing_fields)
    if n_miss == 0:
        field_pts = 8
    elif n_miss <= 2:
        field_pts = 5
    else:
        field_pts = 0
        errors.append(f"Missing {n_miss} required fields: {missing_fields}")
    details["completeness"] = {"missing": missing_fields, "points": field_pts, "max": 8}
    score += field_pts

    # Control bandwidth >= 500 Hz (4 pts)
    bw = data.get("control_bandwidth_Hz", 0)
    if bw >= 500:
        bw_pts = 4
    elif bw >= 300:
        bw_pts = 2
    else:
        bw_pts = 0
        errors.append(f"Control bandwidth {bw} Hz is below the 500 Hz requirement.")
    details["control_bandwidth_Hz"] = {"value": bw, "points": bw_pts, "max": 4}
    score += bw_pts

    # Frequency lists provided and non-empty (3 pts)
    ol_fn = data.get("open_loop_fn_Hz", [])
    cl_fn = data.get("closed_loop_fn_Hz", [])
    if isinstance(ol_fn, list) and len(ol_fn) >= 1 and isinstance(cl_fn, list) and len(cl_fn) >= 1:
        fn_pts = 3
    else:
        fn_pts = 0
        errors.append("open_loop_fn_Hz and/or closed_loop_fn_Hz lists are missing or empty.")
    details["frequency_lists"] = {"ol_len": len(ol_fn) if isinstance(ol_fn, list) else 0,
                                   "cl_len": len(cl_fn) if isinstance(cl_fn, list) else 0,
                                   "points": fn_pts, "max": 3}
    score += fn_pts

    return score, max_score, details, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="VibeKill active vibration control evaluator (MECH-P4)")
    parser.add_argument("--submission", required=True, help="Path to report.json")
    args = parser.parse_args()

    data, load_errors = load_submission(args.submission)
    if data is None:
        result = {"total": 0, "breakdown": {}, "errors": load_errors}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    missing = check_required_fields(data)
    all_errors = list(load_errors)

    breakdown = {}

    att_score,  att_max,  att_det,  att_err  = score_attenuation(data)
    stab_score, stab_max, stab_det, stab_err = score_stability(data)
    rt_score,   rt_max,   rt_det,   rt_err   = score_response_time(data)
    dq_score,   dq_max,   dq_det,   dq_err   = score_design_quality(data, missing)

    all_errors.extend(att_err + stab_err + rt_err + dq_err)

    breakdown["attenuation_achieved"]    = {"score": att_score,  "max": att_max,  "details": att_det}
    breakdown["control_stability"]       = {"score": stab_score, "max": stab_max, "details": stab_det}
    breakdown["response_time"]           = {"score": rt_score,   "max": rt_max,   "details": rt_det}
    breakdown["design_quality"]          = {"score": dq_score,   "max": dq_max,   "details": dq_det}

    total = att_score + stab_score + rt_score + dq_score

    result = {
        "total":     total,
        "breakdown": breakdown,
        "errors":    all_errors,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
