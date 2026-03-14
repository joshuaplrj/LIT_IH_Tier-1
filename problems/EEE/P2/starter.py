"""
FaultSense — Real-Time Power Grid Fault Classification and Localization
Starter skeleton for EEE-P2.

Usage:
    python starter.py --dataset_dir prerequisites/EEE/EEE-P2/fault_dataset \
                      --topology    prerequisites/EEE/EEE-P2/system_topology.json \
                      --output      submission/predictions.csv \
                      [--test_size  0.2]
"""

import argparse
import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)

# Optional — wavelet features
try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False
    warnings.warn("PyWavelets not found. Wavelet features disabled. Install: pip install PyWavelets")


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

BUSES        = [1, 5, 10, 30]
PHASES       = ["a", "b", "c"]
INCEPTION    = 167           # sample index where fault starts
FAULT_TYPES  = ["normal", "SLG", "LL", "DLG", "LLL", "HIF"]

# Fortescue transformation matrix constant
_A_CONST = np.exp(1j * 2 * np.pi / 3)
_A_MAT = np.array([
    [1,            1,            1           ],
    [1, _A_CONST**2, _A_CONST         ],
    [1, _A_CONST,    _A_CONST**2],
])


# ─────────────────────────────────────────────
# 1. DATA LOADING
# ─────────────────────────────────────────────

def load_dataset(dataset_dir: str) -> list:
    """
    Load all fault_NNN.csv files in dataset_dir.
    Returns a list of (fault_id, DataFrame) tuples sorted by fault_id.
    """
    files = sorted(Path(dataset_dir).glob("fault_*.csv"),
                   key=lambda p: int(p.stem.split("_")[1]))

    records = []
    for fp in files:
        fault_id = int(fp.stem.split("_")[1])
        df = pd.read_csv(fp)
        records.append((fault_id, df))

    print(f"[INFO] Loaded {len(records)} fault files from {dataset_dir}")
    return records


# ─────────────────────────────────────────────
# 2. FEATURE EXTRACTION
# ─────────────────────────────────────────────

def rms(arr: np.ndarray) -> float:
    """Root mean square."""
    return float(np.sqrt(np.mean(arr ** 2)))


def symmetrical_components(Va: complex, Vb: complex, Vc: complex):
    """
    Fortescue transformation.
    Returns (V0, V1, V2) as complex values.
    V0 = zero sequence, V1 = positive sequence, V2 = negative sequence.
    """
    phasors = np.array([Va, Vb, Vc])
    V012 = (1.0 / 3.0) * (_A_MAT @ phasors)
    return V012  # [V0, V1, V2]


def wavelet_detail_energy(signal: np.ndarray, wavelet: str = "db4") -> float:
    """Return energy of the first-level wavelet detail coefficient."""
    if not HAS_PYWT:
        return 0.0
    _, detail = pywt.dwt(signal, wavelet)
    return float(np.sum(detail ** 2))


