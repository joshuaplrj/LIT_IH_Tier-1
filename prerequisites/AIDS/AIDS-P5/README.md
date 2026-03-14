# AIDS-P5: CodeMorph — Neural Program Synthesis Dataset

## Structure
```
AIDS-P5/
├── translation_pairs/   100 Python <-> C++ pairs
│   └── pair_001/ ... pair_100/
│       ├── problem.py        Python source function
│       ├── reference.cpp     Equivalent C++ implementation
│       ├── tests.py          Python test assertions
│       └── metadata.json     Category metadata
├── optimization_tasks/  50 slow -> fast Python refactors
│   └── task_001/ ... task_050/
│       ├── slow.py                   Correct but O(n²) or worse
│       ├── HIDDEN_fast_reference.py  (hidden) O(n) or better version
│       └── tests.py                  Correctness tests
└── buggy_programs/      50 Python programs with one bug each
    └── bug_001/ ... bug_050/
        ├── buggy.py           Contains one specific bug
        ├── HIDDEN_fixed.py    (hidden) Corrected version
        └── tests.py           Tests that fail on buggy, pass on fixed

## Task Description
Build a system that can:
1. Translate Python functions to equivalent C++ code that passes all test cases
2. Optimize slow Python programs to be at least 5x faster while producing identical outputs
3. Fix buggy Python programs so they pass all test cases

## Evaluation
- Translation: % of translated C++ programs that compile and pass tests
- Optimization: average speedup factor (target >= 5x)
- Bug fixing: % of bugs correctly fixed (all tests pass)
