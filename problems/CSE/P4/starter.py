"""
Self-Healing Compiler — Starter Skeleton (Fuzzer + Bug Hunter)
CSE Problem 4: Detect, localize, and patch 15 hidden bugs in the MiniRust compiler.

Usage:
    # Generate programs and run fuzzer
    python starter.py --compiler compiler/main.py --output_dir bugs/ --n_programs 10000

    # Run regression suite against patched compiler
    python starter.py --mode regression --compiler compiler/main.py --tests tests/regression/
"""

import argparse
import ast
import json
import os
import random
import subprocess
import sys
import textwrap
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# MiniRust Grammar AST Nodes
# ---------------------------------------------------------------------------

@dataclass
class MRType:
    """Represents a MiniRust type."""
    base: str              # "i32", "bool", "str", "&T", "Box<T>"
    mutable: bool = False  # for reference types
    lifetime: Optional[str] = None
    inner: Optional["MRType"] = None

    def __str__(self):
        if self.base == "ref":
            m = "mut " if self.mutable else ""
            lt = f"'{self.lifetime} " if self.lifetime else ""
            return f"&{lt}{m}{self.inner}"
        return self.base


@dataclass
class MRExpr:
    kind: str   # "literal", "var", "borrow", "deref", "call", "block", "assign", "binop"
    data: dict = field(default_factory=dict)

    def to_source(self) -> str:
        if self.kind == "literal":
            return str(self.data["value"])
        elif self.kind == "var":
            return self.data["name"]
        elif self.kind == "borrow":
            m = "mut " if self.data.get("mutable") else ""
            return f"&{m}{self.data['expr'].to_source()}"
        elif self.kind == "deref":
            return f"*{self.data['expr'].to_source()}"
        elif self.kind == "binop":
            return f"({self.data['left'].to_source()} {self.data['op']} {self.data['right'].to_source()})"
        elif self.kind == "call":
            args = ", ".join(e.to_source() for e in self.data.get("args", []))
            return f"{self.data['fn']}({args})"
        elif self.kind == "block":
            stmts = "\n    ".join(s.to_source() for s in self.data.get("stmts", []))
            return f"{{\n    {stmts}\n}}"
        elif self.kind == "assign":
            return f"{self.data['target']} = {self.data['value'].to_source()}"
        return "/* unknown expr */"


@dataclass
class MRStmt:
    kind: str   # "let", "expr", "return", "drop"
    data: dict = field(default_factory=dict)

    def to_source(self) -> str:
        if self.kind == "let":
            m = "mut " if self.data.get("mutable") else ""
            ty = f": {self.data['type']}" if self.data.get("type") else ""
            val = self.data["value"].to_source() if self.data.get("value") else "uninitialized"
            return f"let {m}{self.data['name']}{ty} = {val};"
        elif self.kind == "expr":
            return f"{self.data['expr'].to_source()};"
        elif self.kind == "return":
            return f"return {self.data['expr'].to_source()};"
        elif self.kind == "drop":
            return f"drop({self.data['name']});"
        return "/* unknown stmt */"


@dataclass
class MRFunction:
    name: str
    params: List[Tuple[str, str]]   # (name, type_str) pairs
    return_type: str
    body: List[MRStmt]

    def to_source(self) -> str:
        params_str = ", ".join(f"{n}: {t}" for n, t in self.params)
        body_str = "\n    ".join(s.to_source() for s in self.body)
        return f"fn {self.name}({params_str}) -> {self.return_type} {{\n    {body_str}\n}}"


@dataclass
class MRProgram:
    functions: List[MRFunction]

    def to_source(self) -> str:
        return "\n\n".join(f.to_source() for f in self.functions)


# ---------------------------------------------------------------------------
# Fuzzer Context (ownership/borrow tracker)
# ---------------------------------------------------------------------------

