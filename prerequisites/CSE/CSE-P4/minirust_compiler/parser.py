"""MiniRust Parser — builds an AST from the token list."""

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
