# 🏗️ Grand Engineering Problem Statement Challenge
### ⏱️ Solve Time: 3 Hours per Problem Set

---

## 📘 DISCIPLINE 1: COMPUTER SCIENCE & ENGINEERING (CSE)

---

### **CSE-Problem 1: "ChronoReconstruct" — Degradation Timeline Recovery Engine**

#### 🧩 Problem Statement

A predictive maintenance company collects **high-frequency vibration recordings** from industrial turbines across 12 months. Due to a catastrophic database corruption event, the filenames of **N = 500 data files** (each representing a single time-window snapshot of vibration data) have been randomly permuted. The true chronological ordering is lost. Your task is to reconstruct the original timeline.

You are provided with:
- `signals/` — 500 `.csv` files, each containing a 1D vibration signal of varying length (10,000–100,000 samples at 25,600 Hz).
- `tachometer/` — 500 corresponding `.csv` files with tachometer (RPM) signals.

**Task:** Design and implement an algorithm that outputs a **permutation array** `P` of length 500 such that `signals/P[0], signals/P[1], ..., signals/P[499]` represents the recovered chronological order.

**Scoring:**
| Metric | Weight |
|---|---|
| Kendall's Tau (τ) against ground truth | 60% |
| Monotonicity of extracted health indicators | 20% |
| Computational efficiency (< 10 minutes) | 10% |
| Novelty of approach (documented) | 10% |

**Constraints:**
- No external pretrained models allowed.
- Must work offline — no internet access during evaluation.
- Output format: a single `solution.csv` with one column: `file_index`.

#### 💡 Expected Novelty
This combines **signal processing**, **time-series analysis**, and **combinatorial optimization**. With 500! possible orderings, brute force is impossible. Solvers must discover latent degradation features that evolve monotonically or quasi-monotonically over time.

---

### **CSE-Problem 2: "Byzantine Maze" — Distributed Consensus Under Adversarial Conditions**

#### 🧩 Problem Statement

You are building a **Byzantine Fault Tolerant (BFT) consensus protocol** for a peer-to-peer network of **N = 3f + 1 nodes**, where up to **f nodes can be Byzantine** (arbitrarily malicious). Unlike classical PBFT, your network has the following real-world constraints:

1. **Asynchronous communication**: Messages have variable, unbounded delays (but are eventually delivered).
2. **Partitions**: The network can undergo temporary partitions where groups of nodes are isolated for unpredictable durations.
3. **Adaptive adversaries**: Byzantine nodes can observe all messages and strategically delay their own responses to maximize disruption.

**Task:** Design and implement a consensus protocol that:
- Achieves **safety** (no two honest nodes decide on different values) and **liveness** (all honest nodes eventually decide) under the above conditions.
- Handles up to **f = ⌊(N-1)/3⌋** Byzantine faults.
- Tolerates **network partitions** of up to T seconds without violating safety.

**Deliverables:**
- Protocol specification (pseudocode + message flow diagram).
- Working simulation in Python/C++/Go with **N = 10 nodes**, simulating random delays (0–5s), partitions (duration 2–10s), and adaptive Byzantine behavior.
- Formal proof sketch of safety and liveness.

**Evaluation:**
| Criterion | Points |
|---|---|
| Safety under all adversarial conditions | 30 |
| Liveness (eventual termination) | 25 |
| Correctness of simulation | 20 |
| Formal proof quality | 15 |
| Efficiency (latency, message complexity) | 10 |

#### 💡 Expected Novelty
The FLP impossibility result states that deterministic consensus in fully asynchronous systems is impossible with even one fault. Solvers must navigate the boundary between theory and practice — perhaps using **randomization**, **partial synchrony assumptions**, or **cryptographic sortition** to circumvent this fundamental limitation.

---

### **CSE-Problem 3: "Infinite Chess Grandmaster" — Solving Generalized Chess with AI**

#### 🧩 Problem Statement

Standard chess is played on an 8×8 board. In this challenge, you must build an AI agent that plays **Generalized Chess** on an **N×N board** (where N can be 8, 10, 12, or 16), with modified rules:

- Standard pieces (King, Queen, Rook, Bishop, Knight, Pawn) with standard movement rules.
- **Bombs**: Three "bomb" squares are randomly placed on the board. Any piece landing on a bomb is eliminated (both the piece and the bomb).
- **Teleporters**: Two pairs of teleporter squares exist. A piece stepping on one teleports to the other.
- **Time dilation**: Every 10 moves, the "temporal phase" shifts — the player whose turn it is gets **2 consecutive moves** instead of 1 (for that round only).

**Task:** Implement an AI agent that:
- Evaluates positions on N×N boards with bombs and teleporters.
- Implements alpha-beta pruning with **iterative deepening** and a **transposition table**.
- Handles the time-dilation rule in its search tree.

**Constraints:**
- Must make each move within **5 seconds**.
- Will be tested on boards of sizes 8, 10, 12, 16.
- Must beat a baseline minimax (depth 3) agent in **≥80% of games** on 8×8.

**Deliverables:**
- Source code with clear architecture.
- Evaluation function design document (explain features and weights).
- Tournament results on at least 50 games per board size.

#### 💡 Expected Novelty
The branching factor explodes with board size. The teleporter and bomb mechanics invalidate standard chess heuristics (piece-square tables, endgame tablebases). The time-dilation rule creates **asymmetric move sequences** that break traditional alternating-move game tree assumptions.

---

### **CSE-Problem 4: "Self-Healing Compiler" — Bug Detection and Auto-Patching**

#### 🧩 Problem Statement

You are given a compiler frontend for a **custom toy language** called **MiniRust** (a simplified Rust-like language with ownership, borrowing, and lifetimes). The compiler has **15 hidden bugs** in its type-checker and code-generation phases. These bugs cause:
- Incorrect type inference (5 bugs).
- Wrong memory deallocation / use-after-free in generated code (5 bugs).
- Deadlock in the compiler's parallel compilation pipeline (5 bugs).

**Task:** Build an **automated tool** that:
1. **Detects** all 15 bugs by generating adversarial MiniRust programs (fuzzing / property-based testing).
2. **Localizes** each bug to the specific file and function.
3. **Generates patches** (diff format) that fix each bug without breaking existing correct behavior.

**Deliverables:**
- Fuzzer / test generator for MiniRust (generate at least 10,000 programs).
- Bug detection report: For each bug, provide the triggering input, the expected vs. actual behavior, and localization.
- Patch files for all 15 bugs.
- Proof of correctness: After patching, the compiler passes the provided **regression test suite** of 200 valid MiniRust programs.

**Scoring:**
| Criterion | Points |
|---|---|
| Number of bugs detected (out of 15) | 40 |
| Localization accuracy | 20 |
| Correctness of patches | 25 |
| Quality of fuzzer / coverage | 15 |

#### 💡 Expected Novelty
This combines **compiler theory**, **automated testing**, **program analysis**, and **program repair**. The ownership/borrowing system in MiniRust makes fuzzing non-trivial — randomly generated programs will overwhelmingly fail to parse or type-check, so the fuzzer must be guided by the language's type system.

---

### **CSE-Problem 5: "Quantum-Safe Encrypted Database" — Encrypted Query Processing**

#### 🧩 Problem Statement

Design and implement a **database system** that stores encrypted records and supports **SQL-like queries on encrypted data** without ever decrypting the data on the server side. The system must be **quantum-resistant** (no RSA, ECC, or traditional DH).

**Requirements:**
1. **Encryption**: Use a post-quantum encryption scheme (e.g., lattice-based, code-based, or hash-based).
2. **Queries supported**:
   - `SELECT * FROM T WHERE column = encrypted_value` (equality search)
   - `SELECT * FROM T WHERE column > encrypted_value` (range query)
   - `SELECT COUNT(*) FROM T WHERE condition` (aggregation)
3. **Security model**: The server is **honest-but-curious** — it follows the protocol but tries to learn as much as possible from the encrypted data and query patterns.
4. **Performance**: For a table of **100,000 records** with 5 columns, a point query must complete in **< 2 seconds**.

**Deliverables:**
- System architecture document.
- Working implementation (Python/C++/Java).
- Security analysis: What information can the server learn? How does your system mitigate access pattern leakage?
- Performance benchmarks.

#### 💡 Expected Novelty
Fully homomorphic encryption (FHE) supports arbitrary computation but is extremely slow. Solvers must find the right trade-off between **functionality**, **security**, and **performance** — perhaps using **Searchable Symmetric Encryption (SSE)** combined with **lattice-based** primitives for quantum resistance.

---
---

## 🔒 DISCIPLINE 2: COMPUTER SCIENCE & ENGINEERING — CYBERSECURITY

---

### **CYBER-Problem 1: "Phantom Protocol" — Stealth Exfiltration Detection in Encrypted Traffic**

#### 🧩 Problem Statement

A corporate network uses **TLS 1.3** for all external communications. An advanced persistent threat (APT) group has implanted malware that exfiltrates sensitive data by encoding it within **encrypted TLS traffic patterns** — without modifying the encrypted payload itself. The malware uses:

- **Inter-packet timing covert channels**: Data bits encoded in the micro-delays between TLS packets (jitter of 0–50ms for bit-0, 50–100ms for bit-1).
- **Packet size covert channels**: Manipulating TLS record sizes (padding) to encode data (512 bytes = bit-0, 516 bytes = bit-1).
- **DNS-over-HTTPS (DoH) tunneling**: Embedding data in DNS queries sent over HTTPS to attacker-controlled resolvers.

**Task:**
Given a **PCAP file** of 24 hours of network traffic (≈50 GB, ~10 million packets):
1. Build a detection system that identifies **covert exfiltration channels** in encrypted traffic.
2. For each detected channel, **decode the exfiltrated message**.
3. Classify the **severity** of each exfiltration event (Low / Medium / Critical) based on estimated data volume and sensitivity.

**Constraints:**
- You cannot decrypt TLS (no private keys available).
- Must distinguish covert channels from legitimate timing/size variations.
- Must process the full 24-hour trace in **< 30 minutes**.

**Deliverables:**
- Detection system source code.
- Decoded messages from all covert channels found.
- Precision/Recall analysis against provided ground truth labels.
- Writeup on detection methodology and evasion countermeasures.

#### 💡 Expected Novelty
Steganographic channels in encrypted traffic are extremely subtle. The solver must build **statistical models** of normal traffic behavior, detect anomalies in timing and size distributions, and then reconstruct hidden messages — all without decryption. The background noise in real network traffic makes this a needle-in-a-haystack problem.

---

### **CYBER-Problem 2: "Rootkit Genesis" — Building and Detecting Kernel-Level Persistence**

#### 🧩 Problem Statement

*Note: This is a controlled lab exercise. All work must be done on the provided isolated VM.*