class FuzzContext:
    """Tracks variable ownership and borrow state for valid program generation."""

    def __init__(self):
        self.vars: dict = {}   # name -> {"type": str, "owned": bool, "borrowed": bool, "mut_borrowed": bool}
        self.lifetime_counter = 0

    def fresh_var(self) -> str:
        n = f"v{len(self.vars)}"
        return n

    def fresh_lifetime(self) -> str:
        self.lifetime_counter += 1
        return f"a{self.lifetime_counter}"

    def declare(self, name: str, type_str: str, mutable: bool = False):
        self.vars[name] = {
            "type": type_str, "owned": True,
            "borrowed": False, "mut_borrowed": False,
            "mutable": mutable,
        }

    def owned_vars(self) -> List[str]:
        return [n for n, info in self.vars.items() if info["owned"]]

    def borrowable_vars(self) -> List[str]:
        return [n for n, info in self.vars.items()
                if info["owned"] and not info["mut_borrowed"]]

    def mut_borrowable_vars(self) -> List[str]:
        return [n for n, info in self.vars.items()
                if info["owned"] and not info["borrowed"] and not info["mut_borrowed"]
                and info.get("mutable")]

    def consume(self, name: str):
        """Mark variable as moved (no longer owned)."""
        if name in self.vars:
            self.vars[name]["owned"] = False


# ---------------------------------------------------------------------------
# Grammar-Guided Program Generator
# ---------------------------------------------------------------------------

PRIMITIVE_TYPES = ["i32", "u64", "bool", "f64"]
BINARY_OPS = ["+", "-", "*", "/", "==", "!=", "<", ">"]


def gen_literal(type_hint: str = "i32") -> MRExpr:
    if type_hint == "bool":
        return MRExpr("literal", {"value": random.choice(["true", "false"])})
    elif type_hint == "f64":
        return MRExpr("literal", {"value": round(random.uniform(-100, 100), 2)})
    else:
        return MRExpr("literal", {"value": random.randint(-1000, 1000)})


def gen_expr(ctx: FuzzContext, depth: int = 0, expected_type: str = "i32") -> MRExpr:
    """Recursively generate a random expression respecting ownership rules."""
    if depth > 4:
        return gen_literal(expected_type)

    weights = [30, 20, 15, 10, 25] if ctx.owned_vars() else [50, 0, 0, 0, 50]
    kind = random.choices(
        ["literal", "var", "borrow", "binop", "call"],
        weights=weights
    )[0]

    if kind == "literal":
        return gen_literal(expected_type)

    elif kind == "var" and ctx.owned_vars():
        name = random.choice(ctx.borrowable_vars() or ctx.owned_vars())
        return MRExpr("var", {"name": name})

    elif kind == "borrow" and ctx.borrowable_vars():
        is_mut = random.random() < 0.3
        candidates = ctx.mut_borrowable_vars() if is_mut else ctx.borrowable_vars()
        if not candidates:
            return gen_literal(expected_type)
        name = random.choice(candidates)
        inner = MRExpr("var", {"name": name})
        return MRExpr("borrow", {"mutable": is_mut, "expr": inner})

    elif kind == "binop":
        op = random.choice(BINARY_OPS[:4] if expected_type in ["i32","f64","u64"] else BINARY_OPS)
        return MRExpr("binop", {
            "left":  gen_expr(ctx, depth+1, expected_type),
            "op":    op,
            "right": gen_expr(ctx, depth+1, expected_type),
        })

    elif kind == "call":
        # TODO: Generate calls to user-defined functions in the program
        return gen_literal(expected_type)

    return gen_literal(expected_type)


def gen_statements(ctx: FuzzContext, n: int = 5) -> List[MRStmt]:
    """Generate a list of statements forming a function body."""
    stmts = []

    # Generate some variable declarations
    for _ in range(n):
        action = random.choices(
            ["let_owned", "let_mut", "let_borrow", "let_move", "drop_var", "expr_stmt"],
            weights=[20, 15, 15, 10, 5, 35]
        )[0]

        if action in ("let_owned", "let_mut"):
            name = ctx.fresh_var()
            ty = random.choice(PRIMITIVE_TYPES)
            mutable = (action == "let_mut")
            val = gen_expr(ctx, 0, ty)
            ctx.declare(name, ty, mutable=mutable)
            stmts.append(MRStmt("let", {
                "name": name, "type": ty, "mutable": mutable, "value": val
            }))

        elif action == "let_borrow" and ctx.borrowable_vars():
            src = random.choice(ctx.borrowable_vars())
            name = ctx.fresh_var()
            is_mut = random.random() < 0.3 and src in ctx.mut_borrowable_vars()
            borrow_expr = MRExpr("borrow", {"mutable": is_mut, "expr": MRExpr("var", {"name": src})})
            ref_type = f"&{'mut ' if is_mut else ''}{ctx.vars[src]['type']}"
            ctx.declare(name, ref_type, mutable=False)
            stmts.append(MRStmt("let", {
                "name": name, "type": ref_type, "mutable": False, "value": borrow_expr
            }))

        elif action == "let_move" and ctx.owned_vars():
            src = random.choice(ctx.owned_vars())
            name = ctx.fresh_var()
            ty = ctx.vars[src]["type"]
            move_expr = MRExpr("var", {"name": src})
            ctx.consume(src)
            ctx.declare(name, ty, mutable=False)
            stmts.append(MRStmt("let", {
                "name": name, "type": ty, "mutable": False, "value": move_expr
            }))

        elif action == "drop_var" and ctx.owned_vars():
            name = random.choice(ctx.owned_vars())
            ctx.consume(name)
            stmts.append(MRStmt("drop", {"name": name}))

        else:   # expr_stmt
            ty = random.choice(PRIMITIVE_TYPES)
            expr = gen_expr(ctx, 0, ty)
            stmts.append(MRStmt("expr", {"expr": expr}))

    # Return a final value
    if ctx.owned_vars():
        ret_var = random.choice(ctx.owned_vars())
        stmts.append(MRStmt("return", {"expr": MRExpr("var", {"name": ret_var})}))
    else:
        stmts.append(MRStmt("return", {"expr": gen_literal("i32")}))

    return stmts