def extract_features(fault_df: pd.DataFrame) -> np.ndarray:
    """
    Extract a fixed-length feature vector from a single fault DataFrame.

    Feature groups (per bus):
      - RMS post-fault per phase (V and I) × 3 phases = 6 features
      - Delta RMS (post - pre) per phase (V and I) × 3 phases = 6 features
      - |V0|/|V1|, |V2|/|V1| symmetrical component ratios = 2 features
      - (optional) wavelet detail energy Va = 1 feature
    Total per bus: 15 features × 4 buses = 60 features (+ wavelet: 64)
    """
    pre_slice  = slice(0, INCEPTION)
    post_slice = slice(INCEPTION, INCEPTION + INCEPTION)  # second cycle post-fault

    features = []

    for bus in BUSES:
        # ── Per-phase RMS and delta ──
        for ph in PHASES:
            v_col = f"V{ph}_{bus}"
            i_col = f"I{ph}_{bus}"

            v_pre  = fault_df[v_col].values[pre_slice]
            v_post = fault_df[v_col].values[post_slice]
            i_pre  = fault_df[i_col].values[pre_slice]
            i_post = fault_df[i_col].values[post_slice]

            v_pre_rms  = rms(v_pre)
            v_post_rms = rms(v_post)
            i_pre_rms  = rms(i_pre)
            i_post_rms = rms(i_post)

            features += [
                v_post_rms,
                i_post_rms,
                v_post_rms - v_pre_rms,   # voltage sag
                i_post_rms - i_pre_rms,   # current surge
                abs(v_post_rms - v_pre_rms) / (v_pre_rms + 1e-9),  # relative sag
                abs(i_post_rms - i_pre_rms) / (i_pre_rms + 1e-9),  # relative surge
            ]

        # ── Symmetrical components (approximate phasors using post-fault mean) ──
        # For a more accurate phasor: use FFT at 60 Hz component
        Va_post = fault_df[f"Va_{bus}"].values[post_slice]
        Vb_post = fault_df[f"Vb_{bus}"].values[post_slice]
        Vc_post = fault_df[f"Vc_{bus}"].values[post_slice]

        # Build approximate phasors: magnitude = RMS, angle from Fortescue assumption
        Va_ph = rms(Va_post) + 1j * 0
        Vb_ph = rms(Vb_post) * np.exp(-1j * 2 * np.pi / 3)
        Vc_ph = rms(Vc_post) * np.exp(1j * 2 * np.pi / 3)

        V012 = symmetrical_components(Va_ph, Vb_ph, Vc_ph)
        V1_mag = abs(V012[1]) + 1e-9
        features += [
            abs(V012[0]) / V1_mag,   # zero-sequence ratio
            abs(V012[2]) / V1_mag,   # negative-sequence ratio
        ]

        # ── Wavelet detail energy (HIF discriminator) ──
        features.append(wavelet_detail_energy(Va_post))

    return np.array(features, dtype=np.float32)


def build_feature_matrix(records: list) -> tuple:
    """
    Extract features from all fault records.
    Returns (X, fault_ids) where X is shape (N, n_features).
    """
    fault_ids = []
    X_list = []

    for fault_id, df in records:
        feats = extract_features(df)
        X_list.append(feats)
        fault_ids.append(fault_id)

    X = np.vstack(X_list)
    print(f"[INFO] Feature matrix shape: {X.shape}")
    return X, fault_ids


# ─────────────────────────────────────────────
# 3. TRAINING (when labels are available)
# ─────────────────────────────────────────────

