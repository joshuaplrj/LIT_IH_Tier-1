"""
Byzantine Maze — Starter Skeleton
CSE Problem 2: BFT Consensus Protocol Simulation

Usage:
    python starter.py --nodes 10 --faults 3 --rounds 5 --timeout 15 --log consensus_log.json
"""

import argparse
import hashlib
import json
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(threadName)s] %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message Types
# ---------------------------------------------------------------------------

class MsgType(str, Enum):
    PRE_PREPARE  = "PRE_PREPARE"
    PREPARE      = "PREPARE"
    COMMIT       = "COMMIT"
    VIEW_CHANGE  = "VIEW_CHANGE"
    NEW_VIEW     = "NEW_VIEW"


@dataclass
class Message:
    msg_type:  MsgType
    sender_id: int
    view:      int
    seq:       int
    value:     Optional[str] = None
    digest:    Optional[str] = None
    extra:     Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type":   self.msg_type.value,
            "from":   self.sender_id,
            "view":   self.view,
            "seq":    self.seq,
            "value":  self.value,
            "digest": self.digest,
        }


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Network Simulator
# ---------------------------------------------------------------------------

class Network:
    """
    Simulates an asynchronous network with configurable delays and partitions.
    """

    def __init__(self, min_delay: float = 0.0, max_delay: float = 0.5):
        self.nodes: Dict[int, "Node"] = {}
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._partition_lock = threading.Lock()
        self._partitioned_pairs: Set[Tuple[int, int]] = set()

    def register(self, node: "Node"):
        self.nodes[node.node_id] = node

    def deliver(self, src_id: int, dst_id: int, msg: Message):
        """Deliver a message with simulated delay; drop if partitioned."""
        pair = (min(src_id, dst_id), max(src_id, dst_id))
        with self._partition_lock:
            if pair in self._partitioned_pairs:
                log.debug(f"PARTITION DROP: {src_id} -> {dst_id}  {msg.msg_type.value}")
                return

        def _delayed():
            delay = random.uniform(self.min_delay, self.max_delay)
            time.sleep(delay)
            if dst_id in self.nodes:
                self.nodes[dst_id].inbox.put(msg)

        t = threading.Thread(target=_delayed, daemon=True)
        t.start()

    def broadcast(self, src_id: int, msg: Message):
        for dst_id in self.nodes:
            if dst_id != src_id:
                self.deliver(src_id, dst_id, msg)

    def inject_partition(self, duration: float, num_pairs: int = 2):
        """Randomly block some node pairs for `duration` seconds."""
        node_ids = list(self.nodes.keys())
        pairs = []
        for _ in range(num_pairs):
            a, b = random.sample(node_ids, 2)
            pair = (min(a, b), max(a, b))
            pairs.append(pair)

        with self._partition_lock:
            self._partitioned_pairs.update(pairs)
        log.info(f"PARTITION injected: {pairs} for {duration:.1f}s")

        def _heal():
            time.sleep(duration)
            with self._partition_lock:
                for p in pairs:
                    self._partitioned_pairs.discard(p)
            log.info(f"PARTITION healed: {pairs}")

        threading.Thread(target=_heal, daemon=True).start()


# ---------------------------------------------------------------------------
# Node Implementation
# ---------------------------------------------------------------------------

