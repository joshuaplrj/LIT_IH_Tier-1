"""MiniRust Compiler entry point. Usage: python main.py source.mr"""

import sys
import os

# Add compiler directory to path
sys.path.insert(0, os.path.dirname(__file__))

from lexer import tokenize, LexError
from parser import parse, ParseError
from typechecker import typecheck, TypeCheckError
from codegen import codegen, CodeGenError


def compile_file(path: str):
    try:
        with open(path) as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    print(f"Compiling: {path}")
    try:
        ast = parse(source)
    except (LexError, ParseError) as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        typecheck(ast)
    except TypeCheckError as e:
        print(f"Type error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        ir = codegen(ast)
    except CodeGenError as e:
        print(f"Code generation error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Compilation successful. {len(ir)} IR instructions emitted.")
    out_path = path.replace(".mr", ".ir")
    with open(out_path, "w", encoding="utf-8") as f:
        for instr in ir:
            f.write(str(instr) + "\n")
    print(f"IR written to: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <source.mr>")
        sys.exit(1)
    compile_file(sys.argv[1])
