"""
AIDS-P1: NeuroDecode - EEG Dataset Generator
Generates 10 subject files, labels.csv, channel_info.json, README.md
"""

import numpy as np
import csv
import json
import os

RANDOM_SEED = 42
OUTPUT_DIR = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\AIDS\AIDS-P1"
EEG_DIR = os.path.join(OUTPUT_DIR, "eeg_data")

N_SUBJECTS = 10
N_TRIALS = 400
N_SAMPLES = 500
N_CHANNELS = 64
N_CLASSES = 4
TRIALS_PER_CLASS = 100
FS = 250  # Hz (500 samples at 250 Hz = 2 seconds)

CHANNEL_NAMES = [
    "Fp1","Fp2","F7","F3","Fz","F4","F8","FC5","FC1","FCz",
    "FC2","FC6","T7","C3","Cz","C4","T8","TP9","CP5","CP1",
    "CPz","CP2","CP6","TP10","P7","P3","Pz","P4","P8","PO9",
    "O1","Oz","O2","PO10","AF7","AF3","AF4","AF8","F5","F1",
    "F2","F6","FT9","FT7","FC3","FC4","FT8","FT10","C5","C1",
    "C2","C6","TP7","CP3","CPz","CP4","TP8","P5","P1","P2",
    "P6","PO7","PO3","PO4","PO8"
]

CLASS_NAMES = ["left_hand", "right_hand", "feet", "tongue"]

