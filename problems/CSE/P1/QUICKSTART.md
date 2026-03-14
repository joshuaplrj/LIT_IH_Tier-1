# ChronoReconstruct — Quick Start

## Objective
Recover the original chronological order of 500 randomly permuted industrial turbine vibration recordings. Output a permutation array that, when applied, restores the files to their true timeline.

## Inputs
- `signals/` — 500 CSV files (`signal_000.csv` … `signal_499.csv`), each with a 1D vibration signal column; 10,000–100,000 samples recorded at 25,600 Hz.
- `tachometer/` — 500 CSV files (`tacho_000.csv` … `tacho_499.csv`), each with a 1D RPM signal corresponding to the same time window.

## Expected Output
- **Filename:** `solution.csv`
- **Format:** Single column header `file_index`, 500 integer rows (0-indexed), where row `i` gives the file index that belongs at position `i` in the chronological sequence.

```
file_index
42
17
301
...
```

## Recommended First Steps
1. Load all 500 signal files and extract scalar health indicators per file (RMS amplitude, spectral centroid, dominant frequency from FFT, kurtosis — these tend to drift monotonically as turbines degrade).
2. Construct a pairwise similarity/distance matrix (500×500) using the extracted features, then apply a sequencing algorithm (e.g., shortest-path TSP approximation or isotonic regression on ranked features) to produce an ordered permutation.
3. Validate your ordering by measuring monotonicity of your health indicators across the recovered sequence and check that it improves over a random baseline.

## Scoring Breakdown
| Metric | Weight |
|---|---|
| Kendall's Tau (τ) vs. ground truth | 60% |
| Monotonicity of extracted health indicators over recovered sequence | 20% |
| Computational efficiency (full pipeline completes in < 10 minutes) | 10% |
| Novelty of approach (documented in comments or README) | 10% |

## Common Pitfalls
- Extracting only time-domain features (RMS, mean) while ignoring frequency-domain degradation signatures — turbine wear is most visible in sideband frequencies around the blade-pass frequency.
- Treating the problem as a pure sorting problem on a single feature; noise in individual features makes multi-feature fusion critical.
- Forgetting that the permutation is 0-indexed — off-by-one errors in `solution.csv` will silently reduce Kendall's Tau.
- Using external pretrained models (prohibited); rely entirely on classical signal processing.
- Running on all 500 files sequentially without vectorization; FFT on 100k-sample files is fast but repeated 500 times needs batching to stay under 10 minutes.
