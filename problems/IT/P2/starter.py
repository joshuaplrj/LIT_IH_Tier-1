"""
IT-P2: HealthBridge — Federated Learning Starter Skeleton
==========================================================
Run:
    python starter.py --data_dir ./data --output_dir ./submission --rounds 10

Requirements:
    pip install torch torchvision opacus
    pip install Pillow numpy scikit-learn tqdm
"""

import argparse
import copy
import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NUM_HOSPITALS = 5
NUM_CLASSES = 5
CLASS_NAMES = ["normal", "pneumonia", "covid19", "tuberculosis", "lung_cancer"]
IMG_SIZE = 224
BATCH_SIZE = 32
LOCAL_EPOCHS = 1
LEARNING_RATE = 1e-3
DP_MAX_GRAD_NORM = 1.0
DP_NOISE_MULTIPLIER = 1.1
DP_DELTA = 1e-5
DP_EPSILON_BUDGET = 3.0
STRAGGLER_TIMEOUT_SEC = 120
DEFAULT_DATA_DIR = "./data"
DEFAULT_OUTPUT_DIR = "./submission"

# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class ChestXRayDataset(Dataset):
    """Loads JPEG/PNG chest X-rays from a directory tree:
        root/
          normal/         *.jpg
          pneumonia/      *.jpg
          covid19/        *.jpg
          tuberculosis/   *.jpg
          lung_cancer/    *.jpg
    """

    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    def __init__(self, root: Path):
        self.samples: List[Tuple[Path, int]] = []
        for idx, cls in enumerate(CLASS_NAMES):
            cls_dir = root / cls
            if not cls_dir.exists():
                continue
            for img_path in cls_dir.glob("*.jpg"):
                self.samples.append((img_path, idx))
            for img_path in cls_dir.glob("*.png"):
                self.samples.append((img_path, idx))
        log.info("Dataset at %s: %d samples", root, len(self.samples))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, int]:
        path, label = self.samples[index]
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (IMG_SIZE, IMG_SIZE))
        return self.transform(img), label


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class DiagnosisNet(nn.Module):
    """ResNet-18 backbone fine-tuned for 5-class chest X-ray diagnosis."""

    def __init__(self, num_classes: int = NUM_CLASSES, pretrained: bool = True):
        super().__init__()
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        base = models.resnet18(weights=weights)

        # Freeze early layers — only train layer3, layer4, fc
        for name, param in base.named_parameters():
            if not any(name.startswith(p) for p in ["layer3", "layer4", "fc"]):
                param.requires_grad = False

        base.fc = nn.Linear(512, num_classes)
        self.net = base

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ---------------------------------------------------------------------------
# Privacy accounting (manual RDP stub)
# ---------------------------------------------------------------------------


class PrivacyAccountant:
    """Tracks cumulative epsilon using a simplified Gaussian mechanism accountant.

    TODO: Replace with opacus.accountants.RDPAccountant for production accuracy.
    """

    def __init__(self, target_delta: float = DP_DELTA):
        self.target_delta = target_delta
        self._cumulative_epsilon = 0.0
        self._log: List[Dict] = []

    def step(self, noise_multiplier: float, sample_rate: float, num_steps: int) -> float:
        """Compute epsilon for one round and accumulate.

        TODO: Replace this approximation with actual RDP accountant math.
        """
        # Rough approximation: eps ≈ sqrt(2 * ln(1/delta)) * sample_rate * sqrt(num_steps) / noise_multiplier
        import math
        approx_eps = (
            math.sqrt(2 * math.log(1 / self.target_delta))
            * sample_rate
            * math.sqrt(num_steps)
            / noise_multiplier
        )
        self._cumulative_epsilon += approx_eps
        entry = {"round_eps": round(approx_eps, 4), "cumulative_eps": round(self._cumulative_epsilon, 4)}
        self._log.append(entry)
        return self._cumulative_epsilon

    @property
    def cumulative_epsilon(self) -> float:
        return self._cumulative_epsilon

    def log(self) -> List[Dict]:
        return self._log


# ---------------------------------------------------------------------------
# Hospital client
# ---------------------------------------------------------------------------


