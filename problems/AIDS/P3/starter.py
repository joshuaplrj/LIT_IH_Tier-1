"""
AIDS-P3: OmniVision — Multi-Modal Medical Image Registration and Fusion
Starter skeleton. Run as-is to verify the pipeline executes end-to-end
on randomly generated dummy 3-D volumes.

Usage:
    python starter.py --data_dir data/patients --output_dir submission
"""

import argparse
import csv
import json
import os
import time
from pathlib import Path

import numpy as np

# Optional imaging imports ---------------------------------------------------
try:
    import nibabel as nib
    NIBABEL_AVAILABLE = True
except ImportError:
    NIBABEL_AVAILABLE = False
    print("[WARN] nibabel not found — using numpy dummy volumes.")

try:
    from scipy import ndimage
    from scipy.optimize import minimize
    from scipy.spatial.distance import directed_hausdorff
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[WARN] SciPy not found — registration stubs will use identity transforms.")

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WARN] PyTorch not found — VoxelMorph deformable registration disabled.")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VOLUME_SHAPE = (64, 64, 64)   # downsampled for demo; full data is ~256^3
TARGET_SPACING_MM = 1.0       # isotropic resampling target
NMI_BINS = 64
DEFORM_LAMBDA = 0.01          # regularisation weight
LEARNING_RATE = 1e-3
N_EPOCHS_DEFORM = 20
BATCH_SIZE = 1


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_nifti(path: str) -> tuple:
    """
    Load a NIfTI volume. Returns (numpy_array, affine_4x4).
    Falls back to random dummy volume if file absent or nibabel missing.
    """
    if NIBABEL_AVAILABLE and os.path.exists(path):
        img = nib.load(path)
        return img.get_fdata(dtype=np.float32), img.affine
    # Dummy: small random volume + identity affine
    vol = np.random.rand(*VOLUME_SHAPE).astype(np.float32)
    affine = np.eye(4, dtype=np.float32)
    return vol, affine


