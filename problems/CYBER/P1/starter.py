#!/usr/bin/env python3
"""
CYBER-P1: Phantom Protocol — Covert Channel Detector
Hackathon starter skeleton. Fill in all TODO sections.
Usage: python starter.py --pcap traffic.pcap --output submission.json
"""

import argparse
import json
import sys
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# ---------------------------------------------------------------------------
# Dependency imports — install with:
#   pip install scapy pyshark pandas numpy scipy scikit-learn dnslib
# ---------------------------------------------------------------------------
try:
    from scapy.all import PcapReader, IP, IPv6, TCP, UDP, Raw
except ImportError:
    print("[ERROR] scapy not installed. Run: pip install scapy", file=sys.stderr)
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("[ERROR] numpy not installed. Run: pip install numpy", file=sys.stderr)
    sys.exit(1)

try:
    from scipy import stats
except ImportError:
    print("[ERROR] scipy not installed. Run: pip install scipy", file=sys.stderr)
    sys.exit(1)

try:
    from sklearn.ensemble import IsolationForest
except ImportError:
    print("[ERROR] scikit-learn not installed. Run: pip install scikit-learn", file=sys.stderr)
    sys.exit(1)

# dnslib is optional — only needed for DoH channel analysis
try:
    import dnslib
    HAS_DNSLIB = True
except ImportError:
    print("[WARN] dnslib not installed. DoH analysis disabled. Run: pip install dnslib",
          file=sys.stderr)
    HAS_DNSLIB = False

# ---------------------------------------------------------------------------
# Constants matching the problem specification
# ---------------------------------------------------------------------------
TIMING_BIT0_MAX_MS = 50.0        # IAT < 50 ms  => bit 0
TIMING_BIT1_MIN_MS = 50.0        # IAT >= 50 ms => bit 1
SIZE_BIT0_BYTES    = 512         # TLS record length 512 => bit 0
SIZE_BIT1_BYTES    = 516         # TLS record length 516 => bit 1
DOH_RESOLVER_IPS   = {"8.8.8.8", "8.8.4.4", "1.1.1.1", "9.9.9.9"}
DOH_PORT           = 443
ANOMALY_THRESHOLD  = 3.0         # standard deviations for baseline deviation
SEVERITY_CRITICAL_BYTES = 102_400  # > 100 KB => Critical
SEVERITY_MEDIUM_BYTES   = 1_024   # > 1 KB  => Medium


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class FlowRecord:
    """Holds lightweight per-packet metadata for a single TCP/UDP flow."""

    def __init__(self, flow_key: str):
        self.flow_key    = flow_key
        self.timestamps: List[float] = []   # Unix timestamps (seconds)
        self.tls_lengths: List[int]  = []   # TLS record lengths in bytes
        self.is_doh: bool = False


def make_flow_key(pkt) -> Optional[str]:
    """Return a canonical 5-tuple string for a packet, or None if not IP/TCP/UDP."""
    # TODO: extract src_ip, dst_ip, src_port, dst_port, proto from the packet.
    # Return format: "src_ip:src_port->dst_ip:dst_port/proto"
    pass


def extract_tls_record_length(raw_payload: bytes) -> Optional[int]:
    """
    Parse the first TLS record header from raw TCP payload bytes.
    TLS record format: ContentType(1) | Version(2) | Length(2) | Data(Length)
    Return the record length field, or None if the payload is not a TLS record.
    """
    # TODO: validate ContentType (20–23) and Version (0x0301–0x0304),
    #       then unpack the 2-byte big-endian length at offset 3.
    pass


# ---------------------------------------------------------------------------
# Phase 1 — PCAP streaming and flow extraction
# ---------------------------------------------------------------------------

