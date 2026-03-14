# Phantom Protocol — Hints

> Each tier costs score points. Only request a hint when you are genuinely stuck.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

The problem lives entirely in the **metadata** of encrypted flows, not the payload. Think about what observable properties remain after encryption: the *time* at which packets arrive, the *size* of each TLS record, and the *destination* of DNS queries. A covert channel encodes information by deliberately perturbing one of these properties according to a secret rule. Your job is to find flows where those properties look statistically unusual compared to how normal TLS traffic behaves, then reverse-engineer the encoding rule to read the hidden message.

---

## Tier 2 — Technique Guidance (-10% score penalty)

- **Timing channels**: Use **Kolmogorov-Smirnov (KS) test** or **Jensen-Shannon divergence** to compare the inter-packet delay distribution of each flow against a reference distribution of benign TLS flows. Flows with abnormally bimodal gap distributions (two distinct clusters around 25 ms and 75 ms) are candidates. Once flagged, apply a **threshold classifier** at 50 ms to extract the bit stream.
- **Packet-size channels**: Compute the distribution of TLS record lengths per flow. Malicious flows will show an unnatural spike at exactly 512 and 516 bytes. Use a **chi-squared goodness-of-fit** test against an expected normal-traffic size histogram.
- **DoH tunneling**: Filter flows to known DoH resolver IPs. Extract the `dns` query name field from HTTP/2 DATA frames (the DoH wire format is `application/dns-message`). Look for Base32/Base64-encoded subdomains in query names — these carry the tunneled payload. Use **Shannon entropy** of subdomain labels as a quick pre-filter (entropy > 3.5 bits/char is suspicious).

---

## Tier 3 — Implementation Guidance (-15% score penalty)

1. **Efficient PCAP streaming**: Use `pyshark.FileCapture` with `display_filter="tls"` and `keep_packets=False`, or use `scapy`'s `PcapReader` iterator. Group packets by 5-tuple flow key; store only `(timestamp, tls_record_length)` per packet — this fits in RAM for 10 M packets.
2. **Per-flow feature extraction**: For each flow compute: median IAT, IAT standard deviation, fraction of records at exactly 512 bytes, fraction at exactly 516 bytes, entropy of record-length histogram.
3. **Anomaly scoring pipeline**: Train a `sklearn.ensemble.IsolationForest` on features from the first 20% of traffic (assumed benign baseline). Score all flows; use contamination ≈ 0.001 (1 in 1000 flows is malicious).
4. **Bit extraction**: For timing channels, sort packets by arrival time, compute consecutive IAT, apply `bit = 0 if iat < 0.050 else 1`, concatenate bits, split into 8-bit groups, decode as ASCII. For size channels apply `bit = 0 if len == 512 else 1`.
5. **DoH payload extraction**: Parse the `dns-message` binary from the HTTP/2 body using Python's `dnslib` library. Extract all `QNAME` labels, concatenate encoded segments, base32-decode to recover the exfiltrated data.
6. **Severity classification**: Low = < 1 KB decoded, Medium = 1–100 KB, Critical = > 100 KB or any decoded message containing regex matches for patterns like SSNs, credit-card numbers, or private keys.