**Part A — Offense (40%):**
Design a **kernel-level rootkit** for the provided Linux 6.x VM that:
1. Hides specific processes from `ps`, `top`, `/proc`.
2. Intercepts and modifies filesystem read operations to hide its own files.
3. Establishes a **reverse shell** that reconnects every 60 seconds if disconnected.
4. Survives a **system reboot** via a modified init script or bootloader hook.
5. Uses **at least 2 anti-forensics techniques** (e.g., log deletion, timestomping, memory-only execution).

**Part B — Defense (60%):**
Without knowing the specifics of your own rootkit (swap with another team), analyze the provided compromised VM and:
1. Detect all hidden processes and files.
2. Identify the persistence mechanism.
3. Trace the network callback to its C2 destination.
4. Extract the rootkit's configuration (target processes, hidden files, C2 address).
5. Produce a **timeline** of the compromise (initial infection → persistence → C2 establishment).

**Deliverables for Part A:** Source code, build instructions, deployment script.
**Deliverables for Part B:** Forensic report, detection scripts, IOCs (Indicators of Compromise).

#### 💡 Expected Novelty
This tests both offensive and defensive capabilities. Building a kernel rootkit requires deep understanding of Linux internals (syscall tables, VFS, netfilter). Detecting it without prior knowledge requires methodical forensic analysis using memory forensics (Volatility), disk forensics, and network analysis.

---

### **CYBER-Problem 3: "CryptoPuzzle" — Breaking a Custom Cryptographic Protocol**

#### 🧩 Problem Statement

A startup claims to have created a novel encryption protocol called **FalconShield**. You are given:

1. The protocol specification (15-page PDF).
2. A reference implementation in Python.
3. **100 ciphertexts** (each encrypting a 256-byte message) along with their corresponding public keys.
4. **10 plaintext-ciphertext pairs** (known-plaintext oracle).
5. Access to an **encryption oracle** (you can encrypt any message of your choice, limited to 100 queries).

The protocol uses a hybrid approach:
- **Key exchange**: Based on a custom variant of the Learning With Errors (LWE) problem with parameters (n=256, q=3329, σ=2.0).
- **Symmetric encryption**: A custom block cipher with 12 rounds, 128-bit key, 256-bit block size.
- **MAC**: HMAC-SHA256.

**Tasks:**
1. **Cryptanalyze** the protocol — find at least one vulnerability.
2. **Decrypt** at least 1 of the 100 provided ciphertexts (recover the full 256-byte plaintext).
3. If you can break the key exchange, recover the shared secret for at least one key pair.
4. Provide a **security assessment report** rating each component (Key Exchange, Encryption, MAC) and recommending fixes.

**Scoring:**
| Criterion | Points |
|---|---|
| Vulnerability identification | 30 |
| Number of ciphertexts decrypted | 40 |
| Quality of security assessment | 20 |
| Proposed fixes | 10 |

#### 💡 Expected Novelty
Custom cryptographic protocols almost always have subtle flaws. The LWE parameters might be too weak (small n, low noise). The custom block cipher might have differential or linear characteristics. The solver must combine **theoretical cryptanalysis** with **practical exploitation**.

---

### **CYBER-Problem 4: "Supply Chain Sentinel" — Software Supply Chain Attack Detection**

#### 🧩 Problem Statement

You are the security team for a company that uses **npm**, **PyPI**, and **Docker Hub** extensively. You are provided with:

1. A **dependency graph** (JSON) of 500 packages used across 50 internal microservices.
2. **Source code snapshots** of the 50 microservices.
3. A **SBOM** (Software Bill of Materials) for each service.
4. Anomalies have been reported: unexpected network connections, high CPU usage, and data access from 3 services.

**Tasks:**
1. **Scan** all 500 dependencies for known vulnerabilities (CVEs), typosquatting, and malicious patterns.
2. Identify **supply chain attacks** — packages that were compromised (e.g., injected malware, dependency confusion, account takeover).
3. For each compromised package, determine:
   - The **attack vector** (typosquatting, maintainer account compromise, dependency confusion, etc.).
   - The **payload** (what the malicious code does — data exfiltration, cryptomining, backdoor, etc.).
   - The **blast radius** — which services are affected.
4. Generate a **remediation plan** prioritized by risk.

**Deliverables:**
- Detection tool (source code + results).
- Compromise report for each affected package.
- Blast radius analysis.
- Remediation plan (patched versions, alternative packages, architectural changes).

#### 💡 Expected Novelty
Modern software supply chains are deeply nested — a single compromised transitive dependency can affect hundreds of services. Solvers must combine **static analysis**, **dynamic analysis** (sandboxing), **behavioral detection**, and **graph analysis** of the dependency tree to find the needle in the haystack.

---

### **CYBER-Problem 5: "Zero-Day Factory" — Automated Vulnerability Discovery in Binary Code**

#### 🧩 Problem Statement

You are given **5 compiled binary executables** (ELF format, x86-64, no source code, no debug symbols) that are networked services listening on various ports. Each binary contains **at least 2 memory corruption vulnerabilities** (buffer overflow, use-after-free, format string, integer overflow, or heap overflow).

**Task:** Build an **automated vulnerability discovery pipeline** that:
1. Performs **binary analysis** (disassembly, control flow graph reconstruction, data flow analysis).
2. Generates **test inputs** (fuzzing, symbolic execution, or a combination).
3. **Triggers crashes** and classifies each crash by vulnerability type.
4. Produces a **proof-of-concept exploit** for at least 1 vulnerability per binary (demonstrating controlled EIP/RIP hijack or arbitrary read/write).

**Constraints:**
- Must run in a Linux environment with standard tools (no commercial tools like IDA Pro — use Ghidra/Binary Ninja/Rizin).
- Must not cause denial-of-service to the evaluation environment.
- PoC exploits must work on the provided binary without ASLR (ASLR disabled for testing).

**Deliverables:**
- Pipeline source code and architecture document.
- Vulnerability report for each binary (type, location, severity, exploitability).
- Working PoC exploits (at least 5 total, at least 1 per binary).
- Performance metrics (paths explored, crashes found, time taken).

#### 💡 Expected Novelty
Without source code, vulnerability discovery in binaries is exponentially harder than source-level analysis. Solvers must combine **symbolic execution** (which suffers from path explosion), **coverage-guided fuzzing** (which struggles with complex input formats), and **manual reverse engineering** to find vulnerabilities within the time limit.

---
---

## 💻 DISCIPLINE 3: INFORMATION TECHNOLOGY (IT)

---

### **IT-Problem 1: "SmartCity Digital Twin" — Real-Time Urban Simulation Platform**

#### 🧩 Problem Statement

A city government wants a **real-time digital twin** of their downtown area (5 km × 5 km) to optimize traffic, energy consumption, and emergency response. You are given:

- **Geospatial data**: Road network (OpenStreetMap format), building footprints, elevation data.
- **Real-time feeds** (simulated): Traffic sensors (1000 sensors, updated every 30s), weather data (every 5 min), power grid data (every 1 min), emergency call locations (real-time).
- **Historical data**: 1 year of traffic patterns, energy usage, and incident logs.

**Task:** Build a web-based platform that:
1. **Ingests** and processes all real-time data streams (handle up to 10,000 events/second).
2. Renders a **3D visualization** of the city with real-time overlays (traffic density heatmap, energy consumption, active incidents).
3. Provides **predictive analytics**:
   - Traffic congestion prediction 30 minutes ahead.
   - Energy demand prediction 1 hour ahead.
   - Emergency response time estimation for any location.
4. Allows **what-if scenario simulation**: "What happens if we close Road X?" or "What if we add a new fire station at location Y?"

**Tech constraints:**
- Backend: Any modern stack (Node.js, Python, Go, Java).
- Frontend: Must work in a browser (WebGL for 3D).
- Database: Time-series DB for sensor data, graph DB for road network.
- Must handle **concurrent users** (at least 50 simultaneous viewers).

**Deliverables:**
- Deployed application (Docker containers).
- Architecture document.
- Performance benchmarks under load.
- Demo video (5 min).

#### 💡 Expected Novelty
This is a full-stack challenge combining **real-time data engineering**, **3D visualization**, **predictive ML**, and **distributed systems**. The scale (10,000 events/sec, 1000 sensors, 3D rendering) demands careful architectural decisions about stream processing, caching, and client-server communication.

---

### **IT-Problem 2: "HealthBridge" — Federated Learning for Multi-Hospital Diagnostics**

#### 🧩 Problem Statement

Five hospitals want to collaboratively train a **chest X-ray diagnosis model** (detecting pneumonia, COVID-19, tuberculosis, and lung cancer) **without sharing patient data** (HIPAA compliance).

Each hospital has:
- A local dataset of **5,000–20,000 chest X-rays** (varying sizes, different imaging equipment, different labeling standards).
- A local GPU server (NVIDIA RTX 4090 or equivalent).
- An unreliable internet connection (can drop for up to 30 minutes).

**Task:** Implement a **federated learning system** that:
1. Trains a shared CNN model across all 5 hospitals using **Federated Averaging (FedAvg)** or a superior algorithm.
2. Handles **non-IID data** (different hospitals see different disease distributions).
3. Handles **stragglers** (one hospital might be 10x slower due to hardware differences).
4. Provides **differential privacy guarantees** (ε ≤ 3.0).
5. Includes a **secure aggregation protocol** so the central server never sees individual hospital updates.

**Deliverables:**
- Federated learning framework (server + client code).
- Training results: convergence curve, final model accuracy per hospital and overall.
- Privacy analysis: demonstrate ε-budget tracking across rounds.
- Robustness analysis: What happens when 1 hospital has poisoned data?
- Comparison with centralized training (the theoretical upper bound).

#### 💡 Expected Novelty
Federated learning with non-IID data, stragglers, differential privacy, and secure aggregation is a research-level challenge. The solver must balance **model accuracy**, **privacy guarantees**, **communication efficiency**, and **robustness to adversarial participants** — all simultaneously.

---

### **IT-Problem 3: "EventHorizon" — Serverless Event-Driven Architecture for E-Commerce**

#### 🧩 Problem Statement

Design and implement a **serverless event-driven backend** for a flash-sale e-commerce platform that must handle **1 million concurrent users** during a 10-minute flash sale of 1,000 limited-quantity items.

**Requirements:**
1. **Architecture**: Fully serverless (AWS Lambda / GCP Cloud Functions / Azure Functions / self-hosted equivalent like OpenFaaS).
2. **Event flow**: User clicks "Buy" → Order Service → Inventory Check → Payment Processing → Fulfillment → Notifications.
3. **Guarantees**:
   - **Exactly-once** inventory deduction (no overselling).
   - **Eventual consistency** for order status (max 5-second lag).
   - **Dead letter queues** for failed events with automatic retry (3 retries with exponential backoff).
4. **Observability**: Distributed tracing (OpenTelemetry), real-time metrics dashboard, alerting.
5. **Cost model**: Estimate the cost for handling 1 million users × 5 events each = 5 million events.

