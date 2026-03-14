#!/usr/bin/env python3
"""
CYBER-P1: Phantom Protocol - Stealth Exfiltration Detection
Generates synthetic PCAP file with covert channels embedded.
"""

import os
import struct
import random
import math
import csv
import time

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CYBER-P1")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Utility helpers ────────────────────────────────────────────────────────

def ip_to_bytes(ip_str):
    parts = ip_str.split(".")
    return bytes(int(p) for p in parts)

def build_ethernet_ip_tcp(src_ip, dst_ip, src_port, dst_port, payload_size, seq=1000, ack=0, flags=0x018):
    """Build a minimal Ethernet + IP + TCP frame with random payload."""
    # Ethernet header (14 bytes): dst_mac(6) + src_mac(6) + ethertype(2=0x0800)
    eth = b"\x00\x11\x22\x33\x44\x55" + b"\xaa\xbb\xcc\xdd\xee\xff" + b"\x08\x00"

    # TCP header (20 bytes, no options)
    tcp_data_offset = 5  # 20 bytes / 4 = 5
    tcp_header = struct.pack(
        "!HHIIHHHH",
        src_port,           # source port
        dst_port,           # dest port
        seq,                # seq number
        ack,                # ack number
        (tcp_data_offset << 12) | flags,  # data offset + flags
        65535,              # window size
        0,                  # checksum (skip)
        0,                  # urgent pointer
    )

    # Payload
    payload = bytes(random.randint(0, 255) for _ in range(max(0, payload_size - 54)))

    # IP header (20 bytes)
    total_len = 20 + 20 + len(payload)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,               # version=4, IHL=5
        0,                  # DSCP/ECN
        total_len,
        random.randint(1, 65535),  # ID
        0x4000,             # DF flag, fragment offset=0
        64,                 # TTL
        6,                  # Protocol = TCP
        0,                  # checksum (skip)
        ip_to_bytes(src_ip),
        ip_to_bytes(dst_ip),
    )

    return eth + ip_header + tcp_header + payload

def build_dns_udp_packet(src_ip, dst_ip, domain_len=30):
    """Build a minimal DNS-over-UDP packet."""
    eth = b"\x00\x11\x22\x33\x44\x55" + b"\xaa\xbb\xcc\xdd\xee\xff" + b"\x08\x00"
    # DNS payload
    dns_payload = struct.pack("!HHHHHH", random.randint(1, 65535), 0x0100, 1, 0, 0, 0)
    # Fake question: simple label bytes
    qname = b"\x0f" + b"a" * domain_len + b"\x03com\x00"
    dns_payload += qname + struct.pack("!HH", 1, 1)  # QTYPE=A, QCLASS=IN

    total_dns_len = 8 + len(dns_payload)
    udp_header = struct.pack("!HHHH", 12345, 53, total_dns_len, 0)

    total_ip_len = 20 + total_dns_len
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_ip_len,
        random.randint(1, 65535), 0x4000, 64, 17, 0,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip),
    )
    return eth + ip_header + udp_header + dns_payload

def lognormal_delay_ms(mean_ms=5.0, sigma=1.5):
    """Return a delay sampled from log-normal distribution (in microseconds)."""
    ms = random.lognormvariate(math.log(mean_ms), sigma)
    return max(1, int(ms * 1000))  # microseconds

def encode_message_as_timing(message, base_time_sec, base_time_usec):
    """
    Encode a string as bits using timing channel:
      bit-0 -> 25ms gap, bit-1 -> 75ms gap
    Returns list of (ts_sec, ts_usec) for each bit-packet.
    """
    bits = []
    for ch in message:
        byte_val = ord(ch)
        for b in range(7, -1, -1):
            bits.append((byte_val >> b) & 1)

    timestamps = []
    t_usec = base_time_usec
    t_sec = base_time_sec
    for bit in bits:
        gap_us = 25000 if bit == 0 else 75000
        t_usec += gap_us
        if t_usec >= 1_000_000:
            t_sec += t_usec // 1_000_000
            t_usec = t_usec % 1_000_000
        timestamps.append((t_sec, t_usec, bit))
    return timestamps

def encode_message_as_size(message):
    """
    Encode string as bits using packet size channel:
      bit-0 -> 512 bytes, bit-1 -> 516 bytes
    Returns list of packet_sizes.
    """
    sizes = []
    for ch in message:
        byte_val = ord(ch)
        for b in range(7, -1, -1):
            bit = (byte_val >> b) & 1
            sizes.append(512 if bit == 0 else 516)
    return sizes

# ─── PCAP writer ─────────────────────────────────────────────────────────────

PCAP_GLOBAL_HEADER = struct.pack(
    "<IHHiIII",
    0xa1b2c3d4,   # magic number
    2,             # version major
    4,             # version minor
    0,             # timezone offset
    0,             # timestamp accuracy
    65535,         # snaplen
    1,             # link type = Ethernet
)

