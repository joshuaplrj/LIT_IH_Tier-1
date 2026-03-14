# OmniVision — Quick Start

## Objective
Build a multi-modal medical image registration and fusion system that accurately aligns CT, MRI (T1/T2/FLAIR), and PET scans of the same patient. The system must handle both rigid alignment (patient positioning differences) and deformable registration (anatomical variations) while producing fused images that preserve diagnostic information from all modalities.

## Inputs
- `data/patients/patient_XX/ct.nii.gz` — CT scan, NIfTI format, isotropic 1 mm voxels
- `data/patients/patient_XX/mri_t1.nii.gz` — T1-weighted MRI scan
- `data/patients/patient_XX/mri_t2.nii.gz` — T2-weighted MRI scan
- `data/patients/patient_XX/pet.nii.gz` — PET scan (lower resolution, ~4 mm voxels)
- `data/patients/patient_XX/landmarks.csv` — Columns: `landmark_id, ct_x,ct_y,ct_z, mri_x,mri_y,mri_z` (anatomical ground-truth points)
- `data/patients/patient_XX/segmentation_gt.nii.gz` — Manual organ/tumour segmentation mask

## Expected Output
- `submission/patient_XX/registered_mri.nii.gz` — MRI resampled into CT space
- `submission/patient_XX/registered_pet.nii.gz` — PET resampled into CT space
- `submission/patient_XX/fused_ct_mri.nii.gz` — Fused CT+MRI volume
- `submission/metrics.csv` — Columns: `patient_id, dice_ct_mri, hausdorff_mm, tre_mm, inference_sec`

## Recommended First Steps
1. Run `python starter.py --data_dir data/patients --output_dir submission` to confirm the pipeline runs on dummy 3-D volumes.
2. Implement rigid registration first using mutual information as the similarity metric before attempting deformable methods.
3. Verify the Dice coefficient on patient 01 before scaling to all 10 patients.

## Scoring Breakdown
| Metric                                    | Weight |
|-------------------------------------------|--------|
| Registration accuracy (Dice + Hausdorff)  | 50%    |
| Modality coverage (CT+MRI+PET handled)    | 25%    |
| Inference speed                           | 15%    |
| Clinical report quality                   | 10%    |

## Common Pitfalls
- Registering images without first normalising intensity ranges (CT in Hounsfield units, MRI in arbitrary units) causes mutual information to behave unpredictably; always rescale both volumes to [0, 1] before computing similarity metrics.
- Using mean-squared error as the registration similarity metric for cross-modal alignment will fail because the same tissue has completely different intensities in CT vs. MRI; use normalised mutual information instead.
- Ignoring voxel spacing metadata from the NIfTI header causes the deformation field to fold — always use `affine` matrix from `nibabel` to work in physical coordinates.
