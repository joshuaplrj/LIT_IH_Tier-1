# Self-Healing Compiler — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

The three categories of bugs require three different detection strategies:

- **Type inference bugs (5)**: These manifest as the compiler accepting programs it should reject (unsoundness) or rejecting valid programs (over-conservatism). To find them, generate programs near the boundary of the type system — programs that mix ownership transfer, reborrowing, and lifetime elision in non-trivial ways. Compare the compiler's output to a reference type-checker (e.g., implement a simple trusted oracle for a restricted subset).

- **Memory / use-after-free bugs (5)**: These are in the code generator, not the type-checker. The generated code (IR or bytecode) incorrectly inserts `free()` calls too early or fails to insert them. Detect these by running generated programs through a memory sanitizer (Valgrind, AddressSanitizer) or by implementing a shadow-memory interpreter that tracks allocation state.

- **Deadlock bugs (5)**: These appear in the compiler's own parallel pipeline (e.g., worker threads acquiring locks in inconsistent order, or a cyclic dependency in the module compilation graph). Trigger these by compiling programs with mutual module dependencies or by using a thread sanitizer (ThreadSanitizer / `tsan`) while running the compiler with high parallelism.

The overarching approach is: **automated test generation → differential testing → delta debugging → patch**.

## Tier 2 — Technique Guidance (-10% score penalty)

**Grammar-guided fuzzing (for type bugs):**
Use a **grammar-based generator** that walks the MiniRust grammar (BNF) and produces valid ASTs. Key productions to fuzz:
- Variable declarations with explicit lifetimes: `let x: &'a i32 = ...`
- Ownership transfers: `let y = x;` (moves `x`) followed by uses of `x` (should be rejected).
- Borrow conflicts: mutable borrow while immutable borrow is live.
Use `hypothesis` (Python) or write a custom recursive descent generator.

**Property-based testing:**
- Property: "any program accepted by the type-checker should not produce a use-after-free in the generated code."
- Property: "any program rejected at compile time should also be rejected when the ownership constraint is clearly violated."

**Delta debugging (for localization):**
After finding a crashing/buggy input, minimize it:
1. Binary split the input (remove half the statements, check if bug persists).
2. Repeat until a minimal triggering program is found.
3. Add instrumentation (print statements or `pdb` breakpoints) at the minimal input to trace the exact code path that produces the wrong output.

**For deadlock detection:**
Run the compiler under Python's `threading` with a watchdog thread: if any thread blocks for > 5 seconds, dump the stack trace of all threads (`faulthandler.dump_traceback()`). The stack trace reveals the exact lock acquisition sequence causing the deadlock.

## Tier 3 — Implementation Guidance (-15% score penalty)

**Fuzzer architecture (`fuzzer.py`):**

1. **Grammar nodes**: Define Python dataclasses for each MiniRust AST node (Program, FnDecl, LetStmt, Expr, Type, Lifetime, etc.).

2. **Weighted random generation**:
   ```python
   def gen_expr(ctx, depth=0):
       if depth > 5:
           return gen_literal(ctx)
       kind = random.choices(
           ["literal", "var_ref", "borrow", "move", "call", "block"],
           weights=[10, 20, 15, 15, 10, 30]
       )[0]
       if kind == "borrow":
           return BorrowExpr(mutable=random.choice([True, False]),
                             inner=gen_expr(ctx, depth+1))
       elif kind == "move":
           var = ctx.pick_owned_var()   # pick from ownership-tracked context
           if var: ctx.consume(var)     # mark as moved
           return MoveExpr(var)
       ...
   ```

3. **Context tracking** (critical for validity):
   - Maintain a `Context` object that tracks: currently live variables, their types, borrow status (borrowed/mutably-borrowed/owned), and lifetimes.
   - Only generate `move` expressions for variables that are not currently borrowed.
   - Only generate mutable borrows for variables not already borrowed.

4. **Mutation fuzzing** (supplement grammar fuzzing):
   - Start with the 200 known-valid regression programs.
   - Apply mutations: swap variable names, change `mut` to non-`mut`, duplicate a borrow, remove a `drop()` call.
   - Run the mutated program and check for unexpected behaviour.

5. **Bug report format** (for `report.txt`):
   ```
   Bug ID: bug_07
   Category: type_inference
   Trigger: trigger.mr (see file)
   Expected: Compile error — use of moved value 'x'
   Actual:   Compiled successfully, generated incorrect code
   Location: compiler/typechecker.py :: infer_expr() :: line 247
   Root Cause: Missing ownership check when resolving variable reference inside closure captures.
   ```

6. **Patch format** (`fix.patch`):
   Generate using `git diff` or `diff -u original_file patched_file > fix.patch`.
   Ensure the patch applies cleanly with `patch -p1 < fix.patch` from the compiler root.

7. **Regression verification**:
   ```bash
   for prog in tests/regression/*.mr; do
       result=$(python compiler/main.py "$prog" 2>&1)
       # Compare to expected output stored in tests/regression/expected/
   done
   ```
   All 200 programs must produce the same output before and after patching (or the expected output for previously-failing ones).
