# GraphFlood — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
Misinformation cascades have distinctive structural signatures before most people even read them: they spread wider and shallower than legitimate news, attract users with low credibility scores early, and show burst-then-plateau temporal patterns instead of slow organic growth. A system that fuses these three signals — graph structure, user credibility, and temporal dynamics — will substantially outperform text-only approaches. Think of your problem as early anomaly detection on an evolving graph, not just text classification.

## Tier 2 — Technique Guidance (-10% score penalty)
Use **GraphSAGE** (or **Graph Attention Network**) for cascade-level classification — it handles inductive settings (new users / new posts not seen during training) and supports mini-batch training on the 500 M-edge graph. For temporal dynamics model the reshare sequence as a **Hawkes process**: misinformation shows a significantly higher branching ratio (each reshare triggers more reshares) than legitimate content. Use a **pretrained sentence-transformer** (e.g., `all-MiniLM-L6-v2`) for sub-10 ms text embeddings. Fuse all features with a lightweight MLP before the final sigmoid output.

## Tier 3 — Implementation Guidance (-15% score penalty)
Follow these steps in order:

1. **Graph construction** — Build a heterogeneous graph where nodes are users and posts, edges are reshare events. Represent it as a `torch_geometric.data.HeteroData` object. Use neighbour sampling (`NeighborLoader`) with K=10 neighbours per hop to keep GPU memory bounded.

2. **Feature engineering** — Per cascade, compute: `depth` (max reshare chain length), `breadth` (unique re-sharers at depth 1), `velocity` (reshares in first 10 min), `avg_follower_count` of re-sharers, `source_credibility` (look up in fact-check DB via TF-IDF similarity to existing claims).

3. **GraphSAGE cascade encoder** — 2-layer GraphSAGE, hidden dim 128, aggregator `mean`. Pool node embeddings to a cascade embedding with `global_mean_pool`.

4. **Temporal module** — Implement `HawkesProcess.fit(reshare_times)` using maximum likelihood; extract `branching_ratio` and `decay_rate` as two scalar features per cascade.

5. **Streaming pipeline** — Use `multiprocessing.Queue` with 4 worker processes for feature extraction. Batch posts into windows of 256 for GNN inference. Measure throughput as `n_posts / elapsed_seconds * 60`.

6. **Threshold calibration** — Set decision threshold by maximising F1 on validation set; do NOT use default 0.5.
