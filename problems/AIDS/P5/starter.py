"""
AIDS-P5: CodeMorph — Neural Program Synthesis and Transformation
Starter skeleton. Run as-is to verify the pipeline executes end-to-end
on randomly generated dummy programs.

Usage:
    python starter.py --data_dir data --output_dir submission
"""

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

# Optional LLM imports -------------------------------------------------------
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[WARN] transformers not found — using echo-stub LLM.")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_ATTEMPTS = 5          # generate-verify-repair iterations
EXEC_TIMEOUT_S = 5.0      # subprocess execution timeout
COMPILE_TIMEOUT_S = 30.0  # compile timeout
DEFAULT_MODEL = "codellama/CodeLlama-7b-Instruct-hf"
TEMPERATURE = 0.2
MAX_NEW_TOKENS = 1024

LANG_TO_EXT = {
    "python": "py",
    "cpp": "cpp",
    "c++": "cpp",
    "rust": "rs",
    "go": "go",
    "java": "java",
}

COMPILE_CMDS = {
    "cpp":  lambda src, out: ["g++", "-O2", "-o", out, src],
    "c++":  lambda src, out: ["g++", "-O2", "-o", out, src],
    "rust": lambda src, out: ["rustc", "--edition=2021", "-o", out, src],
    "go":   lambda src, out: ["go", "build", "-o", out, src],
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_jsonl(path: str) -> list:
    """Load a .jsonl file, returning list of dicts."""
    if not os.path.exists(path):
        return []
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return items


def load_style_guide(data_dir: str, lang: str) -> str:
    """Load language style guide Markdown. Returns empty string if missing."""
    for name in [lang, lang.lower(), lang.upper()]:
        p = Path(data_dir) / "style_guides" / f"{name}.md"
        if p.exists():
            return p.read_text(encoding="utf-8")[:2000]  # truncate for prompt
    return ""


def generate_dummy_programs(task: str = "translation", n: int = 5) -> list:
    """Generate dummy program tasks for smoke-testing."""
    if task == "translation":
        return [
            {
                "id": f"t{i}",
                "source_lang": "python",
                "target_lang": "cpp",
                "source_code": textwrap.dedent(f"""\
                    def add(a, b):
                        return a + b
                    result = add({i}, {i+1})
                    print(result)
                """),
                "test_cases": [
                    {"input": "", "expected_output": str(2 * i + 1)},
                ],
            }
            for i in range(n)
        ]
    elif task == "optimization":
        return [
            {
                "id": f"o{i}",
                "lang": "python",
                "source_code": f"# O(n^2) bubble sort\nn={i+5}\narr=list(range(n,0,-1))\nfor _ in range(n):\n  for j in range(n-1):\n    if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]\nprint(arr[0])",
                "test_cases": [{"input": "", "expected_output": "1"}],
                "reference_runtime_ms": 100.0 * (i + 1),
            }
            for i in range(n)
        ]
    elif task == "bugfix":
        return [
            {
                "id": f"b{i}",
                "lang": "python",
                "buggy_code": f"def multiply(a, b):\n    return a + b  # bug: should be multiplication\nprint(multiply({i}, {i+2}))",
                "failing_tests": [
                    {"input": "", "expected_output": str(i * (i + 2))},
                ],
            }
            for i in range(n)
        ]
    return []


# ---------------------------------------------------------------------------
# LLM interface
# ---------------------------------------------------------------------------

_llm_model = None
_llm_tokenizer = None


def load_llm(model_name: str = DEFAULT_MODEL):
    """Load a CodeLlama / StarCoder model from Hugging Face."""
    global _llm_model, _llm_tokenizer
    if not TRANSFORMERS_AVAILABLE:
        return
    if _llm_model is not None:
        return
    print(f"[INFO] Loading LLM: {model_name} (this may take a while)...")
    _llm_tokenizer = AutoTokenizer.from_pretrained(model_name)
    _llm_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )
    print("[INFO] LLM loaded.")


