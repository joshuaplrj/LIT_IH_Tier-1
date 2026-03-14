"""
AIDS-P1: NeuroDecode — Brain-Computer Interface Signal Decoding
Starter skeleton. Run as-is to verify the pipeline executes end-to-end
on randomly generated dummy EEG data.

Usage:
    python starter.py --data_dir data/eeg_raw --output_dir submission
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

# Deep-learning / signal-processing imports --------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WARN] PyTorch not found — model will use random predictions.")

try:
    from scipy.signal import butter, sosfiltfilt
    from scipy.linalg import sqrtm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[WARN] SciPy not found — preprocessing stubs will be skipped.")

try:
    from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold
    from sklearn.metrics import accuracy_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_CHANNELS = 64
SAMPLE_RATE = 1000          # Hz
TRIAL_DURATION_S = 4        # seconds
N_SAMPLES = SAMPLE_RATE * TRIAL_DURATION_S   # 4000
N_CLASSES = 4               # left-hand, right-hand, feet, tongue
CLASS_NAMES = ["left_hand", "right_hand", "feet", "tongue"]
BAND_LOW_HZ = 8
BAND_HIGH_HZ = 30
DROPOUT_RATE = 0.5
BATCH_SIZE = 32
LEARNING_RATE = 1e-3
N_EPOCHS = 30


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_subject_data(data_dir: str, subject_id: int):
    """
    Load raw EEG data for one subject.
    Expected files:
        <data_dir>/subject_<XX>.npz  -> arrays 'eeg' (n_trials, 64, 4000) and 'labels'
    Falls back to random dummy data if the file is missing.
    """
    path = Path(data_dir) / f"subject_{subject_id:02d}.npz"
    if path.exists():
        data = np.load(str(path))
        eeg = data["eeg"].astype(np.float32)        # (N, 64, 4000)
        labels = data["labels"].astype(np.int64)     # (N,)
    else:
        # Dummy data: 800 trials (200 per class), random Gaussian EEG
        print(f"[INFO] {path} not found — using dummy random data.")
        n_trials = 800
        eeg = np.random.randn(n_trials, N_CHANNELS, N_SAMPLES).astype(np.float32) * 10.0
        labels = np.repeat(np.arange(N_CLASSES), n_trials // N_CLASSES).astype(np.int64)
    return eeg, labels


def load_all_subjects(data_dir: str, n_subjects: int = 10):
    """Return list of (eeg, labels) tuples, one per subject."""
    all_data = []
    for sid in range(1, n_subjects + 1):
        eeg, labels = load_subject_data(data_dir, sid)
        all_data.append((eeg, labels))
    return all_data


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def bandpass_filter(eeg: np.ndarray, low: float, high: float, fs: int) -> np.ndarray:
    """
    Apply 4th-order Butterworth band-pass filter to EEG.
    eeg: (n_trials, n_channels, n_samples)
    Returns filtered array of same shape.
    """
    if not SCIPY_AVAILABLE:
        return eeg
    sos = butter(4, [low, high], btype="band", fs=fs, output="sos")
    # TODO: filter each trial/channel
    filtered = sosfiltfilt(sos, eeg, axis=-1)
    return filtered.astype(np.float32)


def reject_artifacts(eeg: np.ndarray, threshold_uv: float = 100.0):
    """
    Return boolean mask — True means the trial is CLEAN.
    Reject trials whose peak-to-peak amplitude exceeds threshold_uv (µV).
    """
    ptp = eeg.max(axis=-1) - eeg.min(axis=-1)   # (n_trials, n_channels)
    max_ptp = ptp.max(axis=-1)                   # (n_trials,)
    return max_ptp < threshold_uv


def euclidean_alignment(eeg: np.ndarray) -> np.ndarray:
    """
    Euclidean Alignment (EA) for cross-subject normalisation.
    Re-centres each subject's covariance to the identity.
    eeg: (n_trials, n_channels, n_samples)
    """
    if not SCIPY_AVAILABLE:
        return eeg
    # TODO: compute mean covariance R and apply R^{-0.5}
    N, C, T = eeg.shape
    R = np.zeros((C, C), dtype=np.float32)
    for trial in eeg:
        R += trial @ trial.T / T
    R /= N
    # Matrix inverse square root
    R_inv_sqrt = np.linalg.inv(sqrtm(R).real).astype(np.float32)
    aligned = np.stack([R_inv_sqrt @ trial for trial in eeg])
    return aligned


def preprocess(eeg: np.ndarray) -> np.ndarray:
    """Full preprocessing pipeline."""
    eeg = bandpass_filter(eeg, BAND_LOW_HZ, BAND_HIGH_HZ, SAMPLE_RATE)
    mask = reject_artifacts(eeg)
    eeg = eeg[mask]
    # NOTE: return mask so caller can filter labels too
    return eeg, mask


# ---------------------------------------------------------------------------
# EEGNet model
# ---------------------------------------------------------------------------

if TORCH_AVAILABLE:
    class EEGNet(nn.Module):
        """
        Compact CNN for EEG classification (Lawhern et al., 2018).
        Input: (batch, 1, n_channels, n_samples)
        """

        def __init__(self, n_classes: int = N_CLASSES,
                     n_channels: int = N_CHANNELS,
                     n_samples: int = N_SAMPLES,
                     f1: int = 8, d: int = 2, f2: int = 16,
                     dropout: float = DROPOUT_RATE):
            super().__init__()
            # Block 1: Temporal convolution
            self.temporal_conv = nn.Sequential(
                nn.Conv2d(1, f1, kernel_size=(1, 64), padding=(0, 32), bias=False),
                nn.BatchNorm2d(f1),
            )
            # Depthwise spatial convolution
            self.spatial_conv = nn.Sequential(
                nn.Conv2d(f1, f1 * d, kernel_size=(n_channels, 1),
                          groups=f1, bias=False),
                nn.BatchNorm2d(f1 * d),
                nn.ELU(),
                nn.AvgPool2d(kernel_size=(1, 4)),
                nn.Dropout(dropout),
            )
            # Block 2: Separable convolution
            self.separable_conv = nn.Sequential(
                nn.Conv2d(f1 * d, f1 * d, kernel_size=(1, 16),
                          padding=(0, 8), groups=f1 * d, bias=False),
                nn.Conv2d(f1 * d, f2, kernel_size=(1, 1), bias=False),
                nn.BatchNorm2d(f2),
                nn.ELU(),
                nn.AvgPool2d(kernel_size=(1, 8)),
                nn.Dropout(dropout),
            )
            # Classifier
            flat_size = f2 * ((n_samples // 4) // 8)
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(flat_size, n_classes),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """x: (batch, 1, n_channels, n_samples)"""
            # TODO: verify input dimensions match model expectations
            x = self.temporal_conv(x)
            x = self.spatial_conv(x)
            x = self.separable_conv(x)
            x = self.classifier(x)
            return x   # logits — apply softmax externally for probabilities


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_model(model, train_loader, n_epochs: int = N_EPOCHS,
                lr: float = LEARNING_RATE, device: str = "cpu"):
    """Train EEGNet with cross-entropy loss."""
    if not TORCH_AVAILABLE:
        return None
    model = model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    for epoch in range(n_epochs):
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(y_batch)
            correct += (logits.argmax(1) == y_batch).sum().item()
            total += len(y_batch)
        scheduler.step()
        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1:3d}/{n_epochs} | "
                  f"loss={total_loss/total:.4f} | acc={correct/total:.3f}")
    return model


def make_dataloader(eeg: np.ndarray, labels: np.ndarray,
                    batch_size: int = BATCH_SIZE, shuffle: bool = True):
    """Wrap numpy arrays in a PyTorch DataLoader."""
    # EEGNet expects (batch, 1, channels, samples)
    X = torch.from_numpy(eeg[:, np.newaxis, :, :])   # add channel dim
    y = torch.from_numpy(labels)
    ds = TensorDataset(X, y)
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle)


# ---------------------------------------------------------------------------
# Evaluation / inference
# ---------------------------------------------------------------------------

def predict(model, eeg: np.ndarray, device: str = "cpu") -> tuple:
    """
    Run inference on a batch of trials.
    Returns (predicted_classes, confidence_scores).
    """
    if not TORCH_AVAILABLE or model is None:
        # Fallback: random predictions
        n = len(eeg)
        preds = np.random.randint(0, N_CLASSES, size=n)
        confs = np.random.dirichlet(np.ones(N_CLASSES), size=n).max(axis=1)
        return preds, confs

    model.eval()
    model.to(device)
    X = torch.from_numpy(eeg[:, np.newaxis, :, :]).to(device)
    with torch.no_grad():
        logits = model(X)
        probs = torch.softmax(logits, dim=1).cpu().numpy()
    preds = probs.argmax(axis=1)
    confs = probs.max(axis=1)
    return preds, confs


def benchmark_latency(model, n_warmup: int = 100, n_runs: int = 1000,
                      device: str = "cpu") -> dict:
    """Measure single-sample inference latency in milliseconds."""
    if not TORCH_AVAILABLE or model is None:
        return {"mean_ms": 999.0, "p95_ms": 999.0, "p99_ms": 999.0}

    model.eval()
    model.to(device)
    dummy = torch.randn(1, 1, N_CHANNELS, N_SAMPLES).to(device)

    # Warm-up
    for _ in range(n_warmup):
        with torch.no_grad():
            _ = model(dummy)

    # Timed runs
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        with torch.no_grad():
            _ = model(dummy)
        times.append((time.perf_counter() - t0) * 1000)

    times = np.array(times)
    return {
        "mean_ms": float(np.mean(times)),
        "p95_ms": float(np.percentile(times, 95)),
        "p99_ms": float(np.percentile(times, 99)),
    }


# ---------------------------------------------------------------------------
# Cross-subject evaluation
# ---------------------------------------------------------------------------

def leave_one_subject_out(all_data, output_dir: str):
    """
    Perform Leave-One-Subject-Out cross-validation.
    Returns list of per-subject accuracy dicts.
    """
    results = []
    n_subjects = len(all_data)
    for test_idx in range(n_subjects):
        print(f"\n[LOSO] Test subject {test_idx + 1}/{n_subjects}")
        # Build training set from all other subjects
        train_eeg = np.concatenate(
            [all_data[i][0] for i in range(n_subjects) if i != test_idx], axis=0)
        train_labels = np.concatenate(
            [all_data[i][1] for i in range(n_subjects) if i != test_idx], axis=0)
        test_eeg, test_labels = all_data[test_idx]

        # Preprocessing
        train_eeg, train_mask = preprocess(train_eeg)
        train_labels = train_labels[train_mask]
        test_eeg, test_mask = preprocess(test_eeg)
        test_labels = test_labels[test_mask]

        if TORCH_AVAILABLE:
            model = EEGNet()
            loader = make_dataloader(train_eeg, train_labels)
            model = train_model(model, loader, n_epochs=10)
        else:
            model = None

        preds, confs = predict(model, test_eeg)
        acc = float(np.mean(preds == test_labels))
        print(f"  Cross-subject accuracy: {acc:.3f}")
        results.append({
            "test_subject": test_idx + 1,
            "cross_subject_accuracy": acc,
        })
    return results


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_predictions(predictions: list, output_dir: str):
    """Save predictions.csv to submission directory."""
    import csv
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "predictions.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["trial_id", "subject_id", "predicted_class", "confidence"])
        writer.writeheader()
        writer.writerows(predictions)
    print(f"[OUT] Predictions saved to {out_path}")


def save_latency(latency: dict, output_dir: str):
    """Save latency_benchmark.json."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "latency_benchmark.json")
    with open(out_path, "w") as f:
        json.dump(latency, f, indent=2)
    print(f"[OUT] Latency benchmark saved to {out_path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P1 NeuroDecode pipeline")
    parser.add_argument("--data_dir", type=str, default="data/eeg_raw",
                        help="Directory containing subject_XX.npz files")
    parser.add_argument("--output_dir", type=str, default="submission",
                        help="Directory for output files")
    parser.add_argument("--n_subjects", type=int, default=10,
                        help="Number of subjects in dataset")
    parser.add_argument("--n_epochs", type=int, default=N_EPOCHS,
                        help="Training epochs for within-subject model")
    parser.add_argument("--device", type=str, default="cpu",
                        help="PyTorch device (cpu or cuda)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("=" * 60)
    print("AIDS-P1: NeuroDecode — Motor Imagery Classification")
    print("=" * 60)

    # --- Load all subjects ---
    print("\n[1/5] Loading data...")
    all_data = load_all_subjects(args.data_dir, args.n_subjects)

    # --- Within-subject evaluation (Subject 1 demo) ---
    print("\n[2/5] Within-subject training (subject 1)...")
    eeg_s1, labels_s1 = all_data[0]
    eeg_s1, mask = preprocess(eeg_s1)
    labels_s1 = labels_s1[mask]

    # 80/20 split
    split = int(0.8 * len(labels_s1))
    idx = np.random.permutation(len(labels_s1))
    train_idx, test_idx = idx[:split], idx[split:]

    if TORCH_AVAILABLE:
        model = EEGNet()
        print(f"  Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        train_loader = make_dataloader(eeg_s1[train_idx], labels_s1[train_idx],
                                       batch_size=BATCH_SIZE)
        model = train_model(model, train_loader, n_epochs=args.n_epochs,
                            lr=LEARNING_RATE, device=args.device)
    else:
        model = None

    preds, confs = predict(model, eeg_s1[test_idx], device=args.device)
    within_acc = float(np.mean(preds == labels_s1[test_idx]))
    print(f"  Within-subject accuracy (S1): {within_acc:.3f}")

    # --- Cross-subject (LOSO) ---
    print("\n[3/5] Cross-subject evaluation (LOSO)...")
    loso_results = leave_one_subject_out(all_data, args.output_dir)
    mean_cross = np.mean([r["cross_subject_accuracy"] for r in loso_results])
    print(f"\n  Mean cross-subject accuracy: {mean_cross:.3f}")

    # --- Latency benchmark ---
    print("\n[4/5] Benchmarking inference latency...")
    latency = benchmark_latency(model, device=args.device)
    print(f"  Mean latency: {latency['mean_ms']:.2f} ms  "
          f"(p95={latency['p95_ms']:.2f} ms, p99={latency['p99_ms']:.2f} ms)")
    save_latency(latency, args.output_dir)

    # --- Save predictions for all subjects ---
    print("\n[5/5] Saving predictions...")
    all_predictions = []
    trial_counter = 0
    for sid, (eeg, labels) in enumerate(all_data, start=1):
        eeg_proc, mask = preprocess(eeg)
        p, c = predict(model, eeg_proc, device=args.device)
        for i, (pred, conf) in enumerate(zip(p, c)):
            all_predictions.append({
                "trial_id": trial_counter + i,
                "subject_id": sid,
                "predicted_class": int(pred),
                "confidence": round(float(conf), 4),
            })
        trial_counter += len(p)
    save_predictions(all_predictions, args.output_dir)

    # --- Summary ---
    summary = {
        "within_subject_accuracy_s1": within_acc,
        "mean_cross_subject_accuracy": mean_cross,
        "latency": latency,
        "loso_details": loso_results,
    }
    summary_path = os.path.join(args.output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[DONE] Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
