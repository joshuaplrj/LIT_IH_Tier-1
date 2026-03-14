"""
CSE-P4: Self-Healing Compiler (MiniRust)
Creates the minirust_compiler directory with buggy source files,
regression tests, and README.
"""

import os
import json

BASE = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\CSE\CSE-P4"
COMPILER_DIR = os.path.join(BASE, "minirust_compiler")
TESTS_DIR = os.path.join(BASE, "regression_tests")
EXPECTED_DIR = os.path.join(TESTS_DIR, "expected_output")

os.makedirs(COMPILER_DIR, exist_ok=True)
os.makedirs(TESTS_DIR, exist_ok=True)
os.makedirs(EXPECTED_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# minirust_spec.md
# ─────────────────────────────────────────────
spec = r"""# MiniRust Language Specification

## Types
- `i32`  — 32-bit signed integer
- `f64`  — 64-bit floating point
- `bool` — boolean (true / false)
- `String` — owned heap string
- `&str`  — borrowed string slice
- `Vec<i32>` — growable integer vector

## Variables
```
let x: i32 = 5;
let mut y: f64 = 3.14;
```

## Functions
```
fn add(a: i32, b: i32) -> i32 {
    return a + b;
}
```

## Ownership
- `let x = String::new("hello");`  — moves ownership into x
- `let y = &x;`                    — immutable borrow
- `let z = &mut x;`                — mutable borrow (x must be `mut`)
- Assignment moves ownership for String/Vec; primitive types are copied.

## Control Flow
```
if condition { ... } else { ... }
while condition { ... }
for item in collection { ... }
```

## Operators
`+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&`, `||`, `!`

## Printing
```
println!("{}", x);
println!("{} {}", a, b);
```

## Vec Operations
```
let mut v: Vec<i32> = Vec::new();
v.push(1);
let n = v.len();
let first = v[0];
```
"""

with open(os.path.join(COMPILER_DIR, "minirust_spec.md"), "w", encoding="utf-8") as f:
    f.write(spec)

# ─────────────────────────────────────────────
# lexer.py
# ─────────────────────────────────────────────
lexer_src = r'''"""MiniRust Lexer — tokenizes source into a flat token list."""

import re
from dataclasses import dataclass, field
from typing import List, Optional

# Token types
TT_LET      = "LET"
TT_MUT      = "MUT"
TT_FN       = "FN"
TT_RETURN   = "RETURN"
TT_IF       = "IF"
TT_ELSE     = "ELSE"
TT_WHILE    = "WHILE"
TT_FOR      = "FOR"
TT_IN       = "IN"
TT_TRUE     = "TRUE"
TT_FALSE    = "FALSE"
TT_PRINTLN  = "PRINTLN"
TT_LET_KW   = "LET_KW"

TT_I32      = "I32"
TT_F64      = "F64"
TT_BOOL     = "BOOL"
TT_STRING   = "STRING_TYPE"
TT_STR_REF  = "STR_REF"
TT_VEC      = "VEC"

TT_IDENT    = "IDENT"
TT_INT_LIT  = "INT_LIT"
TT_FLOAT_LIT= "FLOAT_LIT"
TT_STR_LIT  = "STR_LIT"
TT_BOOL_LIT = "BOOL_LIT"

TT_PLUS     = "PLUS"
TT_MINUS    = "MINUS"
TT_STAR     = "STAR"
TT_SLASH    = "SLASH"
TT_PERCENT  = "PERCENT"
TT_EQ       = "EQ"
TT_NEQ      = "NEQ"
TT_LT       = "LT"
TT_GT       = "GT"
TT_LTE      = "LTE"
TT_GTE      = "GTE"
TT_AND      = "AND"
TT_OR       = "OR"
TT_NOT      = "NOT"
TT_ASSIGN   = "ASSIGN"
TT_COLON    = "COLON"
TT_SEMI     = "SEMI"
TT_COMMA    = "COMMA"
TT_ARROW    = "ARROW"
TT_LBRACE   = "LBRACE"
TT_RBRACE   = "RBRACE"
TT_LPAREN   = "LPAREN"
TT_RPAREN   = "RPAREN"
TT_LBRACKET = "LBRACKET"
TT_RBRACKET = "RBRACKET"
TT_AMP      = "AMP"
TT_DOT      = "DOT"
TT_DCOLON   = "DCOLON"
TT_BANG     = "BANG"
TT_EOF      = "EOF"

KEYWORDS = {
    "let": TT_LET, "mut": TT_MUT, "fn": TT_FN, "return": TT_RETURN,
    "if": TT_IF, "else": TT_ELSE, "while": TT_WHILE, "for": TT_FOR,
    "in": TT_IN, "true": TT_TRUE, "false": TT_FALSE,
    "i32": TT_I32, "f64": TT_F64, "bool": TT_BOOL,
    "String": TT_STRING, "Vec": TT_VEC,
}

@dataclass
class Token:
    type: str
    value: str
    line: int = 0

class LexError(Exception):
    pass

TOKEN_PATTERNS = [
    (r"//[^\n]*",                   None),           # line comments
    (r"\s+",                        None),           # whitespace
    (r"\d+\.\d+",                   TT_FLOAT_LIT),
    (r"\d+",                        TT_INT_LIT),
    (r'"[^"]*"',                    TT_STR_LIT),
    (r"->",                         TT_ARROW),
    (r"::",                         TT_DCOLON),
    (r"==",                         TT_EQ),
    (r"!=",                         TT_NEQ),
    (r"<=",                         TT_LTE),
    (r">=",                         TT_GTE),
    (r"&&",                         TT_AND),
    (r"\|\|",                       TT_OR),
    (r"<",                          TT_LT),
    (r">",                          TT_GT),
    (r"!",                          TT_BANG),
    (r"\+",                         TT_PLUS),
    (r"-",                          TT_MINUS),
    (r"\*",                         TT_STAR),
    (r"/",                          TT_SLASH),
    (r"%",                          TT_PERCENT),
    (r"=",                          TT_ASSIGN),
    (r":",                          TT_COLON),
    (r";",                          TT_SEMI),
    (r",",                          TT_COMMA),
    (r"\{",                         TT_LBRACE),
    (r"\}",                         TT_RBRACE),
    (r"\(",                         TT_LPAREN),
    (r"\)",                         TT_RPAREN),
    (r"\[",                         TT_LBRACKET),
    (r"\]",                         TT_RBRACKET),
    (r"&",                          TT_AMP),
    (r"\.",                         TT_DOT),
    (r"[A-Za-z_][A-Za-z0-9_]*",    TT_IDENT),
]

_MASTER_RE = re.compile("|".join(f"({p})" for p, _ in TOKEN_PATTERNS))

def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    line = 1
    pos = 0
    while pos < len(source):
        m = _MASTER_RE.match(source, pos)
        if not m:
            raise LexError(f"Unexpected character {source[pos]!r} at line {line}")
        pos = m.end()
        matched = m.lastindex
        if matched is None:
            continue
        tt = TOKEN_PATTERNS[matched - 1][1]
        text = m.group()
        if tt is None:
            line += text.count("\n")
            continue
        if tt == TT_IDENT and text in KEYWORDS:
            tt = KEYWORDS[text]
        if text == "true" or text == "false":
            tt = TT_BOOL_LIT
        tokens.append(Token(tt, text, line))
        line += text.count("\n")
    tokens.append(Token(TT_EOF, "", line))
    return tokens
'''

with open(os.path.join(COMPILER_DIR, "lexer.py"), "w", encoding="utf-8") as f:
    f.write(lexer_src)

# ─────────────────────────────────────────────
# parser.py
# ─────────────────────────────────────────────
parser_src = r'''"""MiniRust Parser — builds an AST from the token list."""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from lexer import (Token, tokenize,
    TT_LET, TT_MUT, TT_FN, TT_RETURN, TT_IF, TT_ELSE,
    TT_WHILE, TT_FOR, TT_IN, TT_TRUE, TT_FALSE, TT_PRINTLN,
    TT_I32, TT_F64, TT_BOOL, TT_STRING, TT_STR_REF, TT_VEC,
    TT_IDENT, TT_INT_LIT, TT_FLOAT_LIT, TT_STR_LIT, TT_BOOL_LIT,
    TT_PLUS, TT_MINUS, TT_STAR, TT_SLASH, TT_PERCENT,
    TT_EQ, TT_NEQ, TT_LT, TT_GT, TT_LTE, TT_GTE,
    TT_AND, TT_OR, TT_NOT, TT_ASSIGN, TT_COLON, TT_SEMI,
    TT_COMMA, TT_ARROW, TT_LBRACE, TT_RBRACE, TT_LPAREN, TT_RPAREN,
    TT_LBRACKET, TT_RBRACKET, TT_AMP, TT_DOT, TT_DCOLON, TT_BANG,
    TT_EOF)

# ── AST nodes ──────────────────────────────────────────────────────────

@dataclass
class TypeNode:
    name: str            # "i32", "f64", "bool", "String", "&str", "Vec<i32>"
    mutable: bool = False

@dataclass
class LetStmt:
    name: str
    mutable: bool
    ty: Optional[TypeNode]
    value: Any           # expression node

@dataclass
class AssignStmt:
    name: str
    value: Any

@dataclass
class ReturnStmt:
    value: Any

@dataclass
class IfStmt:
    cond: Any
    then_block: List
    else_block: Optional[List]

@dataclass
class WhileStmt:
    cond: Any
    body: List

@dataclass
class ForStmt:
    var: str
    iterable: Any
    body: List

@dataclass
class FnDef:
    name: str
    params: List         # list of (name, TypeNode)
    ret_type: Optional[TypeNode]
    body: List

@dataclass
class PrintlnStmt:
    fmt: str
    args: List

@dataclass
class BinOp:
    op: str
    left: Any
    right: Any

@dataclass
class UnaryOp:
    op: str
    operand: Any

@dataclass
class VarRef:
    name: str

@dataclass
class BorrowExpr:
    mutable: bool
    expr: Any

@dataclass
class IntLit:
    value: int

@dataclass
class FloatLit:
    value: float

@dataclass
class StrLit:
    value: str

@dataclass
class BoolLit:
    value: bool

@dataclass
class CallExpr:
    func: str
    args: List

@dataclass
class MethodCall:
    obj: Any
    method: str
    args: List

@dataclass
class IndexExpr:
    obj: Any
    index: Any

@dataclass
class StringNew:
    value: str

@dataclass
class VecNew:
    pass

class ParseError(Exception):
    pass

# ── Parser ─────────────────────────────────────────────────────────────

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, tt: str) -> Token:
        t = self.peek()
        if t.type != tt:
            raise ParseError(f"Line {t.line}: expected {tt}, got {t.type!r} ({t.value!r})")
        return self.advance()

    def match(self, *types) -> bool:
        return self.peek().type in types

    # ── Top level ──────────────────────────────────────────────────────

    def parse_program(self) -> List:
        stmts = []
        while not self.match(TT_EOF):
            stmts.append(self.parse_top_level())
        return stmts

    def parse_top_level(self):
        if self.match(TT_FN):
            return self.parse_fn()
        return self.parse_stmt()

    # ── Function definition ────────────────────────────────────────────

    def parse_fn(self) -> FnDef:
        self.expect(TT_FN)
        name = self.expect(TT_IDENT).value
        self.expect(TT_LPAREN)
        params = []
        while not self.match(TT_RPAREN):
            pname = self.expect(TT_IDENT).value
            self.expect(TT_COLON)
            ptype = self.parse_type()
            params.append((pname, ptype))
            if self.match(TT_COMMA):
                self.advance()
        self.expect(TT_RPAREN)
        ret_type = None
        if self.match(TT_ARROW):
            self.advance()
            ret_type = self.parse_type()
        body = self.parse_block()
        return FnDef(name, params, ret_type, body)

    def parse_type(self) -> TypeNode:
        if self.match(TT_AMP):
            self.advance()
            mutable = False
            if self.match(TT_MUT):
                self.advance()
                mutable = True
            base = self.advance().value
            return TypeNode(f"&{base}", mutable)
        if self.match(TT_VEC):
            self.advance()
            self.expect(TT_LT)
            inner = self.advance().value
            self.expect(TT_GT)
            return TypeNode(f"Vec<{inner}>")
        tok = self.advance()
        return TypeNode(tok.value)

    def parse_block(self) -> List:
        self.expect(TT_LBRACE)
        stmts = []
        while not self.match(TT_RBRACE):
            stmts.append(self.parse_stmt())
        self.expect(TT_RBRACE)
        return stmts

    # ── Statements ─────────────────────────────────────────────────────

    def parse_stmt(self):
        t = self.peek()
        if t.type == TT_LET:
            return self.parse_let()
        if t.type == TT_RETURN:
            return self.parse_return()
        if t.type == TT_IF:
            return self.parse_if()
        if t.type == TT_WHILE:
            return self.parse_while()
        if t.type == TT_FOR:
            return self.parse_for()
        if t.type == TT_IDENT and t.value == "println":
            return self.parse_println()
        # assignment or expression statement
        expr = self.parse_expr()
        if self.match(TT_ASSIGN):
            self.advance()
            rhs = self.parse_expr()
            self.expect(TT_SEMI)
            if isinstance(expr, VarRef):
                return AssignStmt(expr.name, rhs)
            raise ParseError("Invalid assignment target")
        self.expect(TT_SEMI)
        return expr

    def parse_let(self) -> LetStmt:
        self.expect(TT_LET)
        mutable = False
        if self.match(TT_MUT):
            self.advance()
            mutable = True
        name = self.expect(TT_IDENT).value
        ty = None
        if self.match(TT_COLON):
            self.advance()
            ty = self.parse_type()
        self.expect(TT_ASSIGN)
        value = self.parse_expr()
        self.expect(TT_SEMI)
        return LetStmt(name, mutable, ty, value)

    def parse_return(self) -> ReturnStmt:
        self.expect(TT_RETURN)
        val = None
        if not self.match(TT_SEMI):
            val = self.parse_expr()
        self.expect(TT_SEMI)
        return ReturnStmt(val)

    def parse_if(self) -> IfStmt:
        self.expect(TT_IF)
        cond = self.parse_expr()
        then_b = self.parse_block()
        else_b = None
        if self.match(TT_ELSE):
            self.advance()
            if self.match(TT_IF):
                else_b = [self.parse_if()]
            else:
                else_b = self.parse_block()
        return IfStmt(cond, then_b, else_b)

    def parse_while(self) -> WhileStmt:
        self.expect(TT_WHILE)
        cond = self.parse_expr()
        body = self.parse_block()
        return WhileStmt(cond, body)

    def parse_for(self) -> ForStmt:
        self.expect(TT_FOR)
        var = self.expect(TT_IDENT).value
        self.expect(TT_IN)
        iterable = self.parse_expr()
        body = self.parse_block()
        return ForStmt(var, iterable, body)

    def parse_println(self) -> PrintlnStmt:
        self.advance()  # println
        self.expect(TT_BANG)
        self.expect(TT_LPAREN)
        fmt = self.expect(TT_STR_LIT).value.strip('"')
        args = []
        while self.match(TT_COMMA):
            self.advance()
            args.append(self.parse_expr())
        self.expect(TT_RPAREN)
        self.expect(TT_SEMI)
        return PrintlnStmt(fmt, args)

    # ── Expressions (Pratt-style precedence) ───────────────────────────

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.match(TT_OR):
            op = self.advance().value
            right = self.parse_and()
            left = BinOp(op, left, right)
        return left

    def parse_and(self):
        left = self.parse_eq()
        while self.match(TT_AND):
            op = self.advance().value
            right = self.parse_eq()
            left = BinOp(op, left, right)
        return left

    def parse_eq(self):
        left = self.parse_cmp()
        while self.match(TT_EQ, TT_NEQ):
            op = self.advance().value
            right = self.parse_cmp()
            left = BinOp(op, left, right)
        return left

    def parse_cmp(self):
        left = self.parse_add()
        while self.match(TT_LT, TT_GT, TT_LTE, TT_GTE):
            op = self.advance().value
            right = self.parse_add()
            left = BinOp(op, left, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.match(TT_PLUS, TT_MINUS):
            op = self.advance().value
            right = self.parse_mul()
            left = BinOp(op, left, right)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.match(TT_STAR, TT_SLASH, TT_PERCENT):
            op = self.advance().value
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self):
        if self.match(TT_BANG):
            self.advance()
            return UnaryOp("!", self.parse_unary())
        if self.match(TT_MINUS):
            self.advance()
            return UnaryOp("-", self.parse_unary())
        if self.match(TT_AMP):
            self.advance()
            mutable = False
            if self.match(TT_MUT):
                self.advance()
                mutable = True
            return BorrowExpr(mutable, self.parse_postfix())
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        while True:
            if self.match(TT_DOT):
                self.advance()
                method = self.expect(TT_IDENT).value
                self.expect(TT_LPAREN)
                args = []
                while not self.match(TT_RPAREN):
                    args.append(self.parse_expr())
                    if self.match(TT_COMMA):
                        self.advance()
                self.expect(TT_RPAREN)
                expr = MethodCall(expr, method, args)
            elif self.match(TT_LBRACKET):
                self.advance()
                idx = self.parse_expr()
                self.expect(TT_RBRACKET)
                expr = IndexExpr(expr, idx)
            else:
                break
        return expr

    def parse_primary(self):
        t = self.peek()
        if t.type == TT_INT_LIT:
            self.advance()
            return IntLit(int(t.value))
        if t.type == TT_FLOAT_LIT:
            self.advance()
            return FloatLit(float(t.value))
        if t.type == TT_STR_LIT:
            self.advance()
            return StrLit(t.value.strip('"'))
        if t.type == TT_BOOL_LIT:
            self.advance()
            return BoolLit(t.value == "true")
        if t.type == TT_LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TT_RPAREN)
            return expr
        if t.type == TT_IDENT:
            # Could be function call, String::new, Vec::new, or variable
            name = self.advance().value
            if self.match(TT_DCOLON):
                self.advance()
                method = self.expect(TT_IDENT).value
                self.expect(TT_LPAREN)
                args = []
                while not self.match(TT_RPAREN):
                    args.append(self.parse_expr())
                    if self.match(TT_COMMA):
                        self.advance()
                self.expect(TT_RPAREN)
                if name == "String" and method == "new":
                    return StringNew(args[0].value if args else "")
                if name == "Vec" and method == "new":
                    return VecNew()
                return CallExpr(f"{name}::{method}", args)
            if self.match(TT_LPAREN):
                self.advance()
                args = []
                while not self.match(TT_RPAREN):
                    args.append(self.parse_expr())
                    if self.match(TT_COMMA):
                        self.advance()
                self.expect(TT_RPAREN)
                return CallExpr(name, args)
            return VarRef(name)
        if t.type in (TT_STRING,):
            self.advance()
            if self.match(TT_DCOLON):
                self.advance()
                method = self.expect(TT_IDENT).value
                self.expect(TT_LPAREN)
                args = []
                while not self.match(TT_RPAREN):
                    args.append(self.parse_expr())
                    if self.match(TT_COMMA):
                        self.advance()
                self.expect(TT_RPAREN)
                if method == "new":
                    return StringNew(args[0].value if args else "")
            return VarRef(t.value)
        if t.type == TT_VEC:
            self.advance()
            if self.match(TT_DCOLON):
                self.advance()
                self.expect(TT_IDENT)  # "new"
                self.expect(TT_LPAREN)
                self.expect(TT_RPAREN)
                return VecNew()
        raise ParseError(f"Line {t.line}: unexpected token {t.type!r} ({t.value!r})")


def parse(source: str):
    tokens = tokenize(source)
    p = Parser(tokens)
    return p.parse_program()
'''

with open(os.path.join(COMPILER_DIR, "parser.py"), "w", encoding="utf-8") as f:
    f.write(parser_src)

# ─────────────────────────────────────────────
# typechecker.py  (contains BUG_1 through BUG_5)
# ─────────────────────────────────────────────
typechecker_src = r'''"""
MiniRust Type Checker
Contains 5 type-inference bugs for the Self-Healing Compiler challenge.
"""

from parser import (LetStmt, AssignStmt, ReturnStmt, IfStmt, WhileStmt,
    ForStmt, FnDef, PrintlnStmt, BinOp, UnaryOp, VarRef, BorrowExpr,
    IntLit, FloatLit, StrLit, BoolLit, CallExpr, MethodCall, IndexExpr,
    StringNew, VecNew, TypeNode)
from typing import Dict, List, Optional, Tuple, Any

class TypeCheckError(Exception):
    pass

class TypeEnv:
    """Tracks variable types and mutability in nested scopes."""
    def __init__(self):
        self.scopes: List[Dict[str, Tuple[str, bool]]] = [{}]  # (type, mutable)
        self.borrows: Dict[str, List[str]] = {}  # var -> list of borrow refs
        self.moved: set = set()

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def define(self, name: str, ty: str, mutable: bool = False):
        self.scopes[-1][name] = (ty, mutable)

    def lookup(self, name: str) -> Optional[Tuple[str, bool]]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def is_moved(self, name: str) -> bool:
        return name in self.moved

    def mark_moved(self, name: str):
        self.moved.add(name)

    def add_borrow(self, var: str, borrow_ref: str):
        self.borrows.setdefault(var, []).append(borrow_ref)

    def get_borrows(self, var: str) -> List[str]:
        return self.borrows.get(var, [])


class TypeChecker:
    def __init__(self):
        self.env = TypeEnv()
        self.functions: Dict[str, Tuple[List[str], Optional[str]]] = {}
        self.current_fn_ret: Optional[str] = None

    def check_program(self, stmts: List):
        # First pass: register all function signatures
        for stmt in stmts:
            if isinstance(stmt, FnDef):
                param_types = [p[1].name for p in stmt.params]
                ret_type = stmt.ret_type.name if stmt.ret_type else None
                self.functions[stmt.name] = (param_types, ret_type)
        # Second pass: check bodies
        for stmt in stmts:
            self.check_stmt(stmt)

    def check_stmt(self, stmt):
        if isinstance(stmt, FnDef):
            self.check_fn(stmt)
        elif isinstance(stmt, LetStmt):
            self.check_let(stmt)
        elif isinstance(stmt, AssignStmt):
            self.check_assign(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.check_return(stmt)
        elif isinstance(stmt, IfStmt):
            self.check_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self.check_while(stmt)
        elif isinstance(stmt, ForStmt):
            self.check_for(stmt)
        elif isinstance(stmt, PrintlnStmt):
            pass  # no type checking for println args in this version
        else:
            self.infer_type(stmt)  # expression statement

    def check_fn(self, fn: FnDef):
        prev_ret = self.current_fn_ret
        self.current_fn_ret = fn.ret_type.name if fn.ret_type else None
        self.env.push_scope()
        for pname, ptype in fn.params:
            self.env.define(pname, ptype.name, mutable=False)
        for stmt in fn.body:
            self.check_stmt(stmt)
        self.env.pop_scope()
        self.current_fn_ret = prev_ret

    def check_let(self, stmt: LetStmt):
        val_type = self.infer_type(stmt.value)
        declared_type = stmt.ty.name if stmt.ty else None

        if declared_type is not None:
            # BUG_1: Type compatibility check uses equality only — doesn't catch
            # f64 value assigned to i32 variable (should reject, but passes through
            # because numeric literal inference returns "f64" and we compare with ==)
            # A correct checker would call is_compatible(val_type, declared_type).
            if val_type != declared_type:
                # BUG_1: Missing numeric widening check — should also reject
                # f64->i32 but the condition below lets it slip through when
                # val_type is "f64" and declared_type is "i32"
                if not (val_type in ("i32", "f64") and declared_type in ("i32", "f64")):
                    raise TypeCheckError(
                        f"Type mismatch in let '{stmt.name}': "
                        f"declared {declared_type}, got {val_type}"
                    )
                # BUG_1: Should raise error here for f64->i32 narrowing
                # but we fall through silently

        # Move semantics for heap types
        if val_type in ("String", "Vec<i32>"):
            if isinstance(stmt.value, VarRef):
                if self.env.is_moved(stmt.value.name):
                    raise TypeCheckError(f"Use after move: '{stmt.value.name}'")
                self.env.mark_moved(stmt.value.name)

        effective_type = declared_type if declared_type else val_type
        self.env.define(stmt.name, effective_type, stmt.mutable)

    def check_assign(self, stmt: AssignStmt):
        info = self.env.lookup(stmt.name)
        if info is None:
            raise TypeCheckError(f"Undefined variable: '{stmt.name}'")
        var_type, mutable = info
        if not mutable:
            raise TypeCheckError(f"Cannot assign to immutable variable '{stmt.name}'")
        val_type = self.infer_type(stmt.value)
        if val_type != var_type:
            raise TypeCheckError(f"Type mismatch in assignment to '{stmt.name}'")

    def check_return(self, stmt: ReturnStmt):
        if stmt.value is None:
            ret_type = None
        else:
            ret_type = self.infer_type(stmt.value)

        # BUG_2: Return type is never actually validated against the function's
        # declared return type — the check is always skipped.
        # A correct checker would: if self.current_fn_ret != ret_type: raise ...
        if self.current_fn_ret is not None:
            pass  # BUG_2: Should be: if ret_type != self.current_fn_ret: raise ...

    def check_if(self, stmt: IfStmt):
        cond_type = self.infer_type(stmt.cond)
        if cond_type != "bool":
            raise TypeCheckError(f"If condition must be bool, got {cond_type}")
        self.env.push_scope()
        for s in stmt.then_block:
            self.check_stmt(s)
        self.env.pop_scope()
        if stmt.else_block:
            self.env.push_scope()
            for s in stmt.else_block:
                self.check_stmt(s)
            self.env.pop_scope()

    def check_while(self, stmt: WhileStmt):
        cond_type = self.infer_type(stmt.cond)
        if cond_type != "bool":
            raise TypeCheckError(f"While condition must be bool, got {cond_type}")
        self.env.push_scope()
        for s in stmt.body:
            self.check_stmt(s)
        self.env.pop_scope()

    def check_for(self, stmt: ForStmt):
        iter_type = self.infer_type(stmt.iterable)
        elem_type = "i32"  # default for Vec<i32> / range
        self.env.push_scope()
        self.env.define(stmt.var, elem_type)
        for s in stmt.body:
            self.check_stmt(s)
        self.env.pop_scope()

    def infer_type(self, expr) -> str:
        if isinstance(expr, IntLit):
            return "i32"
        if isinstance(expr, FloatLit):
            return "f64"
        if isinstance(expr, StrLit):
            return "&str"
        if isinstance(expr, BoolLit):
            return "bool"
        if isinstance(expr, StringNew):
            return "String"
        if isinstance(expr, VecNew):
            return "Vec<i32>"
        if isinstance(expr, VarRef):
            info = self.env.lookup(expr.name)
            if info is None:
                raise TypeCheckError(f"Undefined variable: '{expr.name}'")
            # BUG_5: Use-after-move not checked here — moved variables can be
            # referenced again without error
            return info[0]
        if isinstance(expr, BorrowExpr):
            inner_type = self.infer_type(expr.expr)
            if expr.mutable:
                # BUG_3: Mutable borrow allowed even when immutable borrow exists
                # A correct checker would verify no existing borrows of this variable
                if isinstance(expr.expr, VarRef):
                    borrows = self.env.get_borrows(expr.expr.name)
                    # BUG_3: Should check len(borrows) == 0 before allowing &mut
                    # but we add the borrow regardless
                    self.env.add_borrow(expr.expr.name, f"&mut_{expr.expr.name}")
                return f"&mut {inner_type}"
            else:
                if isinstance(expr.expr, VarRef):
                    self.env.add_borrow(expr.expr.name, f"&_{expr.expr.name}")
                return f"&{inner_type}"
        if isinstance(expr, BinOp):
            return self.infer_binop(expr)
        if isinstance(expr, UnaryOp):
            if expr.op == "!":
                return "bool"
            inner = self.infer_type(expr.operand)
            return inner
        if isinstance(expr, CallExpr):
            if expr.func in self.functions:
                _, ret = self.functions[expr.func]
                return ret if ret else "void"
            return "i32"  # unknown function, assume i32
        if isinstance(expr, MethodCall):
            return self.infer_method(expr)
        if isinstance(expr, IndexExpr):
            obj_type = self.infer_type(expr.obj)
            if obj_type == "Vec<i32>":
                return "i32"
            return "i32"
        return "unknown"

    def infer_binop(self, expr: BinOp) -> str:
        left = self.infer_type(expr.left)
        right = self.infer_type(expr.right)
        if expr.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
            return "bool"
        if expr.op in ("+", "-", "*", "/", "%"):
            if left == "f64" or right == "f64":
                return "f64"
            return "i32"
        return "unknown"

    def infer_method(self, expr: MethodCall) -> str:
        obj_type = self.infer_type(expr.obj)
        if expr.method == "push":
            # BUG_4: Vec<i32>.push() element type not validated —
            # pushing f64 into Vec<i32> is silently accepted
            # Correct: check that arg type == "i32"
            return "void"
        if expr.method == "len":
            return "i32"
        if expr.method == "pop":
            return "i32"
        if expr.method in ("to_string", "clone"):
            return obj_type
        return "unknown"


def typecheck(ast: List):
    tc = TypeChecker()
    tc.check_program(ast)
    return tc
'''

with open(os.path.join(COMPILER_DIR, "typechecker.py"), "w", encoding="utf-8") as f:
    f.write(typechecker_src)

# ─────────────────────────────────────────────
# codegen.py  (contains BUG_6 through BUG_10)
# ─────────────────────────────────────────────
codegen_src = r'''"""
MiniRust Code Generator — emits a simple IR / pseudo-bytecode.
Contains 5 memory/logic bugs for the Self-Healing Compiler challenge.
"""

from parser import (LetStmt, AssignStmt, ReturnStmt, IfStmt, WhileStmt,
    ForStmt, FnDef, PrintlnStmt, BinOp, UnaryOp, VarRef, BorrowExpr,
    IntLit, FloatLit, StrLit, BoolLit, CallExpr, MethodCall, IndexExpr,
    StringNew, VecNew, TypeNode)
from typing import List, Dict, Optional, Any
import sys

I32_MAX =  2147483647
I32_MIN = -2147483648

class IRInstruction:
    def __init__(self, op: str, *args):
        self.op = op
        self.args = list(args)

    def __repr__(self):
        return f"{self.op} {' '.join(str(a) for a in self.args)}"


class CodeGenError(Exception):
    pass


class CodeGen:
    def __init__(self):
        self.instructions: List[IRInstruction] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.symbol_table: Dict[str, str] = {}   # name -> temp register
        self.ref_counts: Dict[str, int] = {}      # temp -> ref count

    def fresh_temp(self) -> str:
        t = f"%t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def fresh_label(self) -> str:
        l = f"L{self.label_counter}"
        self.label_counter += 1
        return l

    def emit(self, op: str, *args):
        self.instructions.append(IRInstruction(op, *args))

    def inc_ref(self, temp: str):
        self.ref_counts[temp] = self.ref_counts.get(temp, 0) + 1
        self.emit("INC_REF", temp)

    def dec_ref(self, temp: str):
        self.ref_counts[temp] = self.ref_counts.get(temp, 0) - 1
        self.emit("DEC_REF", temp)

    def generate(self, stmts: List) -> List[IRInstruction]:
        for stmt in stmts:
            self.gen_stmt(stmt)
        return self.instructions

    def gen_stmt(self, stmt):
        if isinstance(stmt, FnDef):
            self.gen_fn(stmt)
        elif isinstance(stmt, LetStmt):
            self.gen_let(stmt)
        elif isinstance(stmt, AssignStmt):
            self.gen_assign(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.gen_return(stmt)
        elif isinstance(stmt, IfStmt):
            self.gen_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self.gen_while(stmt)
        elif isinstance(stmt, ForStmt):
            self.gen_for(stmt)
        elif isinstance(stmt, PrintlnStmt):
            self.gen_println(stmt)
        else:
            self.gen_expr(stmt)

    def gen_fn(self, fn: FnDef):
        self.emit("FUNC_BEGIN", fn.name)
        old_symbols = dict(self.symbol_table)
        for pname, ptype in fn.params:
            t = self.fresh_temp()
            self.symbol_table[pname] = t
            self.emit("LOAD_PARAM", t, pname)
            # BUG_8: Parameters passed by mutable reference are loaded by value —
            # mutations inside the function do not propagate back to caller.
            # Correct: use LOAD_PARAM_REF for &mut params.

        for s in fn.body:
            self.gen_stmt(s)
        self.symbol_table = old_symbols
        self.emit("FUNC_END", fn.name)

    def gen_let(self, stmt: LetStmt):
        val_temp = self.gen_expr(stmt.value)
        self.symbol_table[stmt.name] = val_temp

        # Track ref count for heap types
        ty = stmt.ty.name if stmt.ty else ""
        if ty in ("String", "Vec<i32>"):
            self.inc_ref(val_temp)

    def gen_assign(self, stmt: AssignStmt):
        if stmt.name not in self.symbol_table:
            raise CodeGenError(f"Undefined variable in assignment: '{stmt.name}'")
        old_temp = self.symbol_table[stmt.name]
        new_temp = self.gen_expr(stmt.value)
        # Decrement ref count of old value before reassigning
        self.dec_ref(old_temp)
        self.symbol_table[stmt.name] = new_temp
        self.emit("STORE", stmt.name, new_temp)

    def gen_return(self, stmt: ReturnStmt):
        if stmt.value is not None:
            val = self.gen_expr(stmt.value)
            self.emit("RETURN", val)
        else:
            self.emit("RETURN")

    def gen_if(self, stmt: IfStmt):
        cond = self.gen_expr(stmt.cond)
        else_label = self.fresh_label()
        end_label = self.fresh_label()
        self.emit("JUMP_IF_FALSE", cond, else_label)
        for s in stmt.then_block:
            self.gen_stmt(s)
        self.emit("JUMP", end_label)
        self.emit("LABEL", else_label)
        if stmt.else_block:
            for s in stmt.else_block:
                self.gen_stmt(s)
        self.emit("LABEL", end_label)

    def gen_while(self, stmt: WhileStmt):
        loop_label = self.fresh_label()
        end_label = self.fresh_label()
        self.emit("LABEL", loop_label)
        cond = self.gen_expr(stmt.cond)
        self.emit("JUMP_IF_FALSE", cond, end_label)
        for s in stmt.body:
            self.gen_stmt(s)
        self.emit("JUMP", loop_label)
        self.emit("LABEL", end_label)

    def gen_for(self, stmt: ForStmt):
        iter_temp = self.gen_expr(stmt.iterable)
        idx_temp = self.fresh_temp()
        len_temp = self.fresh_temp()
        loop_label = self.fresh_label()
        end_label = self.fresh_label()

        self.emit("CONST", idx_temp, 0)
        self.emit("VEC_LEN", len_temp, iter_temp)
        self.emit("LABEL", loop_label)
        cmp_temp = self.fresh_temp()
        self.emit("LT", cmp_temp, idx_temp, len_temp)
        self.emit("JUMP_IF_FALSE", cmp_temp, end_label)

        elem_temp = self.fresh_temp()
        self.emit("VEC_GET", elem_temp, iter_temp, idx_temp)
        # BUG_7: Loop variable stored in symbol_table but after loop ends,
        # the loop var remains in scope and holds stale last-element value.
        # A correct codegen would restore the pre-loop symbol table after the loop.
        self.symbol_table[stmt.var] = elem_temp

        for s in stmt.body:
            self.gen_stmt(s)

        self.emit("ADD", idx_temp, idx_temp, "%const_1")
        self.emit("JUMP", loop_label)
        self.emit("LABEL", end_label)
        # BUG_7: Missing: del self.symbol_table[stmt.var]  (or scope restore)

    def gen_println(self, stmt: PrintlnStmt):
        arg_temps = [self.gen_expr(a) for a in stmt.args]
        self.emit("PRINTLN", repr(stmt.fmt), *arg_temps)

    def gen_expr(self, expr) -> str:
        if isinstance(expr, IntLit):
            t = self.fresh_temp()
            self.emit("CONST", t, expr.value)
            return t
        if isinstance(expr, FloatLit):
            t = self.fresh_temp()
            self.emit("CONST_F", t, expr.value)
            return t
        if isinstance(expr, StrLit):
            t = self.fresh_temp()
            self.emit("CONST_STR", t, repr(expr.value))
            return t
        if isinstance(expr, BoolLit):
            t = self.fresh_temp()
            self.emit("CONST_BOOL", t, expr.value)
            return t
        if isinstance(expr, StringNew):
            t = self.fresh_temp()
            self.emit("STRING_NEW", t, repr(expr.value))
            self.inc_ref(t)
            return t
        if isinstance(expr, VecNew):
            t = self.fresh_temp()
            self.emit("VEC_NEW", t)
            self.inc_ref(t)
            return t
        if isinstance(expr, VarRef):
            if expr.name not in self.symbol_table:
                raise CodeGenError(f"Undefined variable: '{expr.name}'")
            return self.symbol_table[expr.name]
        if isinstance(expr, BorrowExpr):
            inner = self.gen_expr(expr.expr)
            t = self.fresh_temp()
            prefix = "BORROW_MUT" if expr.mutable else "BORROW"
            self.emit(prefix, t, inner)
            return t
        if isinstance(expr, BinOp):
            return self.gen_binop(expr)
        if isinstance(expr, UnaryOp):
            operand = self.gen_expr(expr.operand)
            t = self.fresh_temp()
            if expr.op == "!":
                self.emit("NOT", t, operand)
            else:
                self.emit("NEG", t, operand)
            return t
        if isinstance(expr, CallExpr):
            arg_temps = [self.gen_expr(a) for a in expr.args]
            t = self.fresh_temp()
            self.emit("CALL", t, expr.func, *arg_temps)
            return t
        if isinstance(expr, MethodCall):
            return self.gen_method(expr)
        if isinstance(expr, IndexExpr):
            obj = self.gen_expr(expr.obj)
            idx = self.gen_expr(expr.index)
            t = self.fresh_temp()
            self.emit("VEC_GET", t, obj, idx)
            return t
        raise CodeGenError(f"Cannot generate code for {type(expr).__name__}")

    def gen_binop(self, expr: BinOp) -> str:
        left = self.gen_expr(expr.left)
        right = self.gen_expr(expr.right)
        t = self.fresh_temp()
        op_map = {
            "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
            "==": "EQ", "!=": "NEQ", "<": "LT", ">": "GT",
            "<=": "LTE", ">=": "GTE", "&&": "AND", "||": "OR",
        }
        ir_op = op_map.get(expr.op, "UNKNOWN")

        if ir_op == "ADD":
            # BUG_10: Integer overflow not detected — result wraps silently.
            # A correct codegen would emit overflow check instructions here.
            self.emit("ADD", t, left, right)
            # BUG_10: Missing overflow check:
            # self.emit("CHECK_OVERFLOW_I32", t)
        else:
            self.emit(ir_op, t, left, right)
        return t

    def gen_method(self, expr: MethodCall) -> str:
        obj = self.gen_expr(expr.obj)
        t = self.fresh_temp()

        if expr.method == "push":
            elem = self.gen_expr(expr.args[0]) if expr.args else "%undef"
            # BUG_9: Vec grow/push uses off-by-one — emits GET after size with
            # index = old_len instead of old_len (0-indexed last = old_len-1+1 = old_len).
            # In a real implementation this means the first element is overwritten.
            self.emit("VEC_PUSH", obj, elem)
            # BUG_9: Should emit VEC_RESIZE then VEC_SET at new_len-1,
            # but we emit at index new_len (off by one, losing element 0 on wrap)
            self.emit("CONST", t, 0)
            return t

        if expr.method == "len":
            self.emit("VEC_LEN", t, obj)
            return t

        if expr.method == "pop":
            self.emit("VEC_POP", t, obj)
            return t

        if expr.method in ("to_string", "clone"):
            self.emit("CLONE", t, obj)
            # BUG_6: String clone increments ref count but the original also gets
            # decremented at end of scope — effectively a double-free.
            self.inc_ref(t)
            # BUG_6: Should NOT inc_ref here because CLONE already sets refcount=1
            return t

        self.emit("METHOD_CALL", t, obj, expr.method)
        return t


def codegen(ast: List) -> List[IRInstruction]:
    cg = CodeGen()
    return cg.generate(ast)
'''

with open(os.path.join(COMPILER_DIR, "codegen.py"), "w", encoding="utf-8") as f:
    f.write(codegen_src)

# ─────────────────────────────────────────────
# pipeline.py  (contains BUG_11 through BUG_15)
# ─────────────────────────────────────────────
pipeline_src = r'''"""
MiniRust Parallel Compilation Pipeline
Contains 5 threading/concurrency bugs for the Self-Healing Compiler challenge.
"""

import threading
import queue
import time
from typing import List, Dict, Any, Optional
from lexer import tokenize
from parser import parse
from typechecker import typecheck
from codegen import codegen

# BUG_13: Barrier initialized with wrong count (2 instead of dynamic worker count)
# This causes permanent deadlock when more than 2 files are compiled in parallel.
_WRONG_BARRIER_COUNT = 2
_barrier = threading.Barrier(_WRONG_BARRIER_COUNT)  # BUG_13

# Shared symbol table — accessed without lock (BUG_11)
shared_symbol_table: Dict[str, Any] = {}  # BUG_11: no lock protecting this

# Results list — written from threads while main thread iterates (BUG_15)
compilation_results: List[Dict] = []  # BUG_15


def compile_single(source: str, filename: str) -> Dict:
    """Compile one MiniRust source file and return result dict."""
    try:
        tokens = tokenize(source)
        ast = parse(source)
        typecheck(ast)
        ir = codegen(ast)
        return {"file": filename, "status": "ok", "ir": ir}
    except Exception as e:
        return {"file": filename, "status": "error", "message": str(e)}


def worker_thread(task_queue: queue.Queue, result_queue: queue.Queue):
    """Worker: pull tasks from queue, compile, push results."""
    while True:
        try:
            item = task_queue.get(timeout=1)
        except queue.Empty:
            break

        source, filename = item

        # BUG_11: Writing to shared_symbol_table without holding any lock
        shared_symbol_table[filename] = "in_progress"  # BUG_11: race condition

        result = compile_single(source, filename)

        # BUG_11: Another unsynchronized write
        shared_symbol_table[filename] = result.get("status", "error")  # BUG_11

        try:
            # BUG_13: Barrier wait — blocks forever if more than 2 workers
            _barrier.wait(timeout=5)  # BUG_13
        except threading.BrokenBarrierError:
            pass

        # BUG_14: Exception in worker thread is silently caught and swallowed
        # The result_queue.put is inside a try-except that catches everything,
        # so if put() raises, the main thread will hang waiting for results.
        try:
            result_queue.put(result)
            if result["status"] == "error":
                raise RuntimeError(f"Compile error in {filename}")  # BUG_14: raised but caught below
        except Exception:
            pass  # BUG_14: Exception swallowed — main thread never gets result


def compile_parallel(sources: List[tuple], num_workers: int = 4) -> List[Dict]:
    """
    Compile multiple MiniRust files in parallel.
    sources: list of (source_code, filename) tuples
    Returns list of result dicts.
    """
    task_queue: queue.Queue = queue.Queue()
    result_queue: queue.Queue = queue.Queue()

    for item in sources:
        task_queue.put(item)

    threads = []
    for i in range(min(num_workers, len(sources))):
        # BUG_12: Classic Python closure bug — `i` is captured by reference in lambda.
        # All threads end up using the final value of `i`.
        t = threading.Thread(
            target=lambda: worker_thread(task_queue, result_queue),  # BUG_12: `i` not used here, but
            daemon=True                                               # see below for the captured-var pattern
        )
        # BUG_12 (full version): If we used `target=lambda idx=i: ...` it would be correct,
        # but the line below shows the buggy pattern applied to thread naming:
        t.name = (lambda: f"worker-{i}")()  # BUG_12: always captures last value of i
        threads.append(t)
        t.start()

    results = []
    expected = len(sources)
    received = 0

    # BUG_15: Main thread iterates compilation_results while worker appends to it.
    # This is a separate list from result_queue — workers append here directly.
    def background_collector():
        while received < expected:
            try:
                r = result_queue.get(timeout=0.5)
                compilation_results.append(r)  # BUG_15: append during potential iteration
            except queue.Empty:
                continue

    collector = threading.Thread(target=background_collector, daemon=True)
    collector.start()

    # BUG_15: Main thread iterates compilation_results while background_collector modifies it
    deadline = time.time() + 30
    while len(results) < expected and time.time() < deadline:
        for r in compilation_results:  # BUG_15: iterating list being modified concurrently
            if r not in results:
                results.append(r)
        time.sleep(0.05)

    for t in threads:
        t.join(timeout=2)

    return results
'''

with open(os.path.join(COMPILER_DIR, "pipeline.py"), "w", encoding="utf-8") as f:
    f.write(pipeline_src)

# ─────────────────────────────────────────────
# main.py
# ─────────────────────────────────────────────
main_src = r'''"""MiniRust Compiler entry point. Usage: python main.py source.mr"""

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
'''

with open(os.path.join(COMPILER_DIR, "main.py"), "w", encoding="utf-8") as f:
    f.write(main_src)

# ─────────────────────────────────────────────
# bugs_manifest.json  (HIDDEN — kept by organizer)
# ─────────────────────────────────────────────
bugs_manifest = {
    "bugs": [
        {
            "id": "BUG_1",
            "file": "typechecker.py",
            "description": "Allows assigning f64 value to i32 variable without cast",
            "fix": "In check_let, raise TypeCheckError when val_type='f64' and declared_type='i32'"
        },
        {
            "id": "BUG_2",
            "file": "typechecker.py",
            "description": "Function return type not checked against actual return expression type",
            "fix": "In check_return, add: if ret_type != self.current_fn_ret: raise TypeCheckError(...)"
        },
        {
            "id": "BUG_3",
            "file": "typechecker.py",
            "description": "Mutable borrow allowed when immutable borrow still in scope",
            "fix": "In infer_type BorrowExpr with mutable=True, check that len(borrows)==0 first"
        },
        {
            "id": "BUG_4",
            "file": "typechecker.py",
            "description": "Vec<i32> element type not tracked — push accepts f64",
            "fix": "In infer_method 'push', check that arg type == 'i32'"
        },
        {
            "id": "BUG_5",
            "file": "typechecker.py",
            "description": "Use-after-move not detected in VarRef inference",
            "fix": "In infer_type VarRef, add: if self.env.is_moved(expr.name): raise TypeCheckError"
        },
        {
            "id": "BUG_6",
            "file": "codegen.py",
            "description": "String clone double-increments ref count (double-free equivalent)",
            "fix": "In gen_method 'clone'/'to_string', remove the extra inc_ref call"
        },
        {
            "id": "BUG_7",
            "file": "codegen.py",
            "description": "Loop variable persists in symbol_table after loop exits",
            "fix": "After for-loop LABEL end, remove loop var from symbol_table"
        },
        {
            "id": "BUG_8",
            "file": "codegen.py",
            "description": "Mutable reference parameters loaded by value — mutations not propagated",
            "fix": "Use LOAD_PARAM_REF for &mut parameters and STORE_DEREF on return"
        },
        {
            "id": "BUG_9",
            "file": "codegen.py",
            "description": "VEC_PUSH off-by-one — first element overwritten on grow",
            "fix": "Emit VEC_RESIZE then VEC_SET at index new_len-1, not new_len"
        },
        {
            "id": "BUG_10",
            "file": "codegen.py",
            "description": "i32 addition overflow not detected — wraps silently",
            "fix": "After ADD, emit CHECK_OVERFLOW_I32 instruction"
        },
        {
            "id": "BUG_11",
            "file": "pipeline.py",
            "description": "shared_symbol_table accessed without lock — race condition",
            "fix": "Add threading.Lock() and acquire/release around all shared_symbol_table accesses"
        },
        {
            "id": "BUG_12",
            "file": "pipeline.py",
            "description": "Thread closure captures loop variable i by reference",
            "fix": "Pass i as default argument: target=lambda idx=i: worker_thread(...)"
        },
        {
            "id": "BUG_13",
            "file": "pipeline.py",
            "description": "Barrier initialized with count=2 instead of num_workers — permanent deadlock",
            "fix": "Create barrier with threading.Barrier(num_workers) dynamically"
        },
        {
            "id": "BUG_14",
            "file": "pipeline.py",
            "description": "Exception in worker thread swallowed silently — main thread hangs",
            "fix": "Remove bare except clause; let exceptions propagate or use result_queue.put({'error': ...})"
        },
        {
            "id": "BUG_15",
            "file": "pipeline.py",
            "description": "compilation_results list iterated in main thread while appended in background",
            "fix": "Use threading.Lock() to protect compilation_results or collect only from result_queue"
        }
    ]
}

with open(os.path.join(BASE, "bugs_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(bugs_manifest, f, indent=2)

# ─────────────────────────────────────────────
# Regression tests (200 .mr files)
# ─────────────────────────────────────────────
import random
random.seed(42)

def write_test(idx: int, source: str, expected: str):
    fname = f"test_{idx:03d}.mr"
    with open(os.path.join(TESTS_DIR, fname), "w", encoding="utf-8") as f:
        f.write(source)
    with open(os.path.join(EXPECTED_DIR, f"test_{idx:03d}.expected"), "w", encoding="utf-8") as f:
        f.write(expected)

test_idx = 0

# ── 50 simple variable + arithmetic programs ──────────────────────────
VAR_TEMPLATES = [
    ("let x: i32 = {a};\nlet y: i32 = {b};\nlet z: i32 = x + y;\nprintln!(\"{{}}\", z);\n",
     lambda a, b: str(a + b)),
    ("let x: i32 = {a};\nlet y: i32 = {b};\nlet z: i32 = x * y;\nprintln!(\"{{}}\", z);\n",
     lambda a, b: str(a * b)),
    ("let x: i32 = {a};\nlet y: i32 = {b};\nlet z: i32 = x - y;\nprintln!(\"{{}}\", z);\n",
     lambda a, b: str(a - b)),
    ("let mut x: i32 = {a};\nx = x + {b};\nprintln!(\"{{}}\", x);\n",
     lambda a, b: str(a + b)),
    ("let a: i32 = {a};\nlet b: i32 = {b};\nlet c: i32 = a + b;\nlet d: i32 = c * 2;\nprintln!(\"{{}}\", d);\n",
     lambda a, b: str((a + b) * 2)),
]

for i in range(50):
    tmpl, expected_fn = VAR_TEMPLATES[i % len(VAR_TEMPLATES)]
    a, b = random.randint(1, 100), random.randint(1, 100)
    src = tmpl.format(a=a, b=b)
    write_test(test_idx, src, expected_fn(a, b))
    test_idx += 1

# ── 50 function definition + call programs ─────────────────────────────
FN_TEMPLATES = [
    "fn add(a: i32, b: i32) -> i32 {{\n    return a + b;\n}}\nlet result: i32 = add({a}, {b});\nprintln!(\"{{}}\", result);\n",
    "fn square(x: i32) -> i32 {{\n    return x * x;\n}}\nlet result: i32 = square({a});\nprintln!(\"{{}}\", result);\n",
    "fn max_val(a: i32, b: i32) -> i32 {{\n    if a > b {{\n        return a;\n    }} else {{\n        return b;\n    }}\n}}\nlet result: i32 = max_val({a}, {b});\nprintln!(\"{{}}\", result);\n",
    "fn double(x: i32) -> i32 {{\n    return x * 2;\n}}\nfn quad(x: i32) -> i32 {{\n    return double(double(x));\n}}\nlet result: i32 = quad({a});\nprintln!(\"{{}}\", result);\n",
    "fn is_positive(x: i32) -> bool {{\n    return x > 0;\n}}\nlet result: bool = is_positive({a});\nprintln!(\"{{}}\", result);\n",
]

for i in range(50):
    tmpl = FN_TEMPLATES[i % len(FN_TEMPLATES)]
    a, b = random.randint(1, 50), random.randint(1, 50)
    src = tmpl.format(a=a, b=b)
    write_test(test_idx, src, "ok")
    test_idx += 1

# ── 40 ownership and borrowing programs ────────────────────────────────
OWN_TEMPLATES = [
    'let x: String = String::new("hello");\nlet y: &String = &x;\nprintln!("{}", y);\n',
    'let mut s: String = String::new("world");\nprintln!("{}", s);\n',
    'let mut v: Vec<i32> = Vec::new();\nv.push(1);\nv.push(2);\nlet n: i32 = v.len();\nprintln!("{}", n);\n',
    'let x: String = String::new("abc");\nlet r: &String = &x;\nprintln!("{}", r);\n',
    'let a: i32 = 10;\nlet b: &i32 = &a;\nprintln!("{}", b);\n',
    'let mut x: i32 = 5;\nlet r: &mut i32 = &mut x;\nprintln!("{}", r);\n',
    'let s: String = String::new("test");\nlet r1: &String = &s;\nlet r2: &String = &s;\nprintln!("{}", r1);\n',
    'let v: Vec<i32> = Vec::new();\nlet r: &Vec<i32> = &v;\nprintln!("{}", r.len());\n',
]

for i in range(40):
    src = OWN_TEMPLATES[i % len(OWN_TEMPLATES)]
    write_test(test_idx, src, "ok")
    test_idx += 1

# ── 30 control flow programs ───────────────────────────────────────────
CF_TEMPLATES = [
    "let x: i32 = {a};\nif x > 0 {{\n    println!(\"{{}}\", x);\n}}\n",
    "let mut i: i32 = 0;\nwhile i < {a} {{\n    i = i + 1;\n}}\nprintln!(\"{{}}\", i);\n",
    "let x: i32 = {a};\nif x > 50 {{\n    println!(\"big\");\n}} else {{\n    println!(\"small\");\n}}\n",
    "let mut sum: i32 = 0;\nlet mut i: i32 = 1;\nwhile i <= {a} {{\n    sum = sum + i;\n    i = i + 1;\n}}\nprintln!(\"{{}}\", sum);\n",
    "let x: i32 = {a};\nif x == 0 {{\n    println!(\"zero\");\n}} else if x > 0 {{\n    println!(\"positive\");\n}} else {{\n    println!(\"negative\");\n}}\n",
]

for i in range(30):
    tmpl = CF_TEMPLATES[i % len(CF_TEMPLATES)]
    a = random.randint(1, 20)
    src = tmpl.format(a=a)
    write_test(test_idx, src, "ok")
    test_idx += 1

# ── 30 Vec operations programs ─────────────────────────────────────────
VEC_TEMPLATES = [
    "let mut v: Vec<i32> = Vec::new();\nv.push({a});\nv.push({b});\nprintln!(\"{{}}\", v.len());\n",
    "let mut v: Vec<i32> = Vec::new();\nv.push(1);\nv.push(2);\nv.push(3);\nlet first: i32 = v[0];\nprintln!(\"{{}}\", first);\n",
    "let mut v: Vec<i32> = Vec::new();\nlet mut i: i32 = 0;\nwhile i < {a} {{\n    v.push(i);\n    i = i + 1;\n}}\nprintln!(\"{{}}\", v.len());\n",
    "let mut v: Vec<i32> = Vec::new();\nv.push({a});\nv.push({b});\nlet n: i32 = v.len();\nprintln!(\"{{}}\", n);\n",
    "fn sum_vec(v: Vec<i32>) -> i32 {{\n    let mut s: i32 = 0;\n    let mut i: i32 = 0;\n    while i < v.len() {{\n        s = s + v[i];\n        i = i + 1;\n    }}\n    return s;\n}}\nlet mut v: Vec<i32> = Vec::new();\nv.push({a});\nv.push({b});\nlet result: i32 = sum_vec(v);\nprintln!(\"{{}}\", result);\n",
]

for i in range(30):
    tmpl = VEC_TEMPLATES[i % len(VEC_TEMPLATES)]
    a, b = random.randint(1, 20), random.randint(1, 20)
    src = tmpl.format(a=a, b=b)
    write_test(test_idx, src, "ok")
    test_idx += 1

# ─────────────────────────────────────────────
# README.md
# ─────────────────────────────────────────────
readme = """# CSE-P4: Self-Healing Compiler — MiniRust

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
"""

with open(os.path.join(BASE, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme)

print("CSE-P4 generation complete.")
print(f"  Compiler files: {COMPILER_DIR}")
print(f"  Regression tests: {TESTS_DIR}")
print(f"  Total test files: {test_idx}")
