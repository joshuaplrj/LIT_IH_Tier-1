"""
IT-P5: MeshNet — Decentralized IoT Fleet Management Simulator Starter Skeleton
===============================================================================
Run:
    python starter.py --data_dir ./data --output_dir ./submission --steps 1000

Requirements:
    pip install numpy scipy networkx tqdm
"""

import argparse
import json
import logging
import math
import os
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import networkx as nx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = "./data"
DEFAULT_OUTPUT_DIR = "./submission"
DEFAULT_STEPS = 1000
DEFAULT_NUM_NODES = 1000
DEFAULT_AREA_KM2 = 500.0

# Radio model parameters
TX_POWER_DBM = 10.0          # Transmit power
PATH_LOSS_EXPONENT = 2.7     # n for open farmland
REF_DISTANCE_M = 1.0         # d0
REF_LOSS_DB = 40.0           # path loss at d0 (free space, ~2.4 GHz)
NOISE_FLOOR_DBM = -100.0
SNR_THRESHOLD_DB = 10.0      # minimum SNR for reliable link

# Energy model (mA at 3.3V)
V_BAT = 3.3
I_TX_MA = 50.0
I_RX_MA = 25.0
I_SLEEP_MA = 0.01
INITIAL_BATTERY_J = 100_000  # ~27.8 Wh

# MAC timing (seconds per step)
T_TX_S = 0.01
T_RX_S = 0.005
T_SLEEP_S = 0.985

# OTA
OTA_CHUNK_BYTES = 128

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SensorNode:
    node_id: int
    x_m: float
    y_m: float
    battery_j: float = INITIAL_BATTERY_J
    is_gateway: bool = False
    is_dead: bool = False
    parent_id: Optional[int] = None
    ofv: float = float("inf")       # Objective Function Value (lower = better route to gateway)
    hop_count: int = 999
    firmware_chunks_received: Set[int] = field(default_factory=set)
    total_firmware_chunks: int = 0
    _tx_count: int = 0
    _rx_count: int = 0

    def energy_cost_tx(self) -> float:
        return (I_TX_MA / 1000) * V_BAT * T_TX_S

    def energy_cost_rx(self) -> float:
        return (I_RX_MA / 1000) * V_BAT * T_RX_S

    def energy_cost_sleep(self) -> float:
        return (I_SLEEP_MA / 1000) * V_BAT * T_SLEEP_S

    def transmit(self, payload_bytes: int) -> bool:
        """Deduct TX energy. Returns False if node is dead or out of energy."""
        if self.is_dead:
            return False
        cost = self.energy_cost_tx()
        if self.battery_j < cost:
            self.is_dead = True
            return False
        self.battery_j -= cost
        self._tx_count += 1
        return True

    def receive(self) -> bool:
        """Deduct RX energy."""
        if self.is_dead:
            return False
        cost = self.energy_cost_rx()
        if self.battery_j < cost:
            self.is_dead = True
            return False
        self.battery_j -= cost
        self._rx_count += 1
        return True

    def sleep_step(self) -> None:
        """Deduct idle sleep energy for one time step."""
        if not self.is_dead:
            cost = self.energy_cost_sleep()
            self.battery_j = max(0.0, self.battery_j - cost)
            if self.battery_j == 0.0:
                self.is_dead = True

    @property
    def firmware_complete(self) -> bool:
        return self.total_firmware_chunks > 0 and len(self.firmware_chunks_received) >= self.total_firmware_chunks


# ---------------------------------------------------------------------------
# Radio model
# ---------------------------------------------------------------------------


def path_loss_db(distance_m: float) -> float:
    """Log-distance path loss in dB."""
    if distance_m <= 0:
        return 0.0
    return REF_LOSS_DB + 10 * PATH_LOSS_EXPONENT * math.log10(max(distance_m, REF_DISTANCE_M) / REF_DISTANCE_M)


def rssi_dbm(distance_m: float) -> float:
    return TX_POWER_DBM - path_loss_db(distance_m)


def link_viable(node_a: SensorNode, node_b: SensorNode) -> bool:
    """Return True if a radio link between two nodes is viable."""
    dist = math.hypot(node_a.x_m - node_b.x_m, node_a.y_m - node_b.y_m)
    snr = rssi_dbm(dist) - NOISE_FLOOR_DBM
    return snr >= SNR_THRESHOLD_DB