def gen_program(complexity: int = 3) -> MRProgram:
    """Generate a random MiniRust program with `complexity` functions."""
    functions = []
    for i in range(complexity):
        ctx = FuzzContext()
        # Declare some parameters
        params = []
        for _ in range(random.randint(0, 3)):
            pname = ctx.fresh_var()
            ptype = random.choice(PRIMITIVE_TYPES)
            params.append((pname, ptype))
            ctx.declare(pname, ptype, mutable=False)
        ret_type = random.choice(PRIMITIVE_TYPES)
        body = gen_statements(ctx, n=random.randint(3, 8))
        functions.append(MRFunction(
            name=f"fn_{i}",
            params=params,
            return_type=ret_type,
            body=body,
        ))
    return MRProgram(functions)


# ---------------------------------------------------------------------------
# Compiler Runner
# ---------------------------------------------------------------------------

TIMEOUT_SECS = 5.0


def run_compiler(compiler_path: str, source_path: str) -> dict:
    """
    Run the MiniRust compiler on source_path.
    Returns {"returncode": int, "stdout": str, "stderr": str, "timed_out": bool}
    """
    try:
        proc = subprocess.run(
            [sys.executable, compiler_path, source_path],
            capture_output=True, text=True, timeout=TIMEOUT_SECS
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "TIMEOUT", "timed_out": True}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e), "timed_out": False}


def classify_bug(result: dict) -> Optional[str]:
    """
    Heuristically classify the bug category from compiler output.
    Returns category string or None if no bug detected.
    """
    if result["timed_out"]:
        return "deadlock"   # hung — likely a deadlock
    stderr = result["stderr"].lower()
    if result["returncode"] != 0:
        if any(kw in stderr for kw in ["use after free", "use-after-free", "double free",
                                        "memory", "dealloc", "segfault"]):
            return "memory"
        if any(kw in stderr for kw in ["type", "inference", "borrow", "lifetime", "ownership"]):
            return "type_inference"
        return "unknown"
    return None


# ---------------------------------------------------------------------------
# Bug Report Writer
# ---------------------------------------------------------------------------

def write_bug_report(bug_id: int, source: str, result: dict,
                     bug_type: str, output_dir: str):
    """Write trigger program and report to bugs/bug_XX/ directory."""
    bug_dir = os.path.join(output_dir, f"bug_{bug_id:02d}")
    os.makedirs(bug_dir, exist_ok=True)

    # Trigger program
    with open(os.path.join(bug_dir, "trigger.mr"), "w") as f:
        f.write(source)

    # Report
    report = textwrap.dedent(f"""
    Bug ID: bug_{bug_id:02d}
    Category: {bug_type}
    Trigger: trigger.mr
    Expected: [TODO: describe expected compiler behaviour]
    Actual: Return code={result['returncode']}
            Timed out={result['timed_out']}
            Stderr={result['stderr'][:500]}
    Location: [TODO: localize to file and function via delta debugging]
    Root Cause: [TODO: identify root cause after reading compiler source]
    """).strip()

    with open(os.path.join(bug_dir, "report.txt"), "w") as f:
        f.write(report)

    # Patch placeholder
    with open(os.path.join(bug_dir, "fix.patch"), "w") as f:
        f.write(f"# TODO: Patch for bug_{bug_id:02d}\n"
                f"# Generate with: git diff compiler/ > fix.patch\n")

    print(f"  Bug {bug_id:02d} [{bug_type}] written to {bug_dir}")


