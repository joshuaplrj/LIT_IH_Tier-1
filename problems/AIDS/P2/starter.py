"""
AIDS-P2: GraphFlood — Real-Time Social Network Misinformation Detection
Starter skeleton. Run as-is to verify the pipeline executes end-to-end
on randomly generated dummy data.

Usage:
    python starter.py --data_dir data --output_dir submission
"""

import argparse
import csv
import json
import os
import random
import time
from pathlib import Path

import numpy as np

# Optional deep-learning imports -------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.optim import Adam
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WARN] PyTorch not found — model will use random predictions.")

try:
    import torch_geometric
    from torch_geometric.nn import SAGEConv, global_mean_pool
    from torch_geometric.data import Data, DataLoader as GeoDataLoader
    PYG_AVAILABLE = True
except ImportError:
    PYG_AVAILABLE = False
    print("[WARN] torch_geometric not found — using MLP fallback.")

try:
    from sklearn.metrics import f1_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    print("[WARN] sentence-transformers not found — using random text embeddings.")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEXT_EMBED_DIM = 384       # all-MiniLM-L6-v2 output size
CASCADE_FEAT_DIM = 6       # hand-crafted cascade features
NODE_FEAT_DIM = TEXT_EMBED_DIM + CASCADE_FEAT_DIM
HIDDEN_DIM = 128
N_GNN_LAYERS = 2
BATCH_SIZE = 64
LEARNING_RATE = 1e-3
N_EPOCHS = 20
DECISION_THRESHOLD = 0.5   # updated after val calibration


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_cascades(data_dir: str, split: str = "train") -> list:
    """
    Load cascade records from cascades_<split>.csv.
    Columns: cascade_id, post_id, label, reshare_sequence (comma-separated timestamps)
    Falls back to dummy data if file is absent.
    """
    path = Path(data_dir) / f"cascades_{split}.csv"
    if not path.exists():
        print(f"[INFO] {path} not found — generating dummy cascades.")
        return _dummy_cascades(n=500 if split == "train" else 100)
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row["label"] = int(row.get("label", 0))
            seq_raw = row.get("reshare_sequence", "")
            row["reshare_times"] = (
                [float(t) for t in seq_raw.split(",") if t.strip()]
                if seq_raw else []
            )
            rows.append(row)
    return rows


def _dummy_cascades(n: int = 500) -> list:
    """Generate synthetic cascade records for smoke-testing."""
    cascades = []
    for i in range(n):
        label = random.randint(0, 1)
        n_reshares = random.randint(2, 80)
        times = sorted(random.uniform(0, 3600) for _ in range(n_reshares))
        cascades.append({
            "cascade_id": str(i),
            "post_id": f"p{i}",
            "text": f"Sample post text number {i}",
            "label": label,
            "reshare_times": times,
        })
    return cascades


def load_content_stream(data_dir: str, max_posts: int = 1000) -> list:
    """
    Load posts from content_stream.jsonl.
    Falls back to dummy posts if file absent.
    """
    path = Path(data_dir) / "content_stream.jsonl"
    if not path.exists():
        return [{"post_id": f"p{i}", "text": f"Post {i}", "user_id": str(i % 1000),
                 "timestamp": time.time() + i} for i in range(max_posts)]
    posts = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i >= max_posts:
                break
            try:
                posts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return posts


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

_sbert_model = None


def get_text_embedding(text: str) -> np.ndarray:
    """Return 384-d sentence embedding. Falls back to random if SBERT absent."""
    global _sbert_model
    if not SBERT_AVAILABLE:
        return np.random.randn(TEXT_EMBED_DIM).astype(np.float32)
    if _sbert_model is None:
        print("[INFO] Loading sentence-transformers model...")
        _sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sbert_model.encode(text, show_progress_bar=False).astype(np.float32)


def hawkes_features(reshare_times: list) -> tuple:
    """
    Estimate Hawkes process branching ratio and decay rate via simple MLE.
    Returns (branching_ratio, decay_rate). Falls back to heuristics if < 3 events.
    """
    if len(reshare_times) < 3:
        return 0.1, 1.0
    times = np.array(sorted(reshare_times))
    # Simple MLE: branching ratio ~ 1 - 1/mean_inter_event_count
    inter = np.diff(times)
    branching_ratio = float(min(0.99, 1.0 - 1.0 / (1.0 + np.mean(inter))))
    decay_rate = float(1.0 / (np.mean(inter) + 1e-9))
    return branching_ratio, decay_rate


