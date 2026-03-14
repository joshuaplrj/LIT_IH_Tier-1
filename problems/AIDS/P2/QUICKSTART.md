# GraphFlood — Quick Start

## Objective
Build a real-time misinformation detection system that classifies social media posts as genuine or misinformation within 1 hour of posting (fewer than 100 reshare events). The system must maintain AUC-ROC > 0.85 and process 50,000 posts per minute end-to-end.

## Inputs
- `data/social_graph.edgelist` — Tab-separated `user_id_src  user_id_dst` edges (500 M rows)
- `data/content_stream.jsonl` — One JSON object per line: `{post_id, user_id, text, image_url, timestamp, reshares: [...]}`
- `data/fact_check_db.csv` — Columns: `claim_id, claim_text, verdict (true/false/mixed), source`
- `data/cascades_train.csv` — Columns: `cascade_id, post_id, label (0=legit, 1=misinfo), reshare_sequence`
- `data/cascades_test.csv` — Same format, labels withheld

## Expected Output
- `submission/predictions.csv` — Columns: `post_id, label (0 or 1), score (float 0–1), top_spreaders (semicolon-separated user IDs)`
- `submission/throughput_report.json` — Keys: `posts_per_minute`, `mean_feature_ms`, `mean_inference_ms`

## Recommended First Steps
1. Run `python starter.py --data_dir data --output_dir submission` to confirm end-to-end execution with dummy data.
2. Build and test the GNN on the small `cascades_train.csv` subset before adding the streaming layer.
3. Profile feature extraction latency per post early; text embedding is usually the bottleneck.

## Scoring Breakdown
| Metric                       | Weight |
|------------------------------|--------|
| Detection F1 score           | 40%    |
| Streaming throughput (posts/min) | 25% |
| False positive rate          | 20%    |
| Network graph analysis quality | 15%  |

## Common Pitfalls
- Loading the full 500 M-edge graph into memory at once causes OOM; use neighbour sampling (GraphSAGE mini-batch) rather than full-graph message passing.
- Text-only baselines achieve ~0.65 AUC; you need cascade structure features (depth, breadth, velocity) to cross 0.85.
- Reporting batch throughput instead of per-post latency will make your system appear faster than it is; measure single-post inference.
