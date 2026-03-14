"""
generate_eee_p2.py
Generates 500 fault scenario CSV files, HIDDEN_fault_labels.csv,
system_topology.json, and README.md for EEE-P2 "FaultSense".
"""

import numpy as np
import csv
import json
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = r"C:\Users\John Jacob\Desktop\Tier-1\prerequisites\EEE\EEE-P2"
FAULT_DIR     = os.path.join(BASE_DIR, "fault_dataset")
LABELS_PATH   = os.path.join(BASE_DIR, "HIDDEN_fault_labels.csv")
TOPOLOGY_PATH = os.path.join(BASE_DIR, "system_topology.json")
README_PATH   = os.path.join(BASE_DIR, "README.md")

os.makedirs(FAULT_DIR, exist_ok=True)

# ── Simulation constants ───────────────────────────────────────────────────────
BASE_SEED        = 42
SAMPLES          = 667          # 2 cycles @ 20 kHz / 60 Hz ≈ 333.33 * 2
PRE_FAULT        = 167          # 1 cycle pre-fault
FS               = 20_000.0     # Hz
F0               = 60.0         # Hz
BUSES            = [1, 5, 10, 30]
NUM_BUSES        = len(BUSES)
VNOM             = 1.0          # per-unit
INOM             = 1.0          # per-unit  (peak of 1.0 pu load current)
PHI              = 0.3          # power factor angle (rad)

# ── Fault distribution ─────────────────────────────────────────────────────────
FAULT_TYPES = {
    "normal": 100,
    "SLG":    100,
    "LL":      80,
    "DLG":     80,
    "LLL":     80,
    "HIF":     60,
}
# Build ordered scenario list
scenarios = []
for ft, count in FAULT_TYPES.items():
    scenarios.extend([ft] * count)
assert len(scenarios) == 500

# ── Time vector ───────────────────────────────────────────────────────────────
t = np.arange(SAMPLES) / FS   # seconds

# ── Helper: balanced 3-phase signals ──────────────────────────────────────────
def balanced_voltage(t, scale=1.0):
    Va = scale * VNOM * np.cos(2 * np.pi * F0 * t)
    Vb = scale * VNOM * np.cos(2 * np.pi * F0 * t - 2 * np.pi / 3)
    Vc = scale * VNOM * np.cos(2 * np.pi * F0 * t + 2 * np.pi / 3)
    return Va, Vb, Vc

def balanced_current(t, scale=1.0):
    Ia = scale * INOM * np.cos(2 * np.pi * F0 * t - PHI)
    Ib = scale * INOM * np.cos(2 * np.pi * F0 * t - PHI - 2 * np.pi / 3)
    Ic = scale * INOM * np.cos(2 * np.pi * F0 * t - PHI + 2 * np.pi / 3)
    return Ia, Ib, Ic

# ── Helper: fault impedance scaling ───────────────────────────────────────────
def impedance_scale(R_fault, Zsys=1.0):
    """Simple voltage divider: effect scales down with higher fault resistance."""
    return Zsys / (Zsys + R_fault / 100.0)   # normalised so R=0→scale=1, R→∞→scale→0

