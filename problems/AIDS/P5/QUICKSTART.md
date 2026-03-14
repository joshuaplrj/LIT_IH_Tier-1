# CodeMorph — Quick Start

## Objective
Build a neural program synthesis system that translates programs between programming languages (Python to C++, Python to Rust, Java to Go and vice versa) while preserving full semantic equivalence verified by test suites. You must implement a verification-and-correction loop — not just a single LLM call.

## Inputs
- `data/translation_pairs.jsonl` — 100 entries, one JSON per line: `{id, source_lang, target_lang, source_code, test_cases: [{input, expected_output}]}`
- `data/optimization_tasks.jsonl` — 50 entries: `{id, lang, source_code, test_cases, reference_runtime_ms}`
- `data/buggy_programs.jsonl` — 50 entries: `{id, lang, buggy_code, failing_tests: [{input, expected_output}]}`
- `data/style_guides/` — One `.md` file per language with coding style rules

## Expected Output
- `submission/translations.jsonl` — One JSON per line: `{id, translated_code, lang, passed_tests, total_tests, syntax_valid}`
- `submission/optimizations.jsonl` — One JSON per line: `{id, optimized_code, lang, passed_tests, speedup_factor}`
- `submission/bugfixes.jsonl` — One JSON per line: `{id, fixed_code, lang, passed_tests, total_tests}`
- `submission/summary.json` — Keys: `translation_accuracy`, `avg_speedup`, `bugfix_rate`

## Recommended First Steps
1. Run `python starter.py --data_dir data --output_dir submission` to confirm the pipeline runs on dummy data.
2. Implement and test the `run_code_in_sandbox()` function to safely execute generated code against test cases — this is the foundation of the verification loop.
3. Integrate one LLM call for translation before adding the correction loop; get a baseline pass rate.

## Scoring Breakdown
| Metric                           | Weight |
|----------------------------------|--------|
| Semantic equivalence (tests pass)| 40%    |
| Syntactic correctness            | 30%    |
| Style adherence                  | 15%    |
| Documentation quality            | 15%    |

## Common Pitfalls
- Running generated C++/Rust/Go code directly on the host machine is a security risk and causes hangs; always use `subprocess` with a strict timeout (5 s) and a resource limit.
- Accepting the first LLM output without running tests means syntax errors and off-by-one bugs go undetected; run tests after every generation attempt.
- Prompting for translation and optimisation with the same generic prompt degrades quality; use task-specific prompts with the relevant style guide pasted inline.