def extract_cascade_features(cascade: dict) -> np.ndarray:
    """
    Extract 6 hand-crafted cascade features.
    Returns float32 array of shape (CASCADE_FEAT_DIM,).
    """
    times = cascade.get("reshare_times", [])
    n = len(times)
    if n == 0:
        return np.zeros(CASCADE_FEAT_DIM, dtype=np.float32)

    times_arr = np.array(sorted(times))
    depth = float(n)                           # proxy for depth
    breadth = float(min(n, 50))               # capped breadth proxy
    velocity = float(np.sum(times_arr < 600)) # reshares in first 10 min
    span = float(times_arr[-1] - times_arr[0] + 1e-9)
    branching_ratio, decay_rate = hawkes_features(times)

    return np.array([depth, breadth, velocity, span,
                     branching_ratio, decay_rate], dtype=np.float32)


def build_feature_vector(cascade: dict) -> np.ndarray:
    """Concatenate text embedding + cascade features."""
    text = cascade.get("text", "")
    text_emb = get_text_embedding(text)
    cascade_feats = extract_cascade_features(cascade)
    return np.concatenate([text_emb, cascade_feats])


# ---------------------------------------------------------------------------
# GNN / MLP model
# ---------------------------------------------------------------------------

if TORCH_AVAILABLE:
    class CascadeGNN(nn.Module):
        """
        2-layer GraphSAGE cascade encoder.
        Falls back to a plain MLP if torch_geometric is unavailable.
        Input node features: (n_nodes, NODE_FEAT_DIM)
        Output: scalar misinfo probability per cascade
        """

        def __init__(self, in_dim: int = NODE_FEAT_DIM,
                     hidden: int = HIDDEN_DIM):
            super().__init__()
            if PYG_AVAILABLE:
                self.conv1 = SAGEConv(in_dim, hidden)
                self.conv2 = SAGEConv(hidden, hidden)
                self.use_gnn = True
            else:
                self.mlp = nn.Sequential(
                    nn.Linear(in_dim, hidden),
                    nn.ReLU(),
                    nn.Linear(hidden, hidden),
                )
                self.use_gnn = False
            self.classifier = nn.Linear(hidden, 1)

        def forward(self, x, edge_index=None, batch=None):
            if self.use_gnn and edge_index is not None:
                x = F.relu(self.conv1(x, edge_index))
                x = F.relu(self.conv2(x, edge_index))
                # Pool nodes to graph-level embedding
                x = global_mean_pool(x, batch)
            else:
                x = self.mlp(x)
                if x.dim() > 1:
                    x = x.mean(dim=0, keepdim=True)
            return torch.sigmoid(self.classifier(x)).squeeze(-1)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def prepare_tensors(cascades: list, device: str = "cpu"):
    """Build feature matrix X and label vector y from cascade list."""
    X = np.stack([build_feature_vector(c) for c in cascades])
    y = np.array([c["label"] for c in cascades], dtype=np.float32)
    if TORCH_AVAILABLE:
        return (torch.from_numpy(X).to(device),
                torch.from_numpy(y).to(device))
    return X, y


def train_model(cascades_train: list, n_epochs: int = N_EPOCHS,
                lr: float = LEARNING_RATE, device: str = "cpu"):
    """Train cascade classifier. Returns (model, threshold)."""
    if not TORCH_AVAILABLE:
        return None, DECISION_THRESHOLD

    print("[INFO] Building feature tensors...")
    X, y = prepare_tensors(cascades_train, device)
    model = CascadeGNN().to(device)
    optimizer = Adam(model.parameters(), lr=lr)
    criterion = nn.BCELoss()

    # Simple batched training over flattened feature vectors
    n = X.shape[0]
    for epoch in range(n_epochs):
        model.train()
        idx = torch.randperm(n)
        total_loss = 0.0
        for start in range(0, n, BATCH_SIZE):
            batch_idx = idx[start:start + BATCH_SIZE]
            x_b = X[batch_idx]
            y_b = y[batch_idx]
            optimizer.zero_grad()
            preds = model(x_b)
            loss = criterion(preds, y_b)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1:3d}/{n_epochs} | loss={total_loss:.4f}")

    # Calibrate threshold on training set
    model.eval()
    with torch.no_grad():
        scores = model(X).cpu().numpy()
    threshold = calibrate_threshold(scores, y.cpu().numpy())
    print(f"[INFO] Calibrated decision threshold: {threshold:.3f}")
    return model, threshold