def pcap_packet_record(ts_sec, ts_usec, data):
    incl_len = len(data)
    orig_len = incl_len
    header = struct.pack("<IIII", ts_sec, ts_usec, incl_len, orig_len)
    return header + data

# ─── Main generation ──────────────────────────────────────────────────────────

def generate():
    random.seed(42)
    print("[CYBER-P1] Starting PCAP generation (manual binary approach)...")

    # Try scapy
    use_scapy = False
    try:
        import importlib
        scapy_spec = importlib.util.find_spec("scapy")
        if scapy_spec is not None:
            use_scapy = True
            print("[CYBER-P1] scapy found, using scapy approach.")
    except Exception:
        pass

    if not use_scapy:
        print("[CYBER-P1] scapy not available, using manual binary PCAP approach.")
        _generate_manual()
    else:
        _generate_scapy()

def _generate_manual():
    """Generate PCAP manually without scapy."""
    pcap_path = os.path.join(OUTPUT_DIR, "traffic.pcap")
    csv_path = os.path.join(OUTPUT_DIR, "traffic_log.csv")
    gt_path = os.path.join(OUTPUT_DIR, "HIDDEN_ground_truth_labels.csv")
    readme_path = os.path.join(OUTPUT_DIR, "README.md")

    TARGET_PACKETS = 10000
    packets = []  # list of (ts_sec, ts_usec, raw_bytes, meta_dict)

    # ── 1. Normal pool of source IPs
    normal_src_ips = [f"192.168.{random.randint(1,10)}.{random.randint(1,254)}" for _ in range(200)]
    normal_dst_ips_https = [f"104.{random.randint(16,31)}.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(50)]
    doh_resolvers = ["8.8.8.8", "1.1.1.1"]
    suspicious_resolver = "203.0.113.53"

    base_sec = 1700000000  # ~Nov 2023
    current_sec = base_sec
    current_usec = 0

    def advance_time(mean_ms=5.0):
        nonlocal current_sec, current_usec
        delta_us = lognormal_delay_ms(mean_ms, 1.5)
        current_usec += delta_us
        if current_usec >= 1_000_000:
            current_sec += current_usec // 1_000_000
            current_usec = current_usec % 1_000_000
        return current_sec, current_usec

    # ── 2. Covert timing channel packets
    COVERT_IP_SRC = "192.168.1.100"
    COVERT_IP_DST = "10.0.0.50"
    TIMING_MSG = "EXFIL:ACCT_DATA_2024Q4"
    timing_bits_ts = encode_message_as_timing(TIMING_MSG, base_sec + 100, 0)
    timing_packet_indices = []

    # ── 3. Covert size channel packets
    SIZE_SRC_IP = "192.168.1.101"
    SIZE_DST_IP = "10.0.0.50"
    SIZE_MSG = "EXFIL:CREDS_HASH"
    size_sizes = encode_message_as_size(SIZE_MSG)
    size_packet_indices = []

    # Build timing channel packets
    timing_ts_iter = iter(timing_bits_ts)
    timing_done = False

    # We'll interleave: produce packets in time order
    # Generate timing channel packets first, record their index ranges
    flow_id_counter = 1

    # Build all packets
    all_packets = []

    # Step A: generate timing channel packets
    timing_start_idx = 0
    for ts_s, ts_u, bit in timing_bits_ts:
        pkt_size = random.randint(64, 128)
        raw = build_ethernet_ip_tcp(COVERT_IP_SRC, COVERT_IP_DST,
                                    random.randint(49152, 65535), 443,
                                    pkt_size, seq=random.randint(1, 2**31))
        all_packets.append((ts_s, ts_u, raw, {
            "src_ip": COVERT_IP_SRC, "dst_ip": COVERT_IP_DST,
            "dst_port": 443, "packet_size": pkt_size,
            "flow_id": "COVERT_TIMING_001",
        }))
    timing_end_idx = len(all_packets) - 1
    timing_bits_count = len(timing_bits_ts)
    print(f"[CYBER-P1] Timing channel: {timing_bits_count} packets")

    # Step B: generate size channel packets
    size_start_idx = len(all_packets)
    size_ts = base_sec + 500
    size_tu = 0
    for sz in size_sizes:
        size_ts_s, size_ts_u = size_ts, size_tu
        size_tu += lognormal_delay_ms(10, 1.0)
        if size_tu >= 1_000_000:
            size_ts += size_tu // 1_000_000
            size_tu = size_tu % 1_000_000
        raw = build_ethernet_ip_tcp(SIZE_SRC_IP, SIZE_DST_IP,
                                    random.randint(49152, 65535), 443,
                                    sz, seq=random.randint(1, 2**31))
        all_packets.append((size_ts_s, size_ts_u, raw, {
            "src_ip": SIZE_SRC_IP, "dst_ip": SIZE_DST_IP,
            "dst_port": 443, "packet_size": sz,
            "flow_id": "COVERT_SIZE_001",
        }))
    size_end_idx = len(all_packets) - 1
    print(f"[CYBER-P1] Size channel: {len(size_sizes)} packets")

    # Step C: DoH tunneling packets
    doh_start_idx = len(all_packets)
    doh_ts = base_sec + 1000
    doh_tu = 0
    doh_count = int(TARGET_PACKETS * 0.02)
    for _ in range(doh_count):
        doh_tu += lognormal_delay_ms(50, 1.5)
        if doh_tu >= 1_000_000:
            doh_ts += doh_tu // 1_000_000
            doh_tu = doh_tu % 1_000_000
        src_ip = f"192.168.2.{random.randint(1, 254)}"
        domain_len = random.randint(40, 60)
        raw = build_dns_udp_packet(src_ip, suspicious_resolver, domain_len)
        sz = len(raw)
        all_packets.append((doh_ts, doh_tu, raw, {
            "src_ip": src_ip, "dst_ip": suspicious_resolver,
            "dst_port": 53, "packet_size": sz,
            "flow_id": "DOH_TUNNEL_001",
        }))

    # Step D: Normal HTTPS traffic (fill to TARGET_PACKETS)
    normal_target = TARGET_PACKETS - len(all_packets)
    doh_https_count = int(normal_target * 0.10)  # 10% DoH over 443
    normal_https_count = normal_target - doh_https_count

    n_ts = base_sec
    n_tu = 0
    for i in range(normal_https_count):
        n_tu += lognormal_delay_ms(5, 1.5)
        if n_tu >= 1_000_000:
            n_ts += n_tu // 1_000_000
            n_tu = n_tu % 1_000_000
        src_ip = random.choice(normal_src_ips)
        dst_ip = random.choice(normal_dst_ips_https)
        pkt_size = random.randint(100, 1400)
        raw = build_ethernet_ip_tcp(src_ip, dst_ip,
                                    random.randint(49152, 65535), 443,
                                    pkt_size)
        all_packets.append((n_ts, n_tu, raw, {
            "src_ip": src_ip, "dst_ip": dst_ip,
            "dst_port": 443, "packet_size": pkt_size,
            "flow_id": f"NORMAL_{i % 500:04d}",
        }))

    d_ts = base_sec + 200
    d_tu = 0
    for i in range(doh_https_count):
        d_tu += lognormal_delay_ms(8, 1.5)
        if d_tu >= 1_000_000:
            d_ts += d_tu // 1_000_000
            d_tu = d_tu % 1_000_000
        src_ip = f"192.168.3.{random.randint(1,254)}"
        dst_ip = random.choice(doh_resolvers)
        pkt_size = random.randint(100, 400)
        raw = build_ethernet_ip_tcp(src_ip, dst_ip,
                                    random.randint(49152, 65535), 443,
                                    pkt_size)
        all_packets.append((d_ts, d_tu, raw, {
            "src_ip": src_ip, "dst_ip": dst_ip,
            "dst_port": 443, "packet_size": pkt_size,
            "flow_id": f"DOH_HTTPS_{i:04d}",
        }))

    # Sort all packets by timestamp
    all_packets.sort(key=lambda p: (p[0], p[1]))
    print(f"[CYBER-P1] Total packets: {len(all_packets)}")

    # Assign sequential indices
    timing_pkt_start = None
    timing_pkt_end = None
    size_pkt_start = None
    size_pkt_end = None
    for idx, (ts_s, ts_u, raw, meta) in enumerate(all_packets):
        fid = meta["flow_id"]
        if fid == "COVERT_TIMING_001":
            if timing_pkt_start is None:
                timing_pkt_start = idx
            timing_pkt_end = idx
        elif fid == "COVERT_SIZE_001":
            if size_pkt_start is None:
                size_pkt_start = idx
            size_pkt_end = idx

    # Write PCAP
    with open(pcap_path, "wb") as f:
        f.write(PCAP_GLOBAL_HEADER)
        prev_ts = (all_packets[0][0], all_packets[0][1])
        for ts_s, ts_u, raw, meta in all_packets:
            # Cap packet to snaplen
            snap = raw[:65535]
            f.write(pcap_packet_record(ts_s, ts_u, snap))
    print(f"[CYBER-P1] PCAP written: {pcap_path}")

    # Write traffic_log.csv
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "packet_num", "timestamp", "src_ip", "dst_ip",
            "dst_port", "packet_size", "inter_arrival_ms", "flow_id"
        ])
        writer.writeheader()
        prev_ts_us = all_packets[0][0] * 1_000_000 + all_packets[0][1]
        for idx, (ts_s, ts_u, raw, meta) in enumerate(all_packets):
            cur_ts_us = ts_s * 1_000_000 + ts_u
            inter_ms = (cur_ts_us - prev_ts_us) / 1000.0
            prev_ts_us = cur_ts_us
            writer.writerow({
                "packet_num": idx,
                "timestamp": f"{ts_s}.{ts_u:06d}",
                "src_ip": meta["src_ip"],
                "dst_ip": meta["dst_ip"],
                "dst_port": meta["dst_port"],
                "packet_size": meta["packet_size"],
                "inter_arrival_ms": round(inter_ms, 3),
                "flow_id": meta["flow_id"],
            })
    print(f"[CYBER-P1] traffic_log.csv written: {csv_path}")

    # Write HIDDEN ground truth CSV
    with open(gt_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "flow_id", "channel_type", "encoded_message", "start_packet", "end_packet"
        ])
        writer.writeheader()
        writer.writerow({
            "flow_id": "COVERT_TIMING_001",
            "channel_type": "timing",
            "encoded_message": TIMING_MSG,
            "start_packet": timing_pkt_start,
            "end_packet": timing_pkt_end,
        })
        writer.writerow({
            "flow_id": "COVERT_SIZE_001",
            "channel_type": "size",
            "encoded_message": SIZE_MSG,
            "start_packet": size_pkt_start,
            "end_packet": size_pkt_end,
        })
        writer.writerow({
            "flow_id": "DOH_TUNNEL_001",
            "channel_type": "dns_tunnel",
            "encoded_message": "DNS tunneling via 203.0.113.53",
            "start_packet": 0,
            "end_packet": len(all_packets) - 1,
        })
    print(f"[CYBER-P1] HIDDEN_ground_truth_labels.csv written: {gt_path}")

    # Write README
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("""# CYBER-P1: Phantom Protocol — Stealth Exfiltration Detection

## Overview
Participants receive a synthetic 24-hour network capture (`traffic.pcap`) containing
multiple covert exfiltration channels embedded within otherwise-normal HTTPS traffic.

## Objective
Identify and decode all covert data exfiltration channels present in the capture.

## Files
- `traffic.pcap` — Synthetic packet capture (~10,000 packets representing compressed 24h traffic)
- `traffic_log.csv` — CSV metadata log with per-packet fields (timestamp, IPs, ports, sizes, flow_id)
- `HIDDEN_ground_truth_labels.csv` — **Hidden from participants.** Ground truth for scoring.
- `README.md` — This file.

## Background
An adversary has exfiltrated sensitive data using three different covert channels:

1. **Timing Channel** — A specific flow modulates inter-arrival times to encode bits:
   - Bit-0 encodes as a ~25 ms gap between packets
   - Bit-1 encodes as a ~75 ms gap between packets

2. **Size Channel** — Another flow encodes data using packet sizes:
   - 512-byte packets encode bit-0
   - 516-byte packets encode bit-1

3. **DNS Tunneling** — Unusually long DNS queries to a suspicious resolver (`203.0.113.53`)

## Traffic Composition
| Category             | Proportion | Description                              |
|----------------------|------------|------------------------------------------|
| Normal HTTPS         | ~80%       | TCP/443, random IPs, realistic sizes     |
| DNS-over-HTTPS       | ~10%       | TCP/443 to 8.8.8.8, 1.1.1.1             |
| Covert Timing        | ~5%        | 192.168.1.100 → 10.0.0.50, port 443     |
| Covert Size          | ~3%        | 192.168.1.101 → 10.0.0.50, port 443     |
| DoH Tunneling        | ~2%        | UDP/53 to 203.0.113.53, long names       |

## Scoring Criteria
- Identify the two covert-channel source IPs (+20 pts each)
- Correctly decode the timing-channel message (+30 pts)
- Correctly decode the size-channel message (+25 pts)
- Identify the suspicious DNS resolver (+10 pts)
- Provide packet-level evidence for each finding (+15 pts)

## Hints
- Examine inter-arrival times for flows originating from `192.168.1.x` subnet
- Look for bimodal distributions in per-flow packet-size histograms
- Check DNS query name lengths against typical baselines

## Encoding Details (for judge reference)
- Timing channel: ASCII bit-stream, MSB first, 25ms = 0, 75ms = 1
- Size channel: ASCII bit-stream, MSB first, 512B = 0, 516B = 1
""")
    print(f"[CYBER-P1] README.md written: {readme_path}")


def _generate_scapy():
    """Generate PCAP using scapy."""
    from scapy.all import (Ether, IP, TCP, UDP, DNS, DNSQR,
                           wrpcap, RandShort, Packet)
    print("[CYBER-P1] Building packets with scapy...")
    # (Fallback: just call manual if scapy import somehow fails here)
    _generate_manual()


if __name__ == "__main__":
    generate()
    print("[CYBER-P1] Done.")
