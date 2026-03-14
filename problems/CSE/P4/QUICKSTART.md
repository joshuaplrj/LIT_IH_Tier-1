# Self-Healing Compiler — Quick Start

## Objective
Automatically find, localize, and fix 15 hidden bugs in a provided MiniRust compiler frontend. The bugs span type-checker errors (5), memory management errors in generated code (5), and deadlocks in the parallel compilation pipeline (5). Your tool must generate adversarial programs to trigger bugs, pinpoint the buggy function, and produce correct patches.

## Inputs
- `compiler/` — Source tree of the MiniRust compiler frontend (Python or C++).
- `tests/regression/` — 200 valid MiniRust programs that must continue to compile correctly after your patches.
- MiniRust language spec (inline documentation in `compiler/`).

## Expected Output
Three deliverables:
- `bugs/` directory with one subdirectory per bug (`bug_01/` … `bug_15/`), each containing:
  - `trigger.mr` — MiniRust program that triggers the bug.
  - `report.txt` — Expected vs. actual behaviour, and the exact file + function where the bug lives.
  - `fix.patch` — Unified diff (git diff format) that fixes the bug.
- `fuzzer.py` — The fuzzer/test generator used to find bugs (must generate ≥10,000 programs).
- `regression_results.txt` — Output of running the patched compiler against all 200 regression tests (all should pass).

## Recommended First Steps
1. Read the MiniRust compiler source and understand the three pipeline stages: parsing → type-checking → code generation + parallel dispatch. Map the code to the three bug categories.
2. Write a type-aware fuzzer: randomly generate syntactically valid MiniRust programs by walking the grammar and resolving ownership/borrow constraints. Even a 10% parse-success rate on 10,000 programs gives 1,000 type-checkable inputs.
3. Run the fuzzer output through the original compiler, comparing output against a reference oracle (a trivially correct interpreter or a manually verified set of expected outputs). Any crash, wrong output, or hang (> 5s) is a candidate bug.

## Scoring Breakdown
| Metric | Points |
|---|---|
| Number of bugs detected out of 15 | 40 |
| Localization accuracy (correct file + function) | 20 |
| Correctness of patches (regression suite passes) | 25 |
| Fuzzer quality (coverage, diversity, guided vs. random) | 15 |

## Common Pitfalls
- Generating syntactically random strings — the MiniRust parser will reject 99%+ of them. The fuzzer must be grammar-guided (AST-level generation, not string mutation).
- Submitting patches that fix one bug but break the regression suite — always run all 200 regression tests after each patch before submitting.
- Reporting the wrong function for localization — use stack traces, delta debugging, or bisection to narrow to the precise function, not just the file.
- Missing deadlock bugs by running single-threaded tests — deadlocks only appear under parallel compilation; test with at least 4 worker threads and programs that trigger parallel module compilation.
- Patching symptoms rather than root causes — a type inference bug fixed by adding a special case may suppress the symptom but fail on a slightly different input.
