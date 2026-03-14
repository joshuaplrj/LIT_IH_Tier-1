# Supply Chain Sentinel — Quick Start

## Objective
Scan a 500-package dependency graph (npm, PyPI, Docker Hub) used by 50 microservices for malicious packages, determine the attack vector and payload for each compromised package, compute blast radius, and produce a prioritized remediation plan.

## Inputs
- `dependency_graph.json` — 500 packages with name, version, ecosystem, dependencies, and checksums
- `services/` — Directory containing source code snapshots for 50 microservices (one subdirectory each)
- `sboms/` — Per-service SBOM JSON files (CycloneDX or SPDX format)
- `anomalies.json` — Reports of unexpected network connections, CPU spikes, and data-access events from 3 specific services

```json
// dependency_graph.json structure
{
  "packages": [
    {
      "name": "package-name",
      "version": "1.2.3",
      "ecosystem": "npm | pypi | dockerhub",
      "checksum_sha256": "...",
      "dependencies": ["dep-a@1.0.0", "dep-b@2.1.0"],
      "registry_url": "..."
    }
  ],
  "services": {
    "service-name": ["package-name@version", ...]
  }
}
```

## Expected Output
Single JSON file named `submission.json`:

```json
{
  "compromised_packages": [
    {
      "name": "package-name",
      "version": "1.2.3",
      "ecosystem": "npm | pypi | dockerhub",
      "attack_vector": "typosquatting | dependency_confusion | account_takeover | malicious_update",
      "payload_type": "data_exfiltration | cryptomining | backdoor | other",
      "payload_description": "...",
      "affected_services": ["service-a", "service-b"],
      "severity": "Critical | High | Medium | Low",
      "remediation": "..."
    }
  ],
  "sbom": {
    "format": "CycloneDX",
    "components": [{"name": "...", "version": "...", "ecosystem": "...", "purl": "..."}]
  },
  "blast_radius": {
    "service-a": ["package-name@version"]
  },
  "remediation_plan": [
    {"priority": 1, "package": "...", "action": "...", "timeline": "..."}
  ]
}
```

## Recommended First Steps
1. Load `dependency_graph.json` and cross-reference every package name against known typosquatting patterns (edit-distance <= 2 from popular packages like `requests`, `lodash`, `numpy`); flag any package whose name scores distance == 1 from a top-1000 npm/PyPI package.
2. Check each package's `checksum_sha256` against the live registry API (PyPI JSON API: `https://pypi.org/pypi/{name}/{version}/json`; npm registry: `https://registry.npmjs.org/{name}/{version}`) — a checksum mismatch indicates a compromised or tampered package.
3. For the 3 services flagged in `anomalies.json`, inspect their dependency lists first; statically grep their source code in `services/` for outbound HTTP calls, base64-encoded strings, and obfuscated function names (those are the highest-probability malicious packages).

## Scoring Breakdown
| Metric                         | Weight |
|--------------------------------|--------|
| Detection rate                 | 50%    |
| False positive rate            | 20%    |
| SBOM completeness              | 30%    |

## Common Pitfalls
- False positives are heavily penalized (20% weight) — do not flag every package with an unusual name; only flag packages with concrete evidence of malicious behavior (checksum mismatch, known CVE, or static analysis finding).
- The SBOM must include all 500 packages, not just the compromised ones — SBOM completeness is 30% of the score and is easy to maximize by automating it.
- Dependency confusion attacks use internal package names; look for packages where the PyPI/npm public version has a higher version number than the internal registry version — an attacker-controlled public package will be silently preferred by the package manager.
