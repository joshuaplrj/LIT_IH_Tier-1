#!/usr/bin/env python3
"""
CYBER-P4: Supply Chain Sentinel — Detection Pipeline Starter
Hackathon starter skeleton. Fill in all TODO sections.
Usage: python starter.py --graph dependency_graph.json
                         --services services/
                         --sboms sboms/
                         --anomalies anomalies.json
                         --output submission.json
"""

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Optional dependency imports
# Install: pip install python-Levenshtein requests
# ---------------------------------------------------------------------------
try:
    from Levenshtein import distance as levenshtein_distance
    HAS_LEVENSHTEIN = True
except ImportError:
    HAS_LEVENSHTEIN = False
    print("[WARN] python-Levenshtein not installed. Using slow fallback. "
          "Run: pip install python-Levenshtein", file=sys.stderr)

    def levenshtein_distance(a: str, b: str) -> int:
        """Pure-Python Levenshtein distance (slow fallback)."""
        if len(a) < len(b):
            return levenshtein_distance(b, a)
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                                prev[j] + (ca != cb)))
            prev = curr
        return prev[-1]

# ---------------------------------------------------------------------------
# Known popular packages for typosquatting comparison
# Extend this list from npm/PyPI top-download statistics
# ---------------------------------------------------------------------------
POPULAR_NPM = [
    "lodash", "express", "react", "axios", "chalk", "commander",
    "moment", "underscore", "webpack", "babel-core", "typescript",
    "jest", "eslint", "prettier", "uuid", "dotenv", "cors",
]

POPULAR_PYPI = [
    "requests", "numpy", "pandas", "flask", "django", "scipy",
    "matplotlib", "boto3", "pyyaml", "pillow", "setuptools",
    "cryptography", "paramiko", "urllib3", "certifi", "six",
    "click", "black", "pytest", "sqlalchemy",
]

POPULAR_PACKAGES: Dict[str, List[str]] = {
    "npm":       POPULAR_NPM,
    "pypi":      POPULAR_PYPI,
    "dockerhub": [],
}

# Patterns that indicate malicious code in package source files
MALICIOUS_PATTERNS = [
    (r"base64\.b64decode.*exec",           "base64-encoded exec"),
    (r"eval\s*\(",                          "dynamic eval()"),
    (r"exec\s*\(",                          "dynamic exec()"),
    (r"__import__\s*\(",                    "dynamic __import__"),
    (r"os\.system\s*\(",                    "os.system shell call"),
    (r"subprocess\.(call|run|Popen)",       "subprocess invocation"),
    (r"socket\.connect\s*\(",              "raw socket connection"),
    (r"urllib.*urlopen.*http",              "outbound HTTP in package code"),
    (r"curl|wget",                          "curl/wget in shell hook"),
    (r"postinstall.*bash|postinstall.*sh",  "postinstall shell script"),
]

