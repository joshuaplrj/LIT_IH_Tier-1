# NeuroDecode — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
EEG motor imagery decoding is a signal processing + domain adaptation problem. The raw voltage time-series contains frequency-band oscillations (mu ~10 Hz, beta ~20 Hz) that modulate during motor imagery — these are the discriminative features. The critical challenge is that electrode impedance, head geometry, and individual neural patterns shift the signal distribution between subjects, making naive training on one subject and testing on another fail badly. Your solution must address this distribution shift explicitly.

## Tier 2 — Technique Guidance (-10% score penalty)
Use **EEGNet** (a compact depthwise-separable CNN designed for EEG) as your base classifier — it has only ~2 K parameters, generalises well across subjects, and runs in <5 ms on CPU. For cross-subject generalisation apply **Euclidean Alignment (EA)**: re-centre each subject's covariance matrix to the identity before feature extraction — this single step typically raises cross-subject accuracy by 10–15 percentage points without any additional training. For explainability compute **class activation maps (CAM)** by applying global average pooling before the final linear layer, then project weights back onto the time-frequency-channel tensor.

## Tier 3 — Implementation Guidance (-15% score penalty)
Follow these steps in order:

1. **Preprocessing pipeline** — Apply a 4th-order Butterworth band-pass filter (8–30 Hz) using `scipy.signal.butter` + `sosfiltfilt`. Epoch the continuous signal into 4-second trials with a 0.5-second baseline. Reject trials whose peak-to-peak amplitude exceeds 100 µV.

2. **Euclidean Alignment** — For each subject compute the mean covariance `R = mean(X @ X.T / T)` over all training trials, then transform each trial as `X_aligned = R^{-0.5} @ X`. Use `scipy.linalg.sqrtm` for the matrix square root.

3. **EEGNet architecture** — Block 1: temporal conv `(1, 64)` → batch norm → depthwise conv `(C, 1)` with depth multiplier 2 → batch norm → ELU → average pool `(1, 4)` → dropout 0.5. Block 2: separable conv `(1, 16)` → batch norm → ELU → average pool `(1, 8)` → dropout 0.5. Flatten → Dense(4) → softmax.

4. **Transfer learning** — Freeze all layers except the final Dense layer. Fine-tune on ≤10 labelled trials from the target subject for 50 epochs with learning rate 1e-4.

5. **Latency benchmark** — Warm up with 100 forward passes then time 1000 single-sample passes using `time.perf_counter`; report mean and percentiles.
