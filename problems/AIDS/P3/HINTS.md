# OmniVision — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
Multi-modal image registration is hard because the same physical tissue produces completely different signal intensities across CT, MRI, and PET — you cannot just subtract images or minimise pixel-difference. The core idea is to find a spatial transformation (first rigid, then deformable) that maximises a statistical dependence measure between the two images rather than their intensity difference. Start with rigid registration to correct for gross patient repositioning, then apply a deformable method to handle local anatomical differences such as tumour growth or surgical changes. Fusion is separate from registration: once images are aligned, combine their complementary information (CT = structural/bone detail, MRI = soft-tissue contrast, PET = metabolic activity).

## Tier 2 — Technique Guidance (-10% score penalty)
For rigid registration use **Normalised Mutual Information (NMI)** as the similarity metric, optimised with gradient descent or Powell's method. For deformable registration use **VoxelMorph** — a learning-based diffeomorphic registration network that takes a pair of 3-D volumes and predicts a smooth deformation field while penalising folding via a regularisation loss on the Jacobian determinant. For image fusion use a **Laplacian pyramid** approach: decompose both registered volumes into frequency bands, take maximum-absolute-coefficient per band, and reconstruct — this preserves sharp edges from CT and soft-tissue contrast from MRI simultaneously.

## Tier 3 — Implementation Guidance (-15% score penalty)
Follow these steps in order:

1. **Load and normalise** — Use `nibabel` to load `.nii.gz` files. Extract the `affine` matrix for physical-space coordinates. Normalise intensities: `img = (img - img.min()) / (img.max() - img.min() + 1e-9)`. Resample all volumes to a common 1 mm isotropic grid using `scipy.ndimage.zoom`.

2. **Rigid registration** — Define NMI as: `H(A) + H(B) - H(A,B)` where entropies are computed from 64-bin joint histograms. Use `scipy.optimize.minimize(method='Powell')` to optimise 6 parameters (3 translation, 3 rotation). Apply the transformation with `scipy.ndimage.affine_transform`.

3. **VoxelMorph deformable** — Input: concatenated fixed+moving volumes `(1, 2, D, H, W)`. UNet encoder-decoder predicts flow field `(1, 3, D, H, W)`. Apply spatial transformer via grid sampling (`torch.nn.functional.grid_sample`). Loss: NMI(warped, fixed) + λ * ||∇flow||² with λ=0.01.

4. **Evaluation** — TRE: mean Euclidean distance between landmark pairs in mm after registration. Dice: `2 * |A ∩ B| / (|A| + |B|)` on binary organ masks after warping. Hausdorff: `scipy.spatial.distance.directed_hausdorff`.

5. **Fusion** — Use `pywavelets` (PyWavelets) 3-D DWT for wavelet-domain fusion: take `max(|coeff_A|, |coeff_B|)` at each subband, then reconstruct with inverse DWT.