ENTROPY_THRESHOLD = 4.5  # bits/char — above this level, variable names may be obfuscated


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_dependency_graph(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_anomalies(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def iter_service_sources(services_dir: str):
    """Yield (service_name, file_path, source_code) for every source file."""
    for svc in os.listdir(services_dir):
        svc_path = os.path.join(services_dir, svc)
        if not os.path.isdir(svc_path):
            continue
        for root, _, files in os.walk(svc_path):
            for fname in files:
                if fname.endswith((".py", ".js", ".ts", ".sh")):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            yield svc, fpath, f.read()
                    except Exception:
                        pass


# ---------------------------------------------------------------------------
# Phase 1 — Typosquatting detection
# ---------------------------------------------------------------------------

def detect_typosquatting(packages: List[Dict]) -> List[Dict]:
    """
    Flag packages whose names are within edit-distance 1 of a popular package.
    Returns list of flagged package dicts with added 'squatting_target' key.
    """
    flagged = []
    for pkg in packages:
        eco   = pkg.get("ecosystem", "pypi")
        name  = pkg.get("name", "")
        pops  = POPULAR_PACKAGES.get(eco, [])

        for popular in pops:
            if name == popular:
                break  # exact match — legitimate
            dist = levenshtein_distance(name, popular)
            if dist == 1:
                flagged.append({**pkg, "squatting_target": popular, "edit_distance": dist})
                break  # one flag per package is enough

    return flagged


# ---------------------------------------------------------------------------
# Phase 2 — Registry checksum verification
# ---------------------------------------------------------------------------

def fetch_pypi_checksums(name: str, version: str) -> Set[str]:
    """Fetch expected SHA-256 hashes from PyPI JSON API. Returns empty set on error."""
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        hashes = set()
        for release_file in data.get("urls", []):
            h = release_file.get("digests", {}).get("sha256")
            if h:
                hashes.add(h.lower())
        return hashes
    except (urllib.error.URLError, json.JSONDecodeError):
        return set()


def fetch_npm_checksum(name: str, version: str) -> Optional[str]:
    """Fetch expected SHA-1 tarball hash from npm registry. Returns None on error."""
    url = f"https://registry.npmjs.org/{name}/{version}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("dist", {}).get("shasum", "").lower() or None
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def verify_checksums(packages: List[Dict]) -> List[Dict]:
    """
    For each package, compare local checksum against the registry.
    Returns list of packages with checksum mismatches.
    """
    mismatches = []
    for pkg in packages:
        eco     = pkg.get("ecosystem", "")
        name    = pkg.get("name", "")
        version = pkg.get("version", "")
        local   = pkg.get("checksum_sha256", "").lower()

        if not local or not name or not version:
            continue

        # TODO: call fetch_pypi_checksums or fetch_npm_checksum based on ecosystem
        # TODO: if local checksum not in registry hashes, append to mismatches with reason
        # Placeholder — remove when implemented:
        pass

    return mismatches


# ---------------------------------------------------------------------------
# Phase 3 — Static source code analysis
# ---------------------------------------------------------------------------

def shannon_entropy(text: str) -> float:
    """Compute Shannon entropy of a string (bits per character)."""
    if not text:
        return 0.0
    from math import log2
    freq = defaultdict(int)
    for ch in text:
        freq[ch] += 1
    n = len(text)
    return -sum((c / n) * log2(c / n) for c in freq.values())


def scan_source_for_malicious_patterns(
    service: str, filepath: str, source: str
) -> List[Dict]:
    """
    Scan a single source file for malicious code patterns.
    Returns list of finding dicts.
    """
    findings = []
    for pattern, description in MALICIOUS_PATTERNS:
        for match in re.finditer(pattern, source, re.IGNORECASE):
            line_no = source[:match.start()].count("\n") + 1
            findings.append({
                "service":     service,
                "file":        filepath,
                "line":        line_no,
                "pattern":     description,
                "snippet":     source[match.start():match.start() + 80].strip(),
            })

    # TODO: parse Python AST and check for high-entropy string literals (obfuscated code)
    # TODO: check for outbound network calls in setup.py or package.json hooks

    return findings


def run_static_analysis(services_dir: str) -> List[Dict]:
    """Scan all service source files and return all findings."""
    all_findings = []
    for service, filepath, source in iter_service_sources(services_dir):
        findings = scan_source_for_malicious_patterns(service, filepath, source)
        all_findings.extend(findings)
    return all_findings


# ---------------------------------------------------------------------------
# Phase 4 — Blast radius (reverse dependency traversal)
# ---------------------------------------------------------------------------

def build_reverse_dependency_graph(packages: List[Dict]) -> Dict[str, Set[str]]:
    """
    Build a mapping: package_name -> set of package names that depend on it.
    """
    reverse: Dict[str, Set[str]] = defaultdict(set)
    for pkg in packages:
        name = pkg.get("name", "")
        for dep_str in pkg.get("dependencies", []):
            dep_name = dep_str.split("@")[0]
            reverse[dep_name].add(name)
    return reverse


def compute_blast_radius(
    compromised_names: Set[str],
    service_deps: Dict[str, List[str]],
    reverse_graph: Dict[str, Set[str]],
) -> Dict[str, List[str]]:
    """
    For each service, return the list of compromised packages it transitively depends on.
    Uses BFS from each compromised package through reverse_graph.
    """
    blast: Dict[str, List[str]] = {}

    for service, direct_deps in service_deps.items():
        affected = set()
        queue = deque(d.split("@")[0] for d in direct_deps)
        visited = set()
        while queue:
            pkg = queue.popleft()
            if pkg in visited:
                continue
            visited.add(pkg)
            if pkg in compromised_names:
                affected.add(pkg)
            # TODO: traverse transitive dependencies using reverse_graph

        if affected:
            blast[service] = sorted(affected)

    return blast


# ---------------------------------------------------------------------------
# Phase 5 — SBOM generation
# ---------------------------------------------------------------------------

def generate_sbom(packages: List[Dict]) -> Dict:
    """Generate a CycloneDX-format SBOM for all 500 packages."""
    components = []
    for pkg in packages:
        eco     = pkg.get("ecosystem", "")
        name    = pkg.get("name", "")
        version = pkg.get("version", "")
        purl    = f"pkg:{eco}/{name}@{version}"
        components.append({
            "type":    "library",
            "name":    name,
            "version": version,
            "purl":    purl,
            "ecosystem": eco,
        })
    return {
        "bomFormat":   "CycloneDX",
        "specVersion": "1.4",
        "components":  components,
    }


# ---------------------------------------------------------------------------
# Phase 6 — Build final submission
# ---------------------------------------------------------------------------

def build_submission(
    typosquats: List[Dict],
    checksum_mismatches: List[Dict],
    static_findings: List[Dict],
    blast: Dict[str, List[str]],
    sbom: Dict,
    packages: List[Dict],
) -> Dict:
    """Consolidate all findings into the submission.json structure."""

    # TODO: merge typosquats + checksum_mismatches + static_findings into compromised_packages list
    # TODO: for each compromised package determine attack_vector, payload_type, payload_description
    # TODO: assign severity: Critical if backdoor/data_exfil, High if cryptomining, Medium otherwise
    # TODO: build remediation_plan sorted by severity then blast radius

    compromised_packages: List[Dict] = []
    remediation_plan: List[Dict] = []

    # Placeholder entries — replace with real findings
    # Example structure:
    # compromised_packages.append({
    #     "name": pkg["name"], "version": pkg["version"], "ecosystem": pkg["ecosystem"],
    #     "attack_vector": "typosquatting",
    #     "payload_type": "data_exfiltration",
    #     "payload_description": "Sends environment variables to attacker IP on install",
    #     "affected_services": blast.get(pkg["name"], []),
    #     "severity": "Critical",
    #     "remediation": f"Remove {pkg['name']} and use {typosquat_target} instead",
    # })

    return {
        "compromised_packages": compromised_packages,
        "sbom":                 sbom,
        "blast_radius":         blast,
        "remediation_plan":     remediation_plan,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CYBER-P4 Supply Chain Sentinel — Malicious Package Detector"
    )
    parser.add_argument("--graph",     required=True,
                        help="Path to dependency_graph.json")
    parser.add_argument("--services",  required=True,
                        help="Path to services/ directory")
    parser.add_argument("--sboms",     required=True,
                        help="Path to sboms/ directory")
    parser.add_argument("--anomalies", required=True,
                        help="Path to anomalies.json")
    parser.add_argument("--output",    default="submission.json",
                        help="Output path for submission JSON")
    args = parser.parse_args()

    for path in (args.graph, args.services, args.sboms, args.anomalies):
        if not os.path.exists(path):
            print(f"[ERROR] Path not found: {path}", file=sys.stderr)
            sys.exit(1)

    print("[*] Loading dependency graph...")
    graph     = load_dependency_graph(args.graph)
    packages  = graph.get("packages", [])
    svc_deps  = graph.get("services", {})
    print(f"    {len(packages)} packages, {len(svc_deps)} services loaded.")

    print("[*] Loading anomaly report...")
    anomalies = load_anomalies(args.anomalies)
    anomalous_services = set(anomalies.get("affected_services", []))
    print(f"    Anomalous services: {anomalous_services}")

    # Phase 1 — Typosquatting
    print("[*] Running typosquatting detection...")
    typosquats = detect_typosquatting(packages)
    print(f"    Flagged {len(typosquats)} potential typosquats.")

    # Phase 2 — Checksum verification
    print("[*] Verifying registry checksums (may be slow — network calls)...")
    mismatches = verify_checksums(packages)
    print(f"    {len(mismatches)} checksum mismatches found.")

    # Phase 3 — Static analysis
    print("[*] Running static code analysis on service source files...")
    static_findings = run_static_analysis(args.services)
    print(f"    {len(static_findings)} malicious-pattern findings.")

    # Phase 4 — Blast radius
    print("[*] Computing blast radius...")
    rev_graph = build_reverse_dependency_graph(packages)
    compromised_names: Set[str] = (
        {p["name"] for p in typosquats} |
        {p["name"] for p in mismatches}
    )
    blast = compute_blast_radius(compromised_names, svc_deps, rev_graph)
    print(f"    Blast radius computed for {len(blast)} services.")

    # Phase 5 — SBOM generation
    print("[*] Generating SBOM...")
    sbom = generate_sbom(packages)
    print(f"    SBOM generated with {len(sbom['components'])} components.")

    # Phase 6 — Build and write submission
    submission = build_submission(
        typosquats, mismatches, static_findings, blast, sbom, packages
    )
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(submission, f, indent=2)
    print(f"[*] Submission written to: {args.output}")
    print(f"[*] Summary: {len(submission['compromised_packages'])} compromised packages found.")


if __name__ == "__main__":
    main()
