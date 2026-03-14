# CYBER-P4: Supply Chain Sentinel

## Overview
A sophisticated supply chain attack has been detected in the production environment.
Malicious packages have been introduced into the dependency trees of several microservices,
causing data exfiltration to an external command-and-control server.

Your mission: identify all compromised packages, determine which microservices are
affected, classify the attack vectors, and produce a remediation report.

## Objective
1. Identify all 50 compromised packages across the 500-package dependency graph
2. Determine which of the 50 microservices are affected (3 are known to be compromised)
3. Classify each malicious package by attack type
4. Explain the payload/behavior of each malicious package
5. Propose specific remediation steps

## Files
| Path                                   | Description                                  |
|----------------------------------------|----------------------------------------------|
| `anomaly_report.txt`                   | Initial incident report given to participants |
| `dependency_graph.json`                | Full dependency graph (500 pkgs, 50 services) |
| `microservices/svc_NN/`                | Source code for each of 50 microservices      |
| `microservices/svc_NN/main.py`         | Service implementation                        |
| `microservices/svc_NN/requirements.txt`| Python dependencies                           |
| `microservices/svc_NN/package.json`    | Node.js dependencies                          |
| `sbom/svc_NN_sbom.json`               | CycloneDX 1.4 SBOM per service                |
| `HIDDEN_compromised_packages.json`     | **Hidden.** Ground truth for scoring.         |
| `README.md`                            | This file                                     |

## Scoring

| Task                                         | Points |
|----------------------------------------------|--------|
| Identify each compromised package (50 total) | 1 pt each (50 pts) |
| Correctly classify attack type               | 1 pt each (50 pts) |
| Identify the 3 affected services             | 10 pts each (30 pts) |
| Describe payload/behavior accurately         | 0.5 pt each (25 pts) |
| Complete remediation plan                    | up to 20 pts |
| **Total**                                    | **175 pts** |

## Attack Taxonomy

### Typosquatting (10 packages)
Packages with names nearly identical to popular libraries. Installed accidentally
via typos in requirements files. Example: `requets` instead of `requests`.

### Dependency Confusion (10 packages)
Internal package names (e.g., `internal-auth-lib`) that an attacker published
to public registries. When the build system resolves dependencies, it may
prefer the public (malicious) version over the private internal one.

### Backdoored Packages (20 packages)
Legitimate-looking packages with injected malicious code. These simulate
maintainer account compromise scenarios where a popular package is updated
with hidden functionality.

### Cryptominer Injections (10 packages)
Packages with cryptocurrency mining code in install hooks (`setup.py`,
`postinstall` scripts). The mining runs as a background process.

## Investigation Tips
- Start with `anomaly_report.txt` to understand the network indicators
- Cross-reference `dependency_graph.json` with `sbom/` files to trace which
  services depend on which packages
- Look for packages with suspicious naming patterns in `requirements.txt` files
- The C2 IP address is 203.0.113.99 (RFC 5737 TEST-NET-3 — safe for simulation)
- Three specific services (svc_03, svc_17, svc_42) are confirmed to be making
  outbound connections; trace their dependencies to find the malicious packages

## Output Format
Submit a JSON report:
```json
{
  "compromised_packages": [
    {
      "name": "requets",
      "attack_type": "typosquatting",
      "mimics": "requests",
      "payload": "...",
      "affected_services": ["svc_03"]
    }
  ],
  "affected_services": ["svc_03", "svc_17", "svc_42"],
  "remediation": {
    "immediate": ["..."],
    "long_term": ["..."]
  }
}
```