**Deliverables:**
- Architecture diagram (C4 model).
- Infrastructure-as-Code (Terraform / Pulumi / CloudFormation).
- Source code for all functions/services.
- Load test results (using k6, Locust, or Gatling) showing:
  - Throughput (events/sec).
  - P50, P95, P99 latencies.
  - Error rate under load.
  - Zero overselling guarantee.
- Cost estimate.

#### 💡 Expected Novelty
Serverless architectures introduce unique challenges: **cold starts**, **event ordering**, **idempotency**, and **distributed transactions**. Preventing overselling of 1,000 items among 1 million users requires careful use of **optimistic locking**, **conditional writes**, or **distributed locks** — all while maintaining sub-second response times.

---

### **IT-Problem 4: "AccessibilityAI" — Automated WCAG 2.2 Compliance Auditor**

#### 🧩 Problem Statement

Build an **AI-powered web accessibility auditing tool** that automatically scans websites for compliance with **WCAG 2.2** (Web Content Accessibility Guidelines) Level AA.

**The tool must:**
1. **Crawl** a given website (up to 10,000 pages) and build a site map.
2. For each page, check for **all 50 WCAG 2.2 Level AA success criteria** using:
   - **Static analysis** (HTML/CSS parsing).
   - **Dynamic analysis** (rendered page analysis via headless browser).
   - **Visual analysis** (screenshot-based ML model to detect contrast issues, text in images, layout problems).
   - **Screen reader simulation** (simulate how a screen reader would interpret the page).
3. Generate a **compliance report** with:
   - Overall compliance score (0–100%).
   - Per-criterion pass/fail.
   - Specific violations with **location** (element selector), **severity**, and **suggested fix**.
4. Generate **auto-fix patches** (HTML/CSS modifications) for at least 30% of detected issues.

**Constraints:**
- Must process a 1000-page website in **< 60 minutes**.
- Must handle JavaScript-rendered SPAs (React, Angular, Vue).
- False positive rate must be **< 10%**.

**Deliverables:**
- Tool source code.
- Architecture and methodology document.
- Results on 5 provided test websites (ground truth available).
- Precision/Recall per WCAG criterion.

#### 💡 Expected Novelty
WCAG compliance checking requires a blend of **DOM analysis**, **computer vision**, **NLP** (for alt-text quality assessment), and **accessibility tree** analysis. Many criteria are inherently subjective (e.g., "meaningful sequence"), making automated assessment extremely challenging.

---

### **IT-Problem 5: "MeshNet" — Decentralized IoT Fleet Management Protocol**

#### 🧩 Problem Statement

An agricultural company deploys **10,000 IoT sensors** across 500 km² of farmland. These sensors must form a **self-organizing mesh network** because:
- Cellular coverage is unreliable.
- Sensors have limited battery (must last 2 years on a single charge).
- The network topology changes (sensors fail, new sensors are added, crops grow and block signals).

**Task:** Design and implement the firmware (simulated) and management protocol for this mesh network:

1. **Routing protocol**: Design a routing protocol that:
   - Adapts to topology changes within 60 seconds.
   - Minimizes energy consumption (favor short hops, let heavily-used nodes rest).
   - Handles up to 50% node loss gracefully.
2. **Data collection**: Sensor data must reach a gateway within **5 minutes** of generation. Design a collection protocol (e.g., trickle, epidemic, structured).
3. **Over-the-Air (OTA) updates**: Design a mechanism to push firmware updates to all 10,000 sensors reliably, even with intermittent connectivity.
4. **Simulation**: Implement a **network simulator** that models:
   - Radio propagation (log-distance path loss model).
   - Battery drain (transmit, receive, sleep modes).
   - Node failures (random, correlated by region).
   - Gateway connectivity (intermittent).

**Deliverables:**
- Protocol specification.
- Simulator source code.
- Simulation results for networks of 100, 1,000, and 10,000 nodes.
- Performance metrics: data delivery rate, latency, energy consumption, network lifetime.

#### 💡 Expected Novelty
At 10,000 nodes with constrained energy and unreliable links, every design choice matters. The solver must make hard trade-offs between **reliability**, **latency**, **energy efficiency**, and **scalability** — and validate them through simulation at scale.

---
---

## ⚡ DISCIPLINE 4: ELECTRICAL & ELECTRONICS ENGINEERING (EEE)

---

### **EEE-Problem 1: "GridBrain" — AI-Optimized Microgrid Energy Management**

#### 🧩 Problem Statement

A remote island community operates an **off-grid microgrid** with the following components:
- **Solar PV**: 500 kW peak capacity.
- **Wind turbines**: 2 × 250 kW (variable output).
- **Battery storage**: 2 MWh lithium-ion (SOC range: 10%–90%, degradation rate: 0.01%/cycle).
- **Diesel generator**: 300 kW (backup only, fuel cost: $1.50/liter, 0.25 L/kWh).
- **Community load**: Variable demand, peak 800 kW, average 400 kW.

You are provided with:
- **1 year of hourly data**: Solar irradiance, wind speed, temperature, load demand.
- **Equipment specifications**: Efficiency curves, degradation models, constraints.

**Task:** Design an **optimal energy management system** that:
1. **Minimizes total cost** over a 20-year horizon (fuel, battery replacement, maintenance).
2. **Ensures reliability**: No more than 10 hours of load shedding per year.
3. **Extends battery life**: Minimize degradation by optimizing charge/discharge cycles.
4. **Adapts in real-time**: Given weather forecasts (24-hour ahead), adjust the schedule hourly.

**Approach requirements:**
- Formulate as an **optimization problem** (MILP, dynamic programming, or RL).
- Implement a working solution.
- Compare against a baseline (rule-based: use renewables first, battery second, diesel last).

**Deliverables:**
- Mathematical formulation of the optimization problem.
- Source code / model implementation.
- 20-year simulation results: total cost, reliability metrics, battery degradation.
- Sensitivity analysis: How does the solution change if fuel price doubles? If solar capacity increases by 50%?

#### 💡 Expected Novelty
This is a **multi-objective, multi-timescale optimization** problem with stochastic inputs (weather, load). The 20-year horizon with battery degradation creates a **non-convex** problem. Solvers must balance immediate fuel savings against long-term battery health — a classic **exploitation-exploration** trade-off.

---

### **EEE-Problem 2: "FaultSense" — Real-Time Power Grid Fault Classification and Localization**

#### 🧩 Problem Statement

You are given **3-phase voltage and current waveforms** sampled at **20 kHz** from **20 buses** of a IEEE 39-bus power system. The system experiences various fault types:

| Fault Type | Description |
|---|---|
| Single Line-to-Ground (SLG) | One phase faults to ground |
| Line-to-Line (LL) | Two phases short together |
| Double Line-to-Ground (DLG) | Two phases short to ground |
| Three-Phase (LLL) | All three phases short together |
| High-Impedance Fault (HIF) | Fault through high impedance (tree contact) — extremely hard to detect |

Faults can occur on any line, at any location (0%–100% of line length from bus A), with varying fault resistances (0.1Ω – 100Ω).

**Task:** Design and implement a system that:
1. **Detects** a fault within **1 cycle** (16.67 ms at 60 Hz) of inception.
2. **Classifies** the fault type with **>95% accuracy**.
3. **Locates** the fault to within **±500 meters** on the line.
4. Handles **HIF detection** with **>90% sensitivity** and **<5% false positive rate**.
5. Works in the presence of **CT saturation**, **noise**, and **transient conditions** (capacitor switching, motor starting).

**Deliverables:**
- Detection/classification/localization algorithm (source code).
- Performance on provided test dataset (5,000 fault scenarios).
- Confusion matrix for classification.
- Error distribution for localization.
- Processing time per sample (must be < 1 ms for real-time).

#### 💡 Expected Novelty
High-impedance faults draw very little current and look similar to normal load changes — they are the "holy grail" of power system protection. Solvers must combine **signal processing** (wavelets, DFT), **pattern recognition**, and possibly **deep learning** to achieve high accuracy across all fault types while meeting the stringent real-time constraint.

---

### **EEE-Problem 3: "MotorForge" — Design and Simulation of a 10 kW BLDC Motor**

#### 🧩 Problem Statement

Design a **10 kW brushless DC (BLDC) motor** for an electric scooter application with the following requirements:
- **Rated power**: 10 kW at 4000 RPM.
- **Peak torque**: 40 Nm (from 0–2000 RPM).
- **Efficiency**: >92% at rated conditions.
- **Voltage**: 72V DC bus.
- **Cooling**: Air-cooled (no liquid cooling).
- **Size constraint**: Outer diameter ≤ 200 mm, axial length ≤ 150 mm.
- **Weight**: ≤ 12 kg.

**Task:**
1. **Electromagnetic design**: Determine the number of poles/slots, winding configuration, magnet grade and dimensions, air gap length, stator/rotor geometry.
2. **Magnetic circuit analysis**: Calculate flux densities, back-EMF, torque constant, inductance.
3. **Loss estimation**: Copper losses, iron losses (hysteresis + eddy current), magnet eddy current losses, mechanical losses.
4. **Thermal analysis**: Estimate temperatures at rated and peak conditions. Verify air-cooling is sufficient.
5. **Controller design**: Design a **FOC (Field-Oriented Control)** algorithm with current/torque/speed loops.
6. **Simulation**: Implement a simulation model (MATLAB/Simulink, Python, or FEA) showing:
   - Torque-speed curve.
   - Efficiency map.
   - Thermal performance over a typical drive cycle.

**Deliverables:**
- Design document with all calculations.
- Motor parameters table.
- Simulation model and results.
- Performance verification against all requirements.

#### 💡 Expected Novelty
This requires deep knowledge of **electromagnetic theory**, **machine design**, **thermal management**, and **control systems**. The weight and size constraints make the design extremely tight — every mm and every gram counts. The solver must optimize across multiple competing objectives simultaneously.

---

### **EEE-Problem 4: "PowerShield" — Solid-State Circuit Breaker for DC Microgrids**

#### 🧩 Problem Statement

Traditional mechanical circuit breakers are too slow (10–100 ms) for DC microgrids, where fault currents can reach **10× rated current in < 1 ms** due to the absence of natural current zero-crossing.

**Task:** Design a **solid-state circuit breaker (SSCB)** for a 400V DC microgrid with:
- **Rated current**: 200A continuous.
- **Breaking capacity**: 10 kA at 400V DC.
- **Breaking time**: < 100 μs from fault detection to current interruption.
- **Bidirectional**: Must interrupt faults in both directions.
- **Voltage clamping**: Limit transient overvoltage to < 600V.
- **Repetitive operation**: Must handle 10,000 switching cycles.

**Design and analyze:**
1. **Power semiconductor selection**: SiC MOSFET vs IGBT vs hybrid — justify choice.
2. **Topology**: Series-connected switches, modular multilevel, or other?
3. **Snubber / clamping circuit**: Design the voltage clamping network (MOV, RC snubber, active clamp).
4. **Gate driver design**: Ultra-fast gate driver (< 1 μs turn-off).
5. **Fault detection**: Current monitoring and fault classification (overcurrent, short circuit, ground fault).
6. **Thermal design**: Heat sink requirements for continuous and fault conditions.
7. **Simulation**: Simulate the SSCB interrupting a 10 kA fault in LTSpice, PLECS, or MATLAB/Simscape.