# ── Generate one bus signal array (Va,Vb,Vc,Ia,Ib,Ic) for a given fault ──────
def make_bus_signals(rng, fault_type, bus_idx, affected_bus_idx,
                     Iload, R_fault, hif_depth, hif_noise_std):
    """
    Returns shape (SAMPLES, 6): [Va, Vb, Vc, Ia, Ib, Ic]
    Faults are strongest at affected_bus; attenuated at other buses.
    """
    # Attenuation: buses further from fault see weaker effect
    distance = abs(bus_idx - affected_bus_idx)
    attenuation = 1.0 / (1.0 + 0.4 * distance)   # 1.0, 0.71, 0.55, 0.45 …

    # Pre-fault: balanced
    Va = VNOM * np.cos(2 * np.pi * F0 * t)
    Vb = VNOM * np.cos(2 * np.pi * F0 * t - 2 * np.pi / 3)
    Vc = VNOM * np.cos(2 * np.pi * F0 * t + 2 * np.pi / 3)
    Ia = Iload * np.cos(2 * np.pi * F0 * t - PHI)
    Ib = Iload * np.cos(2 * np.pi * F0 * t - PHI - 2 * np.pi / 3)
    Ic = Iload * np.cos(2 * np.pi * F0 * t - PHI + 2 * np.pi / 3)

    post = slice(PRE_FAULT, SAMPLES)
    t_post = t[post]
    eff = attenuation * impedance_scale(R_fault)

    if fault_type == "normal":
        pass  # no changes

    elif fault_type == "SLG":
        # Phase A collapses, B/C rise slightly
        Va[post] = (1 - eff * (1 - 0.1)) * VNOM * np.cos(2 * np.pi * F0 * t_post)
        Vb[post] = (1 + eff * 0.15) * VNOM * np.cos(2 * np.pi * F0 * t_post - 2 * np.pi / 3)
        Vc[post] = (1 + eff * 0.15) * VNOM * np.cos(2 * np.pi * F0 * t_post + 2 * np.pi / 3)
        Ia[post] = (1 + eff * 4.0) * Iload * np.cos(2 * np.pi * F0 * t_post - PHI)
        Ib[post] = Iload * np.cos(2 * np.pi * F0 * t_post - PHI - 2 * np.pi / 3)
        Ic[post] = Iload * np.cos(2 * np.pi * F0 * t_post - PHI + 2 * np.pi / 3)

    elif fault_type == "LL":
        # Phases A & B merge toward zero; C unchanged; Ia = -Ib = 3*Iload
        Va[post] = (1 - eff * 1.0) * VNOM * np.cos(2 * np.pi * F0 * t_post)
        Vb[post] = (1 - eff * 1.0) * VNOM * np.cos(2 * np.pi * F0 * t_post - 2 * np.pi / 3)
        Vc[post] = VNOM * np.cos(2 * np.pi * F0 * t_post + 2 * np.pi / 3)
        fault_I = eff * 3.0 * Iload * np.cos(2 * np.pi * F0 * t_post - PHI)
        Ia[post] =  fault_I
        Ib[post] = -fault_I
        Ic[post] = Iload * np.cos(2 * np.pi * F0 * t_post - PHI + 2 * np.pi / 3)

    elif fault_type == "DLG":
        # Phases A & B to ground; C rises
        Va[post] = (1 - eff * 0.9) * VNOM * np.cos(2 * np.pi * F0 * t_post)
        Vb[post] = (1 - eff * 0.9) * VNOM * np.cos(2 * np.pi * F0 * t_post - 2 * np.pi / 3)
        Vc[post] = (1 + eff * 0.2) * VNOM * np.cos(2 * np.pi * F0 * t_post + 2 * np.pi / 3)
        Ia[post] = (1 + eff * 3.0) * Iload * np.cos(2 * np.pi * F0 * t_post - PHI)
        Ib[post] = (1 + eff * 3.0) * Iload * np.cos(2 * np.pi * F0 * t_post - PHI - 2 * np.pi / 3)
        Ic[post] = Iload * np.cos(2 * np.pi * F0 * t_post - PHI + 2 * np.pi / 3)

    elif fault_type == "LLL":
        # All phases collapse symmetrically
        scale_v = 1 - eff * 0.9
        scale_i = 1 + eff * 4.0
        Va[post] = scale_v * VNOM * np.cos(2 * np.pi * F0 * t_post)
        Vb[post] = scale_v * VNOM * np.cos(2 * np.pi * F0 * t_post - 2 * np.pi / 3)
        Vc[post] = scale_v * VNOM * np.cos(2 * np.pi * F0 * t_post + 2 * np.pi / 3)
        Ia[post] = scale_i * Iload * np.cos(2 * np.pi * F0 * t_post - PHI)
        Ib[post] = scale_i * Iload * np.cos(2 * np.pi * F0 * t_post - PHI - 2 * np.pi / 3)
        Ic[post] = scale_i * Iload * np.cos(2 * np.pi * F0 * t_post - PHI + 2 * np.pi / 3)

    elif fault_type == "HIF":
        # Subtle: phase A slightly reduced, extra high-frequency noise
        Va[post] = (1 - hif_depth) * VNOM * np.cos(2 * np.pi * F0 * t_post)
        Ia[post] = (1 + hif_depth * 0.5) * Iload * np.cos(2 * np.pi * F0 * t_post - PHI)
        # High-frequency noise injected on all signals
        Va += rng.normal(0, hif_noise_std, SAMPLES)
        Vb += rng.normal(0, hif_noise_std, SAMPLES)
        Vc += rng.normal(0, hif_noise_std, SAMPLES)
        Ia += rng.normal(0, hif_noise_std * 2, SAMPLES)
        Ib += rng.normal(0, hif_noise_std * 2, SAMPLES)
        Ic += rng.normal(0, hif_noise_std * 2, SAMPLES)

    # Add standard measurement noise
    Va += rng.normal(0, 0.005, SAMPLES)
    Vb += rng.normal(0, 0.005, SAMPLES)
    Vc += rng.normal(0, 0.005, SAMPLES)
    Ia += rng.normal(0, 0.010, SAMPLES)
    Ib += rng.normal(0, 0.010, SAMPLES)
    Ic += rng.normal(0, 0.010, SAMPLES)

    return np.column_stack([Va, Vb, Vc, Ia, Ib, Ic])

