"""
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