def transmission_succeeds(node_a: SensorNode, node_b: SensorNode) -> bool:
    """Probabilistic transmission success based on SNR."""
    dist = math.hypot(node_a.x_m - node_b.x_m, node_a.y_m - node_b.y_m)
    snr = rssi_dbm(dist) - NOISE_FLOOR_DBM
    if snr < 0:
        return False
    # Sigmoid probability curve centred on SNR_THRESHOLD_DB
    prob = 1.0 / (1.0 + math.exp(-(snr - SNR_THRESHOLD_DB)))
    return random.random() < prob


# ---------------------------------------------------------------------------
# Topology builder
# ---------------------------------------------------------------------------


def build_topology(nodes: List[SensorNode]) -> nx.Graph:
    """Build a radio connectivity graph from alive nodes."""
    G = nx.Graph()
    for n in nodes:
        if not n.is_dead:
            G.add_node(n.node_id)
    for i, na in enumerate(nodes):
        if na.is_dead:
            continue
        for nb in nodes[i + 1:]:
            if nb.is_dead:
                continue
            if link_viable(na, nb):
                dist = math.hypot(na.x_m - nb.x_m, na.y_m - nb.y_m)
                # Edge weight = ETX proxy (inverse of link quality)
                etx = max(1.0, SNR_THRESHOLD_DB / max(0.001, rssi_dbm(dist) - NOISE_FLOOR_DBM))
                G.add_edge(na.node_id, nb.node_id, weight=etx, dist_m=dist)
    return G


# ---------------------------------------------------------------------------
# Routing engine
# ---------------------------------------------------------------------------


class RoutingEngine:
    """RPL-inspired gradient routing tree rooted at gateway nodes."""

    def __init__(self, nodes: List[SensorNode]):
        self.nodes: Dict[int, SensorNode] = {n.node_id: n for n in nodes}

    def compute_routing_tree(self) -> None:
        """Build shortest-path tree from every node to nearest gateway using Dijkstra.

        Updates node.parent_id, node.ofv, node.hop_count in place.
        """
        alive_nodes = [n for n in self.nodes.values() if not n.is_dead]
        G = build_topology(alive_nodes)
        gateways = [n.node_id for n in alive_nodes if n.is_gateway]

        if not gateways:
            log.warning("No alive gateway nodes — routing tree cannot be built")
            return

        # Add a virtual super-root connected to all gateways with 0 cost
        SUPER_ROOT = -1
        G.add_node(SUPER_ROOT)
        for gw in gateways:
            G.add_edge(SUPER_ROOT, gw, weight=0.0)

        # Dijkstra from super-root
        try:
            lengths, paths = nx.single_source_dijkstra(G, SUPER_ROOT, weight="weight")
        except nx.NetworkXError as exc:
            log.error("Routing computation failed: %s", exc)
            return

        for node_id, path in paths.items():
            if node_id == SUPER_ROOT:
                continue
            node = self.nodes.get(node_id)
            if node is None or node.is_dead:
                continue
            node.ofv = lengths.get(node_id, float("inf"))
            node.hop_count = len(path) - 2  # subtract super-root and self
            if len(path) >= 3:
                node.parent_id = path[-2]   # immediate parent on path to gateway
            elif node.is_gateway:
                node.parent_id = None
                node.hop_count = 0
                node.ofv = 0.0

    def repair_routes(self, failed_node_ids: Set[int]) -> None:
        """Recompute routing tree after node failures.

        TODO: Implement incremental repair (re-root only subtrees affected by failures)
              for better performance at 10,000 nodes.
        """
        for nid in failed_node_ids:
            node = self.nodes.get(nid)
            if node:
                node.parent_id = None
                node.ofv = float("inf")
                node.hop_count = 999
        # Full recompute (acceptable for hackathon scope)
        self.compute_routing_tree()

    def route_packet(self, src_id: int, payload_bytes: int = 64) -> bool:
        """Attempt to forward one sensor reading from src_id toward its gateway.

        Returns True if the packet is delivered to a gateway.
        TODO: Implement multi-hop store-and-forward with energy deduction per hop.
        """
        current_id = src_id
        visited: Set[int] = set()
        while current_id is not None:
            if current_id in visited:
                return False  # loop detected
            visited.add(current_id)
            node = self.nodes.get(current_id)
            if node is None or node.is_dead:
                return False
            if node.is_gateway:
                return True
            if node.parent_id is None:
                return False
            # Deduct TX energy at current node
            if not node.transmit(payload_bytes):
                return False
            # Deduct RX energy at parent
            parent = self.nodes.get(node.parent_id)
            if parent is None or parent.is_dead or not parent.receive():
                return False
            current_id = node.parent_id
        return False


# ---------------------------------------------------------------------------
# OTA dissemination
# ---------------------------------------------------------------------------