# ── Column header ──────────────────────────────────────────────────────────────
COLUMNS = ["sample_idx"]
for bus in BUSES:
    for sig in ["Va", "Vb", "Vc", "Ia", "Ib", "Ic"]:
        COLUMNS.append(f"{sig}_{bus}")

# ── Labels accumulator ────────────────────────────────────────────────────────
label_rows = []

# ── Main generation loop ───────────────────────────────────────────────────────
print("Generating 500 fault scenario CSV files ...")
for idx, fault_type in enumerate(scenarios):
    rng = np.random.default_rng(BASE_SEED + idx)

    # Affected bus (random)
    affected_bus_idx = int(rng.integers(0, NUM_BUSES))
    affected_bus_id  = BUSES[affected_bus_idx]

    # Fault resistance
    if fault_type == "HIF":
        R_fault = float(rng.uniform(500, 2000))
    elif fault_type == "normal":
        R_fault = 0.0
    else:
        R_fault = float(rng.uniform(0.1, 50))

    # Load current scale: 0.3–0.8 pu
    Iload = float(rng.uniform(0.3, 0.8))

    # HIF parameters
    hif_depth      = float(rng.uniform(0.08, 0.15))
    hif_noise_std  = float(rng.uniform(0.02, 0.05))

    # Fault location along line (%) — metadata only
    fault_loc_pct = float(rng.uniform(0, 100))

    # Build data array: shape (SAMPLES, NUM_BUSES*6)
    bus_data_list = []
    for bus_idx in range(NUM_BUSES):
        signals = make_bus_signals(
            rng, fault_type, bus_idx, affected_bus_idx,
            Iload, R_fault, hif_depth, hif_noise_std
        )
        bus_data_list.append(signals)

    # Interleave: sample_idx | bus1_6cols | bus2_6cols | ...
    sample_idx_col = np.arange(SAMPLES).reshape(-1, 1)
    all_data = np.hstack([sample_idx_col] + bus_data_list)   # (667, 25)

    # Write CSV
    fname = os.path.join(FAULT_DIR, f"fault_{idx:03d}.csv")
    with open(fname, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        for row in all_data:
            writer.writerow([int(row[0])] + [round(float(v), 6) for v in row[1:]])

    label_rows.append({
        "fault_id":             idx,
        "fault_type":           fault_type,
        "affected_bus":         affected_bus_id,
        "fault_resistance_ohm": round(R_fault, 4),
        "inception_sample":     PRE_FAULT,
        "fault_location_pct":   round(fault_loc_pct, 2),
    })

    if (idx + 1) % 50 == 0:
        print(f"  {idx + 1}/500 files written ...")

print("  All 500 files written.")

# ── Write HIDDEN_fault_labels.csv ─────────────────────────────────────────────
print(f"Writing {LABELS_PATH} ...")
with open(LABELS_PATH, "w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=[
        "fault_id", "fault_type", "affected_bus",
        "fault_resistance_ohm", "inception_sample", "fault_location_pct"
    ])
    writer.writeheader()
    writer.writerows(label_rows)
