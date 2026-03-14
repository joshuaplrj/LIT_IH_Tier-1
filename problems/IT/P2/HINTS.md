# HealthBridge — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
This is a **federated optimisation + privacy** problem. Think of it in two interleaved loops: an inner loop where each hospital independently improves a local copy of the global model, and an outer loop where a central coordinator merges those improvements without ever seeing raw gradients (only aggregated deltas). Privacy is enforced by making each individual delta statistically indistinguishable from noise. Robustness is enforced by detecting and down-weighting outlier deltas before aggregation.

## Tier 2 — Technique Guidance (-10% score penalty)
- **Model architecture**: Start with a frozen ImageNet-pretrained ResNet-18 and only fine-tune the last two residual blocks + classifier head. This converges in far fewer rounds than training from scratch.
- **Federated algorithm**: Implement **FedAvg** first (aggregate weighted by local dataset size), then optionally upgrade to **FedProx** (adds a proximal term mu * ||w - w_global||^2 to each local loss) for better non-IID convergence.
- **Differential privacy**: Use **DP-SGD**: clip each per-sample gradient to norm C, then add Gaussian noise with sigma = C * noise_multiplier / batch_size. Track privacy with the **Renyi Differential Privacy (RDP) accountant** — the Opacus library handles this out of the box.
- **Secure aggregation**: Simulate secure aggregation by having each hospital secret-share its delta across the other hospitals using additive secret sharing; the server only ever sees the sum, never an individual delta.
- **Straggler handling**: Set a per-round timeout; if a hospital does not respond within T seconds, proceed with the available clients. Weight the aggregate accordingly.
- **Poisoning detection**: Compute the cosine similarity between each client's delta and the current global model gradient direction; clients with similarity below a threshold (e.g., -0.3) are flagged as potential Byzantine nodes and excluded for that round.

## Tier 3 — Implementation Guidance (-15% score penalty)
1. **Shared model** (`model.py`): `class DiagnosisNet(nn.Module)` wrapping `torchvision.models.resnet18(pretrained=True)`. Replace `fc` with `nn.Linear(512, 5)` (5 classes). Freeze all layers except `layer3`, `layer4`, `fc`.
2. **Hospital client** (`client.py`): `class HospitalClient`: constructor takes `hospital_id`, dataset path. Method `local_train(global_weights, epochs=1, lr=1e-3) -> delta_weights`: loads global weights, runs DP-SGD via `opacus.PrivacyEngine`, returns `{k: local_w[k] - global_w[k] for k in global_w}`.
3. **Privacy accounting** (`privacy.py`): after each round call `privacy_engine.get_epsilon(delta=1e-5)` and append to `privacy_log`. Stop training if cumulative epsilon > 3.0.
4. **Federated server** (`server.py`): `class FedServer`: `aggregate(deltas, weights) -> new_global_weights` using weighted mean. Apply Byzantine filter before aggregating. Broadcast new weights via in-process call (no real network needed for simulation).
5. **Training loop** (`train.py`): for each round, spawn `HospitalClient.local_train()` calls as `concurrent.futures.ThreadPoolExecutor` tasks with a 120-second timeout per client. Collect deltas, filter, aggregate, log metrics.
6. **Evaluation** (`eval.py`): load `global_model.pt`, run on `data/global_test/`, report per-class precision/recall and macro accuracy. Compare with a centralized baseline (train on all hospitals' data merged).
7. **Robustness experiment**: re-run training with hospital_3's labels randomly shuffled (label-flipping attack). Record final accuracy drop vs. clean run in `robustness_report.json`.
