# Byzantine Maze — Quick Start

## Objective
Design and implement a Byzantine Fault Tolerant (BFT) consensus protocol for N = 3f+1 nodes that achieves both safety and liveness under asynchronous communication, network partitions, and adaptive adversarial Byzantine nodes. Demonstrate correctness via a working Python simulation with N = 10 nodes.

## Inputs
- No external data files. The simulation generates its own network with:
  - N = 10 nodes (f = 3 Byzantine)
  - Random message delays: 0–5 seconds
  - Network partitions: duration 2–10 seconds, triggered randomly
  - Byzantine nodes: adaptive adversary — can observe all messages and selectively delay/drop/forge their responses

## Expected Output
Three deliverables scored independently:
- `protocol_spec.md` — Pseudocode and message flow diagram (text/ASCII acceptable).
- `simulation.py` — Runnable simulation producing a log showing safety and liveness.
- `proof_sketch.md` — Formal proof sketch of safety and liveness properties.

Simulation must print a structured log per round showing: node ID, decided value (or "undecided"), Byzantine node IDs, and whether consensus was reached.

## Recommended First Steps
1. Read about the FLP impossibility result and why deterministic async consensus is impossible — your protocol must use either randomization, partial synchrony (a timeout-based fallback), or a cryptographic mechanism to circumvent it.
2. Sketch the message phases of your protocol (e.g., propose → vote → commit) before writing code; define exactly which messages an honest node sends and when it decides.
3. Implement the network simulator first (message queue with configurable delays and partition injection), then layer the consensus logic on top.

## Scoring Breakdown
| Metric | Weight (Points) |
|---|---|
| Safety: no two honest nodes decide different values | 30 |
| Liveness: all honest nodes eventually decide | 25 |
| Correctness of simulation (runs without errors, produces valid logs) | 20 |
| Formal proof quality (covers safety + liveness with clear invariants) | 15 |
| Efficiency (message complexity, latency under normal operation) | 10 |

## Common Pitfalls
- Assuming synchronous clocks or bounded message delays — your protocol must not depend on a global timeout that is guaranteed to expire before messages arrive.
- Confusing "safety" and "liveness": safety means two honest nodes never disagree, not that they agree quickly; liveness means they eventually decide, not that they decide fast.
- Byzantine nodes forging 2f+1 signatures is possible unless you use authenticated channels (MACs or digital signatures) — always verify sender identity.
- Forgetting to handle the view-change / leader-rotation path; many protocols deadlock when the leader is Byzantine without a safe view-change mechanism.
- Not logging enough information: the simulation must clearly show which node decided which value and at which round for the judges to verify safety.
