"""
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
