# ChronoReconstruct — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

The core insight is that industrial machinery degrades over time in physically predictable ways. Your job is not to decode timestamps — those are gone — but to find **signal-level fingerprints** that evolve monotonically (or quasi-monotonically) across 12 months of operation. Think about what changes in a vibration signal as a turbine's bearings, blades, or shaft wear down. The tachometer data gives you rotational speed, which you can use to separate speed-dependent effects from true degradation trends. Once you have per-file scalar indicators that "tell time," the problem reduces to sequencing — ordering 500 items by multiple noisy clocks.

## Tier 2 — Technique Guidance (-10% score penalty)

**Signal feature extraction:** Compute per-file features from both the time and frequency domains:
- Time domain: RMS, peak-to-RMS (crest factor), kurtosis (sensitive to impulsive bearing faults).
- Frequency domain: Apply FFT; extract the dominant frequency, spectral centroid, and energy in the 1–5 kHz band (typical bearing defect frequency range). Use the tachometer RPM to compute the shaft frequency and look at harmonics (1×, 2×, 3× shaft frequency) and their amplitudes.
- Order tracking: Resample the signal from time domain to angular domain using the tachometer — this normalizes speed variation and reveals pure degradation trends.

**Sequencing algorithm:** Once you have a feature vector per file, the ordering problem is related to the **Traveling Salesman Problem (TSP)** on a 1D manifold. Better approaches include:
- **Isotonic regression / rank aggregation**: Sort by each feature independently, then aggregate rankings (Borda count or rank fusion).
- **Dimensionality reduction + manifold unrolling**: Use PCA or UMAP on the feature matrix to project onto 1D, then sort by the 1D coordinate.
- **Seriation**: Treat it as a matrix reordering problem — compute a distance matrix and apply spectral seriation (reorder rows/columns so similar items are adjacent).

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step-by-step implementation:**

1. **Feature Extraction Loop** (vectorize with numpy):
   ```
   for each file i:
       signal = load signals/signal_i.csv (single column)
       rpm    = load tachometer/tacho_i.csv (single column)
       rms_i         = sqrt(mean(signal^2))
       kurtosis_i    = scipy.stats.kurtosis(signal)
       fft_mag       = abs(np.fft.rfft(signal))
       freqs         = np.fft.rfftfreq(len(signal), d=1/25600)
       centroid_i    = sum(freqs * fft_mag) / sum(fft_mag)
       shaft_freq    = mean(rpm) / 60.0          # Hz
       harmonic_amp  = fft_mag at nearest bin to shaft_freq
       feature_i = [rms_i, kurtosis_i, centroid_i, harmonic_amp, ...]
   ```
   Stack into matrix `F` of shape (500, num_features).

2. **Rank Aggregation:**
   - For each feature column, compute its rank vector (argsort of argsort).
   - Average all rank vectors: `mean_rank = mean(rank_matrix, axis=1)`.
   - `P = argsort(mean_rank)` is your initial permutation estimate.

3. **Refinement with Seriation:**
   - Compute pairwise Euclidean distance matrix `D` (500×500) on normalized `F`.
   - Apply spectral reordering: compute graph Laplacian of the k-NN graph from `D`, find the Fiedler vector (second eigenvector), sort files by Fiedler vector coordinate.

4. **Monotonicity score (for self-evaluation):**
   - For each feature, compute the number of adjacent pairs in `P` where the feature increases: `monotone_score = count(f[P[i]] < f[P[i+1]]) / 499`.
   - Optimize `P` locally (2-opt swaps) to improve this score if time permits.

5. **Output:**
   - Write `P` as a CSV with header `file_index` and 500 integer rows.
