# MeshNet — Quick Start

## Objective
Design and simulate a self-organizing mesh network protocol for 10,000 IoT sensors across 500 km² of farmland, demonstrating adaptive routing, energy-efficient data collection, reliable OTA firmware updates, and graceful tolerance of up to 50% node loss.

## Inputs
- `data/topology.json` — Initial node placement: `[{"node_id": 0, "x_m": 0.0, "y_m": 0.0, "battery_j": 100000, "gateway": false}]`
- `data/simulation_config.json` — Sim parameters: `{num_nodes, area_km2, tx_range_m, path_loss_exponent, noise_dbm, gateway_ids, failure_rate, simulation_steps}`
- `data/firmware_payload.bin` — 256 KB binary blob representing a firmware image for OTA testing

## Expected Output
Submission directory `submission/` containing:
- `submission/protocol_spec.md` — Written protocol specification (routing, collection, OTA)
- `submission/simulation_results.json` — Results for 100, 1000, and 10000 node simulations (see schema below)
- `submission/src/` — Simulator source code

`simulation_results.json` schema:
```json
{
  "runs": [
    {
      "num_nodes": 100,
      "data_delivery_rate_pct": 0.0,
      "avg_latency_sec": 0.0,
      "avg_energy_j_per_message": 0.0,
      "network_lifetime_steps": 0,
      "ota_delivery_rate_pct": 0.0
    }
  ]
}
```

## Recommended First Steps
1. Build the radio model first: given two nodes at distance d, compute received signal strength using the log-distance path loss formula (RSSI = Pt - 10*n*log10(d/d0)), then determine if a transmission succeeds based on a SNR threshold.
2. Implement a basic flooding router (broadcast every packet to all neighbours) — this is inefficient but proves end-to-end connectivity before you optimise.
3. Replace flooding with a gradient-based routing tree rooted at gateway nodes: each node stores its "hop distance to nearest gateway" and only forwards to neighbours with a lower hop count.

## Scoring Breakdown
| Metric               | Weight |
|----------------------|--------|
| Protocol correctness | 35%    |
| Efficiency           | 25%    |
| Fault tolerance      | 25%    |
| Documentation        | 15%    |

## Common Pitfalls
- Forgetting energy accounting: every transmission, reception, and idle period must draw from the node's battery_j budget; nodes that run out of energy are dead and stop routing.
- Building a tree that never re-routes: when a node dies, all its downstream children become orphaned — implement a periodic "re-root" where orphaned nodes beacon and re-attach to a live parent.
- OTA stall under packet loss: without acknowledgement and retransmission at the OTA layer, a single lost firmware chunk stops the update indefinitely — implement a sliding window or epidemic dissemination.