class OTAManager:
    """Epidemic firmware dissemination."""

    def __init__(self, firmware_path: Optional[Path], nodes: Dict[int, SensorNode]):
        self.nodes = nodes
        if firmware_path and firmware_path.exists():
            data = firmware_path.read_bytes()
            self.total_chunks = math.ceil(len(data) / OTA_CHUNK_BYTES)
        else:
            self.total_chunks = 256  # default: 256 * 128B = 32 KB stub

        for n in nodes.values():
            n.total_firmware_chunks = self.total_chunks

        # Seed all gateway nodes with the full firmware
        for n in nodes.values():
            if n.is_gateway:
                n.firmware_chunks_received = set(range(self.total_chunks))

    def dissemination_step(self, G: nx.Graph) -> int:
        """One round of epidemic dissemination. Returns number of new chunk transfers."""
        new_transfers = 0
        # Randomise transmission order to avoid bias
        node_ids = list(self.nodes.keys())
        random.shuffle(node_ids)

        for nid in node_ids:
            sender = self.nodes[nid]
            if sender.is_dead or not sender.firmware_chunks_received:
                continue
            for neighbour_id in G.neighbors(nid):
                receiver = self.nodes.get(neighbour_id)
                if receiver is None or receiver.is_dead:
                    continue
                # Find chunks sender has that receiver does not
                missing = sender.firmware_chunks_received - receiver.firmware_chunks_received
                if not missing:
                    continue
                chunk_id = next(iter(missing))   # send one chunk per step per link
                if not sender.transmit(OTA_CHUNK_BYTES):
                    break
                if receiver.receive():
                    receiver.firmware_chunks_received.add(chunk_id)
                    new_transfers += 1

        return new_transfers

    def delivery_rate(self) -> float:
        """Fraction of alive nodes that have received the full firmware."""
        alive = [n for n in self.nodes.values() if not n.is_dead]
        if not alive:
            return 0.0
        complete = sum(1 for n in alive if n.firmware_complete)
        return complete / len(alive)


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------


class NetworkSimulator:
    """Discrete-time IoT mesh network simulator."""

    def __init__(self, nodes: List[SensorNode], config: Dict, firmware_path: Optional[Path] = None):
        self.nodes = nodes
        self.node_map: Dict[int, SensorNode] = {n.node_id: n for n in nodes}
        self.config = config
        self.failure_rate: float = config.get("failure_rate", 0.0001)
        self.router = RoutingEngine(nodes)
        self.ota = OTAManager(firmware_path, self.node_map)
        self._step = 0
        self._delivered = 0
        self._attempted = 0
        self._total_energy_j = 0.0
        self._latency_sum = 0.0
        self._latency_count = 0

    def step(self) -> None:
        """Advance simulation by one time step."""
        self._step += 1

        # 1. Apply random node failures
        for node in self.nodes:
            if not node.is_dead and random.random() < self.failure_rate:
                node.is_dead = True
                log.debug("Node %d failed at step %d", node.node_id, self._step)

        # 2. Update routing tree every 10 steps (or after failures)
        if self._step % 10 == 0:
            self.router.compute_routing_tree()

        # 3. Each alive, non-gateway node generates one sensor reading and routes it
        G = build_topology(self.nodes)
        for node in self.nodes:
            if node.is_dead or node.is_gateway:
                continue
            node.sleep_step()
            self._attempted += 1
            delivered = self.router.route_packet(node.node_id)
            if delivered:
                self._delivered += 1
                # Estimate latency as hop_count * T_TX_S
                self._latency_sum += node.hop_count * T_TX_S
                self._latency_count += 1

        # 4. OTA dissemination round
        self.ota.dissemination_step(G)

    def run(self, steps: int) -> Dict:
        """Run for `steps` time steps and return metrics."""
        log.info("Running simulation: %d nodes, %d steps", len(self.nodes), steps)
        for _ in range(steps):
            self.step()

        alive_count = sum(1 for n in self.nodes if not n.is_dead)
        total_energy_used = sum(
            INITIAL_BATTERY_J - n.battery_j for n in self.nodes
        )
        avg_energy_per_msg = total_energy_used / max(1, self._delivered)
        delivery_rate = self._delivered / max(1, self._attempted) * 100
        avg_latency = self._latency_sum / max(1, self._latency_count)
        ota_rate = self.ota.delivery_rate() * 100

        # Estimate network lifetime: step at which first gateway becomes unreachable
        # Simplified: report current step as lower bound
        network_lifetime = self._step

        return {
            "num_nodes": len(self.nodes),
            "data_delivery_rate_pct": round(delivery_rate, 2),
            "avg_latency_sec": round(avg_latency, 4),
            "avg_energy_j_per_message": round(avg_energy_per_msg, 6),
            "network_lifetime_steps": network_lifetime,
            "ota_delivery_rate_pct": round(ota_rate, 2),
            "alive_nodes_final": alive_count,
        }


