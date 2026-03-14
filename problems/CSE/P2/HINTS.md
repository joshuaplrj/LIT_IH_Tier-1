# Byzantine Maze — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

The fundamental challenge is the **FLP impossibility**: no deterministic protocol can guarantee consensus in a fully asynchronous system with even one faulty node. To build a practical protocol, you need to choose one of three escape routes: (a) **randomization** — use coin flips or a verifiable random function so the protocol terminates in expected finite rounds even under adversarial scheduling; (b) **partial synchrony** — assume the network eventually becomes synchronous (messages are delivered within some unknown-but-finite bound GST) and use this to guarantee liveness while keeping safety unconditional; (c) **threshold cryptography** — use cryptographic primitives (e.g., threshold signatures) to make Byzantine equivocation detectable. Your simulation should clearly demonstrate which assumption you are relying on.

## Tier 2 — Technique Guidance (-10% score penalty)

**Recommended base protocol:** PBFT (Practical Byzantine Fault Tolerance) operates under partial synchrony and has well-understood safety/liveness proofs. Its three phases are:
- **Pre-prepare**: Leader broadcasts a proposal `(view, seq, value, signature)`.
- **Prepare**: Each node broadcasts `PREPARE(view, seq, digest)` upon receiving a valid pre-prepare. A node enters the "prepared" state when it has `2f+1` matching PREPARE messages.
- **Commit**: Each node broadcasts `COMMIT(view, seq, digest)` upon entering prepared state. A node **decides** when it has `2f+1` matching COMMIT messages.

**View change**: When a node times out waiting for the leader, it initiates a view change (increment view number, send `VIEW-CHANGE` with proof of last prepared value, new leader collects `2f+1` VIEW-CHANGE messages before taking over).

**For randomization alternative** (simpler to prove liveness): Ben-Or's randomized protocol or the Tendermint protocol with a probabilistic leader election (using a common-coin oracle).

**Simulation structure**: Use Python `threading` or `asyncio` with a message queue per node. Inject delays by `time.sleep(random.uniform(0, 5))` before delivering messages. Inject partitions by marking certain node-pairs as "blocked" for a random duration.

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step-by-step implementation plan:**

1. **Node class** with:
   - `node_id`, `is_byzantine` flag
   - `view`, `seq_num`, `log` (decided values)
   - `message_inbox`: thread-safe queue
   - Methods: `send(target_id, msg)`, `broadcast(msg)`, `run()` (main loop)

2. **Network class** with:
   - `nodes`: dict of node_id → Node
   - `partition_pairs`: set of (i,j) pairs currently partitioned
   - `deliver(src, dst, msg)`: sleeps for random delay, drops if partitioned, then puts in dst's inbox
   - `inject_partition(duration)`: randomly block a subset of node pairs for `duration` seconds

3. **Byzantine node behaviour** (adaptive): override `send()` to either drop messages with some probability, send conflicting values to different subsets of honest nodes (equivocation), or delay responses until a partition ends.

4. **PBFT consensus round**:
   ```
   Leader (node 0 in view 0):
       broadcast PRE-PREPARE(view=0, seq=1, value="X")

   Each honest node on receiving PRE-PREPARE:
       if valid signature and view matches:
           broadcast PREPARE(view, seq, digest(value))

   Each honest node on receiving 2f+1 PREPARE:
       enter PREPARED state
       broadcast COMMIT(view, seq, digest(value))

   Each honest node on receiving 2f+1 COMMIT:
       decide(value)
       log decision
   ```

5. **View-change trigger**: Set a per-node timer. If a node does not see 2f+1 COMMIT within `timeout` seconds, broadcast VIEW-CHANGE and increment view. New leader (node_id = view mod N) collects 2f+1 VIEW-CHANGE messages, then sends NEW-VIEW and restarts from Pre-prepare.

6. **Safety invariant check** (for your evaluation): After all honest nodes decide, assert that all decided values are identical. Log every decision with its value and the round it was decided.

7. **Proof sketch structure**:
   - **Safety lemma**: If two honest nodes decide in the same view, they decide the same value. Proof: by quorum intersection — any two sets of 2f+1 nodes in a system of N = 3f+1 intersect in at least f+1 nodes, at least one of which is honest.
   - **Liveness lemma**: Under partial synchrony (after GST), the view-change mechanism guarantees an honest leader is eventually elected and completes a round.