**Deliverables:**
- Complete schematic (with component values).
- Design calculations.
- Simulation waveforms (fault interruption sequence).
- Loss analysis and thermal analysis.
- BOM (Bill of Materials) with estimated cost.

#### 💡 Expected Novelty
DC fault interruption is fundamentally harder than AC because there's no natural current zero. The solver must design a complete system from semiconductor selection to thermal management, all while meeting extremely tight timing constraints (< 100 μs) and handling enormous fault energies.

---

### **EEE-Problem 5: "E-Harvest" — High-Efficiency RF Energy Harvesting System**

#### 🧩 Problem Statement

Design an **RF energy harvesting system** that captures ambient RF energy (from WiFi, cellular, TV signals) in the **900 MHz – 2.4 GHz band** and converts it to usable DC power for a low-power IoT sensor (requires 100 μW at 1.8V).

**Constraints:**
- **Antenna**: Must fit within 50 mm × 50 mm PCB area.
- **Available RF power density**: -20 dBm to -10 dBm across the band (urban environment).
- **Efficiency target**: >40% RF-to-DC at -10 dBm input.
- **Output regulation**: Must provide stable 1.8V ± 5% over the input power range.
- **Must operate without batteries** (capacitor-buffered only).

**Design:**
1. **Antenna design**: Wideband or multiband? Patch, dipole, or fractal? Provide antenna gain, radiation pattern, and S11.
2. **Matching network**: Design an impedance matching network between the antenna and rectifier for maximum power transfer across the band.
3. **Rectifier circuit**: Select topology (single-series, single-shunt, voltage doubler, Dickson multiplier). Optimize for low input power.
4. **Voltage regulation**: Design a low-quiescent-current regulator or MPPT circuit.
5. **Energy buffer**: Size the storage capacitor for worst-case duty cycle.
6. **Simulation**: Simulate in ADS, HFSS, or LTSpice — show:
   - Rectenna efficiency vs. input power and frequency.
   - Output voltage vs. input power.
   - Start-up behavior from empty capacitor.

**Deliverables:**
- Antenna design (geometry, simulation results).
- Complete circuit schematic with component values.
- Simulation results.
- Efficiency analysis.
- PCB layout suggestion (2-layer, 50mm × 50mm).

#### 💡 Expected Novelty
At -20 dBm (10 μW) input power, every fraction of dB of loss matters. Rectifier efficiency drops dramatically at low input power. The solver must optimize the entire chain — antenna, matching network, rectifier, and regulator — as a **coupled system**, which requires understanding electromagnetics, nonlinear circuit design, and power electronics simultaneously.

---
---

## 📡 DISCIPLINE 5: ELECTRONICS & COMMUNICATION ENGINEERING (ECE)

---

### **ECE-Problem 1: "RadarForge" — Design of an FMCW Radar System for Drone Detection**

#### 🧩 Problem Statement

Design a **Frequency Modulated Continuous Wave (FMCW) radar** system capable of detecting small drones (RCS ≈ 0.01 m²) at ranges up to **500 meters**.

**System requirements:**
- **Operating frequency**: 24 GHz (ISM band, unlicensed).
- **Range resolution**: ≤ 1 m.
- **Velocity resolution**: ≤ 0.5 m/s.
- **Angular resolution**: ≤ 5° in azimuth.
- **Detection probability**: ≥ 90% at 500 m for Pfa = 10⁻⁶.
- **Update rate**: ≥ 10 Hz (100 ms per scan).

**Task:**
1. **System-level design**:
   - Calculate required bandwidth, chirp duration, number of chirps per frame.
   - Determine transmit power needed (link budget analysis).
   - Select antenna configuration (number of TX/RX elements for MIMO virtual array).
   - Calculate the MIMO array geometry for the required angular resolution.
2. **Signal processing chain**:
   - Range-Doppler processing (2D FFT).
   - CFAR detection (CA-CFAR or OS-CFAR).
   - Angle estimation (MUSIC, ESPRIT, or beamforming).
   - Tracking (Kalman filter or particle filter for target trajectories).
3. **Clutter and interference mitigation**:
   - Design a clutter rejection filter.
   - Handle interference from other 24 GHz radars.
4. **Simulation**:
   - Generate simulated radar returns for a drone trajectory.
   - Process through your signal processing chain.
   - Display range-Doppler map, detected targets, and tracks.

**Deliverables:**
- System design document with all calculations.
- MATLAB/Python simulation of the complete radar signal processing chain.
- Range-Doppler maps for various scenarios.
- Detection performance analysis (ROC curves).
- Tracking results for simulated drone trajectories.

#### 💡 Expected Novelty
Detecting a 0.01 m² target at 500 m with an ISM-band radar pushes the limits of what's possible with legal power limits. The solver must design the entire system end-to-end — from link budget to signal processing — and demonstrate that it meets all requirements simultaneously.

---

### **ECE-Problem 2: "MIMO-Sat" — LEO Satellite Communication Link Design**

#### 🧩 Problem Statement

Design a **communication link** for a **Low Earth Orbit (LEO) satellite** constellation providing broadband internet to rural areas.

**System parameters:**
- **Orbit altitude**: 550 km.
- **Frequency**: Ku-band (12 GHz downlink, 14 GHz uplink).
- **Ground station antenna**: 1.2 m parabolic dish.
- **Satellite antenna**: Phased array, 256 elements.
- **Channel**: Rain attenuation (ITU-R model for tropical zone), atmospheric absorption, free-space loss.
- **Required data rate**: 100 Mbps downlink, 10 Mbps uplink.
- **BER requirement**: 10⁻⁶.

**Task:**
1. **Link budget analysis**:
   - Calculate path loss, atmospheric loss, rain attenuation.
   - Determine required EIRP and G/T for both directions.
   - Calculate received SNR and Eb/N0.
2. **Modulation and coding**:
   - Select modulation scheme (QPSK, 8PSK, 16APSK, etc.).
   - Select FEC code (LDPC, Turbo, Polar) and code rate.
   - Achieve the required data rate at the required BER.
3. **Beamforming design**:
   - Design the phased array beam pattern.
   - Calculate scan loss for different elevation angles.
   - Design a beam hopping schedule to serve multiple ground stations.
4. **Doppler analysis**:
   - Calculate maximum Doppler shift (satellite velocity ≈ 7.6 km/s).
   - Design Doppler compensation (pre-correction and tracking).
5. **Fade mitigation**:
   - Design an adaptive coding and modulation (ACM) scheme that adjusts to rain fade.
   - Calculate availability (percentage of time the link meets requirements).

**Deliverables:**
- Link budget spreadsheets for both directions.
- Modulation/coding selection with waterfall curves (BER vs. Eb/N0).
- Beam pattern plots and beam hopping schedule.
- Doppler analysis and compensation strategy.
- ACM table and availability analysis.
- MATLAB/Python simulation of the link.

#### 💡 Expected Novelty
LEO satellite links are challenging because the satellite is moving at 7.6 km/s (massive Doppler), the link distance changes rapidly (from 550 km at zenith to >2000 km at horizon), and rain attenuation at Ku-band can be severe. The solver must design a complete communication system that handles all these impairments.

---

### **ECE-Problem 3: "PhotonLink" — Free-Space Optical Communication System**

#### 🧩 Problem Statement

Design a **Free-Space Optical (FSO) communication link** between two buildings **5 km apart** in an urban environment.

**Requirements:**
- **Data rate**: 10 Gbps.
- **Wavelength**: 1550 nm (eye-safe, compatible with telecom components).
- **Availability**: 99.9% (accounting for atmospheric effects).
- **BER**: 10⁻⁹.

**Atmospheric challenges:**
- **Fog**: Visibility can drop to 50 m (heavy fog) — the primary impairment.
- **Rain**: Up to 50 mm/hr (tropical rain).
- **Scintillation**: Intensity fluctuations due to atmospheric turbulence.
- **Pointing errors**: Building sway due to wind (± 1 mrad).

**Task:**
1. **Link budget**: Calculate received power accounting for:
   - Transmitted power, beam divergence, receiver aperture.
   - Atmospheric attenuation (use Kim model for fog, ITU-R for rain).
   - Scintillation (use Rytov variance, gamma-gamma distribution).
   - Pointing loss.
2. **Diversity techniques**: Design a spatial diversity system (multiple transmitters/receivers) to achieve 99.9% availability.
3. **Modulation**: Select modulation (OOK, PPM, DPIM, subcarrier) optimized for the turbulence channel.
4. **Adaptive optics**: Design a wavefront sensor and deformable mirror system to mitigate turbulence-induced beam wander and distortion.
5. **Hybrid RF/FSO**: Design a backup RF link (60 GHz) that seamlessly switches when FSO is unavailable.
6. **Simulation**: Model the FSO channel (turbulence + attenuation + pointing) and simulate BER performance.

**Deliverables:**
- System design document.
- Link budget analysis.
- Simulation of atmospheric channel effects.
- Diversity gain analysis.
- Seamless switching protocol for hybrid link.
- Prototype system design (component selection, optical layout).

#### 💡 Expected Novelty
10 Gbps over 5 km of atmosphere is extremely challenging. Fog can attenuate the signal by >100 dB/km. Turbulence causes deep fades (scintillation). The solver must combine **optical engineering**, **atmospheric physics**, **communication theory**, and **adaptive optics** to design a system that meets the 99.9% availability target.

---

### **ECE-Problem 4: "ChipCraft" — Mixed-Signal ASIC Design for Biomedical Sensing**

#### 🧩 Problem Statement

Design an **analog front-end (AFE) ASIC** for a wearable **Electrocardiogram (ECG)** and **Photoplethysmogram (PPG)** sensor with the following requirements:

**ECG channel:**
- Input: 0.5 mV – 5 mV differential signal, 0.05 Hz – 150 Hz bandwidth.
- Noise: < 5 μVrms input-referred (0.5–150 Hz).
- CMRR: > 100 dB.
- Input impedance: > 10 GΩ.

**PPG channel:**
- Input: Photodiode current, 100 pA – 10 μA.
- LED drive: 20 mA pulse, configurable pulse width (10 μs – 1 ms).
- SNR: > 60 dB.
- Ambient light rejection: > 80 dB.

**ADC:**
- Resolution: 16-bit.
- Sampling rate: 1 kSPS per channel (8 channels total).
- ENOB: ≥ 14 bits.
- Power: < 50 μW per channel.

**Power budget**: Total AFE power < 500 μW (for battery-powered operation).