class Node:
    """
    Honest PBFT node skeleton.
    Override or extend byzantine_act() to implement Byzantine behaviour.
    """

    def __init__(self, node_id: int, n_total: int, f: int,
                 network: Network, is_byzantine: bool = False,
                 proposal_value: str = "CONSENSUS_VALUE"):
        self.node_id       = node_id
        self.n             = n_total
        self.f             = f
        self.network       = network
        self.is_byzantine  = is_byzantine
        self.proposal      = proposal_value

        self.inbox: Queue[Message] = Queue()

        # Protocol state
        self.view          = 0
        self.seq           = 1
        self.decided_value: Optional[str] = None
        self.decided_round: Optional[int] = None

        # Message stores: keyed by (view, seq)
        self.prepare_msgs: Dict[Tuple[int,int], List[Message]] = {}
        self.commit_msgs:  Dict[Tuple[int,int], List[Message]] = {}
        self.view_change_msgs: Dict[int, List[Message]] = {}

        self._prepared  = False
        self._committed = False
        self._stop      = threading.Event()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def quorum(self) -> int:
        return 2 * self.f + 1

    def leader(self, view: int = None) -> int:
        v = view if view is not None else self.view
        return v % self.n

    def _log(self, msg: str):
        tag = "[BYZ]" if self.is_byzantine else "[HON]"
        log.info(f"Node {self.node_id:2d} {tag}  {msg}")

    # ------------------------------------------------------------------
    # Send / Broadcast wrappers
    # ------------------------------------------------------------------

    def send(self, dst_id: int, msg: Message):
        if self.is_byzantine:
            self.byzantine_act(dst_id, msg)
        else:
            self.network.deliver(self.node_id, dst_id, msg)

    def broadcast(self, msg: Message):
        for dst_id in self.network.nodes:
            if dst_id != self.node_id:
                self.send(dst_id, msg)

    # ------------------------------------------------------------------
    # Byzantine Behaviour  (TODO: implement adversarial strategy)
    # ------------------------------------------------------------------

    def byzantine_act(self, dst_id: int, msg: Message):
        """
        Default: drop messages with 50% probability, else deliver normally.

        TODO: Implement adaptive adversary logic:
        - Equivocate: send different values to different subsets of nodes.
        - Delay: hold messages until partition heals to maximise disruption.
        - Selectively target: cause view-changes to specific honest nodes.
        """
        if random.random() < 0.5:
            return   # drop
        self.network.deliver(self.node_id, dst_id, msg)

    # ------------------------------------------------------------------
    # PBFT Protocol Steps
    # ------------------------------------------------------------------

    def phase_pre_prepare(self):
        """Leader broadcasts PRE-PREPARE."""
        if self.leader() != self.node_id:
            return
        msg = Message(
            msg_type=MsgType.PRE_PREPARE,
            sender_id=self.node_id,
            view=self.view,
            seq=self.seq,
            value=self.proposal,
            digest=digest(self.proposal),
        )
        self._log(f"Broadcasting PRE-PREPARE view={self.view} seq={self.seq} val={self.proposal}")
        self.broadcast(msg)

    def on_pre_prepare(self, msg: Message):
        """
        Handle PRE-PREPARE: validate and broadcast PREPARE.
        TODO: Add signature verification.
        """
        if msg.sender_id != self.leader(msg.view):
            self._log(f"Ignoring PRE-PREPARE from non-leader {msg.sender_id}")
            return
        if msg.view != self.view or msg.seq != self.seq:
            return
        if msg.digest != digest(msg.value):
            self._log("Digest mismatch in PRE-PREPARE — ignoring.")
            return

        self._log(f"Received valid PRE-PREPARE, broadcasting PREPARE for '{msg.value}'")
        prepare = Message(
            msg_type=MsgType.PREPARE,
            sender_id=self.node_id,
            view=self.view,
            seq=self.seq,
            digest=msg.digest,
        )
        self.broadcast(prepare)
        # Also count own prepare
        self._collect_prepare(prepare)

    def on_prepare(self, msg: Message):
        if msg.view != self.view or msg.seq != self.seq:
            return
        self._collect_prepare(msg)

    def _collect_prepare(self, msg: Message):
        key = (msg.view, msg.seq)
        self.prepare_msgs.setdefault(key, [])
        # Deduplicate by sender
        if any(m.sender_id == msg.sender_id for m in self.prepare_msgs[key]):
            return
        self.prepare_msgs[key].append(msg)

        if len(self.prepare_msgs[key]) >= self.quorum() and not self._prepared:
            self._prepared = True
            self._log(f"PREPARED (quorum={self.quorum()}) — broadcasting COMMIT")
            commit = Message(
                msg_type=MsgType.COMMIT,
                sender_id=self.node_id,
                view=self.view,
                seq=self.seq,
                digest=msg.digest,
            )
            self.broadcast(commit)
            self._collect_commit(commit)

    def on_commit(self, msg: Message):
        if msg.view != self.view or msg.seq != self.seq:
            return
        self._collect_commit(msg)

    def _collect_commit(self, msg: Message):
        key = (msg.view, msg.seq)
        self.commit_msgs.setdefault(key, [])
        if any(m.sender_id == msg.sender_id for m in self.commit_msgs[key]):
            return
        self.commit_msgs[key].append(msg)

        if len(self.commit_msgs[key]) >= self.quorum() and not self._committed:
            self._committed = True
            # Recover value from prepare messages
            prep = self.prepare_msgs.get(key, [])
            # Find the value whose digest matches
            decided = msg.digest   # fallback: store digest only
            self._log(f"*** DECIDED digest={decided} ***")
            self.decided_value = decided
            self.decided_round = self.view

    # ------------------------------------------------------------------
    # View Change  (TODO: implement full view-change logic)
    # ------------------------------------------------------------------

    def trigger_view_change(self):
        """Broadcast VIEW-CHANGE to move to view+1."""
        self.view += 1
        self._prepared = False
        self._committed = False
        self._log(f"Triggering VIEW-CHANGE to view={self.view}")
        vc = Message(
            msg_type=MsgType.VIEW_CHANGE,
            sender_id=self.node_id,
            view=self.view,
            seq=self.seq,
        )
        self.broadcast(vc)

    def on_view_change(self, msg: Message):
        """
        TODO: Collect 2f+1 VIEW-CHANGE messages and send NEW-VIEW if new leader.
        """
        self.view_change_msgs.setdefault(msg.view, [])
        if any(m.sender_id == msg.sender_id for m in self.view_change_msgs[msg.view]):
            return
        self.view_change_msgs[msg.view].append(msg)

        if (len(self.view_change_msgs[msg.view]) >= self.quorum()
                and self.leader(msg.view) == self.node_id):
            self._log(f"New leader for view={msg.view} — sending NEW-VIEW")
            self.view = msg.view
            nv = Message(
                msg_type=MsgType.NEW_VIEW,
                sender_id=self.node_id,
                view=self.view,
                seq=self.seq,
            )
            self.broadcast(nv)
            # Re-run pre-prepare as new leader
            self.phase_pre_prepare()

    def on_new_view(self, msg: Message):
        """TODO: Validate NEW-VIEW and reset state for new view."""
        if msg.view > self.view:
            self.view = msg.view
            self._prepared = False
            self._committed = False

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    def run(self, timeout_secs: float = 10.0):
        """Message processing loop with timeout-based view-change."""
        deadline = time.time() + timeout_secs
        while not self._stop.is_set() and self.decided_value is None:
            try:
                remaining = deadline - time.time()
                if remaining <= 0:
                    if not self._committed:
                        self.trigger_view_change()
                    deadline = time.time() + timeout_secs
                    continue

                msg = self.inbox.get(timeout=min(remaining, 0.5))
                handler = {
                    MsgType.PRE_PREPARE: self.on_pre_prepare,
                    MsgType.PREPARE:     self.on_prepare,
                    MsgType.COMMIT:      self.on_commit,
                    MsgType.VIEW_CHANGE: self.on_view_change,
                    MsgType.NEW_VIEW:    self.on_new_view,
                }.get(msg.msg_type)

                if handler and not self.is_byzantine:
                    handler(msg)

            except Empty:
                pass

        self._log(f"Node halted. Decided: {self.decided_value}")

    def stop(self):
        self._stop.set()