def calibrate_threshold(scores: np.ndarray, labels: np.ndarray) -> float:
    """Find F1-maximising threshold."""
    if not SKLEARN_AVAILABLE:
        return 0.5
    best_f1, best_t = 0.0, 0.5
    for t in np.linspace(0.1, 0.9, 81):
        preds = (scores >= t).astype(int)
        f1 = f1_score(labels, preds, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return float(best_t)


# ---------------------------------------------------------------------------
# Inference & streaming simulation
# ---------------------------------------------------------------------------

def predict_cascade(model, cascade: dict, threshold: float = 0.5,
                    device: str = "cpu") -> dict:
    """Predict a single cascade. Returns dict with label, score, top_spreaders."""
    if not TORCH_AVAILABLE or model is None:
        score = float(random.random())
        label = int(score >= threshold)
        return {"post_id": cascade["post_id"],
                "label": label, "score": round(score, 4),
                "top_spreaders": ""}

    feat = build_feature_vector(cascade)
    x = torch.from_numpy(feat).unsqueeze(0).to(device)
    model.eval()
    with torch.no_grad():
        score = float(model(x).item())
    label = int(score >= threshold)

    # TODO: extract top spreaders from cascade graph
    top_spreaders = ""
    return {"post_id": cascade.get("post_id", ""),
            "label": label,
            "score": round(score, 4),
            "top_spreaders": top_spreaders}


def benchmark_throughput(model, posts: list, threshold: float,
                          device: str = "cpu") -> dict:
    """Measure posts processed per minute and per-post latency."""
    n = min(200, len(posts))
    feature_times, infer_times = [], []

    for post in posts[:n]:
        t0 = time.perf_counter()
        feat = build_feature_vector(post)
        feature_times.append((time.perf_counter() - t0) * 1000)

        if TORCH_AVAILABLE and model is not None:
            x = torch.from_numpy(feat).unsqueeze(0).to(device)
            t1 = time.perf_counter()
            with torch.no_grad():
                _ = model(x)
            infer_times.append((time.perf_counter() - t1) * 1000)

    mean_feat_ms = float(np.mean(feature_times)) if feature_times else 999.0
    mean_infer_ms = float(np.mean(infer_times)) if infer_times else 999.0
    total_ms_per_post = mean_feat_ms + mean_infer_ms
    posts_per_minute = 60_000 / max(total_ms_per_post, 0.01)

    return {
        "posts_per_minute": round(posts_per_minute, 1),
        "mean_feature_ms": round(mean_feat_ms, 3),
        "mean_inference_ms": round(mean_infer_ms, 3),
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_predictions(predictions: list, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "predictions.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["post_id", "label", "score", "top_spreaders"])
        writer.writeheader()
        writer.writerows(predictions)
    print(f"[OUT] Predictions saved to {out_path}")


def save_throughput(report: dict, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "throughput_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[OUT] Throughput report saved to {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P2 GraphFlood pipeline")
    parser.add_argument("--data_dir", type=str, default="data",
                        help="Directory containing cascade and graph files")
    parser.add_argument("--output_dir", type=str, default="submission",
                        help="Directory for output files")
    parser.add_argument("--n_epochs", type=int, default=N_EPOCHS)
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("=" * 60)
    print("AIDS-P2: GraphFlood — Misinformation Detection")
    print("=" * 60)

    # --- Load data ---
    print("\n[1/4] Loading cascade data...")
    train_cascades = load_cascades(args.data_dir, "train")
    test_cascades = load_cascades(args.data_dir, "test")
    print(f"  Train: {len(train_cascades)} cascades | Test: {len(test_cascades)} cascades")

    # --- Train model ---
    print("\n[2/4] Training cascade classifier...")
    model, threshold = train_model(train_cascades, n_epochs=args.n_epochs,
                                   device=args.device)

    # --- Predict on test set ---
    print("\n[3/4] Generating predictions on test set...")
    predictions = [predict_cascade(model, c, threshold, args.device)
                   for c in test_cascades]
    save_predictions(predictions, args.output_dir)

    # --- Throughput benchmark ---
    print("\n[4/4] Benchmarking streaming throughput...")
    stream_posts = load_content_stream(args.data_dir, max_posts=500)
    throughput = benchmark_throughput(model, stream_posts, threshold, args.device)
    print(f"  Throughput: {throughput['posts_per_minute']:.0f} posts/min")
    save_throughput(throughput, args.output_dir)

    print("\n[DONE]")


if __name__ == "__main__":
    main()