def stream_pcap(pcap_path: str) -> Dict[str, FlowRecord]:
    """
    Stream packets from a large PCAP file and build a dict of FlowRecords.
    Stores only timestamps and TLS record lengths — does NOT buffer raw bytes.
    """
    flows: Dict[str, FlowRecord] = {}
    packet_count = 0

    print(f"[*] Streaming PCAP: {pcap_path}")
    with PcapReader(pcap_path) as reader:
        for pkt in reader:
            packet_count += 1
            if packet_count % 500_000 == 0:
                print(f"    ...{packet_count:,} packets processed, {len(flows):,} flows seen")

            # TODO: call make_flow_key(pkt); skip if None
            # TODO: initialise FlowRecord if new flow key
            # TODO: record pkt.time into flow.timestamps
            # TODO: if pkt has Raw layer, call extract_tls_record_length and append to flow.tls_lengths
            # TODO: mark flow.is_doh if dst IP in DOH_RESOLVER_IPS and dst port == DOH_PORT

    print(f"[*] Finished streaming. Total packets: {packet_count:,}, Total flows: {len(flows):,}")
    return flows


# ---------------------------------------------------------------------------
# Phase 2 — Feature engineering
# ---------------------------------------------------------------------------

def compute_flow_features(flow: FlowRecord) -> Optional[Dict[str, float]]:
    """
    Compute statistical features for anomaly detection.
    Returns None if the flow has too few packets to be meaningful.
    """
    MIN_PACKETS = 10
    if len(flow.timestamps) < MIN_PACKETS:
        return None

    # TODO: compute inter-arrival times (IAT) as np.diff(flow.timestamps) * 1000  [ms]
    # TODO: compute iat_mean, iat_std, iat_bimodality (Hartigan dip statistic or simple std/mean ratio)
    # TODO: compute fraction of TLS records at exactly SIZE_BIT0_BYTES
    # TODO: compute fraction of TLS records at exactly SIZE_BIT1_BYTES
    # TODO: compute Shannon entropy of the TLS record length distribution
    # TODO: return dict of all computed features
    pass


# ---------------------------------------------------------------------------
# Phase 3 — Anomaly detection
# ---------------------------------------------------------------------------

def detect_anomalous_flows(flows: Dict[str, FlowRecord]) -> List[str]:
    """
    Use IsolationForest to identify statistically anomalous flows.
    Returns a list of flow_key strings for suspicious flows.
    """
    feature_matrix = []
    flow_keys_ordered = []

    for key, flow in flows.items():
        feats = compute_flow_features(flow)
        if feats is None:
            continue
        # TODO: append feature vector (as a list of float values) to feature_matrix
        # TODO: append key to flow_keys_ordered

    if not feature_matrix:
        print("[WARN] No flows with sufficient packets for anomaly detection.")
        return []

    # TODO: fit IsolationForest(contamination=0.001, random_state=42) on feature_matrix
    # TODO: call predict() — returns -1 for anomalies, 1 for normal
    # TODO: collect flow_keys_ordered[i] for all predictions == -1
    # TODO: return list of anomalous flow keys
    pass


# ---------------------------------------------------------------------------
# Phase 4 — Covert channel decoding
# ---------------------------------------------------------------------------

def decode_timing_channel(flow: FlowRecord) -> Optional[str]:
    """
    Attempt to decode a bit-stream from inter-packet timing.
    Returns decoded ASCII string or None if decoding fails.
    """
    if len(flow.timestamps) < 8:
        return None

    # TODO: compute IATs in milliseconds
    # TODO: apply threshold: bit = 0 if iat < TIMING_BIT0_MAX_MS else 1
    # TODO: group bits into bytes (8-bit chunks)
    # TODO: convert each byte to a character; filter printable ASCII
    # TODO: if result is >= 50% printable ASCII, return the decoded string; else return None
    pass


def decode_size_channel(flow: FlowRecord) -> Optional[str]:
    """
    Attempt to decode a bit-stream from TLS record size modulation.
    Returns decoded ASCII string or None if decoding fails.
    """
    relevant = [l for l in flow.tls_lengths if l in (SIZE_BIT0_BYTES, SIZE_BIT1_BYTES)]
    if len(relevant) < 8:
        return None

    # TODO: map each length to a bit (512->0, 516->1)
    # TODO: group into bytes and decode ASCII as above
    pass


