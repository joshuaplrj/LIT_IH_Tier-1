"""
ChronoReconstruct — Starter Skeleton
CSE Problem 1: Reconstruct chronological order of 500 permuted vibration signal files.

Usage:
    python starter.py --signals_dir signals/ --tacho_dir tachometer/ --output solution.csv
"""

import argparse
import os
import time
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import cdist

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SAMPLE_RATE = 25_600   # Hz
N_FILES = 500


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_signal(filepath: str) -> np.ndarray:
    """Load a 1-D vibration signal from a CSV file (single numeric column)."""
    df = pd.read_csv(filepath, header=0)
    return df.iloc[:, 0].values.astype(np.float64)


def load_tachometer(filepath: str) -> np.ndarray:
    """Load a 1-D RPM tachometer signal from a CSV file (single numeric column)."""
    df = pd.read_csv(filepath, header=0)
    return df.iloc[:, 0].values.astype(np.float64)


def discover_files(signals_dir: str, tacho_dir: str):
    """
    Return sorted lists of (signal_path, tacho_path) pairs.
    Assumes files are named consistently (e.g., signal_000.csv / tacho_000.csv).
    """
    sig_files = sorted(
        [os.path.join(signals_dir, f) for f in os.listdir(signals_dir) if f.endswith(".csv")]
    )
    tach_files = sorted(
        [os.path.join(tacho_dir, f) for f in os.listdir(tacho_dir) if f.endswith(".csv")]
    )
    assert len(sig_files) == N_FILES, f"Expected {N_FILES} signal files, found {len(sig_files)}"
    assert len(tach_files) == N_FILES, f"Expected {N_FILES} tacho files, found {len(tach_files)}"
    return sig_files, tach_files


# ---------------------------------------------------------------------------
# Feature Extraction
# ---------------------------------------------------------------------------

def extract_features(signal: np.ndarray, rpm: np.ndarray) -> np.ndarray:
    """
    Extract a fixed-length health-indicator feature vector from one recording.

    Returns a 1-D numpy array of scalar features that (ideally) drift
    monotonically as machine degradation progresses.
    """
    # --- Time-domain features ---
    rms = np.sqrt(np.mean(signal ** 2))
    crest_factor = np.max(np.abs(signal)) / (rms + 1e-12)
    kurt = float(stats.kurtosis(signal, fisher=True))
    skewness = float(stats.skew(signal))

    # --- Frequency-domain features ---
    n = len(signal)
    fft_mag = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(n, d=1.0 / SAMPLE_RATE)
    total_power = np.sum(fft_mag) + 1e-12

    # Spectral centroid
    spectral_centroid = np.sum(freqs * fft_mag) / total_power

    # Energy in bearing-defect frequency band (1–5 kHz)
    band_mask = (freqs >= 1000) & (freqs <= 5000)
    band_energy = np.sum(fft_mag[band_mask] ** 2) / (np.sum(fft_mag ** 2) + 1e-12)

    # --- Tachometer / order-tracking features ---
    mean_rpm = np.mean(rpm[rpm > 0]) if np.any(rpm > 0) else 1.0
    shaft_freq_hz = mean_rpm / 60.0          # fundamental shaft frequency in Hz

    # Amplitude at 1×, 2×, 3× shaft harmonics
    def harmonic_amp(mult):
        target_freq = shaft_freq_hz * mult
        if target_freq <= 0 or target_freq >= SAMPLE_RATE / 2:
            return 0.0
        idx = int(round(target_freq * n / SAMPLE_RATE))
        idx = min(idx, len(fft_mag) - 1)
        return float(fft_mag[idx])

    h1 = harmonic_amp(1)
    h2 = harmonic_amp(2)
    h3 = harmonic_amp(3)

    # TODO: Add more domain-specific features here (e.g., envelope spectrum,
    #       order-tracked RMS, wavelet energy bands, entropy measures).

    return np.array([rms, crest_factor, kurt, skewness,
                     spectral_centroid, band_energy,
                     h1, h2, h3], dtype=np.float64)


def build_feature_matrix(sig_files: list, tach_files: list) -> np.ndarray:
    """
    Load all files and compute feature matrix F of shape (N_FILES, n_features).
    """
    print(f"Extracting features from {N_FILES} files ...")
    features = []
    for i, (sf, tf) in enumerate(zip(sig_files, tach_files)):
        if i % 50 == 0:
            print(f"  Processing file {i}/{N_FILES} ...")
        sig = load_signal(sf)
        rpm = load_tachometer(tf)
        feat = extract_features(sig, rpm)
        features.append(feat)
    F = np.stack(features, axis=0)   # shape: (500, n_features)
    print(f"Feature matrix shape: {F.shape}")
    return F