def save_nifti(array: np.ndarray, affine: np.ndarray, path: str):
    """Save a numpy array as NIfTI."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if NIBABEL_AVAILABLE:
        img = nib.Nifti1Image(array.astype(np.float32), affine)
        nib.save(img, path)
    else:
        # Save as numpy fallback
        np.save(path.replace(".nii.gz", ".npy"), array)


def load_patient(data_dir: str, patient_id: str) -> dict:
    """Load all modalities for one patient."""
    base = Path(data_dir) / patient_id
    ct, ct_aff = load_nifti(str(base / "ct.nii.gz"))
    mri_t1, mri_aff = load_nifti(str(base / "mri_t1.nii.gz"))
    mri_t2, _ = load_nifti(str(base / "mri_t2.nii.gz"))
    pet, pet_aff = load_nifti(str(base / "pet.nii.gz"))
    seg, _ = load_nifti(str(base / "segmentation_gt.nii.gz"))

    # Load landmarks
    lm_path = base / "landmarks.csv"
    landmarks = []
    if lm_path.exists():
        with open(lm_path) as f:
            for row in csv.DictReader(f):
                landmarks.append(row)

    return {
        "patient_id": patient_id,
        "ct": ct, "ct_affine": ct_aff,
        "mri_t1": mri_t1, "mri_t2": mri_t2, "mri_affine": mri_aff,
        "pet": pet, "pet_affine": pet_aff,
        "seg_gt": seg,
        "landmarks": landmarks,
    }


def list_patients(data_dir: str) -> list:
    """Return sorted list of patient directory names."""
    p = Path(data_dir)
    if not p.exists():
        # Dummy patient list
        return [f"patient_{i:02d}" for i in range(1, 3)]
    return sorted([d.name for d in p.iterdir() if d.is_dir()])


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def normalise(vol: np.ndarray) -> np.ndarray:
    """Rescale volume intensities to [0, 1]."""
    v_min, v_max = vol.min(), vol.max()
    if v_max - v_min < 1e-9:
        return np.zeros_like(vol)
    return (vol - v_min) / (v_max - v_min)


def resample_to_shape(vol: np.ndarray, target_shape: tuple) -> np.ndarray:
    """Resample volume to target_shape using zoom."""
    if not SCIPY_AVAILABLE:
        return vol
    zoom_factors = [t / s for t, s in zip(target_shape, vol.shape)]
    return ndimage.zoom(vol, zoom_factors, order=1).astype(np.float32)


# ---------------------------------------------------------------------------
# Rigid registration (mutual information maximisation)
# ---------------------------------------------------------------------------

def joint_histogram(a: np.ndarray, b: np.ndarray, bins: int = NMI_BINS) -> np.ndarray:
    """Compute 2-D joint histogram of two volumes."""
    a_flat = a.ravel()
    b_flat = b.ravel()
    hist, _, _ = np.histogram2d(a_flat, b_flat, bins=bins,
                                range=[[0, 1], [0, 1]])
    return hist + 1e-10


def normalised_mutual_information(a: np.ndarray, b: np.ndarray) -> float:
    """NMI = (H(A) + H(B)) / H(A,B)."""
    hist = joint_histogram(a, b)
    p_ab = hist / hist.sum()
    p_a = p_ab.sum(axis=1)
    p_b = p_ab.sum(axis=0)
    h_a = -np.sum(p_a * np.log2(p_a + 1e-12))
    h_b = -np.sum(p_b * np.log2(p_b + 1e-12))
    h_ab = -np.sum(p_ab * np.log2(p_ab + 1e-12))
    return float((h_a + h_b) / (h_ab + 1e-12))


def apply_rigid_transform(vol: np.ndarray, params: np.ndarray) -> np.ndarray:
    """
    Apply rigid transform defined by params = [tx, ty, tz, rx, ry, rz]
    (translations in voxels, rotations in radians).
    """
    if not SCIPY_AVAILABLE:
        return vol
    tx, ty, tz, rx, ry, rz = params
    # Build rotation matrix (small angle approximation for demo)
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)],
                   [0, np.sin(rx), np.cos(rx)]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0],
                   [-np.sin(ry), 0, np.cos(ry)]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0],
                   [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    offset = np.array([tx, ty, tz])
    return ndimage.affine_transform(vol, R, offset=offset, order=1)


def rigid_registration(fixed: np.ndarray, moving: np.ndarray) -> np.ndarray:
    """
    Register moving to fixed by maximising NMI.
    Returns optimal params [tx, ty, tz, rx, ry, rz].
    """
    if not SCIPY_AVAILABLE:
        print("[INFO] SciPy unavailable — returning identity rigid params.")
        return np.zeros(6)

    def neg_nmi(params):
        warped = apply_rigid_transform(moving, params)
        return -normalised_mutual_information(fixed, warped)

    x0 = np.zeros(6)
    result = minimize(neg_nmi, x0, method="Powell",
                      options={"maxiter": 100, "disp": False})
    return result.x


# ---------------------------------------------------------------------------
# VoxelMorph-style deformable registration
# ---------------------------------------------------------------------------

if TORCH_AVAILABLE:
    class VoxelMorphNet(nn.Module):
        """
        Lightweight UNet that predicts a 3-D deformation flow field.
        Input: concatenated fixed + moving volumes, shape (B, 2, D, H, W)
        Output: flow field, shape (B, 3, D, H, W)
        """

        def __init__(self, in_channels: int = 2, base_filters: int = 16):
            super().__init__()
            # Encoder
            self.enc1 = self._block(in_channels, base_filters)
            self.enc2 = self._block(base_filters, base_filters * 2)
            # Decoder
            self.dec1 = self._block(base_filters * 2, base_filters)
            self.flow = nn.Conv3d(base_filters, 3, kernel_size=3, padding=1)
            nn.init.zeros_(self.flow.weight)
            nn.init.zeros_(self.flow.bias)

        @staticmethod
        def _block(in_c, out_c):
            return nn.Sequential(
                nn.Conv3d(in_c, out_c, 3, padding=1),
                nn.InstanceNorm3d(out_c),
                nn.LeakyReLU(0.2),
            )

        def forward(self, x):
            e1 = self.enc1(x)
            e2 = self.enc2(F.avg_pool3d(e1, 2))
            d1 = F.interpolate(self.dec1(e2),
                               size=e1.shape[2:], mode="trilinear",
                               align_corners=False)
            flow = self.flow(d1 + e1)
            return flow


    def spatial_transformer(vol: torch.Tensor,
                            flow: torch.Tensor) -> torch.Tensor:
        """
        Warp volume with flow field using differentiable grid sampling.
        vol:  (B, 1, D, H, W)
        flow: (B, 3, D, H, W)
        """
        B, _, D, H, W = vol.shape
        # Create identity grid
        vectors = [torch.linspace(-1, 1, s) for s in (D, H, W)]
        grid = torch.stack(torch.meshgrid(*vectors, indexing="ij"), dim=-1)
        grid = grid.unsqueeze(0).expand(B, -1, -1, -1, -1).to(vol.device)
        # Add normalised flow
        flow_norm = flow.permute(0, 2, 3, 4, 1)
        flow_norm = flow_norm / torch.tensor(
            [D, H, W], dtype=torch.float32).to(vol.device)
        new_locs = grid + flow_norm
        # grid_sample expects (x, y, z) order
        new_locs = new_locs[..., [2, 1, 0]]
        return F.grid_sample(vol, new_locs, align_corners=True,
                             mode="bilinear", padding_mode="border")


def deformable_registration(fixed: np.ndarray, moving: np.ndarray,
                             n_epochs: int = N_EPOCHS_DEFORM,
                             device: str = "cpu") -> np.ndarray:
    """
    Register moving to fixed with a VoxelMorph network.
    Returns the warped moving volume as a numpy array.
    """
    if not TORCH_AVAILABLE:
        print("[INFO] PyTorch unavailable — returning unregistered moving volume.")
        return moving

    import torch.optim as optim
    model = VoxelMorphNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    fixed_t = torch.from_numpy(fixed).unsqueeze(0).unsqueeze(0).to(device)
    moving_t = torch.from_numpy(moving).unsqueeze(0).unsqueeze(0).to(device)
    concat = torch.cat([fixed_t, moving_t], dim=1)

    for epoch in range(n_epochs):
        model.train()
        optimizer.zero_grad()
        flow = model(concat)
        warped = spatial_transformer(moving_t, flow)
        # NMI loss approximation: negative normalised cross-correlation
        ncc_loss = -normalised_cross_correlation(fixed_t, warped)
        # Regularisation: smoothness of flow
        reg_loss = gradient_loss(flow)
        loss = ncc_loss + DEFORM_LAMBDA * reg_loss
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 5 == 0:
            print(f"  Deform epoch {epoch+1}/{n_epochs} | "
                  f"loss={loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        flow = model(concat)
        warped = spatial_transformer(moving_t, flow)
    return warped.squeeze().cpu().numpy()


def normalised_cross_correlation(fixed: "torch.Tensor",
                                  warped: "torch.Tensor",
                                  window: int = 9) -> "torch.Tensor":
    """Approximate NCC for differentiable registration loss."""
    import torch
    f = fixed - fixed.mean()
    w = warped - warped.mean()
    ncc = (f * w).mean() / (f.std() * w.std() + 1e-9)
    return ncc


def gradient_loss(flow: "torch.Tensor") -> "torch.Tensor":
    """Penalise non-smooth deformation field."""
    import torch
    dy = torch.abs(flow[:, :, 1:, :, :] - flow[:, :, :-1, :, :])
    dx = torch.abs(flow[:, :, :, 1:, :] - flow[:, :, :, :-1, :])
    dz = torch.abs(flow[:, :, :, :, 1:] - flow[:, :, :, :, :-1])
    return (dy.mean() + dx.mean() + dz.mean()) / 3.0


# ---------------------------------------------------------------------------
# Image fusion
# ---------------------------------------------------------------------------

def laplacian_pyramid_fusion(vol_a: np.ndarray,
                              vol_b: np.ndarray,
                              levels: int = 3) -> np.ndarray:
    """
    Fuse two registered volumes using a Laplacian pyramid.
    At each level, take the voxel with larger absolute value.
    """
    if not SCIPY_AVAILABLE:
        return (vol_a + vol_b) / 2.0

    def gaussian_blur(v):
        return ndimage.gaussian_filter(v, sigma=1.0)

    pyramids_a, pyramids_b = [], []
    ga, gb = vol_a.copy(), vol_b.copy()
    for _ in range(levels):
        ga_blur = gaussian_blur(ga)
        gb_blur = gaussian_blur(gb)
        pyramids_a.append(ga - ga_blur)
        pyramids_b.append(gb - gb_blur)
        ga, gb = ga_blur, gb_blur
    # Lowest frequency: average
    fused = (ga + gb) / 2.0
    # Reconstruct from highest to lowest
    for la, lb in reversed(list(zip(pyramids_a, pyramids_b))):
        fused = fused + np.where(np.abs(la) >= np.abs(lb), la, lb)
    return np.clip(fused, 0, 1)


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------

def dice_coefficient(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    """Dice overlap between two binary masks."""
    a = (mask_a > 0.5).astype(bool)
    b = (mask_b > 0.5).astype(bool)
    intersection = np.logical_and(a, b).sum()
    denom = a.sum() + b.sum()
    return float(2 * intersection / (denom + 1e-9))


def hausdorff_distance(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    """95th-percentile Hausdorff distance in voxels."""
    pts_a = np.argwhere(mask_a > 0.5).astype(float)
    pts_b = np.argwhere(mask_b > 0.5).astype(float)
    if len(pts_a) == 0 or len(pts_b) == 0:
        return float("inf")
    if SCIPY_AVAILABLE:
        d1 = directed_hausdorff(pts_a, pts_b)[0]
        d2 = directed_hausdorff(pts_b, pts_a)[0]
        return float(max(d1, d2))
    return float("nan")


def target_registration_error(landmarks: list,
                               affine_params: np.ndarray) -> float:
    """
    Compute mean TRE across landmark pairs.
    landmarks: list of dicts with ct_x/y/z and mri_x/y/z keys.
    """
    if not landmarks:
        return float("nan")
    errors = []
    for lm in landmarks:
        try:
            ct_pt = np.array([float(lm["ct_x"]), float(lm["ct_y"]),
                              float(lm["ct_z"])])
            mri_pt = np.array([float(lm["mri_x"]), float(lm["mri_y"]),
                               float(lm["mri_z"])])
            # Apply rigid transform to MRI landmark
            tx, ty, tz = affine_params[:3]
            shifted = mri_pt + np.array([tx, ty, tz])
            errors.append(np.linalg.norm(ct_pt - shifted))
        except (KeyError, ValueError):
            continue
    return float(np.mean(errors)) if errors else float("nan")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_patient(patient: dict, output_dir: str,
                    device: str = "cpu") -> dict:
    """Run full registration + fusion pipeline for one patient."""
    pid = patient["patient_id"]
    out_patient = os.path.join(output_dir, pid)
    os.makedirs(out_patient, exist_ok=True)
    t_start = time.time()

    print(f"\n  Processing {pid}...")
    ct = normalise(resample_to_shape(patient["ct"], VOLUME_SHAPE))
    mri = normalise(resample_to_shape(patient["mri_t1"], VOLUME_SHAPE))
    pet = normalise(resample_to_shape(patient["pet"], VOLUME_SHAPE))
    seg = resample_to_shape(patient["seg_gt"], VOLUME_SHAPE)

    # --- Rigid registration (MRI → CT) ---
    print("    Rigid registration (MRI → CT)...")
    rigid_params = rigid_registration(ct, mri)
    mri_rigid = apply_rigid_transform(mri, rigid_params) if SCIPY_AVAILABLE else mri
    pet_rigid = apply_rigid_transform(pet, rigid_params) if SCIPY_AVAILABLE else pet

    # --- Deformable registration ---
    print("    Deformable registration (MRI → CT)...")
    mri_deformed = deformable_registration(ct, mri_rigid, device=device)
    pet_deformed = deformable_registration(ct, pet_rigid, n_epochs=10, device=device)

    # --- Fusion ---
    print("    Fusing CT + MRI...")
    fused = laplacian_pyramid_fusion(ct, mri_deformed)

    # --- Save outputs ---
    affine = patient["ct_affine"]
    save_nifti(mri_deformed, affine,
               os.path.join(out_patient, "registered_mri.nii.gz"))
    save_nifti(pet_deformed, affine,
               os.path.join(out_patient, "registered_pet.nii.gz"))
    save_nifti(fused, affine,
               os.path.join(out_patient, "fused_ct_mri.nii.gz"))

    # --- Metrics ---
    seg_warped = apply_rigid_transform(seg, rigid_params) if SCIPY_AVAILABLE else seg
    dice = dice_coefficient(seg_warped, seg)
    hd = hausdorff_distance(seg_warped, seg)
    tre = target_registration_error(patient["landmarks"], rigid_params)
    elapsed = time.time() - t_start

    return {
        "patient_id": pid,
        "dice_ct_mri": round(dice, 4),
        "hausdorff_mm": round(hd, 2) if not np.isnan(hd) else -1,
        "tre_mm": round(tre, 2) if not np.isnan(tre) else -1,
        "inference_sec": round(elapsed, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="AIDS-P3 OmniVision pipeline")
    parser.add_argument("--data_dir", type=str, default="data/patients",
                        help="Directory containing patient_XX subdirectories")
    parser.add_argument("--output_dir", type=str, default="submission",
                        help="Output directory")
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("=" * 60)
    print("AIDS-P3: OmniVision — Multi-Modal Image Registration")
    print("=" * 60)

    patient_ids = list_patients(args.data_dir)
    print(f"\nFound {len(patient_ids)} patients: {patient_ids}")

    all_metrics = []
    for pid in patient_ids:
        patient = load_patient(args.data_dir, pid)
        metrics = process_patient(patient, args.output_dir, device=args.device)
        all_metrics.append(metrics)
        print(f"  {pid} — Dice={metrics['dice_ct_mri']:.3f}  "
              f"HD={metrics['hausdorff_mm']} mm  "
              f"TRE={metrics['tre_mm']} mm  "
              f"Time={metrics['inference_sec']} s")

    # --- Save metrics CSV ---
    metrics_path = os.path.join(args.output_dir, "metrics.csv")
    with open(metrics_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["patient_id", "dice_ct_mri",
                           "hausdorff_mm", "tre_mm", "inference_sec"])
        writer.writeheader()
        writer.writerows(all_metrics)
    print(f"\n[OUT] Metrics saved to {metrics_path}")

    # --- Summary ---
    valid = [m for m in all_metrics if m["dice_ct_mri"] >= 0]
    if valid:
        print(f"\n  Mean Dice:      {np.mean([m['dice_ct_mri'] for m in valid]):.3f}")
        print(f"  Mean inference: {np.mean([m['inference_sec'] for m in valid]):.1f} s")
    print("\n[DONE]")


if __name__ == "__main__":
    main()
