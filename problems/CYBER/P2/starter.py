"""
CYBER-P2: Rootkit Genesis — Part A Documentation Scaffold
==========================================================

NOTE: This file is a DOCUMENTATION SCAFFOLD, not executable automation.
Building a kernel rootkit requires manual, deliberate work on the provided
isolated VM. This scaffold organises your deliverables and provides a
structured README template for Part A.

Work must be performed exclusively on the organiser-provided isolated VM.
Never deploy rootkit code outside the designated lab environment.

Deliverable checklist (place all files in partA/):
  [ ] rootkit.c          — Kernel module source code
  [ ] Makefile           — Build and clean targets
  [ ] deploy.sh          — One-shot deployment script
  [ ] README_partA.md    — This file (fill in all sections below)

Run this script to scaffold the partA/ directory and stub files:
  python starter.py --action scaffold --outdir partA
  python starter.py --action checklist
"""

import argparse
import os
import sys
import textwrap

# ---------------------------------------------------------------------------
# Makefile template
# ---------------------------------------------------------------------------
MAKEFILE_TEMPLATE = """\
obj-m += rootkit.o

KDIR  ?= /lib/modules/$(shell uname -r)/build
PWD   := $(shell pwd)

all:
\t$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
\t$(MAKE) -C $(KDIR) M=$(PWD) clean

install: all
\tinsmod rootkit.ko

uninstall:
\trmmod rootkit || true
"""

# ---------------------------------------------------------------------------
# deploy.sh template
# ---------------------------------------------------------------------------
DEPLOY_SH_TEMPLATE = """\
#!/bin/bash
# deploy.sh — Rootkit deployment script
# MUST be run as root on the isolated lab VM only.
set -euo pipefail

MODULE="rootkit"
MODULE_FILE="rootkit.ko"

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Must run as root." >&2
    exit 1
fi

echo "[*] Building kernel module..."
make clean && make

echo "[*] Loading module..."
insmod "${MODULE_FILE}"

echo "[*] Verifying module loaded..."
lsmod | grep "${MODULE}" && echo "[OK] Module loaded." || echo "[FAIL] Module not found."

# TODO: Add persistence setup commands here
# Example (systemd): cp rootkit-loader.service /etc/systemd/system/ && systemctl enable rootkit-loader

echo "[*] Deployment complete."
"""

# ---------------------------------------------------------------------------
# rootkit.c stub — structural template only, no functional implementation
# ---------------------------------------------------------------------------
ROOTKIT_C_TEMPLATE = """\
/*
 * rootkit.c — CYBER-P2 Rootkit Genesis (Part A)
 * Isolated lab VM exercise only.
 *
 * Features to implement:
 *   1. Process hiding      — hide PIDs matching HIDDEN_PID_PREFIX
 *   2. File hiding         — hide files matching HIDDEN_FILE_PREFIX in target dirs
 *   3. Reverse shell       — reconnect to ATTACKER_IP:ATTACKER_PORT every 60s
 *   4. Reboot persistence  — survive reboot via init/systemd hook
 *   5. Anti-forensics      — implement at least 2 techniques (log deletion,
 *                            timestomping, memory-only execution, etc.)
 *
 * Build: make
 * Load:  sudo insmod rootkit.ko
 * Remove: sudo rmmod rootkit
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/sched.h>
#include <linux/list.h>
#include <linux/timer.h>
#include <linux/kprobes.h>
#include <linux/uaccess.h>
#include <linux/kallsyms.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Team Name");
MODULE_DESCRIPTION("CYBER-P2 Lab Exercise — Rootkit Genesis");
MODULE_VERSION("1.0");

/* ---------- Configuration (edit before deploying) ---------- */
#define HIDDEN_PID_PREFIX   "rk_"       /* processes whose cmdline starts with this are hidden */
#define HIDDEN_FILE_PREFIX  ".rk_"      /* files whose names start with this are hidden */
#define ATTACKER_IP         "10.0.0.1"  /* C2 IP — change to your listener */
#define ATTACKER_PORT       4444        /* C2 port */
/* ----------------------------------------------------------- */

/* TODO: Obtain kallsyms_lookup_name pointer via kprobe (required on kernel >= 5.7) */

/* TODO: Feature 1 — Process hiding
 *   - Save original /proc iterate_shared file operation
 *   - Install hooked version that skips entries matching HIDDEN_PID_PREFIX
 */

/* TODO: Feature 2 — File hiding
 *   - Hook iterate_shared for target directory inodes
 *   - Filter out directory entries matching HIDDEN_FILE_PREFIX
 */

/* TODO: Feature 3 — Reverse shell with 60-second reconnect timer
 *   - Use timer_setup + mod_timer for periodic firing
 *   - In timer callback use call_usermodehelper to launch reverse shell
 */

/* TODO: Feature 4 — Reboot persistence
 *   - On module_init, write a systemd unit or crontab entry via call_usermodehelper
 *   - Ensure the unit file path is itself hidden (Feature 2)
 */

/* TODO: Feature 5 — Anti-forensics (implement at least 2)
 *   Option A: Log deletion — call_usermodehelper to truncate /var/log/auth.log entries
 *   Option B: Timestomping — use vfs_utimes() to reset mtime/atime/ctime on module files
 *   Option C: Memory-only execution — drop payload into tmpfs, execute, unlink immediately
 */

static int __init rootkit_init(void)
{
    printk(KERN_INFO "rootkit: module loading\\n");

    /* TODO: call feature initialisation functions in order */

    printk(KERN_INFO "rootkit: module loaded\\n");
    return 0;
}

static void __exit rootkit_exit(void)
{
    /* TODO: restore all hooked function pointers before unloading */
    /* TODO: delete timer */
    printk(KERN_INFO "rootkit: module unloaded\\n");
}

module_init(rootkit_init);
module_exit(rootkit_exit);
"""

