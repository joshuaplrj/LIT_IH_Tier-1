"""
CSE-P1: ChronoReconstruct
Generates 500 signal CSV files, 500 tachometer CSV files,
HIDDEN_ground_truth.csv, and README.md
"""

import numpy as np
import os
import csv

BASE = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\CSE\CSE-P1"
SIGNALS_DIR = os.path.join(BASE, "signals")
TACHO_DIR = os.path.join(BASE, "tachometer")

os.makedirs(SIGNALS_DIR, exist_ok=True)
os.makedirs(TACHO_DIR, exist_ok=True)

np.random.seed(42)

N_FILES = 500
SAMPLE_RATE = 25600   # Hz
N_SAMPLES = 25600     # 1 second

t = np.arange(N_SAMPLES)   # sample indices 0..25599

# True chronological order
true_order = np.arange(N_FILES)

# Random permutation — this is the shuffled order
shuffled = np.random.permutation(N_FILES)

# shuffled[file_index] = true_time_window index
# So file signal_0000.csv contains window shuffled[0]

print("Generating 500 signal + tachometer files...")
for file_idx in range(N_FILES):
    if file_idx % 50 == 0:
        print(f"  Progress: {file_idx}/{N_FILES}")

    i = int(shuffled[file_idx])   # true chronological window index

    # --- Degradation parameters ---
    health = 1.0 - (i / 499.0) * 0.7 + np.random.normal(0, 0.02)
    health = max(0.05, health)
    rms = 0.3 + 0.7 * (i / 499.0) + np.random.normal(0, 0.01)
    rms = max(0.05, rms)
    health_amplitude = rms * np.sqrt(2)

    # Slight RPM / frequency drift over time
    rpm_variation = 1.0 + 0.05 * np.sin(2 * np.pi * i / 499.0)

    # Gaussian noise level increases with degradation
    noise_std = 0.05 + 0.15 * (i / 499.0)
    noise = np.random.normal(0, noise_std, N_SAMPLES)

    # Harmonic vibration signal
    signal = (health_amplitude * np.sin(2 * np.pi * 120 * rpm_variation * t / 25600)
              + 0.4 * health_amplitude * np.sin(2 * np.pi * 240 * rpm_variation * t / 25600)
              + 0.2 * health_amplitude * np.sin(2 * np.pi * 360 * rpm_variation * t / 25600)
              + noise)

    # Add impulse trains for heavily degraded windows (i > 350)
    if i > 350:
        n_spikes = 50
        spike_locs = np.random.choice(N_SAMPLES, size=n_spikes, replace=False)
        spike_amps = 3.0 * (i / 499.0) * (np.random.rand(n_spikes) * 0.5 + 0.75)
        signal[spike_locs] += spike_amps

    # --- Write signal CSV ---
    fname = f"signal_{file_idx:04d}.csv"
    fpath = os.path.join(SIGNALS_DIR, fname)
    with open(fpath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["amplitude"])
        for v in signal:
            writer.writerow([round(float(v), 6)])

    # --- Tachometer signal ---
    base_rpm = 7200 + 200 * np.sin(2 * np.pi * i / 499.0)
    rpm_values = base_rpm + np.random.normal(0, 5, N_SAMPLES)

    fname_t = f"tachometer_{file_idx:04d}.csv"
    fpath_t = os.path.join(TACHO_DIR, fname_t)
    with open(fpath_t, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rpm"])
        for v in rpm_values:
            writer.writerow([round(float(v), 3)])

print("All signal and tachometer files written.")

# --- HIDDEN_ground_truth.csv ---
# file_index: 0-499, true_order: the true chronological index of that file
gt_path = os.path.join(BASE, "HIDDEN_ground_truth.csv")
with open(gt_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["file_index", "true_order"])
    for file_idx in range(N_FILES):
        writer.writerow([file_idx, int(shuffled[file_idx])])
print(f"Written: {gt_path}")

# --- README.md ---
readme = """# CSE-P1: ChronoReconstruct

## Overview
You are given 500 vibration signal snapshots from an industrial turbine, captured
over 12 months. The files have been shuffled — your task is to reconstruct the
true chronological order.

## Data
- `signals/signal_XXXX.csv` — vibration amplitude at 25,600 Hz (25,600 rows, 1 second each)
- `tachometer/tachometer_XXXX.csv` — instantaneous RPM values (25,600 rows)

## Task
Determine the correct chronological ordering of the 500 files.

Submit a CSV with columns `file_index,predicted_order` where `predicted_order`
is your estimate of the file's position in the true chronological sequence (0 = earliest).

## Scoring
Kendall's Tau correlation between your predicted order and the true order.
Score = 1.0 for perfect reconstruction.

## Hints
- The turbine degrades over time; statistical features (RMS, kurtosis, peak factor)
  may encode temporal information.
- RPM drifts slowly over the 12-month period.
- Harmonic amplitudes change with health state.
- Impulsive events appear in later (more degraded) windows.
"""

with open(os.path.join(BASE, "README.md"), "w") as f:
    f.write(readme)
print("README.md written.")
print("CSE-P1 generation complete.")