**Task:**
1. Design the **ECG analog front-end**: instrumentation amplifier, high-pass filter, low-pass filter, programmable gain.
2. Design the **PPG analog front-end**: transimpedance amplifier, ambient light cancellation, sample-and-hold.
3. Design the **SAR ADC**: capacitor DAC, comparator, SAR logic. Optimize for low power.
4. Design the **biasing and reference circuits**: Bandgap reference, current references.
5. **Simulation**: Simulate in Cadence (or LTSpice/gsim):
   - ECG channel: AC analysis, noise analysis, transient with ECG signal.
   - PPG channel: Transient response to PPG pulse.
   - ADC: INL/DNL, FFT (SNDR, ENOB).
6. **Layout considerations**: Estimate die area, discuss matching, shielding, ESD.

**Deliverables:**
- Schematic with all transistor sizes.
- Simulation results for each block.
- ADC performance metrics (INL, DNL, ENOB, power).
- System-level power budget.
- Layout floorplan.

#### 💡 Expected Novelty
The power budget (500 μW total for 2 analog channels + 8-channel ADC) is extremely tight. Achieving 100 dB CMRR with 10 GΩ input impedance at sub-100 μW power requires careful circuit design. The SAR ADC must achieve 14+ ENOB at < 50 μW per channel — pushing the state of the art.

---

### **ECE-Problem 5: "WaveCraft" — Software-Defined Radio for Multi-Standard Reception**

#### 🧩 Problem Statement

Design a **Software-Defined Radio (SDR) receiver** capable of simultaneously receiving and demodulating signals from multiple wireless standards:

| Standard | Frequency | Bandwidth | Modulation |
|---|---|---|---|
| FM Radio | 88–108 MHz | 200 kHz | Wideband FM |
| DAB+ | 174–240 MHz | 1.5 MHz | OFDM (QPSK/16-QAM) |
| LTE | 700 MHz – 2.6 GHz | Up to 20 MHz | OFDMA (QPSK to 256-QAM) |
| WiFi 6E | 5.925–7.125 GHz | Up to 160 MHz | OFDM (BPSK to 1024-QAM) |
| GPS L1 | 1.57542 GHz | 2.046 MHz | BPSK (CDMA) |

**Task:**
1. **Architecture design**:
   - Direct conversion vs. superheterodyne vs. direct sampling?
   - ADC requirements: sampling rate, ENOB, bandwidth.
   - Frequency planning, image rejection, I/Q imbalance correction.
2. **Analog front-end**:
   - Wideband LNA design (noise figure < 3 dB across all bands).
   - Frequency-agile LO (PLL/synthesizer design).
   - Band-select and channel-select filtering.
3. **Digital front-end**:
   - Digital down-conversion (DDC).
   - Sample rate conversion (handle different bandwidths).
   - Channelization (polyphase filter bank for simultaneous reception).
4. **Baseband processing** (implement for at least 2 standards):
   - FM: Discriminator demod + de-emphasis + stereo decoding.
   - LTE: OFDM demodulation, channel estimation, equalization, demapping.
   - GPS: Acquisition (code phase + Doppler), tracking (PLL + DLL), navigation solution.
5. **Simulation**:
   - Simulate the receiver chain for 2 standards simultaneously.
   - Show constellation diagrams, BER curves, audio quality (for FM).

**Deliverables:**
- System architecture document.
- Detailed design of analog front-end (schematics, calculations).
- Digital signal processing chain (source code + explanation).
- Simulation results for 2 selected standards.
- Performance analysis (sensitivity, selectivity, dynamic range).

#### 💡 Expected Novelty
Covering 88 MHz to 7.125 GHz (a 80:1 frequency range) with a single receiver architecture is extremely challenging. The solver must make fundamental architecture trade-offs and then implement working demodulators for at least 2 very different standards — each with its own unique signal processing challenges.

---
---

## 🔧 DISCIPLINE 6: MECHANICAL ENGINEERING (MECH)

---

### **MECH-Problem 1: "AeroBot" — VTOL UAV Airframe and Propulsion Design**

#### 🧩 Problem Statement

Design a **Vertical Take-Off and Landing (VTOL) fixed-wing UAV** for **aerial surveying** of agricultural land.

**Mission requirements:**
- **Payload**: 2 kg (camera, LiDAR, GPS).
- **Endurance**: ≥ 2 hours (cruise).
- **Cruise speed**: 20 m/s.
- **Range**: 100 km (round trip).
- **Max wind tolerance**: 10 m/s.
- **Takeoff/landing**: VTOL from unprepared surfaces (no runway).
- **Max MTOW**: 15 kg.

**Task:**
1. **Configuration selection**: Quad-plane, tilt-rotor, tail-sitter, or hybrid? Justify with trade study.
2. **Aerodynamic design**:
   - Wing: airfoil selection, aspect ratio, wing area, twist distribution.
   - Fuselage: streamlined body for minimum drag.
   - Tail: horizontal and vertical stabilizer sizing.
   - VTOL system: rotor placement, rotor sizing, transition mechanism.
3. **Propulsion system**:
   - Motor selection (for cruise and VTOL).
   - Propeller selection (fixed-wing prop + VTOL rotors).
   - Battery sizing for 2-hour mission.
4. **Structural design**:
   - Material selection (CFRP, balsa, foam, 3D-printed).
   - Structural analysis of wing spar (bending moment, shear).
   - Landing gear design for VTOL landing loads.
5. **Performance analysis**:
   - Lift and drag polar.
   - Power required vs. speed.
   - Endurance and range calculations.
   - VTOL hover time and transition analysis.
6. **Stability analysis**:
   - Static margin.
   - Longitudinal and lateral stability.

**Deliverables:**
- Design document with all calculations.
- 3D CAD model (SolidWorks, Fusion 360, or FreeCAD).
- Performance analysis plots.
- Structural analysis (FEA of critical components).
- Bill of Materials.

#### 💡 Expected Novelty
VTOL + fixed-wing is one of the hardest configuration problems in UAV design. The solver must optimize for **hover efficiency** (large rotors, low disk loading) AND **cruise efficiency** (high aspect ratio wing, low drag) simultaneously — two fundamentally opposing requirements. The transition between hover and cruise adds enormous complexity.

---

### **MECH-Problem 2: "ThermoCell" — Design of a High-Temperature Thermal Energy Storage System**

#### 🧩 Problem Statement

Design a **thermal energy storage (TES) system** for a concentrated solar power (CSP) plant that stores heat at **565°C** and delivers it to a steam Rankine cycle.

**Requirements:**
- **Storage capacity**: 1,000 MWh thermal.
- **Discharge power**: 100 MW thermal.
- **Charge power**: 50 MW thermal.
- **Storage duration**: 10 hours discharge.
- **Round-trip efficiency**: > 95%.
- **Design lifetime**: 30 years (10,950 cycles).
- **Cost target**: < $20/kWh.

**Technology options:**
- **Sensible heat**: Molten salt (Solar Salt: 60% NaNO₃ + 40% KNO₃), concrete, sand.
- **Latent heat**: Phase change materials (PCM) — NaCl, KCl, MgCl₂.
- **Thermochemical**: Metal oxide reduction/oxidation.

**Task:**
1. **Technology selection**: Compare the three options for this application. Select one and justify.
2. **Storage system design**:
   - Tank design (dimensions, material, insulation).
   - Heat exchanger design (type, area, NTU effectiveness).
   - Thermal losses analysis (conduction, convection, radiation).
   - Thermal stress analysis (cycling from 290°C to 565°C).
3. **Charging system**: How does solar heat get into the storage? Design the solar receiver and HTF loop.
4. **Discharging system**: How does heat get from storage to the steam cycle? Design the steam generator.
5. **Control strategy**: How to manage charging/discharging to maximize efficiency and minimize thermal cycling damage?
6. **Economic analysis**: Calculate LCOE contribution of the storage system.

**Deliverables:**
- Design document with all engineering calculations.
- Heat transfer analysis (steady-state and transient).
- Thermal stress analysis.
- P&ID (Piping and Instrumentation Diagram).
- Economic analysis spreadsheet.

#### 💡 Expected Novelty
1,000 MWh of thermal energy at 565°C is an enormous amount of stored energy. The thermal stress from daily cycling between 290°C and 565°C for 30 years (10,950 cycles) is a severe fatigue problem. The solver must design a system that handles extreme temperatures, massive thermal gradients, and long-term durability — all while hitting aggressive cost targets.

---

### **MECH-Problem 3: "GearPro" — Epicyclic Gear Train Design for Wind Turbine**

#### 🧩 Problem Statement

Design a **3-stage epicyclic (planetary) gearbox** for a **5 MW wind turbine** that converts low-speed, high-torque rotor motion to high-speed generator motion.

**Input conditions:**
- **Rotor speed**: 8–15 RPM (variable).
- **Rotor torque**: 3.2 MN·m at rated wind speed.
- **Generator speed**: 1,500 RPM (for 50 Hz grid).
- **Overall gear ratio**: ~1:100.

**Design requirements:**
- **Design life**: 20 years (175,200 hours at equivalent rated conditions).
- **Efficiency**: > 97% overall.
- **Reliability**: < 1% failure probability over design life.
- **Noise**: < 85 dBA at 1 m.

**Task:**
1. **Gear ratio distribution**: Distribute the 1:100 ratio across 3 planetary stages optimally.
2. **Gear geometry**:
   - Select number of planet gears per stage.
   - Calculate gear dimensions (module, number of teeth, face width, helix angle).
   - Design tooth profiles (involute, with profile modifications).
3. **Gear rating**:
   - AGMA bending stress and contact stress calculations for each stage.
   - Calculate safety factors against pitting and tooth breakage.
   - Account for load sharing among planets.
4. **Bearing selection**: Select bearings for planet gears, sun shaft, ring gear support.
5. **Lubrication**: Design the lubrication system (oil type, flow rate, cooling).
6. **Housing design**: Structural analysis of the gearbox housing under worst-case loads.
7. **Efficiency analysis**: Calculate mesh losses, bearing losses, windage, and churning losses.

**Deliverables:**
- Gear train schematic with all dimensions.
- AGMA rating calculations for all gear meshes.
- Gearbox efficiency analysis.
- Bearing selection and life calculations.
- 3D CAD model of the gearbox assembly.
- Assembly drawing.

#### 💡 Expected Novelty
A 5 MW gearbox is one of the most challenging mechanical designs in existence. The loads are enormous (3.2 MN·m), the design life is long (175,200 hours), and the consequences of failure are catastrophic. Load sharing among planets, manufacturing tolerances, and dynamic effects from wind gusts make the analysis extremely complex.

---

### **MECH-Problem 4: "VibeKill" — Active Vibration Control for Precision Machine Tool**

#### 🧩 Problem Statement

A CNC milling machine experiences **chatter vibration** during high-speed machining of titanium alloy (Ti-6Al-4V). Chatter causes:
- Poor surface finish (Ra > 3.2 μm, target < 0.8 μm).
- Accelerated tool wear.
- Potential tool breakage.
- Dimensional inaccuracy.

The dominant chatter frequency is **250–400 Hz** (depending on spindle speed and tool overhang).