# ---------------------------------------------------------------------------
# Sequencing / Ordering Algorithm
# ---------------------------------------------------------------------------

def normalize_features(F: np.ndarray) -> np.ndarray:
    """Z-score normalize each feature column."""
    mu = np.mean(F, axis=0)
    sigma = np.std(F, axis=0) + 1e-12
    return (F - mu) / sigma


def rank_aggregation(F_norm: np.ndarray) -> np.ndarray:
    """
    Simple baseline: average the rank of each file across all features,
    then return argsort of average rank.

    Returns permutation P such that P[0] is the estimated first file.
    """
    # TODO: Replace / augment this with a more sophisticated algorithm:
    #       - Spectral seriation (Fiedler vector of the Laplacian)
    #       - Manifold learning (UMAP/PCA -> 1D projection -> sort)
    #       - Isotonic regression on individual feature trends
    #       - TSP-based sequencing on pairwise distance matrix

    n = F_norm.shape[0]
    rank_matrix = np.zeros_like(F_norm)
    for col in range(F_norm.shape[1]):
        rank_matrix[:, col] = stats.rankdata(F_norm[:, col])

    mean_rank = np.mean(rank_matrix, axis=1)
    permutation = np.argsort(mean_rank)
    return permutation


def spectral_seriation(F_norm: np.ndarray, k_neighbors: int = 10) -> np.ndarray:
    """
    Spectral seriation via the Fiedler vector of the k-NN graph Laplacian.

    TODO: Implement or replace with your chosen sequencing method.
    """
    n = F_norm.shape[0]
    D = cdist(F_norm, F_norm, metric="euclidean")

    # Build sparse k-NN adjacency
    W = np.zeros((n, n))
    for i in range(n):
        neighbors = np.argsort(D[i])[1: k_neighbors + 1]
        W[i, neighbors] = 1.0
        W[neighbors, i] = 1.0          # symmetrize

    # Graph Laplacian
    deg = W.sum(axis=1)
    L = np.diag(deg) - W

    # Fiedler vector (second-smallest eigenvector)
    eigenvalues, eigenvectors = np.linalg.eigh(L)
    fiedler_vec = eigenvectors[:, 1]   # second column
    permutation = np.argsort(fiedler_vec)
    return permutation


def two_opt_improve(permutation: np.ndarray, F_norm: np.ndarray,
                    max_iter: int = 1000) -> np.ndarray:
    """
    Local search: 2-opt swaps to improve monotonicity of features
    along the current permutation.

    TODO: Implement monotonicity-guided local search.
    """
    # Placeholder — return permutation unchanged
    return permutation


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_solution(permutation: np.ndarray, output_path: str) -> None:
    """Write the permutation array to solution.csv with header 'file_index'."""
    df = pd.DataFrame({"file_index": permutation.astype(int)})
    df.to_csv(output_path, index=False)
    print(f"Solution written to: {output_path}")


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ChronoReconstruct: recover chronological order of vibration files."
    )
    parser.add_argument("--signals_dir", type=str, default="signals/",
                        help="Directory containing signal_*.csv files.")
    parser.add_argument("--tacho_dir", type=str, default="tachometer/",
                        help="Directory containing tacho_*.csv files.")
    parser.add_argument("--output", type=str, default="solution.csv",
                        help="Path for the output solution CSV.")
    parser.add_argument("--method", type=str, default="rank_aggregation",
                        choices=["rank_aggregation", "spectral_seriation"],
                        help="Sequencing algorithm to use.")
    args = parser.parse_args()

    t_start = time.time()

    # Step 1: Discover input files
    sig_files, tach_files = discover_files(args.signals_dir, args.tacho_dir)

    # Step 2: Extract features
    F = build_feature_matrix(sig_files, tach_files)

    # Step 3: Normalize
    F_norm = normalize_features(F)

    # Step 4: Sequence
    print(f"Running sequencing algorithm: {args.method} ...")
    if args.method == "rank_aggregation":
        permutation = rank_aggregation(F_norm)
    elif args.method == "spectral_seriation":
        permutation = spectral_seriation(F_norm)
    else:
        raise ValueError(f"Unknown method: {args.method}")

    # Step 5: (Optional) Local search refinement
    # permutation = two_opt_improve(permutation, F_norm)

    # Step 6: Write output
    write_solution(permutation, args.output)

    elapsed = time.time() - t_start
    print(f"Total runtime: {elapsed:.1f}s (limit: 600s)")
    if elapsed > 600:
        print("WARNING: Exceeded 10-minute efficiency threshold.")


if __name__ == "__main__":
    main()