class HospitalClient:
    """Simulates one hospital's local training process."""

    def __init__(self, hospital_id: int, data_dir: Path, device: torch.device):
        self.hospital_id = hospital_id
        self.device = device
        train_path = data_dir / f"hospital_{hospital_id}" / "train"
        val_path = data_dir / f"hospital_{hospital_id}" / "val"
        self.train_dataset = ChestXRayDataset(train_path)
        self.val_dataset = ChestXRayDataset(val_path)
        self.n_samples = len(self.train_dataset)
        log.info("Hospital %d: %d training samples", hospital_id, self.n_samples)

    def local_train(
        self,
        global_state_dict: Dict[str, torch.Tensor],
        epochs: int = LOCAL_EPOCHS,
        lr: float = LEARNING_RATE,
        noise_multiplier: float = DP_NOISE_MULTIPLIER,
        max_grad_norm: float = DP_MAX_GRAD_NORM,
    ) -> Tuple[Dict[str, torch.Tensor], int]:
        """Train local model and return weight delta + number of samples used.

        Returns:
            delta_weights: {param_name: (local_weight - global_weight)}
            n_samples: number of training samples processed
        """
        if len(self.train_dataset) == 0:
            log.warning("Hospital %d has no training data — skipping", self.hospital_id)
            return {}, 0

        model = DiagnosisNet(pretrained=False).to(self.device)
        model.load_state_dict(global_state_dict)
        model.train()

        loader = DataLoader(self.train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
        optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)
        criterion = nn.CrossEntropyLoss()

        for _epoch in range(epochs):
            for images, labels in loader:
                images, labels = images.to(self.device), labels.to(self.device)
                optimizer.zero_grad()
                logits = model(images)
                loss = criterion(logits, labels)
                loss.backward()

                # DP-SGD: clip per-sample gradients and add Gaussian noise
                # TODO: use opacus.PrivacyEngine for correct per-sample clipping
                nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                with torch.no_grad():
                    for param in model.parameters():
                        if param.grad is not None:
                            param.grad += torch.randn_like(param.grad) * noise_multiplier * max_grad_norm

                optimizer.step()

        local_state = model.state_dict()
        delta = {k: local_state[k].cpu() - global_state_dict[k].cpu() for k in global_state_dict}
        return delta, len(self.train_dataset)

    def evaluate(self, state_dict: Dict[str, torch.Tensor]) -> float:
        """Return accuracy of state_dict on the hospital's local validation set."""
        if len(self.val_dataset) == 0:
            return 0.0
        model = DiagnosisNet(pretrained=False).to(self.device)
        model.load_state_dict(state_dict)
        model.eval()
        loader = DataLoader(self.val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
        correct = total = 0
        with torch.no_grad():
            for images, labels in loader:
                images, labels = images.to(self.device), labels.to(self.device)
                preds = model(images).argmax(dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        return correct / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Federated server
# ---------------------------------------------------------------------------


class FedServer:
    """Central aggregation server (no raw data ever passes through)."""

    def __init__(self, device: torch.device):
        self.device = device
        self.global_model = DiagnosisNet(pretrained=True).to(device)

    def global_state(self) -> Dict[str, torch.Tensor]:
        return copy.deepcopy(self.global_model.state_dict())

    def aggregate(
        self,
        deltas: List[Dict[str, torch.Tensor]],
        weights: List[int],
    ) -> None:
        """FedAvg: weighted average of deltas, added to global model.

        TODO: Add Byzantine filtering (cosine similarity check) before averaging.
        """
        if not deltas:
            log.warning("No client deltas received — skipping aggregation")
            return

        total_weight = sum(weights)
        if total_weight == 0:
            return

        global_sd = self.global_model.state_dict()
        for key in global_sd:
            if not global_sd[key].is_floating_point():
                continue
            # Weighted sum of deltas
            weighted_delta = torch.zeros_like(global_sd[key].float())
            for delta, w in zip(deltas, weights):
                if key in delta:
                    weighted_delta += delta[key].float() * (w / total_weight)
            global_sd[key] = global_sd[key].float() + weighted_delta

        self.global_model.load_state_dict(global_sd)
        log.info("Aggregation complete — %d clients, total samples: %d", len(deltas), total_weight)


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


def run_federated_training(
    data_dir: Path,
    output_dir: Path,
    rounds: int,
    poisoned_hospital: Optional[int] = None,
) -> Dict:
    """Main federated training loop.

    Args:
        data_dir: root data directory
        output_dir: where to write submission artefacts
        rounds: number of federated rounds
        poisoned_hospital: if set, simulate a label-flipping attack on this hospital ID
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Using device: %s", device)

    server = FedServer(device)
    clients = [HospitalClient(i + 1, data_dir, device) for i in range(NUM_HOSPITALS)]
    accountant = PrivacyAccountant()

    convergence_curve = []
    per_hospital_accuracy: Dict[str, float] = {}

    for round_num in range(1, rounds + 1):
        log.info("=== Round %d / %d ===", round_num, rounds)
        global_state = server.global_state()

        # Parallel local training with straggler timeout
        deltas: List[Dict[str, torch.Tensor]] = []
        sample_counts: List[int] = []

        with ThreadPoolExecutor(max_workers=NUM_HOSPITALS) as executor:
            futures = {
                executor.submit(client.local_train, global_state): client
                for client in clients
            }
            for future, client in futures.items():
                try:
                    delta, n = future.result(timeout=STRAGGLER_TIMEOUT_SEC)
                    if n > 0:
                        deltas.append(delta)
                        sample_counts.append(n)
                except FuturesTimeoutError:
                    log.warning("Hospital %d timed out — treated as straggler", client.hospital_id)
                except Exception as exc:
                    log.error("Hospital %d failed: %s", client.hospital_id, exc)

        # Aggregate
        server.aggregate(deltas, sample_counts)

        # Track privacy budget
        sample_rate = BATCH_SIZE / max(1, min(c.n_samples for c in clients))
        num_steps = LOCAL_EPOCHS * max(1, max(c.n_samples for c in clients) // BATCH_SIZE)
        cumulative_eps = accountant.step(DP_NOISE_MULTIPLIER, sample_rate, num_steps)
        log.info("Cumulative epsilon: %.4f", cumulative_eps)

        # Evaluate global model on each hospital's val set
        current_state = server.global_state()
        round_accs = []
        for client in clients:
            acc = client.evaluate(current_state)
            per_hospital_accuracy[f"hospital_{client.hospital_id}"] = round(acc, 4)
            round_accs.append(acc)

        global_acc = float(np.mean(round_accs))
        convergence_curve.append({"round": round_num, "global_acc": round(global_acc, 4)})
        log.info("Round %d global accuracy: %.4f", round_num, global_acc)

        # Stop if epsilon budget exhausted
        if cumulative_eps > DP_EPSILON_BUDGET:
            log.warning("Privacy budget exhausted (eps=%.4f > %.1f) — stopping early", cumulative_eps, DP_EPSILON_BUDGET)
            break

    # Save artefacts
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "global_model.pt"
    torch.save(server.global_model.state_dict(), model_path)
    log.info("Global model saved to %s", model_path)

    results = {
        "rounds_completed": len(convergence_curve),
        "global_accuracy": convergence_curve[-1]["global_acc"] if convergence_curve else 0.0,
        "per_hospital_accuracy": per_hospital_accuracy,
        "convergence_curve": convergence_curve,
        "centralized_baseline_accuracy": 0.0,  # TODO: fill from centralized training run
    }
    with open(output_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    privacy_analysis = {"epsilon_budget": DP_EPSILON_BUDGET, "delta": DP_DELTA, "rounds": accountant.log()}
    with open(output_dir / "privacy_analysis.json", "w") as f:
        json.dump(privacy_analysis, f, indent=2)

    return results


def run_robustness_experiment(data_dir: Path, output_dir: Path, rounds: int) -> Dict:
    """Re-run training with one hospital's labels poisoned (label-flipping attack).

    TODO: Implement actual label flipping on the dataset before training.
    Returns robustness report comparing clean vs. poisoned global accuracy.
    """
    log.info("Running robustness experiment (label-flipping on hospital_3)")
    clean_results = run_federated_training(data_dir, output_dir, rounds)
    # TODO: flip labels in hospital_3's dataset copy and re-run
    poisoned_results = {"global_accuracy": 0.0}  # stub

    report = {
        "clean_global_accuracy": clean_results["global_accuracy"],
        "poisoned_global_accuracy": poisoned_results["global_accuracy"],
        "accuracy_drop": round(clean_results["global_accuracy"] - poisoned_results["global_accuracy"], 4),
        "poisoned_hospital": 3,
        "attack_type": "label_flipping",
    }
    with open(output_dir / "robustness_report.json", "w") as f:
        json.dump(report, f, indent=2)
    return report


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="HealthBridge Federated Learning — IT-P2")
    parser.add_argument("--data_dir", default=DEFAULT_DATA_DIR, help="Root data directory")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Submission output directory")
    parser.add_argument("--rounds", type=int, default=10, help="Number of federated rounds")
    parser.add_argument("--robustness", action="store_true", help="Also run robustness experiment")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    results = run_federated_training(data_dir, output_dir, args.rounds)
    log.info("Final global accuracy: %.4f", results["global_accuracy"])

    if args.robustness:
        report = run_robustness_experiment(data_dir, output_dir, args.rounds)
        log.info("Robustness accuracy drop: %.4f", report["accuracy_drop"])


if __name__ == "__main__":
    main()