**Task:** Design an **active vibration control system** that:
1. **Sensing**: Design a sensor array (accelerometers, force sensors, or displacement sensors) to monitor vibration in real-time.
2. **Modeling**: Create a dynamic model of the machine tool structure:
   - Identify natural frequencies and mode shapes (using FEA).
   - Model the cutting process (regenerative chatter model, stability lobes).
3. **Active control**: Design an active damping system using one of:
   - **Piezoelectric actuators** on the spindle housing.
   - **Active magnetic bearings** on the spindle.
   - **Electromagnetic shakers** on the machine structure.
   - **Adaptive spindle speed control** (varying RPM to avoid chatter).
4. **Control algorithm**:
   - Implement an adaptive filter (FxLMS) or H∞ controller.
   - Must achieve > 20 dB vibration attenuation at chatter frequencies.
   - Must not affect static stiffness (> 90% preserved).
5. **Simulation**:
   - Model the machine tool dynamics (MATLAB/Simulink or ANSYS).
   - Simulate the cutting process with and without active control.
   - Generate stability lobes with and without active damping.

**Deliverables:**
- Dynamic model of the machine tool (FEA results + reduced-order model).
- Chatter stability lobes.
- Active control system design (actuator + sensor + controller).
- Simulation results showing vibration reduction.
- Comparison of surface finish with and without control.

#### 💡 Expected Novelty
Regenerative chatter is a self-excited vibration that arises from the interaction between the tool and workpiece — it's not just a simple forced vibration problem. The solver must understand **machine dynamics**, **cutting mechanics**, **control theory**, and **actuator/sensor technology** to design a system that suppresses chatter without compromising the machine's static performance.

---

### **MECH-Problem 5: "HyperCool" — Two-Phase Cooling System for Data Center Servers**

#### 🧩 Problem Statement

Design a **two-phase (evaporative) cooling system** for a high-density data center rack with:
- **Heat load**: 50 kW per rack (10 servers × 5 kW each).
- **Chip-level heat flux**: Up to 100 W/cm² on GPU/CPU dies.
- **Coolant temperature**: Must maintain junction temperature < 85°C.
- **Coolant options**: Water (100°C boiling), dielectric fluids (Novec 7100, boiling at 61°C), or refrigerant (R134a, boiling at -26°C).
- **Form factor**: Must fit within a standard 42U rack (600mm × 1000mm × 2000mm).

**Task:**
1. **Technology selection**: Compare direct-to-chip liquid cooling, immersion cooling, and heat pipe arrays. Select and justify.
2. **Evaporator design**:
   - Design a microchannel cold plate for the GPU (100 W/cm²).
   - Select channel geometry (width, height, shape).
   - Calculate heat transfer coefficient, pressure drop, and critical heat flux.
   - Avoid flow instabilities (flow reversal, pressure drop oscillation).
3. **Condenser design**:
   - Air-cooled or liquid-cooled condenser?
   - Size the condenser for 50 kW heat rejection.
   - Design for worst-case ambient (40°C).
4. **Flow system**:
   - Pump selection (for liquid cooling) or natural circulation design.
   - Reservoir/expansion tank sizing.
   - Piping layout and pressure drop analysis.
5. **Thermal analysis**:
   - Calculate total thermal resistance from junction to ambient.
   - Ensure Tj < 85°C at maximum load and maximum ambient.
   - Analyze transient response (server load changes from 10% to 100% in 1 second).
6. **Reliability analysis**:
   - Leak detection and mitigation.
   - Coolant degradation over time.
   - Failure modes (pump failure, leak, dry-out).

**Deliverables:**
- System architecture and layout.
- Detailed evaporator design with calculations.
- Thermal resistance network and analysis.
- Transient thermal simulation.
- P&ID diagram.
- Comparison of coolant options with pros/cons.

#### 💡 Expected Novelty
100 W/cm² is near the limit of what single-phase liquid cooling can handle, making two-phase cooling necessary. But two-phase flow is inherently unstable — flow instabilities, dry-out, and flooding must be carefully managed. The solver must combine **heat transfer**, **fluid mechanics**, and **system design** to create a reliable cooling solution for extreme heat fluxes.

---
---

## 🤖 DISCIPLINE 7: ARTIFICIAL INTELLIGENCE & DATA SCIENCE (AIDS)

---

### **AIDS-Problem 1: "NeuroDecode" — Brain-Computer Interface Signal Decoding**

#### 🧩 Problem Statement

You are given **electroencephalogram (EEG) data** from 64 channels, sampled at 1000 Hz, recorded from subjects performing a **motor imagery** task (imagining left hand, right hand, feet, or tongue movement). The dataset contains:
- 10 subjects.
- 4 classes of motor imagery.
- 200 trials per class per subject (800 trials total per subject).
- Each trial is 4 seconds long.

**Task:** Build a **deep learning pipeline** for motor imagery classification that achieves:
- **Within-subject accuracy**: > 80% (train and test on same subject).
- **Cross-subject accuracy**: > 60% (train on 9 subjects, test on 1 unseen subject).
- **Real-time decoding**: Inference in < 50 ms on a single CPU core.

**Specific requirements:**
1. **Preprocessing**: Design an EEG preprocessing pipeline:
   - Artifact removal (eye blinks, muscle artifacts) — use ICA or artifact subspace reconstruction.
   - Band-pass filtering (8–30 Hz for mu/beta rhythms).
   - Common Spatial Pattern (CSP) or Riemannian geometry features.
2. **Model architecture**: Design a deep learning model. Options:
   - EEGNet (compact CNN).
   - ShallowConvNet / DeepConvNet.
   - EEG Conformer (transformer-based).
   - Graph Neural Network on EEG channel topology.
   - Custom architecture.
3. **Transfer learning**: Design a strategy to transfer knowledge from source subjects to a new subject with minimal calibration (≤ 10 trials).
4. **Explainability**: Generate visualizations showing which brain regions and frequency bands the model uses for each class.

**Deliverables:**
- Complete pipeline (preprocessing + model + training + inference).
- Within-subject results for all 10 subjects.
- Cross-subject results (leave-one-subject-out).
- Transfer learning results.
- Explainability visualizations.
- Real-time inference benchmark.

#### 💡 Expected Novelty
EEG is extremely noisy, has low spatial resolution, and varies dramatically between subjects. Achieving 80% within-subject accuracy on 4-class motor imagery is at the state of the art. Cross-subject generalization is even harder because EEG patterns are highly individual. The solver must combine **signal processing**, **deep learning**, and **domain adaptation** techniques.

---

### **AIDS-Problem 2: "GraphFlood" — Real-Time Social Network Misinformation Detection**

#### 🧩 Problem Statement

Design a system that detects **misinformation cascades** in a social network in real-time. You are provided with:

- **Social graph**: 10 million users, 500 million edges (follower/following relationships).
- **Content stream**: 50,000 posts per minute with text, images, timestamps, and engagement metrics.
- **Fact-check database**: 100,000 verified claims (true/false/mixed).
- **Historical cascades**: 50,000 labeled cascades (misinformation vs. legitimate).

**Task:**
1. **Cascade modeling**: Model information propagation using:
   - Graph Neural Networks on the social network.
   - Temporal dynamics (how the cascade grows over time — Hawkes processes or neural point processes).
   - Content features (text embeddings, image features, source credibility).
2. **Early detection**: Detect misinformation within **1 hour** of posting (when < 100 reshare events have occurred), achieving:
   - **AUC-ROC > 0.85**.
   - **Precision > 0.80** at a recall of 0.70.
3. **Real-time processing**: The system must process 50,000 posts/minute:
   - Feature extraction: < 10 ms per post.
   - Inference: < 50 ms per post.
   - Graph update: < 100 ms per edge addition.
4. **Explainability**: For each detected misinformation cascade, generate:
   - The most influential spreaders.
   - Key content features that triggered the detection.
   - A credibility score with confidence interval.

**Deliverables:**
- System architecture (streaming pipeline).
- GNN model for cascade classification.
- Temporal model for early detection.
- Real-time processing benchmarks.
- Explainability module.
- Results on provided test set.

#### 💡 Expected Novelty
Detecting misinformation from just the first few minutes of a cascade is extremely challenging — there's very little information to work with. The solver must fuse **graph structure**, **temporal dynamics**, and **content semantics** in a model that runs fast enough for real-time processing on a graph with 10M nodes and 500M edges.

---

### **AIDS-Problem 3: "OmniVision" — Multi-Modal Medical Image Registration and Fusion**

#### 🧩 Problem Statement

Build a system that **registers and fuses** medical images from different modalities for improved diagnosis:

- **CT scans**: High-resolution anatomical detail, good for bones and dense tissue.
- **MRI scans**: Excellent soft tissue contrast (T1, T2, FLAIR sequences).
- **PET scans**: Functional/metabolic information, low spatial resolution.
- **Ultrasound**: Real-time imaging, operator-dependent quality.

**Task:**
1. **Rigid registration**: Align CT and MRI scans of the same patient (account for different patient positioning).
   - Implement intensity-based (mutual information) and feature-based registration.
   - Handle different resolutions and field-of-view.
2. **Deformable registration**: Register images from patients with anatomical variations (tumor growth, surgical changes).
   - Use optical flow, diffeomorphic demons, or learning-based methods (VoxelMorph).
   - Preserve topology (no folding of the deformation field).
3. **Multi-modal fusion**: Fuse registered CT+MRI or PET+MRI into a single informative image.
   - Wavelet-based fusion, Laplacian pyramid, or learned fusion.
   - Preserve diagnostic information from both modalities.
4. **Evaluation**:
   - Target Registration Error (TRE) using landmark points.
   - Dice coefficient for organ/tumor segmentation overlap.
   - Visual assessment by simulated radiologist scoring.

**Deliverables:**
- Registration pipeline (rigid + deformable).
- Fusion algorithm.
- Results on provided multi-modal dataset (10 patient cases).
- Quantitative evaluation metrics.
- Visualization of registered/fused images.

#### 💡 Expected Novelty
Multi-modal registration is fundamentally harder than mono-modal because the same tissue looks completely different in CT vs. MRI vs. PET. Intensity-based similarity metrics don't work directly — the solver must use mutual information or learned feature spaces. Deformable registration must handle large anatomical changes while preserving topology, which is a difficult optimization problem.

---

### **AIDS-Problem 4: "AutoTrader" — Reinforcement Learning for Portfolio Management**

#### 🧩 Problem Statement

Design a **reinforcement learning agent** for **multi-asset portfolio management** that dynamically allocates capital across:
- 50 stocks (S&P 500 subset).
- 5 bond ETFs.
- 3 commodity ETFs.
- 2 crypto assets.

**Environment:**
- Historical daily data from 2010–2023 for training, 2024–2025 for testing.
- Features: OHLCV, technical indicators, fundamental data, news sentiment scores, macroeconomic indicators.
- Transaction costs: 0.1% per trade.
- Constraints: No short selling, maximum 20% allocation to any single asset, minimum 5% cash reserve.