print("  Done.")

# ── Write system_topology.json ────────────────────────────────────────────────
topology = {
    "description": "Simplified 4-bus monitoring subset of IEEE 39-bus New England system",
    "buses": [
        {"id": 1,  "type": "PQ",  "nominal_kv": 345, "zone": 1, "description": "Load bus — southwestern region"},
        {"id": 5,  "type": "PQ",  "nominal_kv": 345, "zone": 1, "description": "Load bus — central connection"},
        {"id": 10, "type": "PV",  "nominal_kv": 345, "zone": 2, "description": "Generator bus — northeastern region"},
        {"id": 30, "type": "Slack","nominal_kv": 345, "zone": 3, "description": "Reference/slack bus — main interconnect"}
    ],
    "lines": [
        {"from": 1,  "to": 5,  "resistance_pu": 0.001,  "reactance_pu": 0.011,  "susceptance_pu": 0.218, "rating_mva": 600},
        {"from": 1,  "to": 10, "resistance_pu": 0.002,  "reactance_pu": 0.020,  "susceptance_pu": 0.390, "rating_mva": 500},
        {"from": 5,  "to": 10, "resistance_pu": 0.0008, "reactance_pu": 0.0085, "susceptance_pu": 0.176, "rating_mva": 600},
        {"from": 5,  "to": 30, "resistance_pu": 0.001,  "reactance_pu": 0.013,  "susceptance_pu": 0.260, "rating_mva": 550},
        {"from": 10, "to": 30, "resistance_pu": 0.0015, "reactance_pu": 0.018,  "susceptance_pu": 0.360, "rating_mva": 600}
    ],
    "frequency_hz": 60,
    "sampling_rate_hz": 20000,
    "samples_per_file": 667,
    "pre_fault_samples": 167,
    "post_fault_samples": 500,
    "base_mva": 100,
    "base_kv": 345,
    "measurement_description": (
        "2 cycles of 3-phase voltage (pu) and current (pu) at all 4 monitored buses. "
        "Fault inception always occurs at sample index 167 (end of 1 pre-fault cycle)."
    ),
    "signal_columns_per_bus": ["Va", "Vb", "Vc", "Ia", "Ib", "Ic"],
    "column_order": "sample_idx, then for each bus in [1,5,10,30]: Va_<bus>, Vb_<bus>, Vc_<bus>, Ia_<bus>, Ib_<bus>, Ic_<bus>"
}

print(f"Writing {TOPOLOGY_PATH} ...")
with open(TOPOLOGY_PATH, "w") as fh:
    json.dump(topology, fh, indent=2)
print("  Done.")

# ── Write README.md ───────────────────────────────────────────────────────────
readme_text = """# EEE-P2: FaultSense — Power System Fault Classification

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
"""

print(f"Writing {README_PATH} ...")
with open(README_PATH, "w", encoding="utf-8") as fh:
    fh.write(readme_text)
print("  Done.")

print("\nEEE-P2 generation complete.")
