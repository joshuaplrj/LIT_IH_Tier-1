"""
ChipCraft — Mixed-Signal ASIC Design for Biomedical Sensing Starter
====================================================================
Problem: Design an analog front-end (AFE) ASIC for ECG + PPG wearable sensor.

Requirements:
    ECG  : 0.5–5 mV differential, 0.05–150 Hz, noise < 5 µVrms, CMRR > 100 dB
    PPG  : photodiode current 100 pA – 10 µA, LED 20 mA, SNR > 60 dB
    ADC  : 16-bit SAR, 1 kSPS/channel, ENOB >= 14 bits, < 50 µW/channel
    Power: total AFE < 500 µW

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

# ─── Physical / process constants ────────────────────────────────────────────
K_B = 1.38e-23
T_KELVIN = 300.0        # nominal temperature (K)
Q_ELECTRON = 1.6e-19   # electron charge (C)

# Default supply / process parameters
VDD = 1.8               # supply voltage (V)
VREF = 1.0              # ADC reference voltage (V)
N_BITS = 16             # ADC resolution
FS = 1e3                # ADC sample rate (SPS)
N_CHANNELS = 8          # total ADC channels


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — SAR ADC DESIGN
# ═════════════════════════════════════════════════════════════════════════════

def design_sar_adc(n_bits: int = N_BITS, fs: float = FS,
                   vref: float = VREF, vdd: float = VDD) -> dict:
    """
    Design a 16-bit SAR ADC optimised for low power.

    Key design decisions:
        - CDAC: binary-weighted capacitor array
        - Comparator: dynamic latch (StrongARM)
        - SAR logic: static CMOS

    Returns:
        dict with c_unit_f, c_total_f, p_cdac_uw, p_comp_uw, p_logic_uw,
             p_total_uw, inl_lsb_rms, dnl_lsb_rms, enob_bits, sndr_db
    """
    # ── TODO 1: Compute minimum unit capacitance from kT/C noise constraint
    #   kT/C noise must be < (0.5 LSB)^2 = (Vref / 2^(N+1))^2
    #   C_unit >= kT * 2^(2*N) / Vref^2
    lsb_v = vref / (2 ** n_bits)
    c_unit_ktc = K_B * T_KELVIN * (2 ** (2 * n_bits)) / (vref ** 2)
    c_unit = max(c_unit_ktc * 2.0, 30e-15)     # PLACEHOLDER: use 2x margin, min 30 fF
    c_total = c_unit * (2 ** n_bits - 1)        # PLACEHOLDER: total CDAC capacitance

    # ── TODO 2: CDAC switching energy (average over binary codes)
    #   P_CDAC ≈ C_unit * Vref^2 * fs * N  (simplified; exact depends on code statistics)
    p_cdac = c_unit * (vref ** 2) * fs * n_bits       # PLACEHOLDER (W)

    # ── TODO 3: Comparator power (dynamic latch, clocked N times per conversion)
    #   P_comp = C_load * Vdd^2 * fs * N
    c_load_comp = 10e-15     # PLACEHOLDER (F) — output load capacitance of comparator
    p_comp = c_load_comp * (vdd ** 2) * fs * n_bits   # PLACEHOLDER (W)

    # ── TODO 4: SAR logic power (static CMOS, activity factor 0.5)
    #   P_logic = alpha * C_logic * Vdd^2 * f_clock
    #   f_clock = N * fs  (N clock cycles per conversion)
    c_logic = 50e-15     # PLACEHOLDER: total switching capacitance of SAR logic
    f_clock = n_bits * fs
    p_logic = 0.5 * c_logic * (vdd ** 2) * f_clock   # PLACEHOLDER (W)

    p_total_w = p_cdac + p_comp + p_logic
    p_total_uw = p_total_w * 1e6

    # ── TODO 5: Estimate INL/DNL from capacitor mismatch
    #   For sigma_C/C = 1%:  DNL_rms ~ sigma_C/C * 2^(N/2) LSBs
    sigma_c_rel = 0.01      # PLACEHOLDER: 1% relative capacitor mismatch
    dnl_rms = sigma_c_rel * np.sqrt(2 ** n_bits)
    inl_rms = dnl_rms * np.sqrt(n_bits) / 2    # PLACEHOLDER: rough INL estimate

    # ── TODO 6: Compute ENOB and SNDR
    #   SNDR_ideal = 6.02*N + 1.76 dB  minus noise penalty
    #   ENOB = (SNDR - 1.76) / 6.02
    #   Dominant noise sources: kT/C, comparator noise, quantisation
    sigma_ktc = np.sqrt(K_B * T_KELVIN / c_total) if c_total > 0 else 1e-6
    sigma_comp = 5e-6          # PLACEHOLDER: 5 µV RMS comparator noise
    sigma_quant = lsb_v / np.sqrt(12)
    sigma_total = np.sqrt(sigma_ktc ** 2 + sigma_comp ** 2 + sigma_quant ** 2)

    sndr_db = 20 * np.log10((vref / 2) / (sigma_total * np.sqrt(2))) if sigma_total > 0 else 98.0
    enob = (sndr_db - 1.76) / 6.02

    return {
        "resolution_bits": n_bits,
        "sampling_rate_ksps": fs / 1e3,
        "c_unit_ff": round(c_unit * 1e15, 2),
        "c_total_pf": round(c_total * 1e12, 4),
        "p_cdac_nw": round(p_cdac * 1e9, 2),
        "p_comp_nw": round(p_comp * 1e9, 2),
        "p_logic_nw": round(p_logic * 1e9, 2),
        "power_uw_per_channel": round(p_total_uw, 3),
        "inl_lsb_rms": round(inl_rms, 3),
        "dnl_lsb_rms": round(dnl_rms, 3),
        "sndr_db": round(sndr_db, 2),
        "enob_bits": round(enob, 2),
        "lsb_uv": round(lsb_v * 1e6, 4),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ECG ANALOG FRONT-END
# ═════════════════════════════════════════════════════════════════════════════

def design_ecg_frontend(vdd: float = VDD) -> dict:
    """
    Design the ECG instrumentation amplifier (3-op-amp INA topology).

    ECG requirements:
        Input  : 0.5 – 5 mV differential
        Noise  : < 5 µVrms (0.5 – 150 Hz)
        CMRR   : > 100 dB
        Bandwidth: 0.05 – 150 Hz
        Power  : < 100 µW for the channel

    Returns:
        dict with gain, CMRR, IRN, power_uw, bandwidth, input_impedance
    """
    # ── TODO 7: Design first-stage INA
    #   Gain = 1 + 2*R1/Rg  (choose Rg to set gain)
    R1 = 100e3      # PLACEHOLDER (Ω)
    Rg = 2e3        # PLACEHOLDER (Ω) → stage1 gain ≈ 101
    G_stage1 = 1 + 2 * R1 / Rg

    # ── TODO 8: Second-stage differential amplifier gain
    R3 = 100e3      # PLACEHOLDER (Ω)
    R2 = 10e3       # PLACEHOLDER (Ω) → G_stage2 = R3/R2 = 10
    G_stage2 = R3 / R2
    G_total = G_stage1 * G_stage2

    # ── TODO 9: Estimate CMRR
    #   CMRR ~ (1 + 2*R1/Rg) * (R3/R2) / delta_R  where delta_R = relative mismatch
    resistor_mismatch = 1e-4    # PLACEHOLDER: 0.01% matching (laser-trimmed)
    cmrr_linear = G_total / resistor_mismatch
    cmrr_db = 20 * np.log10(cmrr_linear)

    # ── TODO 10: Estimate input-referred noise (IRN)
    #   IRN = sqrt(en_amp^2 + (2*in_amp*Rs)^2) / G_stage1
    #   At low freq, must use chopper-stabilised OA to eliminate 1/f noise
    en_amp = 10e-9      # PLACEHOLDER: 10 nV/√Hz voltage noise spectral density
    in_amp = 1e-12      # PLACEHOLDER: 1 pA/√Hz current noise spectral density
    Rs = 10e3           # PLACEHOLDER: source resistance (electrode impedance)
    bw = 150.0          # Hz
    irn_rms = np.sqrt((en_amp ** 2 + (2 * in_amp * Rs) ** 2) * bw) / G_stage1 * 1e6  # µVrms

    # ── TODO 11: Estimate input impedance
    #   For chopper-stabilised INA: Zin ~ Vdd / (2 * I_bias * f_chop * C_in)
    #   Simplified: assume bootstrap input buffer adds > 100 MΩ
    input_impedance = 10e9      # PLACEHOLDER: > 10 GΩ (bootstrapped input)

    # ── TODO 12: Power estimate
    #   P = Vdd * (I_INA_stage1 * 2 + I_INA_stage2 + I_filter)
    I_bias_ua = 5.0     # PLACEHOLDER: µA per op-amp
    n_opamps = 3        # 3-op-amp INA
    power_uw = vdd * I_bias_ua * n_opamps

    return {
        "topology": "3-op-amp INA",
        "r_gain_ohm": Rg,
        "gain_stage1": round(G_stage1, 1),
        "gain_stage2": round(G_stage2, 1),
        "total_gain_db": round(20 * np.log10(G_total), 1),
        "cmrr_db": round(cmrr_db, 1),
        "input_referred_noise_uvrms": round(float(irn_rms), 3),
        "bandwidth_hz": bw,
        "input_impedance_ohm": input_impedance,
        "power_uw": round(power_uw, 2),
        "chopper_frequency_hz": 4000.0,    # chopper clock > 1/f corner
        "resistor_mismatch_ppm": resistor_mismatch * 1e6,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PPG ANALOG FRONT-END
# ═════════════════════════════════════════════════════════════════════════════

def design_ppg_frontend(vdd: float = VDD) -> dict:
    """
    Design the PPG transimpedance amplifier + LED drive circuit.

    PPG requirements:
        Photodiode current: 100 pA – 10 µA
        LED drive: 20 mA pulse, 10 µs – 1 ms configurable
        SNR: > 60 dB
        Ambient light rejection: > 80 dB

    Returns:
        dict with TIA design, LED power, SNR, ambient_rejection
    """
    # ── TODO 13: Size TIA feedback resistor and capacitor
    #   Rf >= Vout_min / I_min  (for 1 mV output at 100 pA input → Rf >= 10 MΩ)
    Rf = 10e6       # PLACEHOLDER (Ω)
    Cf = 10e-12     # PLACEHOLDER (F) → BW = 1/(2*pi*Rf*Cf)

    bw_tia = 1.0 / (2 * np.pi * Rf * Cf)

    # ── TODO 14: Noise: dominated by Johnson noise of Rf and shot noise
    #   In_Rf = sqrt(4*kT/Rf)  (Johnson noise current)
    #   In_shot at max current I_max = 10 µA, BW = 1 kHz
    in_johnson = np.sqrt(4 * K_B * T_KELVIN / Rf)   # A/√Hz
    I_dc_ppg = 1e-6     # PLACEHOLDER: mean photodiode DC current (A)
    in_shot = np.sqrt(2 * Q_ELECTRON * I_dc_ppg)     # A/√Hz
    in_total = np.sqrt(in_johnson ** 2 + in_shot ** 2)

    # Output noise referred to input in µA
    vout_noise = in_total * Rf * np.sqrt(bw_tia) * 1e6   # µVrms output noise

    # SNR with 1 µA signal and 1 kHz bandwidth
    signal_vout = 1e-6 * Rf    # V (1 µA × Rf)
    snr_db = 20 * np.log10(signal_vout / (in_total * Rf * np.sqrt(bw_tia) + 1e-12))

    # ── TODO 15: LED power
    #   Average P_LED = I_LED * Vf_LED * duty_cycle
    I_led = 20e-3       # PLACEHOLDER (A)
    V_fwd = 1.8         # PLACEHOLDER (V) forward voltage
    pulse_width_s = 100e-6   # PLACEHOLDER: 100 µs pulse
    pulse_rate_hz = 1e3      # PLACEHOLDER: 1 kHz PRF
    duty_cycle = pulse_width_s * pulse_rate_hz
    p_led_mw = I_led * V_fwd * duty_cycle * 1000   # mW

    # ── TODO 16: Ambient light rejection
    #   Using synchronous detection (lock-in) at f_LED: rejection ~ CMRR of
    #   synchronous demodulator = typically > 80 dB with low-pass filter
    ambient_rejection_db = 80.0   # PLACEHOLDER: target from problem statement

    # TIA quiescent power
    I_bias_tia = 2.0    # PLACEHOLDER: µA
    p_tia_uw = vdd * I_bias_tia

    return {
        "tia_feedback_resistance_mohm": Rf / 1e6,
        "tia_feedback_capacitance_pf": Cf * 1e12,
        "tia_bandwidth_hz": round(bw_tia, 1),
        "led_drive_current_ma": I_led * 1e3,
        "led_pulse_width_us": pulse_width_s * 1e6,
        "led_duty_cycle_pct": duty_cycle * 100,
        "snr_db": round(float(snr_db), 1),
        "ambient_rejection_db": ambient_rejection_db,
        "p_led_average_uw": round(p_led_mw * 1000, 1),
        "p_tia_quiescent_uw": round(p_tia_uw, 2),
        "p_channel_total_uw": round(p_led_mw * 1000 + p_tia_uw, 1),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — BIASING AND REFERENCE CIRCUITS
# ═════════════════════════════════════════════════════════════════════════════

def design_biasing(vdd: float = VDD, temperature_c: float = 27.0) -> dict:
    """
    Design bandgap voltage reference and current biasing.

    Target:
        Bandgap Vref ≈ 1.25 V (silicon bandgap at 0 K extrapolation)
        TC < 20 ppm/°C
        Output voltage 1.0 V for ADC reference

    Returns:
        dict with bandgap_voltage_v, tc_ppm_per_c, reference_accuracy_ppm_per_c,
             bias_current_na, power_uw
    """
    # ── TODO 17: Compute CTAT and PTAT components for bandgap
    #   V_BG = V_CTAT + V_PTAT
    #   V_CTAT ≈ Vbe (decreases with T, ~-1.5 mV/°C for BJT)
    #   V_PTAT ≈ k*T/q * ln(N)  (increases with T)
    v_be = 0.6          # PLACEHOLDER: forward voltage of BJT at T=300K
    v_t = K_B * T_KELVIN / Q_ELECTRON   # thermal voltage (~26 mV)
    v_ptat = v_t * np.log(8)            # PLACEHOLDER: ln(N) where N = emitter area ratio
    v_bg = v_be + 12 * v_ptat           # PLACEHOLDER: empirical factor for cancellation

    tc_ppm = 10.0       # PLACEHOLDER: ppm/°C (achievable with trimming)

    # Current reference: PTAT current through a resistor
    R_ptat = 100e3      # PLACEHOLDER (Ω)
    I_bias = v_ptat / R_ptat   # PLACEHOLDER (A)

    p_bias_uw = vdd * (I_bias * 4) * 1e6   # PLACEHOLDER: 4 mirror branches

    return {
        "bandgap_voltage_v": round(float(v_bg), 4),
        "reference_accuracy_ppm_per_c": tc_ppm,
        "bias_current_na": round(float(I_bias * 1e9), 2),
        "r_ptat_kohm": R_ptat / 1e3,
        "power_uw": round(float(p_bias_uw), 2),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — POWER BUDGET
# ═════════════════════════════════════════════════════════════════════════════

def compute_power_budget(ecg: dict, ppg: dict, adc: dict, bias: dict,
                          n_adc_channels: int = N_CHANNELS) -> dict:
    """
    Assemble total AFE power budget and check against 500 µW limit.

    Returns:
        dict with per-block and total power consumption
    """
    p_ecg = ecg["power_uw"]
    p_ppg = ppg["p_channel_total_uw"]
    p_adc_total = adc["power_uw_per_channel"] * n_adc_channels
    p_bias = bias["power_uw"]

    total_uw = p_ecg + p_ppg + p_adc_total + p_bias

    return {
        "ecg_total_uw": round(p_ecg, 2),
        "ppg_total_uw": round(p_ppg, 2),
        "adc_8ch_total_uw": round(p_adc_total, 2),
        "biasing_uw": round(p_bias, 2),
        "total_afe_uw": round(total_uw, 2),
        "meets_500uw_budget": total_uw <= 500.0,
        "budget_margin_uw": round(500.0 - total_uw, 2),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — NOISE SIMULATION (OPTIONAL VALIDATION)
# ═════════════════════════════════════════════════════════════════════════════

def simulate_ecg_noise(ecg: dict, n_samples: int = 10000) -> dict:
    """
    Monte Carlo simulation of ECG channel noise performance.

    Returns:
        dict with integrated noise, simulated IRN, margin vs 5 µVrms spec
    """
    # ── TODO 18: Simulate ECG signal chain
    #   Generate white noise + 1/f noise, filter, compute RMS
    bw = ecg.get("bandwidth_hz", 150.0)
    en_amp_nv_rtHz = 10.0       # PLACEHOLDER: 10 nV/√Hz
    in_rms = en_amp_nv_rtHz * np.sqrt(bw) / ecg.get("gain_stage1", 101) * 1e-3   # µVrms

    return {
        "integrated_noise_uvrms": round(in_rms, 3),
        "meets_5uvrms_spec": in_rms <= 5.0,
        "noise_margin_uvrms": round(5.0 - in_rms, 3),
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — INL / DNL SIMULATION (OPTIONAL)
# ═════════════════════════════════════════════════════════════════════════════

def simulate_adc_inl_dnl(adc: dict, n_mc: int = 200) -> dict:
    """
    Monte Carlo simulation of SAR ADC INL and DNL from capacitor mismatch.

    Returns:
        dict with peak INL, peak DNL, ENOB from simulation
    """
    n_bits = adc.get("resolution_bits", 16)
    sigma_c_rel = 0.005   # PLACEHOLDER: 0.5% relative capacitor mismatch

    inl_peaks = []
    dnl_peaks = []

    for _ in range(n_mc):
        # ── TODO 19: Simulate CDAC transfer function with random cap mismatch
        cap_weights = np.array([2 ** i for i in range(n_bits)], dtype=float)
        noise = np.random.normal(0, sigma_c_rel, n_bits)
        actual_weights = cap_weights * (1 + noise)
        actual_weights /= actual_weights.sum() / (2 ** n_bits - 1)

        # Generate transfer curve
        codes = np.arange(0, 2 ** n_bits)
        ideal_output = codes.astype(float)
        # Simplified: approximate actual output
        actual_output = ideal_output + np.random.normal(0, 0.5, len(codes))

        inl = actual_output - ideal_output
        dnl = np.diff(actual_output) - 1.0

        inl_peaks.append(np.max(np.abs(inl)))
        dnl_peaks.append(np.max(np.abs(dnl)))

    return {
        "peak_inl_lsb_mean": round(float(np.mean(inl_peaks)), 3),
        "peak_dnl_lsb_mean": round(float(np.mean(dnl_peaks)), 3),
        "peak_inl_lsb_3sigma": round(float(np.mean(inl_peaks) + 3 * np.std(inl_peaks)), 3),
    }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ChipCraft AFE ASIC design tool")
    parser.add_argument("--scenario", default=None,
                        help="JSON with process/supply overrides")
    parser.add_argument("--output", default="submission.json",
                        help="Output submission JSON path")
    parser.add_argument("--plot", action="store_true",
                        help="Generate noise spectrum plot")
    args = parser.parse_args()

    scenario = {"vdd_v": VDD, "process_node_nm": 180, "temperature_c": 27.0}
    if args.scenario and os.path.exists(args.scenario):
        with open(args.scenario) as f:
            scenario.update(json.load(f))

    vdd = scenario["vdd_v"]

    print("[ChipCraft] Step 1: SAR ADC design...")
    adc = design_sar_adc(N_BITS, FS, VREF, vdd)
    print(f"  C_unit         : {adc['c_unit_ff']:.1f} fF")
    print(f"  C_total        : {adc['c_total_pf']:.3f} pF")
    print(f"  Power/channel  : {adc['power_uw_per_channel']:.3f} µW")
    print(f"  ENOB           : {adc['enob_bits']:.2f} bits")
    print(f"  SNDR           : {adc['sndr_db']:.2f} dB")
    print(f"  INL (RMS)      : {adc['inl_lsb_rms']:.3f} LSB")
    print(f"  DNL (RMS)      : {adc['dnl_lsb_rms']:.3f} LSB")

    print("\n[ChipCraft] Step 2: ECG front-end design...")
    ecg = design_ecg_frontend(vdd)
    print(f"  Total gain     : {ecg['total_gain_db']:.1f} dB")
    print(f"  CMRR           : {ecg['cmrr_db']:.1f} dB")
    print(f"  IRN            : {ecg['input_referred_noise_uvrms']:.3f} µVrms")
    print(f"  Power          : {ecg['power_uw']:.2f} µW")

    print("\n[ChipCraft] Step 3: PPG front-end design...")
    ppg = design_ppg_frontend(vdd)
    print(f"  TIA Rf         : {ppg['tia_feedback_resistance_mohm']:.1f} MΩ")
    print(f"  SNR            : {ppg['snr_db']:.1f} dB")
    print(f"  Total power    : {ppg['p_channel_total_uw']:.1f} µW")

    print("\n[ChipCraft] Step 4: Biasing and reference design...")
    bias = design_biasing(vdd, scenario["temperature_c"])
    print(f"  Bandgap Vref   : {bias['bandgap_voltage_v']:.4f} V")
    print(f"  TC             : {bias['reference_accuracy_ppm_per_c']:.1f} ppm/°C")
    print(f"  Bias current   : {bias['bias_current_na']:.2f} nA")

    print("\n[ChipCraft] Step 5: Power budget...")
    pwr = compute_power_budget(ecg, ppg, adc, bias, N_CHANNELS)
    print(f"  ECG channel    : {pwr['ecg_total_uw']:.2f} µW")
    print(f"  PPG channel    : {pwr['ppg_total_uw']:.2f} µW")
    print(f"  ADC (8 ch)     : {pwr['adc_8ch_total_uw']:.2f} µW")
    print(f"  Biasing        : {pwr['biasing_uw']:.2f} µW")
    print(f"  TOTAL AFE      : {pwr['total_afe_uw']:.2f} µW  "
          f"({'PASS' if pwr['meets_500uw_budget'] else 'FAIL'} < 500 µW)")

    print("\n[ChipCraft] Step 6: Noise simulation...")
    noise = simulate_ecg_noise(ecg)
    print(f"  ECG IRN (sim)  : {noise['integrated_noise_uvrms']:.3f} µVrms "
          f"({'PASS' if noise['meets_5uvrms_spec'] else 'FAIL'} < 5 µVrms)")

    print("\n[ChipCraft] Step 7: INL/DNL Monte Carlo simulation...")
    linearity = simulate_adc_inl_dnl(adc, n_mc=100)
    print(f"  Peak INL mean  : {linearity['peak_inl_lsb_mean']:.3f} LSB")
    print(f"  Peak DNL mean  : {linearity['peak_dnl_lsb_mean']:.3f} LSB")

    if args.plot and HAS_PLOT:
        freqs = np.logspace(-1, 3, 500)
        bw_ecg = ecg["bandwidth_hz"]
        en = 10e-9   # nV/√Hz noise density
        noise_density = en * np.ones_like(freqs)   # white noise approx
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.loglog(freqs, noise_density * 1e9, label="Input-referred noise density")
        ax.axvspan(0.05, bw_ecg, alpha=0.15, color="green", label="ECG band (0.05–150 Hz)")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Noise (nV/√Hz)")
        ax.set_title("ECG Channel Input-Referred Noise Spectrum")
        ax.legend()
        ax.grid(True, which="both")
        fig.tight_layout()
        out_dir = os.path.dirname(os.path.abspath(args.output)) or "."
        fig.savefig(os.path.join(out_dir, "ecg_noise_spectrum.png"), dpi=150)
        plt.close(fig)

    # ── Assemble submission JSON ─────────────────────────────────────────────
    submission = {
        "ecg_channel": {
            "ina_gain_db": ecg["total_gain_db"],
            "input_impedance_ohm": ecg["input_impedance_ohm"],
            "cmrr_db": ecg["cmrr_db"],
            "input_referred_noise_uvrms": ecg["input_referred_noise_uvrms"],
            "bandwidth_hz": ecg["bandwidth_hz"],
            "power_uw": ecg["power_uw"],
        },
        "ppg_channel": {
            "tia_transimpedance_kohm": ppg["tia_feedback_resistance_mohm"] * 1e3,
            "led_drive_current_ma": ppg["led_drive_current_ma"],
            "snr_db": ppg["snr_db"],
            "ambient_rejection_db": ppg["ambient_rejection_db"],
            "power_uw": ppg["p_channel_total_uw"],
        },
        "sar_adc": {
            "resolution_bits": adc["resolution_bits"],
            "sampling_rate_ksps": adc["sampling_rate_ksps"],
            "enob_bits": adc["enob_bits"],
            "inl_lsb": linearity["peak_inl_lsb_mean"],
            "dnl_lsb": linearity["peak_dnl_lsb_mean"],
            "sndr_db": adc["sndr_db"],
            "power_uw_per_channel": adc["power_uw_per_channel"],
        },
        "biasing": {
            "bandgap_voltage_v": bias["bandgap_voltage_v"],
            "reference_accuracy_ppm_per_c": bias["reference_accuracy_ppm_per_c"],
            "bias_current_na": bias["bias_current_na"],
        },
        "power_budget": pwr,
    }

    with open(args.output, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"\n[ChipCraft] Submission saved to: {args.output}")


if __name__ == "__main__":
    main()
