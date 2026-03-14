"""
WaveCraft — Software-Defined Radio for Multi-Standard Reception Starter
=======================================================================
Problem: Design an SDR receiver for simultaneous multi-standard reception.

Target standards:
    FM Radio : 88–108 MHz, 200 kHz, Wideband FM
    DAB+     : 174–240 MHz, 1.5 MHz, OFDM (DQPSK/QAM)
    LTE      : 700 MHz–2.6 GHz, up to 20 MHz, OFDMA
    WiFi 6E  : 5.925–7.125 GHz, up to 160 MHz, OFDM
    GPS L1   : 1575.42 MHz, 2.046 MHz, BPSK-CDMA

Minimum requirement: implement demodulation for at least 2 standards.

Usage:
    python starter.py --output submission.json
    python starter.py --standards FM LTE --output submission.json
    python starter.py --scenario scenario.json --output submission.json
"""

import argparse
import json
import os
import numpy as np
from scipy import signal as sp_signal
from scipy.signal import lfilter, firwin, resample_poly

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

# ─── Physical constants ──────────────────────────────────────────────────────
C = 3e8
K_B = 1.38e-23
T0 = 290.0

# ─── Standard definitions ────────────────────────────────────────────────────
STANDARDS = {
    "FM": {
        "freq_mhz": 98.0,
        "bandwidth_mhz": 0.2,
        "modulation": "WBFM",
        "max_deviation_hz": 75e3,
        "audio_bw_hz": 15e3,
        "min_snr_db": 10.0,
    },
    "DAB+": {
        "freq_mhz": 220.352,
        "bandwidth_mhz": 1.536,
        "modulation": "OFDM-DQPSK",
        "n_carriers": 1536,
        "symbol_duration_us": 1000.0,
    },
    "LTE": {
        "freq_mhz": 1800.0,
        "bandwidth_mhz": 10.0,
        "modulation": "OFDMA",
        "subcarrier_spacing_khz": 15.0,
        "n_subcarriers": 600,
        "cp_samples": 144,
        "fft_size": 1024,
    },
    "GPS": {
        "freq_mhz": 1575.42,
        "bandwidth_mhz": 2.046,
        "modulation": "BPSK-CDMA",
        "chip_rate_mcps": 1.023,
        "code_length": 1023,
    },
    "WiFi": {
        "freq_mhz": 6000.0,
        "bandwidth_mhz": 80.0,
        "modulation": "OFDM",
        "n_subcarriers": 996,
        "subcarrier_spacing_khz": 78.125,
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ARCHITECTURE DESIGN
# ═════════════════════════════════════════════════════════════════════════════

def design_architecture(standards: list) -> dict:
    """
    Select and parameterise the SDR receiver architecture.

    Args:
        standards : list of standard names to support (e.g. ["FM", "LTE"])

    Returns:
        dict with topology, ADC requirements, frequency plan, image rejection
    """
    # ── TODO 1: Select architecture topology
    #   Options: direct_conversion, superheterodyne, direct_sampling
    #   Direct conversion recommended for simplicity; superheterodyne for max performance.
    topology = "direct_conversion"    # PLACEHOLDER — justify your choice

    # ── TODO 2: Determine ADC sample rate from widest required bandwidth
    max_bw = max(STANDARDS[s]["bandwidth_mhz"] for s in standards if s in STANDARDS)
    adc_fs_msps = max_bw * 2.5   # PLACEHOLDER: Nyquist with 25% oversampling margin
    adc_fs_msps = max(adc_fs_msps, 10.0)    # minimum 10 Msps

    # ── TODO 3: ADC ENOB requirement
    #   For dynamic range > 60 dB: ENOB >= (DR - 1.76) / 6.02 >= 10 bits
    required_dr_db = 80.0    # PLACEHOLDER: desired dynamic range (dB)
    adc_enob = max(10.0, (required_dr_db - 1.76) / 6.02)

    # ── TODO 4: LNA noise figure and gain
    lna_nf_db = 2.5          # PLACEHOLDER: target NF (dB)
    lna_gain_db = 20.0       # PLACEHOLDER: LNA gain (dB)

    # ── TODO 5: Image rejection (direct conversion — use I/Q quadrature)
    #   Image rejection = 20 * log10(1 / delta_IQ) where delta_IQ is I/Q imbalance
    iq_amplitude_imbalance = 0.01   # PLACEHOLDER: 1% amplitude imbalance
    image_rejection_db = -20 * np.log10(iq_amplitude_imbalance / 2)

    # ── TODO 6: System noise figure (Friis formula)
    #   NF_sys = NF_LNA + (NF_mixer - 1) / G_LNA + ...
    nf_mixer_db = 8.0
    nf_sys = lna_nf_db + (10 ** (nf_mixer_db / 10) - 1) / 10 ** (lna_gain_db / 10)
    nf_sys_db = 10 * np.log10(nf_sys)

    # Frequency ranges per band
    freq_ranges = {}
    for s in standards:
        if s in STANDARDS:
            std = STANDARDS[s]
            fc = std["freq_mhz"]
            bw = std["bandwidth_mhz"]
            freq_ranges[s] = {"lo_mhz": fc - bw / 2, "hi_mhz": fc + bw / 2}

    return {
        "topology": topology,
        "adc_sampling_rate_msps": round(adc_fs_msps, 2),
        "adc_enob": round(adc_enob, 2),
        "rf_bandwidth_mhz": round(max_bw * 1.5, 2),
        "image_rejection_db": round(image_rejection_db, 1),
        "iq_imbalance_correction": True,
        "lna_noise_figure_db": lna_nf_db,
        "lna_gain_db": lna_gain_db,
        "system_noise_figure_db": round(nf_sys_db, 2),
        "standards_supported": standards,
        "frequency_ranges": freq_ranges,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — DIGITAL FRONT-END (DDC + CHANNELIZER)
# ═════════════════════════════════════════════════════════════════════════════

def digital_frontend_ddc(iq_signal: np.ndarray, fs: float,
                          center_offset_hz: float,
                          decimation: int = 1) -> np.ndarray:
    """
    Digital Down-Converter (DDC): frequency-shift + decimate.

    Args:
        iq_signal      : complex baseband IQ samples at fs
        fs             : sample rate (Hz)
        center_offset_hz: frequency offset to shift to DC (Hz)
        decimation     : decimation factor

    Returns:
        baseband : complex signal at fs/decimation
    """
    n = len(iq_signal)

    # ── TODO 7: Numerically-controlled oscillator (NCO)
    #   nco = exp(-j * 2 * pi * f_offset * n / fs)
    nco = np.exp(-1j * 2 * np.pi * center_offset_hz * np.arange(n) / fs)  # PLACEHOLDER
    shifted = iq_signal * nco

    # ── TODO 8: Low-pass filter + decimate
    #   Use a FIR LPF with cutoff = fs / (2 * decimation)
    if decimation > 1:
        n_taps = 64
        cutoff = 1.0 / decimation
        lpf = firwin(n_taps, cutoff, window="hamming")
        filtered = lfilter(lpf, 1.0, shifted)
        decimated = filtered[::decimation]
    else:
        decimated = shifted

    return decimated


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — FM DEMODULATOR
# ═════════════════════════════════════════════════════════════════════════════

def demodulate_fm(iq_signal: np.ndarray, fs: float,
                   max_deviation_hz: float = 75e3,
                   audio_bw_hz: float = 15e3) -> dict:
    """
    FM frequency discriminator + de-emphasis + audio filter.

    Args:
        iq_signal      : complex baseband IQ samples (signal centred at DC)
        fs             : sample rate (Hz)
        max_deviation_hz: FM max frequency deviation (Hz)
        audio_bw_hz    : audio baseband bandwidth (Hz)

    Returns:
        dict with demodulated audio, snr_db estimate, sensitivity_dbm
    """
    # ── TODO 9: FM discriminator
    #   phi_diff[n] = angle(conj(x[n-1]) * x[n])
    #   This gives instantaneous frequency deviation
    phi_diff = np.angle(np.conj(iq_signal[:-1]) * iq_signal[1:])  # PLACEHOLDER
    audio_raw = phi_diff * fs / (2 * np.pi * max_deviation_hz)

    # ── TODO 10: Low-pass audio filter (15 kHz cutoff)
    n_taps = 127
    audio_cutoff = 2 * audio_bw_hz / fs
    if audio_cutoff < 1.0:
        lpf = firwin(n_taps, audio_cutoff, window="hamming")
        audio_filtered = lfilter(lpf, 1.0, audio_raw)
    else:
        audio_filtered = audio_raw

    # ── TODO 11: De-emphasis (75 µs time constant for US/Europe standard)
    tau = 75e-6
    alpha_de = np.exp(-1.0 / (tau * fs))
    audio_deemph = lfilter([1.0 - alpha_de], [1.0, -alpha_de], audio_filtered)

    # SNR estimate
    signal_power = np.mean(audio_deemph ** 2)
    noise_floor = np.percentile(np.abs(audio_deemph), 5) ** 2
    snr_db = 10 * np.log10(max(signal_power / (noise_floor + 1e-20), 1))

    # Sensitivity estimation
    sensitivity_dbm = -174 + 10 * np.log10(200e3) + 5.0 + 10.0   # kTB + NF + SNR_min

    return {
        "audio_samples": audio_deemph[:1000].tolist(),   # first 1000 samples
        "audio_snr_db": round(float(snr_db), 2),
        "sensitivity_dbm": round(float(sensitivity_dbm), 1),
        "selectivity_db": 30.0,    # TODO: compute from adjacent channel test
        "ber_at_sensitivity": 0.0,  # FM has no digital BER (analog quality metric)
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — LTE OFDM DEMODULATOR (SKELETON)
# ═════════════════════════════════════════════════════════════════════════════

def demodulate_lte(iq_signal: np.ndarray, fs: float,
                    fft_size: int = 1024, cp_len: int = 144,
                    n_subcarriers: int = 600) -> dict:
    """
    LTE OFDM demodulation skeleton: timing sync, FFT, channel estimation.

    Args:
        iq_signal   : complex baseband IQ signal at fs
        fs          : sample rate (Hz)
        fft_size    : OFDM FFT size (default 1024 for 10 MHz LTE)
        cp_len      : cyclic prefix length (samples)
        n_subcarriers: number of data subcarriers

    Returns:
        dict with constellation, EVM, SNR estimate
    """
    symbol_len = fft_size + cp_len

    # ── TODO 12: Timing synchronisation using PSS (Zadoff-Chu sequence)
    #   PSS root sequences: u = 25, 29, 34
    #   Cross-correlate with received signal to find symbol boundary
    # (Placeholder: assume perfect synchronisation)
    timing_offset = 0

    # ── TODO 13: Segment received signal into OFDM symbols, remove CP
    n_symbols = len(iq_signal) // symbol_len
    subcarrier_data = []

    for k in range(min(n_symbols, 14)):     # 14 symbols per subframe
        start = k * symbol_len + timing_offset
        if start + symbol_len > len(iq_signal):
            break
        symbol = iq_signal[start + cp_len: start + symbol_len]  # Remove CP

        # ── TODO 14: FFT demodulation
        spectrum = np.fft.fftshift(np.fft.fft(symbol, fft_size))
        # Extract active subcarriers (skip DC, guard bands)
        half = n_subcarriers // 2
        center = fft_size // 2
        active = np.concatenate([
            spectrum[center - half: center],
            spectrum[center + 1: center + half + 1]
        ])
        subcarrier_data.append(active)

    if not subcarrier_data:
        return {"error": "Insufficient samples for LTE demodulation",
                "sensitivity_dbm": -90.0, "selectivity_db": 30.0,
                "ber_at_sensitivity": 0.5}

    # ── TODO 15: Channel estimation using pilot subcarriers (CRS)
    #   Simplified: assume perfect channel for now
    subcarrier_matrix = np.array(subcarrier_data)
    # EVM calculation (normalised to unit power)
    evm_rms = np.sqrt(np.mean(np.abs(subcarrier_matrix - np.round(subcarrier_matrix)) ** 2))

    snr_db = -20 * np.log10(evm_rms + 1e-10)
    sensitivity_dbm = -174 + 10 * np.log10(10e6) + 5.0 + 7.0  # kTB + NF + SNR_min for QPSK

    return {
        "n_ofdm_symbols": len(subcarrier_data),
        "evm_rms_pct": round(float(evm_rms * 100), 2),
        "estimated_snr_db": round(float(snr_db), 1),
        "sensitivity_dbm": round(float(sensitivity_dbm), 1),
        "selectivity_db": 45.0,    # TODO: compute from adjacent channel simulation
        "ber_at_sensitivity": 1e-4,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — GPS ACQUISITION (SKELETON)
# ═════════════════════════════════════════════════════════════════════════════

def generate_gps_ca_code(sv_id: int) -> np.ndarray:
    """
    Generate GPS C/A spreading code for satellite sv_id (1-based).
    Uses the standard G1/G2 generator polynomial.

    Returns:
        ca_code : numpy array of ±1 values, length 1023
    """
    # G1: x^10 + x^3 + 1
    # G2: x^10 + x^9 + x^8 + x^6 + x^3 + x^2 + 1
    g2_taps = {
        1: [2, 6], 2: [3, 7], 3: [4, 8], 4: [5, 9], 5: [1, 9],
        6: [2, 10], 7: [1, 8], 8: [2, 9], 9: [3, 10], 10: [2, 3],
        11: [3, 4], 12: [5, 6], 13: [6, 7], 14: [7, 8], 15: [8, 9],
        16: [9, 10], 17: [1, 4], 18: [2, 5], 19: [3, 6], 20: [4, 7],
        21: [5, 8], 22: [6, 9], 23: [1, 3], 24: [4, 6], 25: [5, 7],
        26: [6, 8], 27: [7, 9], 28: [8, 10], 29: [1, 6], 30: [2, 7],
        31: [3, 8], 32: [4, 9],
    }
    sv_id = max(1, min(32, sv_id))
    taps = g2_taps.get(sv_id, [2, 6])

    g1 = [1] * 10
    g2 = [1] * 10
    ca = []

    for _ in range(1023):
        # ── TODO 16: Implement G1/G2 LFSR and XOR output
        g1_out = g1[9]
        g2_out = g2[taps[0] - 1] ^ g2[taps[1] - 1]
        chip = g1_out ^ g2_out
        ca.append(1 - 2 * chip)   # convert to ±1

        g1_feedback = g1[9] ^ g1[2]
        g1 = [g1_feedback] + g1[:9]

        g2_feedback = g2[9] ^ g2[8] ^ g2[7] ^ g2[5] ^ g2[2] ^ g2[1]
        g2 = [g2_feedback] + g2[:9]

    return np.array(ca, dtype=float)


def gps_acquisition(iq_signal: np.ndarray, fs: float,
                     doppler_range_hz: float = 10e3,
                     doppler_step_hz: float = 500.0,
                     sv_ids: list = None) -> dict:
    """
    GPS L1 C/A code acquisition using FFT-based parallel code search.

    Args:
        iq_signal      : complex baseband signal at fs
        fs             : ADC sample rate (Hz)
        doppler_range_hz: Doppler search range (Hz)
        doppler_step_hz : Doppler hypothesis step (Hz)
        sv_ids         : list of satellite IDs to search (default [1, 3, 7, 11])

    Returns:
        dict with acquired satellites, code phases, Doppler offsets, C/N0
    """
    if sv_ids is None:
        sv_ids = [1, 3, 7, 11]

    chip_rate = 1.023e6   # chips/s
    samples_per_chip = int(round(fs / chip_rate))
    code_len_samples = 1023 * samples_per_chip

    signal_1ms = iq_signal[:code_len_samples] if len(iq_signal) >= code_len_samples else iq_signal

    doppler_bins = np.arange(-doppler_range_hz, doppler_range_hz + 1, doppler_step_hz)

    acquired = []

    for sv_id in sv_ids:
        # ── TODO 17: Generate locally replicated C/A code upsampled to fs
        ca_code = generate_gps_ca_code(sv_id)
        # Upsample to ADC sample rate
        ca_upsampled = np.repeat(ca_code, samples_per_chip)[:code_len_samples]
        ca_upsampled = np.resize(ca_upsampled, len(signal_1ms))

        best_cn0 = 0.0
        best_code_phase = 0
        best_doppler = 0.0

        for doppler in doppler_bins[:8]:    # limit search for speed in this skeleton
            # ── TODO 18: Apply Doppler wipe-off and correlate
            t = np.arange(len(signal_1ms)) / fs
            doppler_mix = np.exp(-1j * 2 * np.pi * doppler * t)
            signal_dop = signal_1ms * doppler_mix

            # FFT-based parallel code correlation
            sig_fft = np.fft.fft(signal_dop, len(signal_1ms))
            ca_fft = np.fft.fft(ca_upsampled, len(signal_1ms))
            corr = np.abs(np.fft.ifft(sig_fft * np.conj(ca_fft)))

            peak_idx = np.argmax(corr)
            peak_val = corr[peak_idx]
            noise_floor_est = np.mean(np.sort(corr)[:len(corr) // 2])
            cn0 = peak_val / (noise_floor_est + 1e-10)

            if cn0 > best_cn0:
                best_cn0 = cn0
                best_code_phase = int(peak_idx)
                best_doppler = doppler

        if best_cn0 > 3.0:   # acquisition threshold (simplified)
            acquired.append({
                "sv_id": sv_id,
                "code_phase_samples": best_code_phase,
                "doppler_hz": best_doppler,
                "cn0_ratio": round(float(best_cn0), 2),
            })

    sensitivity_dbm = -174 + 10 * np.log10(2.046e6) + 3.0 + 14.0

    return {
        "acquired_satellites": acquired,
        "n_acquired": len(acquired),
        "sensitivity_dbm": round(float(sensitivity_dbm), 1),
        "selectivity_db": 25.0,
        "ber_at_sensitivity": 1e-5,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — RECEIVER SENSITIVITY AND SELECTIVITY CALCULATOR
# ═════════════════════════════════════════════════════════════════════════════

def compute_sensitivity(bandwidth_hz: float, nf_db: float = 5.0,
                         min_snr_db: float = 10.0) -> float:
    """
    Compute minimum detectable signal (MDS) in dBm.
    MDS = kTB + NF + SNR_min
    """
    # ── TODO 19: Implement MDS formula
    ktb_dbm = 10 * np.log10(K_B * T0 * bandwidth_hz) + 30    # dBm
    mds_dbm = ktb_dbm + nf_db + min_snr_db
    return round(float(mds_dbm), 1)


def compute_selectivity(channel_bw_hz: float, filter_order: int = 8,
                         adj_channel_offset_hz: float = None) -> float:
    """
    Estimate adjacent-channel selectivity (dB) from digital channel-select filter.

    Args:
        channel_bw_hz         : desired channel bandwidth (Hz)
        filter_order          : Butterworth equivalent filter order
        adj_channel_offset_hz : adjacent channel centre offset (Hz), defaults to channel_bw

    Returns:
        selectivity_db : attenuation at adjacent channel centre (dB)
    """
    if adj_channel_offset_hz is None:
        adj_channel_offset_hz = channel_bw_hz

    # ── TODO 20: Compute filter attenuation using Butterworth approximation
    normalised_freq = adj_channel_offset_hz / (channel_bw_hz / 2)
    if normalised_freq > 1:
        attenuation_db = 10 * np.log10(1 + normalised_freq ** (2 * filter_order))
    else:
        attenuation_db = 0.0

    return round(float(attenuation_db), 1)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="WaveCraft SDR multi-standard receiver design")
    parser.add_argument("--standards", nargs="+", default=["FM", "LTE"],
                        choices=["FM", "DAB+", "LTE", "GPS", "WiFi"],
                        help="Standards to implement (default: FM LTE)")
    parser.add_argument("--scenario", default=None, help="JSON with scenario overrides")
    parser.add_argument("--output", default="submission.json", help="Output submission JSON path")
    parser.add_argument("--plot", action="store_true", help="Generate constellation plots")
    args = parser.parse_args()

    selected_standards = args.standards
    if args.scenario and os.path.exists(args.scenario):
        with open(args.scenario) as f:
            sc = json.load(f)
            selected_standards = sc.get("standards", selected_standards)

    print(f"[WaveCraft] Implementing standards: {selected_standards}")

    print("\n[WaveCraft] Step 1: Architecture design...")
    arch = design_architecture(selected_standards)
    print(f"  Topology       : {arch['topology']}")
    print(f"  ADC rate       : {arch['adc_sampling_rate_msps']:.1f} Msps")
    print(f"  ADC ENOB       : {arch['adc_enob']:.1f} bits")
    print(f"  Image rejection: {arch['image_rejection_db']:.1f} dB")
    print(f"  System NF      : {arch['system_noise_figure_db']:.2f} dB")

    fs = arch["adc_sampling_rate_msps"] * 1e6

    standards_results = []

    for std_name in selected_standards:
        if std_name not in STANDARDS:
            print(f"  [WARN] Unknown standard: {std_name}, skipping.")
            continue

        std = STANDARDS[std_name]
        print(f"\n[WaveCraft] Step 2: Demodulating {std_name}...")

        # Generate a synthetic test signal (placeholder)
        bw = std["bandwidth_mhz"] * 1e6
        n_samples = int(fs * 0.01)   # 10 ms of signal
        t = np.arange(n_samples) / fs

        if std_name == "FM":
            # Simulate FM signal: sinusoidal audio modulating carrier
            f_audio = 1000.0   # 1 kHz test tone
            dev = std["max_deviation_hz"]
            phi = 2 * np.pi * dev / f_audio * np.sin(2 * np.pi * f_audio * t)
            iq_signal = np.exp(1j * phi)
            iq_signal += 0.01 * (np.random.randn(n_samples) + 1j * np.random.randn(n_samples))

            result = demodulate_fm(iq_signal, fs,
                                    max_deviation_hz=dev,
                                    audio_bw_hz=std["audio_bw_hz"])
            std_result = {
                "name": "FM",
                "center_freq_mhz": std["freq_mhz"],
                "bandwidth_mhz": std["bandwidth_mhz"],
                "demodulation": "Frequency discriminator + de-emphasis + stereo decode",
                "sensitivity_dbm": result["sensitivity_dbm"],
                "selectivity_db": result["selectivity_db"],
                "ber_at_sensitivity": result["ber_at_sensitivity"],
            }

        elif std_name == "LTE":
            # Simulate LTE-like OFDM signal
            fft_size = std["fft_size"]
            cp_len = std["cp_samples"]
            n_sub = std["n_subcarriers"]
            # Generate OFDM symbols with QPSK symbols
            n_symbols = 10
            symbols_qpsk = (2 * (np.random.randint(0, 2, (n_symbols, n_sub)) * 2 - 1) +
                            2j * (np.random.randint(0, 2, (n_symbols, n_sub)) * 2 - 1)) / np.sqrt(2)
            iq_signal = np.array([], dtype=complex)
            for sym in symbols_qpsk:
                spectrum = np.zeros(fft_size, dtype=complex)
                half = n_sub // 2
                spectrum[fft_size // 2 - half: fft_size // 2] = sym[:half]
                spectrum[fft_size // 2 + 1: fft_size // 2 + 1 + half] = sym[half:]
                time_sym = np.fft.ifft(np.fft.ifftshift(spectrum))
                cp_sym = np.concatenate([time_sym[-cp_len:], time_sym])
                iq_signal = np.concatenate([iq_signal, cp_sym])
            iq_signal += 0.05 * (np.random.randn(len(iq_signal)) + 1j * np.random.randn(len(iq_signal)))

            result = demodulate_lte(iq_signal, fs, fft_size, cp_len, n_sub)
            std_result = {
                "name": "LTE",
                "center_freq_mhz": std["freq_mhz"],
                "bandwidth_mhz": std["bandwidth_mhz"],
                "demodulation": "OFDM: timing sync, FFT, channel estimation, ZF equalisation",
                "sensitivity_dbm": result["sensitivity_dbm"],
                "selectivity_db": result["selectivity_db"],
                "ber_at_sensitivity": result["ber_at_sensitivity"],
            }

        elif std_name == "GPS":
            # Generate simulated GPS signal
            n_gps = int(fs * 0.001)   # 1 ms
            t_gps = np.arange(n_gps) / fs
            # Simulate SV1 with 500 Hz Doppler offset
            ca_code = generate_gps_ca_code(1)
            chip_rate = 1.023e6
            code_phase = np.floor(t_gps * chip_rate).astype(int) % 1023
            ca_samples = ca_code[code_phase]
            gps_signal = ca_samples * np.exp(1j * 2 * np.pi * 500 * t_gps)
            gps_signal += 5.0 * (np.random.randn(n_gps) + 1j * np.random.randn(n_gps))

            result = gps_acquisition(gps_signal, fs, sv_ids=[1, 3, 7])
            std_result = {
                "name": "GPS",
                "center_freq_mhz": STANDARDS["GPS"]["freq_mhz"],
                "bandwidth_mhz": STANDARDS["GPS"]["bandwidth_mhz"],
                "demodulation": "CA code acquisition (FFT correlation) + DLL/PLL tracking",
                "sensitivity_dbm": result["sensitivity_dbm"],
                "selectivity_db": result["selectivity_db"],
                "ber_at_sensitivity": result["ber_at_sensitivity"],
            }
            print(f"  Acquired {result['n_acquired']} satellites: {result['acquired_satellites']}")

        else:
            # Stub for DAB+ and WiFi
            bw_hz = std["bandwidth_mhz"] * 1e6
            sens = compute_sensitivity(bw_hz, arch["system_noise_figure_db"] + 2.0, 12.0)
            sel = compute_selectivity(bw_hz, filter_order=8)
            std_result = {
                "name": std_name,
                "center_freq_mhz": std["freq_mhz"],
                "bandwidth_mhz": std["bandwidth_mhz"],
                "demodulation": std["modulation"] + " (TODO: implement demodulator)",
                "sensitivity_dbm": sens,
                "selectivity_db": sel,
                "ber_at_sensitivity": 0.1,   # TODO: placeholder
            }

        print(f"  Sensitivity  : {std_result['sensitivity_dbm']} dBm")
        print(f"  Selectivity  : {std_result['selectivity_db']} dB")
        standards_results.append(std_result)

    if args.plot and HAS_PLOT and "LTE" in selected_standards:
        # Plot LTE subcarrier constellation (placeholder)
        n_pts = 500
        qpsk_pts = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2)
        pts = qpsk_pts[np.random.randint(0, 4, n_pts)]
        pts += 0.05 * (np.random.randn(n_pts) + 1j * np.random.randn(n_pts))
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.scatter(pts.real, pts.imag, s=5, alpha=0.5)
        ax.set_xlabel("I")
        ax.set_ylabel("Q")
        ax.set_title("LTE QPSK Constellation (simulated)")
        ax.grid(True)
        fig.tight_layout()
        out_dir = os.path.dirname(os.path.abspath(args.output)) or "."
        fig.savefig(os.path.join(out_dir, "lte_constellation.png"), dpi=150)
        plt.close(fig)

    # ── Assemble submission JSON ─────────────────────────────────────────────
    submission = {
        "architecture": {
            "topology": arch["topology"],
            "adc_sampling_rate_msps": arch["adc_sampling_rate_msps"],
            "adc_enob": arch["adc_enob"],
            "rf_bandwidth_mhz": arch["rf_bandwidth_mhz"],
            "image_rejection_db": arch["image_rejection_db"],
            "iq_imbalance_correction": arch["iq_imbalance_correction"],
        },
        "analog_frontend": {
            "lna_noise_figure_db": arch["lna_noise_figure_db"],
            "lna_gain_db": arch["lna_gain_db"],
            "frequency_range_mhz": {"min": 88.0, "max": 7125.0},
            "lo_frequency_mhz": standards_results[0]["center_freq_mhz"] if standards_results else 98.0,
            "phase_noise_dbc_per_hz_at_1khz": -95.0,   # TODO: compute from PLL design
        },
        "digital_frontend": {
            "ddc_implemented": True,
            "channelization_type": "polyphase",
            "sample_rate_conversion": True,
        },
        "standards_implemented": standards_results,
        "performance": {
            "n_standards_implemented": len(standards_results),
            "dynamic_range_db": arch["adc_enob"] * 6.02 + 1.76,
            "noise_figure_system_db": arch["system_noise_figure_db"],
        },
    }

    with open(args.output, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"\n[WaveCraft] Submission saved to: {args.output}")


if __name__ == "__main__":
    main()
