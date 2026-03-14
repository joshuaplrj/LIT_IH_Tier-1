# NeuroDecode — Quick Start

## Objective
Build a deep learning pipeline to classify 4 motor imagery classes (left hand, right hand, feet, tongue) from 64-channel EEG data recorded at 1000 Hz. The model must achieve >80% within-subject accuracy and >60% cross-subject accuracy while delivering inference in under 50 ms on a single CPU core.

## Inputs
- `data/eeg_raw/subject_XX.npz` — Raw EEG arrays, shape `(n_trials, 64, 4000)` (64 channels × 4 s × 1000 Hz), dtype float32
- `data/eeg_raw/subject_XX_labels.npy` — Integer class labels `{0,1,2,3}` per trial, shape `(n_trials,)`
- `data/channel_info.csv` — Channel names and 3-D electrode coordinates for topology graphs
- `data/subject_metadata.csv` — Age, handedness, session date per subject (10 subjects total)

## Expected Output
- `submission/predictions.csv` — Columns: `trial_id, subject_id, predicted_class, confidence`
- `submission/latency_benchmark.json` — Keys: `mean_ms`, `p95_ms`, `p99_ms`
- `submission/explainability/` — One PNG per class showing topographic activation map

## Recommended First Steps
1. Run `python starter.py --data_dir data/eeg_raw --output_dir submission` to verify the pipeline runs end-to-end on random dummy data.
2. Implement band-pass filtering (8–30 Hz) and CSP feature extraction inside `preprocess()` before touching the model.
3. Train EEGNet on a single subject first; confirm >70% accuracy before attempting cross-subject transfer.

## Scoring Breakdown
| Metric                    | Weight |
|---------------------------|--------|
| Classification accuracy   | 40%    |
| Cross-subject generalization | 30% |
| Inference latency (<50 ms)| 20%    |
| Model explainability      | 10%    |

## Common Pitfalls
- Forgetting to apply band-pass filtering before feature extraction causes near-chance accuracy; EEG noise outside 8–30 Hz dominates the raw signal.
- Computing CSP filters on the full dataset (data leakage) instead of fitting only on training folds inflates within-subject numbers and collapses cross-subject performance.
- Using large batch sizes during inference benchmarking hides per-sample latency; always time single-sample forward passes.