# ---------------------------------------------------------------------------
# Topology generators
# ---------------------------------------------------------------------------


def load_topology(data_dir: Path) -> Optional[List[Dict]]:
    path = data_dir / "topology.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def generate_random_topology(num_nodes: int, area_km2: float, gateway_fraction: float = 0.005) -> List[SensorNode]:
    """Generate a random uniform node placement."""
    side_m = math.sqrt(area_km2 * 1e6)
    num_gateways = max(1, int(num_nodes * gateway_fraction))
    nodes = []
    for i in range(num_nodes):
        nodes.append(SensorNode(
            node_id=i,
            x_m=random.uniform(0, side_m),
            y_m=random.uniform(0, side_m),
            battery_j=INITIAL_BATTERY_J,
            is_gateway=(i < num_gateways),
        ))
    return nodes


def nodes_from_topology(topology: List[Dict]) -> List[SensorNode]:
    nodes = []
    for entry in topology:
        nodes.append(SensorNode(
            node_id=entry["node_id"],
            x_m=entry.get("x_m", 0.0),
            y_m=entry.get("y_m", 0.0),
            battery_j=entry.get("battery_j", INITIAL_BATTERY_J),
            is_gateway=entry.get("gateway", False),
        ))
    return nodes


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def run_benchmarks(data_dir: Path, output_dir: Path, steps: int, config: Dict) -> Dict:
    """Run the simulator for 100, 1000, and 10000 nodes and write results."""
    firmware_path = data_dir / "firmware_payload.bin"
    runs = []

    for num_nodes in [100, 1000, 10_000]:
        log.info("Benchmark: %d nodes", num_nodes)
        nodes = generate_random_topology(
            num_nodes=num_nodes,
            area_km2=config.get("area_km2", DEFAULT_AREA_KM2),
        )
        sim = NetworkSimulator(nodes, config, firmware_path if firmware_path.exists() else None)
        sim.router.compute_routing_tree()
        metrics = sim.run(steps)
        runs.append(metrics)
        log.info("  Delivery rate: %.1f%% | OTA: %.1f%% | Latency: %.3fs",
                 metrics["data_delivery_rate_pct"],
                 metrics["ota_delivery_rate_pct"],
                 metrics["avg_latency_sec"])

    results = {"runs": runs}
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "simulation_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Simulation results written to %s", path)
    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def load_config(data_dir: Path) -> Dict:
    path = data_dir / "simulation_config.json"
    defaults = {
        "num_nodes": DEFAULT_NUM_NODES,
        "area_km2": DEFAULT_AREA_KM2,
        "tx_range_m": 500.0,
        "path_loss_exponent": PATH_LOSS_EXPONENT,
        "noise_dbm": NOISE_FLOOR_DBM,
        "gateway_ids": [],
        "failure_rate": 0.0001,
        "simulation_steps": DEFAULT_STEPS,
    }
    if not path.exists():
        log.warning("simulation_config.json not found — using defaults")
        return defaults
    with open(path) as f:
        return {**defaults, **json.load(f)}


def main() -> None:
    parser = argparse.ArgumentParser(description="MeshNet IoT Fleet Simulator — IT-P5")
    parser.add_argument("--data_dir", default=DEFAULT_DATA_DIR, help="Path to input data directory")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Path to submission output directory")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Simulation time steps per benchmark run")
    parser.add_argument("--benchmark", action="store_true", help="Run full 100/1k/10k node benchmark suite")
    parser.add_argument("--num_nodes", type=int, default=DEFAULT_NUM_NODES, help="Number of nodes for single run")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    config = load_config(data_dir)

    if args.benchmark:
        run_benchmarks(data_dir, output_dir, args.steps, config)
    else:
        # Single run
        topology = load_topology(data_dir)
        if topology:
            nodes = nodes_from_topology(topology)
        else:
            nodes = generate_random_topology(args.num_nodes, config.get("area_km2", DEFAULT_AREA_KM2))

        firmware_path = data_dir / "firmware_payload.bin"
        sim = NetworkSimulator(nodes, config, firmware_path if firmware_path.exists() else None)
        sim.router.compute_routing_tree()
        metrics = sim.run(args.steps)

        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "simulation_results.json"
        with open(path, "w") as f:
            json.dump({"runs": [metrics]}, f, indent=2)
        log.info("Results: %s", metrics)


if __name__ == "__main__":
    main()
