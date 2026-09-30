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
    origin: str = ""   # original SSIS expression, for -- SSIS: annotations


# SSIS cast tokens -> SQL types
_DT_CAST = {
    "DT_WSTR":        "varchar",
    "DT_STR":         "varchar",
    "DT_I1":          "tinyint",
    "DT_I2":          "smallint",
    "DT_I4":          "int",
    "DT_I8":          "bigint",
    "DT_UI1":         "tinyint",
    "DT_UI2":         "smallint",
    "DT_UI4":         "int",
    "DT_UI8":         "bigint",
    "DT_R4":          "float",
    "DT_R8":          "float",
    "DT_NUMERIC":     "numeric",
    "DT_DECIMAL":     "decimal",
    "DT_BOOL":        "boolean",
    "DT_DBDATE":      "date",
    "DT_DBTIMESTAMP": "timestamp",
    "DT_DBTIMESTAMPOFFSET": "timestamp_tz",
    "DT_CY":          "numeric(19,4)",
    "DT_GUID":        "varchar(36)",
    "DT_BYTES":       "binary",
    "DT_IMAGE":       "binary",
}


def translate(expr: str, dialect: Dialect) -> ExprResult:
    if not expr or not expr.strip():
        return ExprResult("", True)
    original = expr
    s = expr.strip()
    confident = True
    notes = []

    # SSIS cast syntax comes in two forms:
    #   (a) (DT_WSTR,50)[Col]          -- column/word operand
    #   (b) (DT_DBTIMESTAMP)(@[Var])   -- parenthesised sub-expression operand
    #
    # We handle (b) by first translating the inner sub-expression, then wrapping.
    # Run in a loop so nested casts are fully resolved.
    def _cast_repl(m):
        dt   = m.group("dt").upper()
        size = m.group("size")
        raw_operand = m.group("operand") or m.group("paren_operand") or ""
        # Recursively translate inner expression (handles @[Var], ternary, etc.)
        inner = translate(raw_operand.strip("()"), dialect)
        sqltype = _DT_CAST.get(dt, "varchar")
        if size and sqltype in ("varchar", "numeric", "decimal"):
            # size may be "50" or "10,2" (precision,scale) — use as-is
            sqltype = f"{sqltype}({size})"
        translated = inner.sql if inner.sql else _col(raw_operand)
        return dialect.cast(translated, sqltype)

    # Pattern covers both (a) column/word and (b) (parenthesised sub-expression).
    # size captures the first numeric arg (e.g. 50 in DT_WSTR,50); for two-arg
    # types like DT_NUMERIC,10,2 we capture "10,2" so the type becomes numeric(10,2).
    s = re.sub(
        r"\(\s*(?P<dt>DT_[A-Z0-9_]+)\s*(?:,\s*(?P<size>\d+(?:\s*,\s*\d+)?)\s*)?\)"
        r"\s*(?:(?P<paren_operand>\([^)]*\))|(?P<operand>\[[^\]]+\]|\w+))",
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

    # NULL(DT_TYPE) -> CAST(NULL AS <type>)  — SSIS null-literal constructor
    def _null_repl(m):
        dt = m.group(1).upper()
        sqltype = _DT_CAST.get(dt, "varchar")
        return f"cast(null as {sqltype})"

    s = re.sub(
        r"\bNULL\s*\(\s*(DT_[A-Z0-9_]+)\s*(?:,\s*\d+\s*)?\)",
        _null_repl, s, flags=re.I,
    )

    # GETDATE() -> dialect current_timestamp
    s = re.sub(r"\bGETDATE\s*\(\s*\)", dialect.current_timestamp(), s, flags=re.I)

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

    # String concatenation: SSIS uses + for both arithmetic and string concat.
    # Heuristic: if the expression contains any single-quoted string literal, all
    # + operators are string concatenation -> use dialect concat operator (|| in
    # Snowflake/Databricks, + in T-SQL).
    if "'" in s and "+" in s:
        concat_op = dialect.concat("__A__", "__B__")
        # detect which operator the dialect uses by inspecting its output
        if "||" in concat_op:
            s = re.sub(r"\s*\+\s*", " || ", s)
        elif concat_op == "__A__ + __B__":
            pass  # T-SQL keeps +
        else:
            # dialect wraps in CONCAT() — rebuild the full chain
            parts = [p.strip() for p in re.split(r"\+", s)]
            if len(parts) > 1:
                s = parts[0]
                for part in parts[1:]:
                    s = dialect.concat(s, part)

    # column refs [Col] -> col
    s = re.sub(r"\[([^\]]+)\]", lambda m: _col(m.group(0)), s)

    # detect leftover unmapped SSIS functions
    leftover = re.findall(r"\b([A-Z][A-Z_]{2,})\s*\(", s)
    if leftover:
        confident = False
        notes.append(f"unmapped function(s): {', '.join(sorted(set(leftover)))}")

    return ExprResult(sql=s.strip(), confident=confident,
                      note="; ".join(notes) if notes else "",
                      origin=original.strip())


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
