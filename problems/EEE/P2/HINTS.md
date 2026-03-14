# FaultSense — Hints

> Each tier reveals progressively more implementation detail and carries a score penalty. Penalties are cumulative — requesting Tier 3 costs -30% in total.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

This is a **multiclass time-series classification** problem. The raw signals contain rich information, but the key is in what changes at fault inception. Focus on extracting compact numerical summaries that distinguish each fault type: think about what happens to signal symmetry, magnitude ratios, and high-frequency content when different types of faults occur. The pre-fault window (samples 0–166) gives you a clean baseline for each scenario — use it to compute delta features. Bus localization is essentially a separate classifier that leverages which bus signals are most disturbed.

---

## Tier 2 — Technique Guidance (-10% score penalty)

Use a two-stage approach:

**Stage 1 — Feature extraction per file:**
- **Symmetrical components (Fortescue):** Compute positive (V1), negative (V2), and zero (V0) sequence voltages for each bus using the formula V0/1/2 = (1/3) * a_matrix @ [Va, Vb, Vc] where a = e^(j2π/3). The ratios |V2|/|V1| and |V0|/|V1| are diagnostic: SLG has large V0, LL has large V2 but no V0, LLL has neither.
- **RMS per half-cycle window** (samples 167–250, then 250–333): compute per phase per bus.
- **Differential energy:** sum of |signal[post] - signal[pre]|^2 per bus to identify the most-disturbed bus.
- **Wavelet energy (optional):** apply a 1-level DWT (db4 wavelet) to Va at each bus; the detail coefficient energy distinguishes HIF from normal.

**Stage 2 — Classification:**
- Use a **Random Forest** (100–300 trees, class_weight="balanced") from `sklearn` on the extracted feature vector (~60–80 features). Balanced weights are critical for HIF.
- For bus identification, train a second Random Forest on the differential energy features, or add bus features to the same classifier.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Feature extraction (per file, window post-fault = samples 167–333):**

```python
import numpy as np

a = np.exp(1j * 2 * np.pi / 3)
A = np.array([[1, 1, 1],
              [1, a**2, a],
              [1, a, a**2]])

def symmetrical_components(Va, Vb, Vc):
    """Returns (V0, V1, V2) as complex scalars from phasors."""
    phasors = np.array([Va, Vb, Vc])  # complex-valued phasors
    V012 = (1/3) * A @ phasors
    return V012  # [V0, V1, V2]

def rms(x):
    return np.sqrt(np.mean(x**2))

def extract_features(df, inception=167, post_len=167):
    feats = []
    buses = [1, 5, 10, 30]
    pre   = slice(0, inception)
    post  = slice(inception, inception + post_len)

    for bus in buses:
        for ph in ['a', 'b', 'c']:
            v_col = f"V{ph}_{bus}"
            i_col = f"I{ph}_{bus}"
            v_post_rms = rms(df[v_col].values[post])
            i_post_rms = rms(df[i_col].values[post])
            v_delta    = v_post_rms - rms(df[v_col].values[pre])
            i_delta    = i_post_rms - rms(df[i_col].values[pre])
            feats += [v_post_rms, i_post_rms, v_delta, i_delta]

        # Symmetrical components — use post-fault mean as proxy phasor
        Va = df[f"Va_{bus}"].values[post].mean() + 1j * 0
        Vb = df[f"Vb_{bus}"].values[post].mean() * np.exp(-1j * 2*np.pi/3)
        Vc = df[f"Vc_{bus}"].values[post].mean() * np.exp(1j * 2*np.pi/3)
        V012 = symmetrical_components(Va, Vb, Vc)
        V1_mag = abs(V012[1]) + 1e-9
        feats += [abs(V012[0]) / V1_mag,   # |V0|/|V1|
                  abs(V012[2]) / V1_mag]    # |V2|/|V1|

    return np.array(feats, dtype=np.float32)
```

**Training:**
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold

clf = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                             max_features="sqrt", random_state=42, n_jobs=-1)
# Cross-validate with StratifiedKFold to maintain class ratios
```

**HIF boost:** after fitting, if `predicted == "normal"` but the wavelet detail energy is above a threshold (tune on validation set), relabel as `"HIF"`. A simple 1D DWT on Va_1 with `pywavelets` (pywt.dwt) gives this detail coefficient.