# ---------------------------------------------------------------------------
# Simulation Runner
# ---------------------------------------------------------------------------

def run_simulation(n_nodes: int, f: int, rounds: int,
                   node_timeout: float, log_path: str):
    network = Network(min_delay=0.0, max_delay=0.5)

    byzantine_ids = random.sample(range(n_nodes), f)
    log.info(f"Byzantine nodes: {byzantine_ids}")

    nodes = []
    for i in range(n_nodes):
        is_byz = (i in byzantine_ids)
        node = Node(node_id=i, n_total=n_nodes, f=f,
                    network=network, is_byzantine=is_byz)
        network.register(node)
        nodes.append(node)

    # Start all node threads
    threads = []
    for node in nodes:
        t = threading.Thread(target=node.run,
                             args=(node_timeout,),
                             name=f"Node-{node.node_id}",
                             daemon=True)
        threads.append(t)
        t.start()

    # Leader kicks off the protocol
    nodes[0].phase_pre_prepare()

    # Inject a partition mid-way
    time.sleep(node_timeout * 0.3)
    partition_duration = random.uniform(2, min(5, node_timeout * 0.5))
    network.inject_partition(duration=partition_duration, num_pairs=2)

    # Wait for all threads to finish or global timeout
    for t in threads:
        t.join(timeout=node_timeout + 5)

    # Collect results
    decisions = {
        n.node_id: n.decided_value
        for n in nodes
        if not n.is_byzantine
    }

    log.info(f"=== DECISIONS ===  {decisions}")

    # Safety check: all honest nodes must agree (or be undecided)
    decided_values = set(v for v in decisions.values() if v is not None)
    safety_ok = (len(decided_values) <= 1)
    liveness_ok = all(v is not None for v in decisions.values())

    log.info(f"Safety OK:   {safety_ok}")
    log.info(f"Liveness OK: {liveness_ok}")

    result = {
        "n_nodes":       n_nodes,
        "f":             f,
        "byzantine_ids": byzantine_ids,
        "decisions":     decisions,
        "safety_ok":     safety_ok,
        "liveness_ok":   liveness_ok,
    }

    with open(log_path, "w") as fp:
        json.dump(result, fp, indent=2)
    log.info(f"Simulation log written to: {log_path}")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Byzantine Maze: BFT consensus simulation."
    )
    parser.add_argument("--nodes",   type=int,   default=10,
                        help="Total number of nodes N (should be 3f+1).")
    parser.add_argument("--faults",  type=int,   default=3,
                        help="Number of Byzantine faults f.")
    parser.add_argument("--rounds",  type=int,   default=1,
                        help="Number of consensus rounds to simulate.")
    parser.add_argument("--timeout", type=float, default=15.0,
                        help="Per-node message processing timeout (seconds).")
    parser.add_argument("--log",     type=str,   default="consensus_log.json",
                        help="Output path for the simulation JSON log.")
    args = parser.parse_args()

    if args.nodes < 3 * args.faults + 1:
        print(f"WARNING: N={args.nodes} < 3f+1={3*args.faults+1}. "
              f"BFT guarantees require N >= 3f+1.")

    result = run_simulation(
        n_nodes=args.nodes,
        f=args.faults,
        rounds=args.rounds,
        node_timeout=args.timeout,
        log_path=args.log,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