**Task:**
1. **State representation**: Design a state space that captures:
   - Current portfolio weights.
   - Market features (prices, volumes, correlations, volatility).
   - Macro regime (expansion, contraction, crisis).
   - Sentiment indicators.
2. **Action space**: Continuous portfolio weight vector (summing to 1.0).
3. **Reward function**: Design a reward that balances:
   - Return (Sharpe ratio).
   - Risk (maximum drawdown < 15%).
   - Turnover penalty (minimize trading).
   - Tail risk (CVaR at 95%).
4. **Algorithm**: Implement one of:
   - PPO / SAC / TD3 for continuous action spaces.
   - Deep Deterministic Policy Gradient (DDPG).
   - Ensemble of multiple agents.
5. **Risk management**: Implement:
   - Position sizing based on volatility.
   - Dynamic hedging when market regime changes.
   - Stop-loss mechanisms.

**Deliverables:**
- RL environment implementation.
- Trained agent.
- Backtest results on 2024–2025 data:
  - Cumulative return, Sharpe ratio, maximum drawdown, Calmar ratio.
  - Comparison with: equal-weight portfolio, 60/40 portfolio, S&P 500.
- Ablation study on reward function components.
- Risk analysis.

#### 💡 Expected Novelty
Financial markets are non-stationary, noisy, and adversarial. The action space is continuous and high-dimensional (58 assets). Transaction costs and constraints make the optimization landscape rugged. The agent must learn to manage risk during black swan events that it may never have seen in training — requiring robust generalization, not just memorization.

---

### **AIDS-Problem 5: "CodeMorph" — Neural Program Synthesis and Transformation**

#### 🧩 Problem Statement

Build a system that can **automatically translate** programs between programming languages while preserving semantics. Specifically:

1. **Python ↔ C++ translation**: Given a Python function, generate equivalent C++ code and vice versa.
2. **Code optimization**: Given a correct but inefficient program, generate an optimized version that is **at least 5× faster** while producing identical outputs.
3. **Bug fixing**: Given a buggy program and a set of failing test cases, generate a patch that makes all tests pass.

**Constraints:**
- Programs are up to 200 lines long.
- Translation must preserve semantics (pass all provided test cases).
- You may use:
  - Large language models (GPT-4, CodeLlama, StarCoder) as components.
  - Program analysis tools (AST parsing, symbolic execution).
  - Search algorithms (beam search, MCTS).
- You may NOT simply prompt an LLM and return its output — you must build a **verification and correction loop**.

**Evaluation:**
1. **Translation accuracy**: Percentage of programs that pass all test cases after translation.
2. **Optimization speedup**: Average speedup factor of optimized code vs. original.
3. **Bug fix success rate**: Percentage of bugs correctly fixed.

**Deliverables:**
- System architecture (how you combine LLMs, verification, and search).
- Implementation.
- Results on provided benchmark (100 translation pairs, 50 optimization tasks, 50 buggy programs).
- Error analysis: What types of programs are hardest to translate/optimize/fix?

#### 💡 Expected Novelty
Pure LLM-based translation often produces code that looks correct but has subtle semantic errors. The solver must build a **neuro-symbolic** system that uses LLMs for generation but formal methods / testing for verification, and search algorithms for correction. The optimization task requires understanding algorithmic complexity — something LLMs struggle with.

---
---

## 📊 DISCIPLINE 8: MASTER OF BUSINESS ADMINISTRATION (MBA)

---

### **MBA-Problem 1: "MarketPivot" — Strategic Repositioning in the Age of AI Disruption**

#### 🧩 Problem Statement

You are the **CEO** of **"MediCore Health"**, a $2 billion revenue company that provides:
- **Electronic Health Records (EHR)** software to hospitals (60% of revenue).
- **Medical billing services** (25% of revenue).
- **Telehealth platform** (15% of revenue).

The company faces an existential threat:
- **AI-native startups** are offering EHR systems at 1/10th the cost with AI-powered clinical decision support, automated coding, and voice-based documentation.
- **Major tech companies** (Google Health, Microsoft/Nuance, Amazon Clinic) are entering healthcare with massive AI capabilities.
- Your **customer churn** has increased from 5% to 15% in the last 18 months.
- Your **NPS score** has dropped from +45 to +12.
- **Regulatory changes** (CMS interoperability mandates) require you to open your APIs — commoditizing your data moat.

**Your financial position:**
- Annual revenue: $2 billion (declining 5% YoY).
- EBITDA margin: 18%.
- Cash reserves: $500 million.
- Debt: $800 million (maturing in 3 years).
- R&D spend: 8% of revenue ($160M/year).

**Task:** Develop a **comprehensive 3-year strategic plan** that addresses:

1. **Strategic options analysis**:
   - Build: Develop proprietary AI capabilities in-house.
   - Buy: Acquire AI healthcare startups.
   - Partner: Form strategic alliances with tech giants.
   - Pivot: Transform into a healthcare AI platform company.
   - Evaluate each option using a weighted scoring model.

2. **Go-to-market transformation**:
   - How to transition from enterprise license to SaaS/platform model?
   - How to retain existing customers while acquiring new ones?
   - Pricing strategy for the AI-augmented products.

3. **Financial plan**:
   - 3-year P&L projection under your recommended strategy.
   - Capital allocation: How to fund the transformation (R&D, M&A, hiring)?
   - Debt management: How to handle the $800M maturing debt?
   - Break-even analysis for new AI products.

4. **Organizational transformation**:
   - What new roles/capabilities are needed? (AI engineers, data scientists, clinical AI specialists)
   - What is the talent acquisition and development plan?
   - How to change the company culture from "healthcare IT" to "AI-first healthcare"?

5. **Risk analysis**:
   - What are the key risks of your strategy?
   - Develop a risk mitigation plan.
   - Create contingency plans (Plan B and Plan C).

**Deliverables:**
- Strategic plan document (max 30 pages).
- Financial model (Excel/Google Sheets) with scenario analysis.
- Executive presentation (15 slides).
- 1-page board summary.

#### 💡 Expected Novelty
This requires the solver to integrate **strategic analysis**, **financial modeling**, **technology assessment**, **organizational design**, and **risk management** into a coherent plan. The AI disruption creates genuine uncertainty about the future competitive landscape — there's no single "right" answer, and the solver must make and defend difficult trade-offs.

---

### **MBA-Problem 2: "PricingGenius" — Dynamic Pricing Strategy for a Ride-Hailing Platform**

#### 🧩 Problem Statement

You are the **VP of Pricing** at **"GoRide"**, a ride-hailing company operating in 50 cities across 5 countries. The company is:
- **#3 market share** in most cities (behind Uber and a local competitor).
- **Burning $50M/month** with a path to profitability in 18 months.
- Processing **5 million rides/day**.
- Average ride price: $12.

You must design a **dynamic pricing strategy** that:

1. **Maximizes revenue** while maintaining **market share** (cannot exceed competitor prices by >15%).
2. **Balances supply and demand** in real-time (surge pricing during peak, incentives during off-peak).
3. **Segments customers** by price sensitivity and adjusts accordingly.
4. **Accounts for**:
   - Time of day, day of week, weather, events.
   - Competitor pricing (monitored in real-time).
   - Driver supply and incentives.
   - City-specific regulations (some cities cap surge at 2×).
   - Customer lifetime value (don't overcharge loyal customers).

**Data provided:**
- 6 months of ride data (500M rides): timestamps, locations, prices, durations, ratings.
- Competitor price samples (scraped, 30% coverage).
- Weather data, event calendars, traffic data.

**Task:**
1. **Demand forecasting**: Build a model predicting ride demand at the zone-level (500m × 500m grid) for 15-minute intervals, 1 hour ahead.
2. **Price elasticity estimation**: Estimate price elasticity of demand for different segments, times, and cities.
3. **Pricing optimization**: Design the pricing engine:
   - Base price calculation (distance + time).
   - Surge multiplier optimization (constrained by regulation and competition).
   - Personalized discounts for price-sensitive segments.
   - Driver incentive optimization (when and how much to pay drivers).
4. **A/B testing framework**: Design how to safely test pricing changes:
   - What metrics to track?
   - How to ensure statistical significance?
   - How to avoid regulatory scrutiny?
5. **Financial impact**: Quantify the expected revenue and profit impact of your pricing strategy vs. the current approach.

**Deliverables:**
- Demand forecasting model (accuracy metrics).
- Price elasticity analysis.
- Pricing engine design and algorithm.
- A/B testing plan.
- Financial impact analysis (3-year projection).
- Simulation results showing revenue, utilization, and market share.

#### 💡 Expected Novelty
Dynamic pricing is a multi-sided optimization problem: pricing affects demand (customers), supply (drivers), competition, and regulation simultaneously. The solver must build a system that balances short-term revenue maximization against long-term market position and regulatory compliance — while operating at 5M rides/day scale.

---

### **MBA-Problem 3: "SupplyZen" — Supply Chain Resilience Optimization**

#### 🧩 Problem Statement

You are the **Chief Supply Chain Officer** at **"ElectraTech"**, a $10B consumer electronics company. The supply chain has been disrupted by:
- **Semiconductor shortage** (ongoing, affecting 40% of components).
- **Red Sea shipping disruptions** (shipping costs up 300%, transit times up 40%).
- **Factory fire** at a critical component supplier (6-month recovery).
- **Tariff uncertainty** (potential 25% tariffs on imports from Country X, 50% probability).

**Current supply chain:**
- 2,000 components from 500 suppliers across 20 countries.
- 8 contract manufacturers in 5 countries.
- 50 distribution centers globally.
- Products: 3 SKUs (smartphone, tablet, laptop).
- Annual volume: 100M units.
- Current inventory: 3 weeks of supply (industry best practice: 8 weeks).

**Task:**
1. **Risk assessment**: Quantify the risk exposure:
   - Map the supply chain (Tier 1, Tier 2, Tier 3 suppliers).
   - Identify single points of failure.
   - Calculate the probability and impact of various disruption scenarios.
   - Build a risk heat map.

2. **Mitigation strategies** (evaluate each):
   - **Dual sourcing**: Qualify alternative suppliers for critical components.
   - **Nearshoring**: Move manufacturing closer to end markets.
   - **Inventory buffering**: Increase safety stock for critical components.
   - **Product redesign**: Substitute hard-to-source components.
   - **Vertical integration**: Acquire or invest in critical suppliers.
   - **Digital twin**: Build a real-time supply chain simulation for scenario planning.

3. **Optimization model**: Build a mathematical model that:
   - Minimizes total cost (procurement + manufacturing + logistics + inventory + tariff) under disruption scenarios.
   - Subject to: service level > 95%, lead time < 4 weeks, quality defect rate < 0.1%.
   - Decisions: supplier allocation, manufacturing allocation, inventory levels, transportation modes.

4. **Financial analysis**:
   - Cost of each mitigation strategy.
   - Expected value of each strategy (factoring in disruption probability).
   - ROI and payback period.
   - Impact on gross margin.

5. **Implementation roadmap**: Prioritized 18-month action plan with milestones and KPIs.

**Deliverables:**
- Supply chain risk assessment report.
- Optimization model (mathematical formulation + solution).
- Financial analysis of mitigation strategies.
- Implementation roadmap.
- Executive presentation.

#### 💡 Expected Novelty
Modern supply chains are deeply global and interconnected — a disruption in one node cascades through the entire network. The solver must combine **risk management**, **operations research**, **financial analysis**, and **strategic thinking** to design a supply chain that is both resilient (robust to disruptions) and efficient (low cost under normal conditions) — two fundamentally competing objectives.

---

### **MBA-Problem 4: "LaunchPad" — Go-to-Market Strategy for a Deep-Tech B2B Product**

#### 🧩 Problem Statement

You are the **VP of Marketing** at **"QuantumLeap"**, a startup that has developed a **quantum-inspired optimization engine** that solves complex logistics problems 100× faster than classical solvers. The product:
- Works on classical hardware (no quantum computer needed).
- Solves Vehicle Routing Problems (VRP), facility location, and supply chain optimization.
- API-first, cloud-deployed.
- Pricing: Usage-based ($0.01 per optimization call).

**Current state:**
- 5 paying customers (all pilot programs, $50K ARR total).
- 20 employees (10 engineers, 3 sales, 2 marketing, 5 leadership).
- $15M Series A funding (18 months runway).
- No brand awareness in the market.
- Target market: Logistics and supply chain executives at Fortune 500 companies.

**Market context:**
- **TAM**: $15B (optimization software market).
- **Competitors**: Gurobi, CPLEX (classical solvers), D-Wave, Rigetti (quantum), Google OR-Tools (open-source).
- **Buyer persona**: VP of Supply Chain / VP of Operations, budget authority > $1M, 6–18 month sales cycle.

**Task:** Develop a comprehensive **go-to-market strategy**:

1. **Positioning and messaging**:
   - How to position "quantum-inspired" technology to a non-technical buyer?
   - Value proposition canvas.
   - Competitive positioning matrix.
   - Messaging framework for different personas.

2. **Target market prioritization**:
   - Which industries/segments to target first? (Use a scoring model.)
   - Ideal Customer Profile (ICP).
   - Account-Based Marketing (ABM) target list (top 100 accounts).

3. **Channel strategy**:
   - Direct sales vs. channel partners vs. PLG (product-led growth)?
   - Content marketing plan (thought leadership, case studies).
   - Event strategy (conferences, webinars).
   - Digital marketing (SEO, SEM, LinkedIn, programmatic).

4. **Sales process design**:
   - Sales methodology (Challenger, MEDDIC, SPIN).
   - Sales playbook for each stage of the funnel.
   - Proof-of-concept (POC) framework.
   - Pricing and packaging strategy.

5. **Metrics and targets**:
   - Build a funnel model: awareness → interest → POC → closed deal.
   - Set quarterly targets for: MQLs, SQLs, POCs, closed deals, ARR.
   - Calculate CAC, LTV, LTV/CAC ratio, and payback period.
   - What ARR must you achieve in 18 months to raise a Series B?

**Deliverables:**
- Go-to-market strategy document.
- Sales playbook.
- Marketing plan with budget allocation ($500K for 18 months).
- Financial model (revenue projection, CAC/LTV analysis).
- 90-day action plan.

#### 💡 Expected Novelty
Selling deep-tech B2B products requires translating complex technology into business value for non-technical buyers. The long sales cycle, small target market, and limited budget force difficult prioritization decisions. The solver must demonstrate mastery of **product marketing**, **demand generation**, **sales process design**, and **financial modeling**.

---

### **MBA-Problem 5: "DealArchitect" — M&A Valuation and Integration Planning**

#### 🧩 Problem Statement

You are the **Head of Corporate Development** at **"CloudStack Inc."**, a $5B enterprise software company. The CEO has asked you to evaluate the **acquisition of "DataFlow Analytics"**, a fast-growing data analytics startup.

**CloudStack Inc. (Acquirer):**
- Revenue: $5B (growing 12% YoY).
- EBITDA margin: 30%.
- Market cap: $50B.
- Products: Cloud infrastructure, databases, developer tools.
- Strategic rationale: Needs a strong analytics/BI offering to compete with Snowflake, Databricks.

**DataFlow Analytics (Target):**
- Revenue: $200M (growing 80% YoY).
- Gross margin: 75%.
- EBITDA: -$50M (investing heavily in growth).
- ARR: $180M, NDR (Net Dollar Retention): 140%.
- Customers: 500 enterprises, average ACV $360K.
- Employees: 800 (500 engineers).
- Last valuation (Series D, 12 months ago): $2B.
- Founder/CEO wants to stay but is open to the right deal.
- Competitive interest: Snowflake and Google are also reportedly interested.

**Task:**

1. **Valuation**: 
   - Build a **DCF model** for DataFlow:
     - Revenue projections for 10 years (consider growth decay, TAM).
     - Margin expansion trajectory.
     - Terminal value (exit multiple and perpetuity growth methods).
   - Build a **comparable companies analysis** (select 10 relevant comps).
   - Build a **precedent transactions analysis** (select 5 relevant deals).
   - Calculate a valuation range and recommend an offer price.

2. **Synergy analysis**:
   - **Revenue synergies**: Cross-sell to existing customers, bundle pricing, upsell. Quantify.
   - **Cost synergies**: Eliminate redundant functions, reduce S&M spend, leverage CloudStack's infrastructure. Quantify.
   - Present a **conservative**, **base**, and **optimistic** synergy case.
   - What percentage of synergies should be paid to DataFlow shareholders?

3. **Deal structure**:
   - Cash vs. stock vs. mixed? Tax implications?
   - Earnout structure to align incentives?
   - Key employee retention packages?
   - Board representation?

4. **Integration planning**:
   - Day 1 readiness plan.
   - 100-day integration plan.
   - Organizational design (where does DataFlow fit? Stand-alone division or integrated?)
   - Technology integration roadmap.
   - Culture integration plan (startup culture vs. enterprise culture).
   - Customer communication plan.
   - Key risks and mitigation.

5. **Recommendation**: Should CloudStack acquire DataFlow? At what price? What is the maximum you would pay (walk-away price)?

**Deliverables:**
- Valuation model (Excel with all three methodologies).
- Synergy analysis.
- Deal structure proposal.
- Integration plan (100 days).
- Investment committee presentation (20 slides).
- Board memo (2 pages).

#### 💡 Expected Novelty
This problem integrates **financial valuation** (DCF, comparables, precedents), **strategic analysis** (synergies, competitive dynamics), **deal structuring** (cash/stock, earnouts, retention), and **integration planning** (organizational, cultural, technical). The solver must make a clear recommendation while acknowledging uncertainty and managing multiple stakeholder interests (shareholders, founders, employees, customers).

---
---

## 📋 SUMMARY TABLE

| # | Discipline | Problem | Core Skills Tested |
|---|---|---|---|
| 1 | CSE | ChronoReconstruct | Signal processing, time-series analysis, combinatorial optimization |
| 2 | CSE | Byzantine Maze | Distributed systems, fault tolerance, formal verification |
| 3 | CSE | Infinite Chess Grandmaster | Game AI, search algorithms, heuristic design |
| 4 | CSE | Self-Healing Compiler | Compiler theory, fuzzing, program repair |
| 5 | CSE | Quantum-Safe Encrypted Database | Cryptography, database systems, security |
| 1 | CYBER | Phantom Protocol | Network forensics, steganography, statistical analysis |
| 2 | CYBER | Rootkit Genesis | Kernel programming, reverse engineering, forensics |
| 3 | CYBER | CryptoPuzzle | Cryptanalysis, protocol security, vulnerability assessment |
| 4 | CYBER | Supply Chain Sentinel | Software security, static/dynamic analysis, SBOM |
| 5 | CYBER | Zero-Day Factory | Binary analysis, fuzzing, exploit development |
| 1 | IT | SmartCity Digital Twin | Full-stack, real-time systems, 3D visualization, IoT |
| 2 | IT | HealthBridge | Federated learning, privacy, distributed ML |
| 3 | IT | EventHorizon | Serverless architecture, distributed systems, load testing |
| 4 | IT | AccessibilityAI | Web technologies, computer vision, NLP, WCAG |
| 5 | IT | MeshNet | IoT, mesh networking, protocol design, simulation |
| 1 | EEE | GridBrain | Energy optimization, MILP/RL, multi-objective optimization |
| 2 | EEE | FaultSense | Signal processing, ML classification, power systems |
| 3 | EEE | MotorForge | Electromagnetic design, motor control, thermal analysis |
| 4 | EEE | PowerShield | Power electronics, semiconductor selection, circuit design |
| 5 | EEE | E-Harvest | RF design, rectenna, antenna theory, low-power electronics |
| 1 | ECE | RadarForge | Radar systems, signal processing, detection theory |
| 2 | ECE | MIMO-Sat | Satellite communications, link budget, beamforming |
| 3 | ECE | PhotonLink | Optical communications, atmospheric physics, adaptive optics |
| 4 | ECE | ChipCraft | Analog IC design, ADC design, biomedical electronics |
| 5 | ECE | WaveCraft | SDR architecture, DSP, multi-standard receiver design |
| 1 | MECH | AeroBot | Aerodynamics, structures, propulsion, UAV design |
| 2 | MECH | ThermoCell | Heat transfer, thermal storage, structural analysis |
| 3 | MECH | GearPro | Gear design, AGMA standards, bearing selection |
| 4 | MECH | VibeKill | Vibration analysis, control systems, machine dynamics |
| 5 | MECH | HyperCool | Two-phase heat transfer, thermal management, fluid mechanics |
| 1 | AIDS | NeuroDecode | Deep learning, EEG processing, transfer learning |
| 2 | AIDS | GraphFlood | Graph neural networks, temporal modeling, streaming |
| 3 | AIDS | OmniVision | Image registration, multi-modal fusion, medical imaging |
| 4 | AIDS | AutoTrader | Reinforcement learning, portfolio optimization, finance |
| 5 | AIDS | CodeMorph | Program synthesis, neuro-symbolic AI, code translation |
| 1 | MBA | MarketPivot | Strategic planning, competitive analysis, financial modeling |
| 2 | MBA | PricingGenius | Dynamic pricing, demand forecasting, elasticity estimation |
| 3 | MBA | SupplyZen | Supply chain management, risk assessment, optimization |
| 4 | MBA | LaunchPad | Go-to-market, B2B marketing, sales strategy |
| 5 | MBA | DealArchitect | M&A valuation, synergy analysis, integration planning |

---

> **Note to Organizers:** Each problem is designed to be solvable within **3 hours** by a well-prepared team, but will require integration of multiple sub-skills. Problems are deliberately open-ended in solution approach — multiple valid strategies exist for each, encouraging creativity and depth of analysis. Consider providing starter code/templates for implementation-heavy problems to keep teams focused on the core engineering challenge.