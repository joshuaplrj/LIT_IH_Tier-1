# Phantom Protocol — Quick Start

## Objective
Detect covert exfiltration channels hidden inside encrypted TLS 1.3 traffic by analyzing inter-packet timing, TLS record sizes, and DNS-over-HTTPS query patterns. For every channel found, decode the exfiltrated message and classify its severity.

## Inputs
- `traffic.pcap` — 50 GB PCAP file, approximately 10 million packets, 24 hours of corporate network traffic (TLS 1.3, DoH, mixed protocols)
- `ground_truth.json` — Labeled ground-truth file listing known covert-channel packet ranges and decoded messages (used only by the evaluator)

## Expected Output
Single JSON file named `submission.json` with the following structure:

```json
{
  "channels": [
    {
      "channel_id": "CC-001",
      "type": "timing | packet_size | doh_tunneling",
      "flow_key": "src_ip:src_port->dst_ip:dst_port",
      "packet_range": [first_pkt_no, last_pkt_no],
      "decoded_message": "plaintext string",
      "severity": "Low | Medium | Critical",
      "confidence": 0.0
    }
  ],
  "summary": {
    "total_channels": 0,
    "timing_channels": 0,
    "size_channels": 0,
    "doh_channels": 0
  }
}
```

## Recommended First Steps
1. Stream the PCAP with `pyshark` or `scapy` in chunks; extract per-flow (5-tuple) inter-arrival times and TLS record sizes into a compact DataFrame — do NOT load 50 GB into RAM.
2. Build a baseline distribution (mean, std, IQR) of inter-packet gaps and record sizes per flow using a sliding 1000-packet window; flag flows whose distributions deviate by more than 3σ.
3. For flagged timing flows apply bit-extraction using the 50 ms threshold (gap < 50 ms = bit 0, gap ≥ 50 ms = bit 1) and attempt UTF-8/ASCII decode on bit strings; for size channels use the 512/516-byte rule.

## Scoring Breakdown
| Metric                          | Weight |
|---------------------------------|--------|
| Detection precision / recall    | 50%    |
| Decoded messages (exact match)  | 30%    |
| Severity classification accuracy| 20%    |

## Common Pitfalls
- Loading the entire 50 GB PCAP into memory causes OOM — always stream packet-by-packet or in flow-level chunks.
- Legitimate retransmissions and TCP delayed-ACKs mimic timing channels; filter on TLS Application Data records only before computing inter-arrival times.
- DoH tunneling hides in HTTPS flows to known resolver IPs (e.g., 8.8.8.8:443, 1.1.1.1:443) — restrict your DoH analysis to those destination IPs and inspect DNS wire-format payloads inside the HTTP/2 DATA frames after decoding base64url query parameters.
