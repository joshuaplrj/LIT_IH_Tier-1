# Supply Chain Sentinel — Hints

> Each tier costs score points. Only request a hint when you are genuinely stuck.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

Software supply chain attacks exploit the trust relationship between a project and the packages it pulls in automatically. The attacker does not need to compromise your own code — they only need to compromise (or impersonate) one package that your code imports. The four main vectors are: (1) **typosquatting** — publishing a package with a name one keystroke away from a popular one; (2) **dependency confusion** — publishing a public package with the same name as a private internal package but a higher version number so the package manager downloads the attacker's version; (3) **account takeover** — gaining control of a legitimate maintainer's registry account and pushing a malicious version; and (4) **malicious update** — a legitimate package becomes malicious after an ownership transfer. Your job is to identify which of these vectors was used for each compromised package, based on observable evidence in the dependency graph and source code.

---

## Tier 2 — Technique Guidance (-10% score penalty)

- **Typosquatting detection**: Compute the **Levenshtein distance** between every package name in the graph and the top-1000 most-downloaded packages for each ecosystem (npm and PyPI both publish download statistics). Any package with distance == 1 from a popular package with a significantly higher download count is a typosquatting candidate. Also check for character-swap variants (e.g., `requeests`, `lodahs`, `numppy`).
- **Checksum verification**: Query the registry API for each package version's published SHA-256 or SHA-512 hash and compare against `checksum_sha256` in the dependency graph. Mismatches unambiguously indicate tampering. PyPI endpoint: `https://pypi.org/pypi/{name}/{version}/json` — field `info.digests`. npm endpoint: `https://registry.npmjs.org/{name}/{version}` — field `dist.shasum`.
- **Static analysis for malicious patterns**: Use `ast.parse()` (Python) or `esprima`/`acorn` (JavaScript) to parse source code and detect: `exec()` / `eval()` calls on dynamic strings, `base64.b64decode` followed by `exec`, outbound `socket` calls to non-localhost IPs, `os.environ` access in `setup.py` / `postinstall` hooks, and obfuscated variable names (entropy > 4.5 bits/char).
- **Blast radius analysis**: Build a reverse dependency graph (which services depend on each package, transitively) using a BFS/DFS traversal of `dependency_graph.json`. Flag all services reachable from a compromised package as affected.
- **SBOM generation**: Use `cyclonedx-bom` (Python) or `syft` (Go) to automatically generate CycloneDX-format SBOMs. For the purpose of this challenge, parse `dependency_graph.json` and emit the SBOM directly.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

1. **Typosquatting pipeline**:
```python
from Levenshtein import distance  # pip install python-Levenshtein
TOP_PACKAGES = load_top_1000_npm_pypi()  # fetch from bundled file or API
for pkg in dependency_graph["packages"]:
    for popular in TOP_PACKAGES[pkg["ecosystem"]]:
        if distance(pkg["name"], popular) == 1 and pkg["download_count"] < popular["downloads"] / 100:
            flag_as_typosquatting(pkg, popular)
```

2. **Registry checksum verification**:
```python
import urllib.request, json, hashlib
def verify_pypi(name, version, local_sha256):
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    data = json.loads(urllib.request.urlopen(url).read())
    for release_file in data["urls"]:
        if release_file["digests"]["sha256"] == local_sha256:
            return True
    return False  # mismatch = compromised
```

3. **Malicious `setup.py` / `postinstall` hook detection**:
   - For PyPI packages: grep `setup.py` for `subprocess`, `os.system`, `urllib`, `socket` outside of test or build code.
   - For npm packages: check `package.json` `scripts.postinstall` field — any non-trivial shell command there is a red flag.
   - Use regex: `re.search(r"base64|b64decode|eval\(|exec\(|__import__", code)` as a fast pre-filter.

4. **Dependency confusion detection**:
   - Build a set of all package names that appear to be internal (not on public registries — 404 from registry API).
   - Cross-check whether any of those internal names exist on the *public* registry with a version higher than the one in the graph — that is the dependency confusion attack.

5. **SBOM output** (CycloneDX JSON format):
```python
sbom = {
    "bomFormat": "CycloneDX", "specVersion": "1.4",
    "components": [
        {"type": "library", "name": p["name"], "version": p["version"],
         "purl": f"pkg:{p['ecosystem']}/{p['name']}@{p['version']}"}
        for p in dependency_graph["packages"]
    ]
}
```

6. **Remediation plan** — prioritize by: (1) packages used in the 3 anomalous services first, (2) Critical severity packages, (3) packages with the widest blast radius (most services affected). For each: pin to the last known-good version, or replace with the legitimately-named package.