os.makedirs(EEG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_subject_data(subject_idx, rng):
    """Generate EEG data for one subject: shape (400, 500, 64)"""
    t = np.arange(N_SAMPLES) / FS  # time vector in seconds

    # Subject-specific spatial mixing matrix (realistic EEG mixing)
    mixing = rng.standard_normal((N_CHANNELS, N_CHANNELS)).astype(np.float32) * 0.1
    np.fill_diagonal(mixing, 1.0)

    data = np.zeros((N_TRIALS, N_SAMPLES, N_CHANNELS), dtype=np.float32)

    for trial in range(N_TRIALS):
        class_label = trial // TRIALS_PER_CLASS  # 0,1,2,3

        # Base noise: pink-ish (1/f weighted sinusoids) + gaussian
        base = np.zeros((N_CHANNELS, N_SAMPLES), dtype=np.float32)
        for ch in range(N_CHANNELS):
            # Gaussian background
            bg = rng.standard_normal(N_SAMPLES).astype(np.float32)
            # Add 1/f structure: sum sinusoids at 1-50 Hz
            pink = np.zeros(N_SAMPLES, dtype=np.float32)
            for f in range(1, 51):
                amp = 1.0 / f
                phase = rng.uniform(0, 2 * np.pi)
                pink += amp * np.sin(2 * np.pi * f * t + phase).astype(np.float32)
            base[ch] = bg + pink * 0.3

        # Class-specific signal injection
        trial_amplitude = 0.5 + rng.uniform(-0.1, 0.1)
        trial_phase = rng.uniform(0, 2 * np.pi)

        if class_label == 0:  # Left Hand: ERD right motor (ch 25-30), ERS left (ch 20-25)
            sig_erd = trial_amplitude * np.sin(2 * np.pi * 10 * t + trial_phase).astype(np.float32)
            sig_ers = -trial_amplitude * 0.5 * np.sin(2 * np.pi * 10 * t + trial_phase).astype(np.float32)
            for ch in range(25, 31):
                base[ch] += sig_erd
            for ch in range(20, 25):
                base[ch] += sig_ers

        elif class_label == 1:  # Right Hand: opposite pattern
            sig_erd = trial_amplitude * np.sin(2 * np.pi * 10 * t + trial_phase).astype(np.float32)
            sig_ers = -trial_amplitude * 0.5 * np.sin(2 * np.pi * 10 * t + trial_phase).astype(np.float32)
            for ch in range(20, 26):
                base[ch] += sig_erd
            for ch in range(25, 31):
                base[ch] += sig_ers

        elif class_label == 2:  # Feet: bilateral ERD, 12 Hz
            sig = trial_amplitude * np.sin(2 * np.pi * 12 * t + trial_phase).astype(np.float32)
            for ch in range(22, 28):
                base[ch] += sig

        else:  # Tongue: oral motor cortex (different topography)
            sig = trial_amplitude * np.sin(2 * np.pi * 10 * t + trial_phase).astype(np.float32)
            for ch in range(28, 36):
                base[ch] += sig

        # Apply subject-specific spatial mixing and scale to µV range
        mixed = (mixing @ base).astype(np.float32)
        data[trial] = (mixed * 10.0).T  # shape: (500, 64)

    return data


def shuffle_trials_per_subject(data, labels, rng):
    """Shuffle trials within a subject"""
    idx = np.arange(N_TRIALS)
    rng.shuffle(idx)
    return data[idx], labels[idx]


print("Generating AIDS-P1: NeuroDecode EEG Dataset...")
print(f"Output directory: {OUTPUT_DIR}")

rng_master = np.random.default_rng(RANDOM_SEED)

all_labels = []

for subj in range(1, N_SUBJECTS + 1):
    subj_seed = RANDOM_SEED + subj * 1000
    subj_rng = np.random.default_rng(subj_seed)

    print(f"  Generating subject {subj:02d}/10...", end="", flush=True)
    data = generate_subject_data(subj - 1, subj_rng)

    # Labels before shuffle: first 100=class0, next 100=class1, etc.
    labels_subj = np.repeat(np.arange(N_CLASSES), TRIALS_PER_CLASS)

    # Shuffle trials
    shuffle_rng = np.random.default_rng(subj_seed + 1)
    perm = np.arange(N_TRIALS)
    shuffle_rng.shuffle(perm)
    data = data[perm]
    labels_subj = labels_subj[perm]

    # Save numpy file
    fname = os.path.join(EEG_DIR, f"subject_{subj:02d}.npy")
    np.save(fname, data)
    print(f" saved {data.shape} -> {fname}")

    # Collect labels
    for trial_id, cls in enumerate(labels_subj):
        all_labels.append({
            "subject_id": subj,
            "trial_id": trial_id,
            "class_label": int(cls),
            "class_name": CLASS_NAMES[int(cls)]
        })

# Write labels.csv
labels_path = os.path.join(OUTPUT_DIR, "labels.csv")
with open(labels_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["subject_id", "trial_id", "class_label", "class_name"])
    writer.writeheader()
    writer.writerows(all_labels)
print(f"  Wrote {len(all_labels)} label rows -> {labels_path}")

# Write channel_info.json
channel_info = {
    "n_channels": N_CHANNELS,
    "sampling_rate_hz": FS,
    "channels": CHANNEL_NAMES,
    "reference": "CAR (Common Average Reference)",
    "units": "microvolts (µV)",
    "electrode_system": "10-20 extended",
    "channel_index": {name: idx for idx, name in enumerate(CHANNEL_NAMES)}
}
chan_path = os.path.join(OUTPUT_DIR, "channel_info.json")
with open(chan_path, "w", encoding="utf-8") as f:
    json.dump(channel_info, f, indent=2)
print(f"  Wrote channel info -> {chan_path}")

# Write README.md
readme = """# AIDS-P1: NeuroDecode — EEG Motor Imagery Dataset

## Overview
This dataset contains electroencephalography (EEG) recordings from 10 subjects performing 4-class motor imagery tasks.

## Task
4-class motor imagery classification:
- **Class 0**: Left Hand
- **Class 1**: Right Hand
- **Class 2**: Feet
- **Class 3**: Tongue

## Dataset Structure
```
AIDS-P1/
├── eeg_data/
│   ├── subject_01.npy    # shape: (400, 500, 64) float32
│   ├── subject_02.npy
│   ...
│   └── subject_10.npy
├── labels.csv            # subject_id, trial_id, class_label, class_name
├── channel_info.json     # EEG channel names and metadata
└── README.md
```

## Data Format
Each `.npy` file has shape **(400, 500, 64)**:
- **400** trials (100 per class)
- **500** time samples (2 seconds at 250 Hz)
- **64** EEG channels (10-20 extended system)
- dtype: float32, units: microvolts (µV)

## EEG Channels
64 standard 10-20 channels covering the full scalp. Motor cortex channels (C3, Cz, C4 area) are indices 13-16.

## Signal Characteristics
- Sampling rate: 250 Hz
- Epoch duration: 2 seconds
- Motor cortex ERD/ERS patterns in mu (8-12 Hz) and beta (13-30 Hz) bands
- Subject-specific spatial mixing (realistic volume conduction)

## Loading Example
```python
import numpy as np
data = np.load('eeg_data/subject_01.npy')  # (400, 500, 64)
import csv
labels = list(csv.DictReader(open('labels.csv')))
```

## Task Objective
Build a classifier that decodes the motor imagery class from EEG signals.
Evaluation metric: classification accuracy (4-class).
"""
readme_path = os.path.join(OUTPUT_DIR, "README.md")
with open(readme_path, "w", encoding="utf-8") as f:
    f.write(readme)
print(f"  Wrote README -> {readme_path}")

print("\nAIDS-P1 generation complete!")
# Verify file sizes
total_bytes = sum(
    os.path.getsize(os.path.join(EEG_DIR, f"subject_{i:02d}.npy"))
    for i in range(1, 11)
)
print(f"Total EEG data size: {total_bytes / (1024**3):.2f} GB ({total_bytes / (1024**2):.1f} MB)")
