# CodeMorph — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
LLMs are good at local pattern matching — translating Python idioms to C++ syntax — but bad at preserving global semantics, especially around integer overflow, memory management, and language-specific library behaviour. The key architectural insight is to treat the LLM as a **generator** and a **test executor** as the **verifier**: generate a candidate translation, run the test cases, if any fail feed the failure output back to the LLM as context and ask it to fix only the failing part. This generate-verify-repair loop (sometimes called "self-repair" or "reflexion") dramatically improves pass rates over single-shot generation. For code optimisation the bottleneck is usually algorithmic — O(n²) to O(n log n) — which requires understanding the algorithm, not just syntax.

## Tier 2 — Technique Guidance (-10% score penalty)
Use a **CodeLlama-7B-Instruct** or **StarCoder2-7B** model (via Hugging Face `transformers`) as your LLM backbone — both handle multi-language translation well and are small enough to run on a single GPU or quantised on CPU. Structure your pipeline as: (1) **initial generation** with a carefully crafted prompt including the source code + language pair + relevant style guide excerpt; (2) **execution-based verification** using `subprocess` with a 5-second timeout; (3) **targeted repair** where you include the test failure output in a follow-up prompt asking the model to fix only the specific error. Use **beam search** (beam width 5) or sampling with temperature 0.2 at generation time — low temperature reduces hallucination for code tasks. For syntax checking, use the target language's native parser/compiler before even running tests.

## Tier 3 — Implementation Guidance (-15% score penalty)
Follow these steps in order:

1. **Sandbox executor** — `run_code(code, lang, test_input, timeout=5.0)`: compile (for C++/Rust/Go) using `subprocess.run(["g++", "-o", ...])` or `rustc`, then execute with piped stdin and capture stdout. Compare stdout to `expected_output`. Catch `subprocess.TimeoutExpired` and return `("timeout", None)`. Use `tempfile.TemporaryDirectory` for all intermediate files.

2. **Syntax validator** — Python: `ast.parse(code)`. C++: `subprocess.run(["g++", "-fsyntax-only", "-x", "c++", "-"])`. Rust: `rustc --edition=2021 --emit=metadata`. Go: `go build`. Return `True/False` plus compiler error message.

3. **Translation prompt template** — `"Translate the following {source_lang} code to {target_lang}. Follow the style guide below. Return ONLY the translated code with no explanation.\n\nStyle Guide:\n{style_guide}\n\nSource Code:\n```{source_lang}\n{source_code}\n```\n\nTranslated Code:\n```{target_lang}"`.

4. **Repair prompt template** — `"The following {target_lang} code fails test case: input={test_input}, expected={expected}, actual={actual}.\n\nFix only the bug — return the complete corrected code.\n\n```{target_lang}\n{broken_code}\n```"`.

5. **Outer loop** — For each program: try up to `max_attempts=5` generate/repair cycles. After each attempt, run ALL test cases (not just failing ones). Stop early if all pass. Track `attempts_used` for analysis.

6. **Optimisation task** — After translation, profile with `timeit.timeit` (n=100 runs), compare to `reference_runtime_ms`. Use the LLM to suggest algorithmic improvements by including big-O complexity analysis in the prompt.
