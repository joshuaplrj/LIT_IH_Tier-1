# CSE-P1: ChronoReconstruct

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
