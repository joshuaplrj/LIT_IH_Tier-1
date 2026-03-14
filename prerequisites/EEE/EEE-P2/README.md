# EEE-P2: FaultSense — Power System Fault Classification

## Problem Statement
Build a fault classification and localisation system for a high-voltage transmission network.
Given two cycles of waveform data from four monitoring buses, correctly identify:
1. The **fault type** (Normal / SLG / LL / DLG / LLL / HIF)
2. The **affected bus**
3. Optionally, the **fault resistance** (bonus)

## Dataset

### fault_dataset/ (500 CSV files)
Each file `fault_NNN.csv` contains **667 samples** (2 cycles at 20 kHz, 60 Hz system).

| Column | Description |
|--------|-------------|
| sample_idx | 0–666 |
| Va_1, Vb_1, Vc_1 | 3-phase voltage at Bus 1 (per unit) |
| Ia_1, Ib_1, Ic_1 | 3-phase current at Bus 1 (per unit) |
| Va_5 … Ic_5 | Same for Bus 5 |
| Va_10 … Ic_10 | Same for Bus 10 |
| Va_30 … Ic_30 | Same for Bus 30 |

**Fault inception always occurs at sample index 167** (after 1 pre-fault cycle).

### system_topology.json
Simplified 4-bus monitoring subset of the IEEE 39-bus New England system.
Contains bus data, line impedances, and signal metadata.

### HIDDEN_fault_labels.csv *(not distributed to participants)*
Contains the true labels: fault_id, fault_type, affected_bus, fault_resistance_ohm,
inception_sample, fault_location_pct.

## Fault Type Distribution
| Type | Count | Description |
|------|-------|-------------|
| normal | 100 | No fault — balanced steady-state operation |
| SLG | 100 | Single Line-to-Ground (phase A to ground) |
| LL | 80 | Line-to-Line (phases A & B) |
| DLG | 80 | Double Line-to-Ground (phases A & B to ground) |
| LLL | 80 | Three-Phase (symmetrical fault) |
| HIF | 60 | High-Impedance Fault (subtle — high noise) |

## Evaluation
- **Primary**: Fault type classification accuracy (%)
- **Secondary**: Affected bus identification accuracy (%)
- **Bonus**: Fault resistance estimation MAE (Ω)

Participants must submit a CSV: `fault_id, predicted_fault_type, predicted_affected_bus`

## Getting Started
```python
import pandas as pd, json, os

topology = json.load(open("system_topology.json"))
df0 = pd.read_csv("fault_dataset/fault_000.csv")
print(df0.shape)        # (667, 25)
print(df0.columns[:7])  # sample_idx, Va_1, Vb_1, Vc_1, Ia_1, Ib_1, Ic_1
print(df0["Va_1"].describe())
```

## Tips
- Extract RMS, peak, and THD features per half-cycle window.
- Symmetrical component analysis (zero/positive/negative sequence) is highly informative.
- HIF is the hardest class — look at high-frequency noise signature.
- The pre-fault window (samples 0–166) gives a clean baseline for each scenario.
