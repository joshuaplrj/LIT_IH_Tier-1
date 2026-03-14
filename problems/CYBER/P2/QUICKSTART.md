# Rootkit Genesis — Quick Start

## Objective
Part A: Design and implement a kernel-level Linux rootkit on the provided isolated VM that hides processes/files, maintains a reverse shell, survives reboot, and employs anti-forensics. Part B: Forensically analyze a different team's rootkit-infected VM and produce a comprehensive incident report.

## Inputs
**Part A (you build):**
- Isolated Linux 6.x VM (provided by organizers) with root access and kernel headers
- Kernel version details available via `uname -r`

**Part B (you analyze):**
- Compromised VM disk image or live VM (provided — NOT your own team's work)
- Network capture from the compromised VM (optional, may be provided)

## Expected Output
**Part A deliverables** (place in `partA/` directory):
- `rootkit.c` — Kernel module source code
- `Makefile` — Build instructions
- `deploy.sh` — Deployment script
- `README_partA.md` — Architecture description and feature list

**Part B deliverables** (single file):
- `forensic_report.md` — Structured forensic report (see format below)

`forensic_report.md` required sections:
```
## Hidden Processes
## Hidden Files
## Persistence Mechanism
## C2 Address
## Rootkit Configuration
## Timeline
## IOCs
## Detection Scripts
```

## Recommended First Steps
1. Read the Linux Kernel Module Programming Guide for your kernel version; verify that `CONFIG_MODULE_UNLOAD` and `CONFIG_KALLSYMS` are enabled via `grep CONFIG_KALLSYMS /boot/config-$(uname -r)`.
2. For Part A, implement features incrementally — start with process hiding (hook `iterate_shared` in `/proc`), verify it works, then add file hiding, then the reverse shell.
3. For Part B, start forensics from a known-good baseline: boot a clean identical VM, compare `/proc`, running processes, loaded modules (`lsmod`), and network connections side-by-side with the compromised VM.

## Scoring Breakdown
| Metric                              | Weight |
|-------------------------------------|--------|
| Part A — Rootkit implementation     | 40%    |
| Part B — Forensic report quality    | 60%    |

**Part A sub-criteria:**
| Feature                             | Weight |
|-------------------------------------|--------|
| Process hiding (ps / top / /proc)   | 25%    |
| File hiding (VFS intercept)         | 20%    |
| Reverse shell (60s reconnect)       | 25%    |
| Reboot persistence                  | 15%    |
| Anti-forensics (2+ techniques)      | 15%    |

**Part B sub-criteria (forensic report):**
| Section                             | Weight |
|-------------------------------------|--------|
| Hidden processes identified         | 20%    |
| Persistence mechanism described     | 20%    |
| C2 address traced                   | 20%    |
| Configuration extracted             | 20%    |
| Timeline reconstructed              | 20%    |

## Common Pitfalls
- Kernel symbol addresses differ between kernel versions — use `kallsyms_lookup_name()` at load time rather than hardcoding offsets; note that this symbol requires a custom trampoline on kernels >= 5.7.
- Missing `MODULE_LICENSE("GPL")` causes `module_param` failures and taints the kernel in ways that may prevent loading entirely.
- For Part B forensics, never trust `/proc` or `ps` on the compromised system — they may be hooked; use a clean `busybox` binary copied from a trusted source, or attach Volatility to a memory dump.
