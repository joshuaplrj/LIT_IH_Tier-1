# CYBER-P1: Phantom Protocol — Stealth Exfiltration Detection

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