# ---------------------------------------------------------------------------
# Regression Tester
# ---------------------------------------------------------------------------

def run_regression(compiler_path: str, tests_dir: str) -> dict:
    """
    Run all .mr files in tests_dir through the compiler.
    Returns summary dict.
    """
    test_files = [
        os.path.join(tests_dir, f)
        for f in sorted(os.listdir(tests_dir))
        if f.endswith(".mr")
    ]
    results = {"passed": 0, "failed": 0, "errors": []}
    for tf in test_files:
        r = run_compiler(compiler_path, tf)
        if r["returncode"] == 0 and not r["timed_out"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({
                "file": tf,
                "returncode": r["returncode"],
                "timed_out": r["timed_out"],
                "stderr": r["stderr"][:200],
            })
    return results


# ---------------------------------------------------------------------------
# Main Fuzzer Pipeline
# ---------------------------------------------------------------------------

def run_fuzzer(compiler_path: str, output_dir: str, n_programs: int):
    os.makedirs(output_dir, exist_ok=True)
    tmpdir = os.path.join(output_dir, "_tmp")
    os.makedirs(tmpdir, exist_ok=True)

    bugs_found = {}
    bug_counter = 0
    generated = 0
    crashes = 0

    print(f"Generating and testing {n_programs} programs ...")

    for i in range(n_programs):
        # Generate a random program
        prog = gen_program(complexity=random.randint(1, 4))
        source = prog.to_source()

        # Write to temp file
        tmp_path = os.path.join(tmpdir, f"prog_{i:06d}.mr")
        with open(tmp_path, "w") as f:
            f.write(source)

        # Run compiler
        result = run_compiler(compiler_path, tmp_path)
        bug_type = classify_bug(result)

        if bug_type:
            crashes += 1
            # Deduplication: use stderr fingerprint
            fingerprint = result["stderr"][:80].strip()
            if fingerprint not in bugs_found:
                bugs_found[fingerprint] = bug_counter
                bug_counter += 1
                write_bug_report(bug_counter, source, result, bug_type, output_dir)

        generated += 1
        if generated % 1000 == 0:
            print(f"  {generated}/{n_programs} programs tested, "
                  f"{crashes} crashes, {bug_counter} unique bugs so far")

    print(f"\nFuzzing complete: {generated} programs, "
          f"{crashes} total crashes, {bug_counter} unique bugs written to {output_dir}")
    return {"generated": generated, "bugs_found": bug_counter}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Self-Healing Compiler: fuzzer and regression tester."
    )
    parser.add_argument("--mode", type=str, default="fuzz",
                        choices=["fuzz", "regression"],
                        help="Run mode: 'fuzz' to find bugs, 'regression' to verify patches.")
    parser.add_argument("--compiler", type=str, default="compiler/main.py",
                        help="Path to MiniRust compiler entry point.")
    parser.add_argument("--output_dir", type=str, default="bugs/",
                        help="Output directory for bug reports (fuzz mode).")
    parser.add_argument("--tests", type=str, default="tests/regression/",
                        help="Regression test directory (regression mode).")
    parser.add_argument("--n_programs", type=int, default=10_000,
                        help="Number of programs to generate and test.")
    args = parser.parse_args()

    if args.mode == "fuzz":
        if not os.path.isfile(args.compiler):
            print(f"ERROR: Compiler not found at {args.compiler}")
            sys.exit(1)
        stats = run_fuzzer(args.compiler, args.output_dir, args.n_programs)
        print(json.dumps(stats, indent=2))

    elif args.mode == "regression":
        if not os.path.isfile(args.compiler):
            print(f"ERROR: Compiler not found at {args.compiler}")
            sys.exit(1)
        if not os.path.isdir(args.tests):
            print(f"ERROR: Regression tests directory not found: {args.tests}")
            sys.exit(1)
        results = run_regression(args.compiler, args.tests)
        print(f"Regression results: {results['passed']} passed, {results['failed']} failed")
        if results["errors"]:
            print("Failing tests:")
            for e in results["errors"]:
                print(f"  {e['file']}: {e['stderr']}")
        with open("regression_results.txt", "w") as f:
            json.dump(results, f, indent=2)
        print("Results written to regression_results.txt")


if __name__ == "__main__":
    main()
