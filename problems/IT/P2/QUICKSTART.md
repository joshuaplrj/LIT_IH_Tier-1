# HealthBridge — Quick Start

## Objective
Implement a federated learning system that trains a shared chest X-ray diagnosis CNN across 5 simulated hospitals without any hospital sharing raw patient data, while enforcing differential privacy (epsilon <= 3.0).

## Inputs
- `data/hospital_{1..5}/train/` — JPEG/PNG chest X-rays, organised into subdirectories by label: `pneumonia/`, `covid19/`, `tuberculosis/`, `lung_cancer/`, `normal/`
- `data/hospital_{1..5}/val/` — Held-out validation split per hospital (same structure)
- `data/hospital_{1..5}/metadata.json` — Per-hospital info: `{hospital_id, num_samples, gpu, bandwidth_mbps}`
- `data/global_test/` — Central test set (labels withheld during training; evaluator uses ground truth)

## Expected Output
Submission directory `submission/` containing:
- `submission/global_model.pt` — Final PyTorch state dict of the globally aggregated model
- `submission/results.json` — Training metrics (see schema below)
- `submission/privacy_analysis.json` — Epsilon budget per round and cumulative epsilon
- `submission/robustness_report.json` — Results of poisoned-hospital experiment

`results.json` schema:
```json
{
  "rounds_completed": 0,
  "global_accuracy": 0.0,
  "per_hospital_accuracy": {"hospital_1": 0.0, "hospital_2": 0.0},
  "convergence_curve": [{"round": 1, "global_acc": 0.0}],
  "centralized_baseline_accuracy": 0.0
}
```

## Recommended First Steps
1. Scaffold `HospitalClient` — a class that wraps a local dataset, trains one epoch of a ResNet-18, and returns clipped + noised parameter deltas (DP-SGD pattern).
2. Scaffold `FederatedServer` — collects deltas from all clients, runs FedAvg aggregation (weighted by dataset size), updates the global model, and broadcasts new weights.
3. Run a 3-round dry run on hospital_1 only to verify the training loop, then expand to all 5 hospitals.

## Scoring Breakdown
| Metric                  | Weight |
|-------------------------|--------|
| Model accuracy          | 40%    |
| Privacy preservation    | 30%    |
| System robustness       | 20%    |
| Documentation           | 10%    |

## Common Pitfalls
- Forgetting to clip gradients before adding Gaussian noise: without clipping, the DP guarantee is invalid regardless of sigma.
- Using the same privacy budget accounting for every round: epsilon accumulates via the moments accountant (use Opacus or a manual RDP accountant), not simple addition.
- Ignoring non-IID drift: FedAvg without correction diverges on skewed label distributions — add at least FedProx or local epoch limiting.