# ---------------------------------------------------------------------------
# README_partA.md template
# ---------------------------------------------------------------------------
README_TEMPLATE = """\
# CYBER-P2 Part A — Rootkit Genesis: Architecture & Feature Documentation

## Team Information
- **Team Name:** [FILL IN]
- **VM Kernel Version:** [FILL IN — output of `uname -r`]
- **Build Date:** [FILL IN]

## Architecture Overview
[Describe your rootkit's overall design: how the kernel module is structured,
which kernel subsystems are hooked, and how the components interact.]

## Feature 1: Process Hiding
- **Mechanism:** [Describe which kernel structure/function is hooked]
- **Hidden criteria:** [How do you decide which PIDs to hide]
- **Verification:** [How to confirm a process is hidden — e.g., `ps aux | grep PROC` returns nothing]

## Feature 2: File Hiding
- **Mechanism:** [Describe VFS hook used]
- **Hidden criteria:** [File name prefix/pattern]
- **Verification:** [ls command that shows nothing vs debugfs that shows the file]

## Feature 3: Reverse Shell
- **Mechanism:** [How the shell is launched from kernel space]
- **Reconnect logic:** [How the 60-second timer is implemented]
- **C2 endpoint:** [IP and port — fill in attacker listener details]

## Feature 4: Reboot Persistence
- **Mechanism:** [systemd unit / cron / bootloader hook — describe which and how]
- **File path:** [Where the loader lives on disk]
- **Verification:** [How to confirm it survives a reboot]

## Feature 5 & 6: Anti-Forensics Techniques
### Technique A: [Name]
- **What it erases/obscures:** [Description]
- **Implementation:** [Brief technical description]

### Technique B: [Name]
- **What it erases/obscures:** [Description]
- **Implementation:** [Brief technical description]

## Build Instructions
```bash
cd partA/
make
sudo insmod rootkit.ko
```

## Deployment Instructions
```bash
sudo bash deploy.sh
```

## Known Limitations
[List any features that are partially implemented or environment-specific]

## References
[Kernel documentation, papers, or resources consulted]
"""

# ---------------------------------------------------------------------------
# Checklist printer
# ---------------------------------------------------------------------------
CHECKLIST = [
    ("partA/rootkit.c",       "Kernel module source code"),
    ("partA/Makefile",        "Build instructions"),
    ("partA/deploy.sh",       "Deployment script"),
    ("partA/README_partA.md", "Architecture documentation"),
    ("Feature: process hiding",          "Hides target PIDs from ps/top//proc"),
    ("Feature: file hiding",             "Hides target files from ls/find"),
    ("Feature: reverse shell",           "Reverse shell with 60s reconnect"),
    ("Feature: reboot persistence",      "Survives reboot"),
    ("Feature: anti-forensics (x2)",     "At least 2 techniques implemented"),
]

PART_B_CHECKLIST = [
    ("forensic_report.md: ## Hidden Processes",        "Hidden processes listed with PIDs"),
    ("forensic_report.md: ## Hidden Files",            "Hidden files listed with full paths"),
    ("forensic_report.md: ## Persistence Mechanism",   "Persistence mechanism described"),
    ("forensic_report.md: ## C2 Address",              "C2 IP:port extracted"),
    ("forensic_report.md: ## Rootkit Configuration",   "Target process names, file names, C2"),
    ("forensic_report.md: ## Timeline",                "Infection timeline reconstructed"),
    ("forensic_report.md: ## IOCs",                    "Indicators of Compromise listed"),
    ("forensic_report.md: ## Detection Scripts",       "Scripts or commands used for detection"),
]


def scaffold(outdir: str):
    """Create stub deliverable files in outdir."""
    os.makedirs(outdir, exist_ok=True)
    files = {
        "rootkit.c":       ROOTKIT_C_TEMPLATE,
        "Makefile":        MAKEFILE_TEMPLATE,
        "deploy.sh":       DEPLOY_SH_TEMPLATE,
        "README_partA.md": README_TEMPLATE,
    }
    for filename, content in files.items():
        path = os.path.join(outdir, filename)
        if os.path.exists(path):
            print(f"[SKIP] {path} already exists.")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[CREATE] {path}")
    print(f"\n[*] Scaffold complete. Edit files in {outdir}/ to implement your rootkit.")


def print_checklist():
    print("\n=== PART A DELIVERABLE CHECKLIST ===")
    for item, desc in CHECKLIST:
        print(f"  [ ] {item:<45} — {desc}")
    print("\n=== PART B DELIVERABLE CHECKLIST ===")
    for item, desc in PART_B_CHECKLIST:
        print(f"  [ ] {item:<55} — {desc}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="CYBER-P2 Rootkit Genesis — Part A Scaffold Tool"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    p_scaffold = subparsers.add_parser("scaffold", help="Create stub deliverable files")
    p_scaffold.add_argument("--outdir", default="partA",
                            help="Output directory for Part A files (default: partA)")

    subparsers.add_parser("checklist", help="Print deliverable checklist")

    args = parser.parse_args()

    if args.action == "scaffold":
        scaffold(args.outdir)
    elif args.action == "checklist":
        print_checklist()


if __name__ == "__main__":
    main()
