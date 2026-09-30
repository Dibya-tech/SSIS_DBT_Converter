"""Translate the SSIS expression language into SQL (PRD section 6.2).

SSIS expressions use a C-like syntax (used in Derived Columns, Conditional
Splits, and variables). This is a pragmatic translator covering the common
constructs; anything it cannot map confidently is returned flagged so the
caller can grade it Warning and emit a commented placeholder.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..dialects.base import Dialect


@dataclass
class ExprResult:
    sql: str
    confident: bool
    note: str = ""


# SSIS cast tokens -> SQL types
_DT_CAST = {
    "DT_WSTR": "varchar",
    "DT_STR": "varchar",
    "DT_I4": "int",
    "DT_I8": "bigint",
    "DT_R8": "float",
    "DT_NUMERIC": "numeric",
    "DT_BOOL": "boolean",
    "DT_DBDATE": "date",
    "DT_DBTIMESTAMP": "timestamp",
    "DT_GUID": "varchar",
}


def translate(expr: str, dialect: Dialect) -> ExprResult:
    if not expr or not expr.strip():
        return ExprResult("", True)
    original = expr
    s = expr.strip()
    confident = True
    notes = []

    # (DT_WSTR,50)[Col]  ->  cast(col as varchar(50))
    def _cast_repl(m):
        dt = m.group("dt").upper()
        size = m.group("size")
        operand = m.group("operand")
        sqltype = _DT_CAST.get(dt, "varchar")
        if size and sqltype in ("varchar", "numeric"):
            sqltype = f"{sqltype}({size})"
        return dialect.cast(_col(operand), sqltype)

    s = re.sub(
        r"\(\s*(?P<dt>DT_[A-Z0-9_]+)\s*(?:,\s*(?P<size>\d+)\s*)?\)\s*(?P<operand>\[[^\]]+\]|\w+)",
        _cast_repl, s,
    )

    # @[User::Var] or @[$Project::Param] -> {{ var('Var') }}
    s = re.sub(r"@\[\$?[A-Za-z]+::([A-Za-z0-9_]+)\]", r"{{ var('\1') }}", s)
    s = re.sub(r"@\[([A-Za-z0-9_]+)\]", r"{{ var('\1') }}", s)

    # ISNULL([Col]) -> col is null
    s = re.sub(r"ISNULL\s*\(\s*(\[[^\]]+\]|\w+)\s*\)",
               lambda m: f"{_col(m.group(1))} is null", s, flags=re.I)

    # ternary  cond ? a : b  -> case when cond then a else b end
    s = _translate_ternary(s)

    # string functions passthrough (UPPER, LOWER, TRIM, LEN/LENGTH)
    s = re.sub(r"\bUPPER\s*\(", "upper(", s, flags=re.I)
    s = re.sub(r"\bLOWER\s*\(", "lower(", s, flags=re.I)
    s = re.sub(r"\bTRIM\s*\(", "trim(", s, flags=re.I)
    s = re.sub(r"\bLEN\s*\(", "length(", s, flags=re.I)

    # operators
    s = s.replace("==", "=").replace("!=", "<>")
    s = re.sub(r"&&", " and ", s)
    s = re.sub(r"\|\|", " or ", s)  # SSIS logical OR (note: differs from concat)

    # string literals: SSIS uses double quotes -> single quotes
    s = re.sub(r'"([^"]*)"', r"'\1'", s)

    # column refs [Col] -> col
    s = re.sub(r"\[([^\]]+)\]", lambda m: _col(m.group(0)), s)

    # detect leftover unmapped SSIS functions
    leftover = re.findall(r"\b([A-Z][A-Z_]{2,})\s*\(", s)
    if leftover:
        confident = False
        notes.append(f"unmapped function(s): {', '.join(sorted(set(leftover)))}")

    return ExprResult(sql=s.strip(), confident=confident,
                      note="; ".join(notes) if notes else "")


def _col(token: str) -> str:
    """Normalize a [Column Name] or bare column into a SQL identifier."""
    token = token.strip()
    if token.startswith("[") and token.endswith("]"):
        token = token[1:-1]
    from ..ir.model import sanitize_identifier
    return sanitize_identifier(token)


def _translate_ternary(s: str) -> str:
    """Convert  cond ? a : b  into  case when cond then a else b end.

    Handles a single (outermost) ternary; nested ternaries recurse.
    """
    depth = 0
    q_idx = -1
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "?" and depth == 0:
            q_idx = i
            break
    if q_idx == -1:
        return s
    # find matching ':' at same depth
    depth = 0
    c_idx = -1
    for i in range(q_idx + 1, len(s)):
        ch = s[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "?" and depth == 0:
            # nested ternary before we found our colon; skip its colon
            depth += 100
        elif ch == ":" and depth == 0:
            c_idx = i
            break
        elif ch == ":" and depth >= 100:
            depth -= 100
    if c_idx == -1:
        return s
    cond = s[:q_idx].strip()
    a = s[q_idx + 1:c_idx].strip()
    b = s[c_idx + 1:].strip()
    return f"case when {cond} then {_translate_ternary(a)} else {_translate_ternary(b)} end"