def train_classifier(X: np.ndarray, y_type: np.ndarray, y_bus: np.ndarray) -> tuple:
    """
    Train fault type and bus classifiers.

    Parameters
    ----------
    X      : feature matrix (N, n_features)
    y_type : fault type labels (N,)
    y_bus  : affected bus labels (N,)

    Returns (clf_type, clf_bus, le_type, le_bus)
    """
    le_type = LabelEncoder()
    le_bus  = LabelEncoder()

    y_type_enc = le_type.fit_transform(y_type)
    y_bus_enc  = le_bus.fit_transform(y_bus)

    # TODO: tune hyperparameters, try XGBoost or MLP for higher accuracy
    clf_type = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )
    clf_bus = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )

    print("[INFO] Training fault type classifier...")
    clf_type.fit(X, y_type_enc)

    print("[INFO] Training bus identification classifier...")
    clf_bus.fit(X, y_bus_enc)

    # Cross-validation report
    cv_scores = cross_val_score(clf_type, X, y_type_enc,
                                cv=StratifiedKFold(5, shuffle=True, random_state=42),
                                scoring="accuracy")
    print(f"[INFO] Fault type CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    return clf_type, clf_bus, le_type, le_bus


# ─────────────────────────────────────────────
# 4. INFERENCE
# ─────────────────────────────────────────────

def predict(clf_type, clf_bus, le_type, le_bus, X: np.ndarray) -> tuple:
    """Run inference and return decoded label arrays."""
    t0 = time.perf_counter()
    y_type_enc = clf_type.predict(X)
    y_bus_enc  = clf_bus.predict(X)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    pred_types = le_type.inverse_transform(y_type_enc)
    pred_buses = le_bus.inverse_transform(y_bus_enc)

    ms_per_sample = elapsed_ms / len(X)
    print(f"[INFO] Inference: {elapsed_ms:.1f} ms total, "
          f"{ms_per_sample:.3f} ms/sample (target <1 ms)")

    return pred_types, pred_buses


# ─────────────────────────────────────────────
# 5. OUTPUT
# ─────────────────────────────────────────────

def save_predictions(fault_ids: list, pred_types, pred_buses, output_path: str):
    """Write the submission CSV."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results_df = pd.DataFrame({
        "fault_id": fault_ids,
        "predicted_fault_type": pred_types,
        "predicted_affected_bus": pred_buses,
    })
    results_df.to_csv(out_path, index=False)
    print(f"[INFO] Predictions saved to {out_path} ({len(results_df)} rows)")


# ─────────────────────────────────────────────
# 6. MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FaultSense Fault Classifier")
    parser.add_argument("--dataset_dir", default="prerequisites/EEE/EEE-P2/fault_dataset",
                        help="Directory containing fault_NNN.csv files")
    parser.add_argument("--topology",    default="prerequisites/EEE/EEE-P2/system_topology.json",
                        help="Path to system_topology.json")
    parser.add_argument("--output",      default="submission/predictions.csv",
                        help="Output predictions CSV")
    parser.add_argument("--labels",      default=None,
                        help="Optional: path to ground truth CSV for training/evaluation")
    parser.add_argument("--test_size",   type=float, default=0.2,
                        help="Fraction of labeled data to hold out for evaluation")
    args = parser.parse_args()

    # Load topology
    with open(args.topology) as f:
        topology = json.load(f)
    print(f"[INFO] Loaded topology: {list(topology.keys())}")

    # Load dataset
    records = load_dataset(args.dataset_dir)

    # Extract features
    print("[INFO] Extracting features from all files...")
    t_start = time.perf_counter()
    X, fault_ids = build_feature_matrix(records)
    print(f"[INFO] Feature extraction: {(time.perf_counter()-t_start)*1000:.0f} ms total")

    if args.labels is not None:
        # ── Supervised mode: train and evaluate ──
        labels_df = pd.read_csv(args.labels)
        # Expected columns: fault_id, fault_type, affected_bus
        labels_df = labels_df.set_index("fault_id")

        y_type = np.array([labels_df.loc[fid, "fault_type"]  for fid in fault_ids])
        y_bus  = np.array([str(labels_df.loc[fid, "affected_bus"]) for fid in fault_ids])

        from sklearn.model_selection import train_test_split
        idx = np.arange(len(fault_ids))
        idx_tr, idx_te = train_test_split(idx, test_size=args.test_size,
                                          stratify=y_type, random_state=42)

        clf_type, clf_bus, le_type, le_bus = train_classifier(
            X[idx_tr], y_type[idx_tr], y_bus[idx_tr]
        )

        # Evaluate on held-out set
        pred_types_te, pred_buses_te = predict(clf_type, clf_bus, le_type, le_bus, X[idx_te])
        print("\n[EVAL] Fault type classification report:")
        print(classification_report(y_type[idx_te], pred_types_te, zero_division=0))
        print("[EVAL] Bus identification accuracy:",
              f"{accuracy_score(y_bus[idx_te], pred_buses_te):.3f}")

        # Full-dataset inference for submission
        pred_types_all, pred_buses_all = predict(clf_type, clf_bus, le_type, le_bus, X)

    else:
        # ── Unsupervised / inference-only mode ──
        # TODO: Replace with your trained model or rule-based fallback.
        # For the hackathon, if no labels file is provided, we output a placeholder.
        print("[WARN] No --labels file provided. Outputting placeholder predictions.")
        print("[WARN] Provide a labels CSV to train a real classifier.")

        # Rule-based placeholder: detect obvious faults from RMS drops
        pred_types_all = []
        pred_buses_all = []
        for fault_id, df in records:
            # Heuristic: large current surge on any bus → not normal
            max_i_delta = 0.0
            max_bus = 1
            for bus in BUSES:
                pre_i  = rms(df[f"Ia_{bus}"].values[:INCEPTION])
                post_i = rms(df[f"Ia_{bus}"].values[INCEPTION:INCEPTION+INCEPTION])
                delta = post_i - pre_i
                if delta > max_i_delta:
                    max_i_delta = delta
                    max_bus = bus

            # TODO: improve this heuristic or replace with trained model
            if max_i_delta < 0.05:
                fault_type = "normal"
            elif max_i_delta < 0.3:
                fault_type = "HIF"
            else:
                fault_type = "SLG"  # placeholder; train a real classifier

            pred_types_all.append(fault_type)
            pred_buses_all.append(str(max_bus))

    save_predictions(fault_ids, pred_types_all, pred_buses_all, args.output)


if __name__ == "__main__":
    main()