def llm_generate(prompt: str, max_new_tokens: int = MAX_NEW_TOKENS,
                  temperature: float = TEMPERATURE) -> str:
    """
    Generate text from the loaded LLM.
    Falls back to returning the source code unchanged (echo stub).
    """
    if not TRANSFORMERS_AVAILABLE or _llm_model is None:
        # Echo stub: return first code block from prompt unchanged
        lines = prompt.split("\n")
        code_lines = [l for l in lines if not l.startswith("#") and l.strip()]
        return "\n".join(code_lines[-10:]) if code_lines else "# TODO: implement"

    inputs = _llm_tokenizer(prompt, return_tensors="pt").to(_llm_model.device)
    with torch.no_grad():
        outputs = _llm_model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=(temperature > 0),
            pad_token_id=_llm_tokenizer.eos_token_id,
        )
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return _llm_tokenizer.decode(generated, skip_special_tokens=True)


def extract_code_block(text: str, lang: str = "") -> str:
    """Extract code from a markdown code block in LLM output."""
    lang_tag = lang.lower()
    # Try ```lang ... ```
    import re
    pattern = rf"```(?:{lang_tag}|{lang_tag.replace('++', r'\+\+')})\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try ``` ... ``` (generic)
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Return full text
    return text.strip()


# ---------------------------------------------------------------------------
# Sandbox execution
# ---------------------------------------------------------------------------

