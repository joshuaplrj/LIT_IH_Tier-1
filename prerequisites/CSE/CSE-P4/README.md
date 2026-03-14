# CSE-P4: Self-Healing Compiler — MiniRust

## Overview
You are given a partially-implemented MiniRust compiler with **15 deliberately
introduced bugs** spread across the type checker, code generator, and parallel
compilation pipeline.

Your task: identify and fix all 15 bugs so that the compiler correctly compiles
all 200 regression tests in `regression_tests/`.

## Compiler Structure
```
minirust_compiler/
  lexer.py          — tokenizer (correct)
  parser.py         — AST parser (correct)
  typechecker.py    — type inference (5 bugs: BUG_1 ... BUG_5)
  codegen.py        — IR generator   (5 bugs: BUG_6 ... BUG_10)
  pipeline.py       — threading      (5 bugs: BUG_11 ... BUG_15)
  main.py           — entry point
  minirust_spec.md  — language spec
```

## Running the Compiler
```bash
cd minirust_compiler
python main.py path/to/source.mr
```

## Running Regression Tests
```bash
cd minirust_compiler
for f in ../regression_tests/*.mr; do python main.py "$f"; done
```

## Scoring
- 1 point per bug correctly identified and fixed (description + fix)
- 1 point per regression test that passes after your fixes
- Maximum: 15 (bugs) + 200 (tests) = 215 points

## Hints
- Each bug is marked with a comment `// BUG_N: description` in the source
- The MiniRust spec in `minirust_spec.md` describes correct language semantics
- Bugs are real classes of compiler bugs: type confusion, memory management errors,
  and concurrency issues