def decode_doh_channel(flow: FlowRecord, raw_payloads: List[bytes]) -> Optional[str]:
    """
    Extract and decode DoH-tunneled data from DNS query names.
    raw_payloads: list of HTTP/2 DATA frame bodies for this flow.
    Returns decoded string or None.
    """
    if not HAS_DNSLIB or not flow.is_doh:
        return None

    # TODO: for each payload, parse as DNS wire-format using dnslib.DNSRecord.parse()
    # TODO: extract QNAME labels, strip the known domain suffix
    # TODO: concatenate encoded segments; try base32 then base64url decode
    # TODO: return decoded plaintext or None
    pass


def classify_severity(decoded_message: Optional[str], channel_type: str) -> str:
    """Classify exfiltration severity based on decoded message length and content."""
    if decoded_message is None:
        return "Low"

    byte_count = len(decoded_message.encode("utf-8", errors="replace"))

    # TODO: check decoded_message for sensitive patterns using re (SSN, CC, PEM headers)
    # TODO: return "Critical" if sensitive patterns found OR byte_count > SEVERITY_CRITICAL_BYTES
    # TODO: return "Medium" if byte_count > SEVERITY_MEDIUM_BYTES
    # TODO: else return "Low"
    pass


# ---------------------------------------------------------------------------
# Phase 5 — Build submission
# ---------------------------------------------------------------------------

def build_submission(
    anomalous_keys: List[str],
    flows: Dict[str, FlowRecord],
    channel_counter: List[int],
) -> Dict:
    """Construct the submission.json dictionary from detected channels."""
    channels = []
    type_counts = {"timing": 0, "packet_size": 0, "doh_tunneling": 0}

    for key in anomalous_keys:
        flow = flows[key]
        channel_id = f"CC-{len(channels) + 1:03d}"

        # TODO: attempt decode_timing_channel(flow) — if success, channel_type = "timing"
        # TODO: if timing decode fails, attempt decode_size_channel(flow) — channel_type = "packet_size"
        # TODO: if flow.is_doh, attempt decode_doh_channel — channel_type = "doh_tunneling"
        # TODO: determine packet_range as [flow packet index start, end] (track these during streaming)
        # TODO: compute confidence (e.g., fraction of record lengths matching the encoding rule)
        channel_type   = "timing"         # placeholder
        decoded        = None             # placeholder
        packet_range   = [0, 0]           # placeholder
        confidence     = 0.0              # placeholder
        severity       = classify_severity(decoded, channel_type)

        type_counts[channel_type] = type_counts.get(channel_type, 0) + 1
        channels.append({
            "channel_id":      channel_id,
            "type":            channel_type,
            "flow_key":        key,
            "packet_range":    packet_range,
            "decoded_message": decoded or "",
            "severity":        severity,
            "confidence":      round(confidence, 4),
        })

    return {
        "channels": channels,
        "summary": {
            "total_channels":  len(channels),
            "timing_channels": type_counts["timing"],
            "size_channels":   type_counts["packet_size"],
            "doh_channels":    type_counts["doh_tunneling"],
        },
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CYBER-P1 Phantom Protocol — Covert Channel Detector"
    )
    parser.add_argument("--pcap",   required=True,  help="Path to input PCAP file (e.g. traffic.pcap)")
    parser.add_argument("--output", default="submission.json", help="Path for output JSON submission")
    args = parser.parse_args()

    if not os.path.isfile(args.pcap):
        print(f"[ERROR] PCAP file not found: {args.pcap}", file=sys.stderr)
        sys.exit(1)

    # Step 1 — Stream PCAP and build flow records
    flows = stream_pcap(args.pcap)

    # Step 2 — Detect anomalous flows via IsolationForest
    print("[*] Running anomaly detection...")
    anomalous_keys = detect_anomalous_flows(flows)
    print(f"[*] Found {len(anomalous_keys)} anomalous flows.")

    # Step 3 — Decode channels and build submission
    print("[*] Decoding covert channels...")
    submission = build_submission(anomalous_keys, flows, [])

    # Step 4 — Write output
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(submission, f, indent=2)
    print(f"[*] Submission written to: {args.output}")
    print(f"[*] Channels detected: {submission['summary']['total_channels']}")


if __name__ == "__main__":
    main()