def check_syntax_python(code: str) -> tuple:
    """Returns (is_valid: bool, error_msg: str)."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, str(e)


def check_syntax_compiled(code: str, lang: str) -> tuple:
    """
    Check syntax by attempting compilation with -fsyntax-only flag or equivalent.
    Returns (is_valid, error_msg).
    """
    lang_key = lang.lower().replace(" ", "")
    ext = LANG_TO_EXT.get(lang_key, "txt")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, f"prog.{ext}")
            with open(src, "w") as f:
                f.write(code)
            if lang_key in ("cpp", "c++"):
                cmd = ["g++", "-fsyntax-only", src]
            elif lang_key == "rust":
                cmd = ["rustc", "--edition=2021", "--emit=metadata", src,
                       "--out-dir", tmpdir]
            elif lang_key == "go":
                cmd = ["go", "vet", src]
            else:
                return True, ""  # unknown lang — assume valid
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=COMPILE_TIMEOUT_S)
            if result.returncode == 0:
                return True, ""
            return False, (result.stderr or result.stdout)[:500]
    except FileNotFoundError:
        return True, "(compiler not found — syntax check skipped)"
    except subprocess.TimeoutExpired:
        return False, "syntax check timeout"
    except Exception as exc:
        return False, str(exc)


def check_syntax(code: str, lang: str) -> tuple:
    """Dispatch to appropriate syntax checker."""
    if lang.lower() == "python":
        return check_syntax_python(code)
    return check_syntax_compiled(code, lang)


def run_python_test(code: str, test_input: str, expected: str) -> tuple:
    """
    Run Python code in subprocess with given stdin.
    Returns (passed: bool, actual_output: str, error: str).
    """
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                         delete=False) as f:
            f.write(code)
            fname = f.name
        result = subprocess.run(
            [sys.executable, fname],
            input=test_input, capture_output=True, text=True,
            timeout=EXEC_TIMEOUT_S,
        )
        os.unlink(fname)
        actual = result.stdout.strip()
        passed = actual == expected.strip()
        error = result.stderr[:200] if result.returncode != 0 else ""
        return passed, actual, error
    except subprocess.TimeoutExpired:
        try:
            os.unlink(fname)
        except Exception:
            pass
        return False, "", "execution timeout"
    except Exception as exc:
        return False, "", str(exc)


def run_compiled_test(code: str, lang: str, test_input: str,
                       expected: str) -> tuple:
    """
    Compile and run C++/Rust/Go code against one test case.
    Returns (passed, actual_output, error).
    """
    lang_key = lang.lower().replace(" ", "").replace("+", "p")
    ext = LANG_TO_EXT.get(lang.lower(), "txt")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, f"prog.{ext}")
            exe = os.path.join(tmpdir, "prog")
            with open(src, "w") as f:
                f.write(code)
            lang_lower = lang.lower()
            if lang_lower in ("cpp", "c++"):
                compile_cmd = ["g++", "-O2", "-o", exe, src]
            elif lang_lower == "rust":
                compile_cmd = ["rustc", "--edition=2021", "-o", exe, src]
            elif lang_lower == "go":
                compile_cmd = ["go", "build", "-o", exe, src]
            else:
                return False, "", f"unsupported lang: {lang}"

            cr = subprocess.run(compile_cmd, capture_output=True, text=True,
                                timeout=COMPILE_TIMEOUT_S)
            if cr.returncode != 0:
                return False, "", f"compile error: {cr.stderr[:300]}"

            run_result = subprocess.run(
                [exe], input=test_input, capture_output=True, text=True,
                timeout=EXEC_TIMEOUT_S,
            )
            actual = run_result.stdout.strip()
            passed = actual == expected.strip()
            error = run_result.stderr[:200] if run_result.returncode != 0 else ""
            return passed, actual, error
    except FileNotFoundError:
        return False, "", "compiler not found"
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as exc:
        return False, "", str(exc)


def run_test_suite(code: str, lang: str, test_cases: list) -> dict:
    """
    Run all test cases for a given code snippet.
    Returns {passed, total, results: list of {input, expected, actual, passed}}.
    """
    results = []
    for tc in test_cases:
        inp = tc.get("input", "")
        expected = str(tc.get("expected_output", ""))
        if lang.lower() == "python":
            p, actual, err = run_python_test(code, inp, expected)
        else:
            p, actual, err = run_compiled_test(code, lang, inp, expected)
        results.append({
            "input": inp,
            "expected": expected,
            "actual": actual,
            "passed": p,
            "error": err,
        })
    passed = sum(1 for r in results if r["passed"])
    return {"passed": passed, "total": len(test_cases), "results": results}


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def translation_prompt(source_code: str, source_lang: str,
                        target_lang: str, style_guide: str = "") -> str:
    style_section = f"\n\nStyle Guide for {target_lang}:\n{style_guide}" if style_guide else ""
    return (
        f"Translate the following {source_lang} code to {target_lang}."
        f" Preserve exact semantics. Return ONLY the translated code."
        f"{style_section}\n\n"
        f"Source ({source_lang}):\n```{source_lang}\n{source_code}\n```\n\n"
        f"Translation ({target_lang}):\n```{target_lang}"
    )


def repair_prompt(code: str, lang: str, failing_result: dict) -> str:
    failures = [r for r in failing_result["results"] if not r["passed"]][:3]
    failure_str = "\n".join(
        f"  input={r['input']!r}, expected={r['expected']!r}, "
        f"actual={r['actual']!r}, error={r['error']!r}"
        for r in failures
    )
    return (
        f"The following {lang} code fails these test cases:\n{failure_str}\n\n"
        f"Fix only the bugs. Return ONLY the complete corrected code.\n\n"
        f"```{lang}\n{code}\n```\n\n"
        f"Fixed code:\n```{lang}"
    )


def optimization_prompt(source_code: str, lang: str) -> str:
    return (
        f"Optimize the following {lang} code to run at least 5x faster "
        f"while producing identical outputs. Focus on algorithmic improvements.\n\n"
        f"```{lang}\n{source_code}\n```\n\n"
        f"Optimized code:\n```{lang}"
    )


def bugfix_prompt(buggy_code: str, lang: str, failing_tests: list) -> str:
    tests_str = "\n".join(
        f"  input={t.get('input','')!r}, expected={t.get('expected_output','')!r}"
        for t in failing_tests[:5]
    )
    return (
        f"Fix the following {lang} program so it passes all failing test cases:\n"
        f"{tests_str}\n\n"
        f"Buggy code:\n```{lang}\n{buggy_code}\n```\n\n"
        f"Fixed code:\n```{lang}"
    )


# ---------------------------------------------------------------------------
# Generate-verify-repair loop
# ---------------------------------------------------------------------------

def translate_with_repair(task: dict, data_dir: str,
                            max_attempts: int = MAX_ATTEMPTS) -> dict:
    """
    Translate a program with iterative repair.
    Returns result dict for submission.
    """
    src_lang = task.get("source_lang", "python")
    tgt_lang = task.get("target_lang", "cpp")
    src_code = task.get("source_code", "")
    tests = task.get("test_cases", [])
    style_guide = load_style_guide(data_dir, tgt_lang)

    current_code = None
    best_result = {"passed": 0, "total": len(tests), "results": []}
    syntax_valid = False

    for attempt in range(max_attempts):
        if attempt == 0:
            prompt = translation_prompt(src_code, src_lang, tgt_lang, style_guide)
        else:
            prompt = repair_prompt(current_code, tgt_lang, best_result)

        raw = llm_generate(prompt)
        code = extract_code_block(raw, tgt_lang)
        if not code:
            continue

        # Syntax check
        valid, syn_err = check_syntax(code, tgt_lang)
        if not valid:
            current_code = code
            continue

        syntax_valid = True
        # Run tests
        test_result = run_test_suite(code, tgt_lang, tests)
        if test_result["passed"] > best_result["passed"]:
            best_result = test_result
            current_code = code
        if test_result["passed"] == test_result["total"]:
            break

    return {
        "id": task.get("id", ""),
        "translated_code": current_code or "",
        "lang": tgt_lang,
        "passed_tests": best_result["passed"],
        "total_tests": best_result["total"],
        "syntax_valid": syntax_valid,
    }


def optimize_with_repair(task: dict, data_dir: str,
                          max_attempts: int = MAX_ATTEMPTS) -> dict:
    """Optimise a program and measure speedup."""
    lang = task.get("lang", "python")
    src_code = task.get("source_code", "")
    tests = task.get("test_cases", [])
    ref_ms = float(task.get("reference_runtime_ms", 1000.0))

    current_code = None
    best_result = {"passed": 0, "total": len(tests), "results": []}
    speedup = 1.0

    for attempt in range(max_attempts):
        if attempt == 0:
            prompt = optimization_prompt(src_code, lang)
        else:
            prompt = repair_prompt(current_code, lang, best_result)

        raw = llm_generate(prompt)
        code = extract_code_block(raw, lang)
        if not code:
            continue

        valid, _ = check_syntax(code, lang)
        if not valid:
            continue

        test_result = run_test_suite(code, lang, tests)
        if test_result["passed"] >= best_result["passed"]:
            best_result = test_result
            current_code = code
        if test_result["passed"] == test_result["total"]:
            # Benchmark
            if lang.lower() == "python" and current_code:
                try:
                    import timeit
                    elapsed_ms = timeit.timeit(
                        stmt=compile(current_code, "<string>", "exec"),
                        number=10,
                    ) * 100  # ms
                    speedup = ref_ms / (elapsed_ms + 1e-9)
                except Exception:
                    speedup = 1.0
            break

    return {
        "id": task.get("id", ""),
        "optimized_code": current_code or "",
        "lang": lang,
        "passed_tests": best_result["passed"],
        "speedup_factor": round(speedup, 2),
    }


def fix_bug_with_repair(task: dict, data_dir: str,
                         max_attempts: int = MAX_ATTEMPTS) -> dict:
    """Fix a buggy program so all failing tests pass."""
    lang = task.get("lang", "python")
    buggy = task.get("buggy_code", "")
    failing = task.get("failing_tests", [])

    current_code = buggy
    best_result = {"passed": 0, "total": len(failing), "results": []}

    for attempt in range(max_attempts):
        if attempt == 0:
            prompt = bugfix_prompt(buggy, lang, failing)
        else:
            prompt = repair_prompt(current_code, lang, best_result)

        raw = llm_generate(prompt)
        code = extract_code_block(raw, lang)
        if not code:
            continue

        valid, _ = check_syntax(code, lang)
        if not valid:
            continue

        test_result = run_test_suite(code, lang, failing)
        if test_result["passed"] >= best_result["passed"]:
            best_result = test_result
            current_code = code
        if test_result["passed"] == test_result["total"]:
            break

    return {
        "id": task.get("id", ""),
        "fixed_code": current_code,
        "lang": lang,
        "passed_tests": best_result["passed"],
        "total_tests": best_result["total"],
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_jsonl(records: list, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    print(f"[OUT] {len(records)} records saved to {path}")


def save_summary(translations: list, optimizations: list,
                  bugfixes: list, output_dir: str):
    trans_acc = (sum(1 for r in translations if r["passed_tests"] == r["total_tests"])
                 / max(len(translations), 1))
    avg_speedup = (sum(r["speedup_factor"] for r in optimizations)
                   / max(len(optimizations), 1))
    bugfix_rate = (sum(1 for r in bugfixes if r["passed_tests"] == r["total_tests"])
                   / max(len(bugfixes), 1))

    summary = {
        "translation_accuracy": round(trans_acc, 4),
        "avg_speedup": round(avg_speedup, 2),
        "bugfix_rate": round(bugfix_rate, 4),
    }
    path = os.path.join(output_dir, "summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[OUT] Summary saved to {path}")
    return summary


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P5 CodeMorph pipeline")
    parser.add_argument("--data_dir", type=str, default="data",
                        help="Directory containing translation_pairs.jsonl, etc.")
    parser.add_argument("--output_dir", type=str, default="submission")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help="HuggingFace model ID for code generation")
    parser.add_argument("--max_attempts", type=int, default=MAX_ATTEMPTS,
                        help="Max repair iterations per program")
    parser.add_argument("--skip_llm_load", action="store_true",
                        help="Skip loading LLM (use echo stub — fast demo)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("=" * 60)
    print("AIDS-P5: CodeMorph — Neural Program Synthesis")
    print("=" * 60)

    if not args.skip_llm_load and TRANSFORMERS_AVAILABLE:
        load_llm(args.model)

    # --- Load tasks ---
    print("\n[1/4] Loading tasks...")
    trans_tasks = load_jsonl(os.path.join(args.data_dir, "translation_pairs.jsonl"))
    opt_tasks = load_jsonl(os.path.join(args.data_dir, "optimization_tasks.jsonl"))
    bug_tasks = load_jsonl(os.path.join(args.data_dir, "buggy_programs.jsonl"))

    if not trans_tasks:
        print("  [INFO] No translation_pairs.jsonl found — using 5 dummy tasks.")
        trans_tasks = generate_dummy_programs("translation", 5)
    if not opt_tasks:
        print("  [INFO] No optimization_tasks.jsonl found — using 5 dummy tasks.")
        opt_tasks = generate_dummy_programs("optimization", 5)
    if not bug_tasks:
        print("  [INFO] No buggy_programs.jsonl found — using 5 dummy tasks.")
        bug_tasks = generate_dummy_programs("bugfix", 5)

    print(f"  Translation: {len(trans_tasks)} | "
          f"Optimization: {len(opt_tasks)} | Bugfix: {len(bug_tasks)}")

    # --- Translation ---
    print(f"\n[2/4] Running translation (max {args.max_attempts} attempts each)...")
    translations = []
    for i, task in enumerate(trans_tasks):
        print(f"  [{i+1}/{len(trans_tasks)}] {task.get('id','')} "
              f"{task.get('source_lang','')} → {task.get('target_lang','')}")
        res = translate_with_repair(task, args.data_dir, args.max_attempts)
        translations.append(res)
        print(f"    Passed: {res['passed_tests']}/{res['total_tests']} | "
              f"Syntax: {res['syntax_valid']}")
    save_jsonl(translations, os.path.join(args.output_dir, "translations.jsonl"))

    # --- Optimization ---
    print(f"\n[3/4] Running optimization (max {args.max_attempts} attempts each)...")
    optimizations = []
    for i, task in enumerate(opt_tasks):
        print(f"  [{i+1}/{len(opt_tasks)}] {task.get('id','')}")
        res = optimize_with_repair(task, args.data_dir, args.max_attempts)
        optimizations.append(res)
        print(f"    Passed: {res['passed_tests']} | Speedup: {res['speedup_factor']}x")
    save_jsonl(optimizations, os.path.join(args.output_dir, "optimizations.jsonl"))

    # --- Bug fixing ---
    print(f"\n[4/4] Running bug fixing (max {args.max_attempts} attempts each)...")
    bugfixes = []
    for i, task in enumerate(bug_tasks):
        print(f"  [{i+1}/{len(bug_tasks)}] {task.get('id','')}")
        res = fix_bug_with_repair(task, args.data_dir, args.max_attempts)
        bugfixes.append(res)
        print(f"    Passed: {res['passed_tests']}/{res['total_tests']}")
    save_jsonl(bugfixes, os.path.join(args.output_dir, "bugfixes.jsonl"))

    # --- Summary ---
    summary = save_summary(translations, optimizations, bugfixes, args.output_dir)
    print(f"\n  Translation accuracy: {summary['translation_accuracy']*100:.1f}%")
    print(f"  Avg speedup:          {summary['avg_speedup']:.2f}x")
    print(f"  Bugfix rate:          {summary['bugfix_rate']*100:.1f}%")
    print("\n[DONE]")


if __name__ == "__main__":
    main()
