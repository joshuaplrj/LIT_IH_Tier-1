# FaultSense — Quick Start

## Objective
Build a fault classification and localization system for a 4-bus monitoring subset of the IEEE 39-bus power system. Given 2 cycles of 3-phase voltage and current waveforms (20 kHz sampling), classify the fault type and identify the affected bus.

## Inputs

- `prerequisites/EEE/EEE-P2/fault_dataset/` — 500 CSV files named `fault_000.csv` through `fault_499.csv`:
  - Each file: 667 rows (2 cycles at 20 kHz, 60 Hz), 25 columns
  - Columns: `sample_idx`, then `Va_1, Vb_1, Vc_1, Ia_1, Ib_1, Ic_1` (Bus 1), repeated for Bus 5, Bus 10, Bus 30
  - **Fault inception always at sample index 167** (1 pre-fault cycle available as baseline)
- `prerequisites/EEE/EEE-P2/system_topology.json` — bus data, line impedances, signal metadata

**Fault type distribution:**

| Type   | Count | Description                          |
|--------|-------|--------------------------------------|
| normal | 100   | No fault — balanced steady state     |
| SLG    | 100   | Single line-to-ground (phase A)      |
| LL     | 80    | Line-to-line (phases A and B)        |
| DLG    | 80    | Double line-to-ground (A and B)      |
| LLL    | 80    | Three-phase symmetrical              |
| HIF    | 60    | High-impedance fault (subtle)        |

## Expected Output

**Filename:** `submission/predictions.csv`

```
fault_id,predicted_fault_type,predicted_affected_bus
0,SLG,1
1,normal,1
...
499,HIF,30
```

- `fault_id`: integer 0–499
- `predicted_fault_type`: one of `normal`, `SLG`, `LL`, `DLG`, `LLL`, `HIF`
- `predicted_affected_bus`: integer, one of `1`, `5`, `10`, `30`

## Recommended First Steps

1. Load a single CSV (`fault_000.csv`), plot the 3-phase voltages and currents for Bus 1 around the inception point (sample 167), and visually confirm you can see the disturbance.
2. Extract RMS and symmetrical component features (positive/negative/zero sequence) from the post-fault half-cycle window (samples 167–250) for all 500 files, then inspect the feature distribution per fault type.
3. Train a Random Forest or SVM classifier on 80% of the files and evaluate on the remaining 20%; use the confusion matrix to see which fault types are hardest to separate.

## Scoring Breakdown

| Metric                          | Weight |
|---------------------------------|--------|
| Fault type classification accuracy | 50%  |
| Affected bus identification accuracy | 30% |
| Inference speed (< 1 ms/sample target) | 20% |

## Common Pitfalls

- Using the full 667-sample window as raw input overwhelms simple classifiers; extract compact features (RMS, THD, sequence components) rather than raw time-series.
- Treating HIF as just another class without oversampling or class weighting will give near-zero HIF recall since it is only 12% of the dataset.
- Computing symmetrical components incorrectly — the Clarke/Park or Fortescue transform requires complex arithmetic; a common mistake is applying it to magnitude instead of phasor values.
