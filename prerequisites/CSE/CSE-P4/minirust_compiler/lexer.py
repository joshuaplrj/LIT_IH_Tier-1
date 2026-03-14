"""MiniRust Lexer — tokenizes source into a flat token list."""

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
