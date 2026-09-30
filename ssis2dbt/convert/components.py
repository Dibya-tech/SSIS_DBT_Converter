"""Component converters: translate one SSIS component into a CTE body.

Each converter receives the component, its upstream CTE names, and a build
context, and returns a CTEResult. Converters are registered by canonical
component type so new mappings can be added without touching the generator
(PRD section 11 extensibility).

Changes vs v1:
  - All source converters emit explicit column SELECTs (no select *)
  - DataConversion emits real CAST expressions
  - Destination emits its explicit input-column list
  - Every CTE body opens with a description block comment
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..dialects.base import Dialect
from ..ir.model import Column, Component, Grade, sanitize_identifier
from .expression import translate as translate_expr

# ---------------------------------------------------------------------------
# SSIS dataType -> SQL type
# ---------------------------------------------------------------------------

_SSIS_TO_SQL: dict[str, str] = {
    "date": "date",
    "dbDate": "date",
    "dbTimeStamp": "timestamp",
    "dbTimeStampOffset": "timestamp_tz",
    "wstr": "varchar",
    "str": "varchar",
    "i1": "tinyint",
    "i2": "smallint",
    "i4": "int",
    "i8": "bigint",
    "ui1": "tinyint",
    "ui2": "smallint",
    "ui4": "int",
    "ui8": "bigint",
    "r4": "float",
    "r8": "float",
    "numeric": "numeric",
    "decimal": "decimal",
    "bool": "boolean",
    "guid": "varchar(36)",
    "bytes": "binary",
    "image": "binary",
    "cy": "numeric(19,4)",
}


def _sql_type(col: Column) -> str:
    base = _SSIS_TO_SQL.get(col.data_type or "", "varchar")
    if col.precision and base in ("numeric", "decimal"):
        if col.scale:
            return f"{base}({col.precision},{col.scale})"
        return f"{base}({col.precision})"
    if col.length and base in ("varchar", "nvarchar"):
        return f"{base}({col.length})"
    return base


# ---------------------------------------------------------------------------
# CTE description block
# ---------------------------------------------------------------------------

def _cte_desc(comp: Component, extra_lines: list[str] | None = None) -> str:
    """Return a comment block that opens every CTE body."""
    lines = [
        f"    -- [{comp.component_type}] {comp.name}",
    ]
    if comp.description:
        lines.append(f"    --   {comp.description}")
    if extra_lines:
        for ln in extra_lines:
            lines.append(f"    --   {ln}")
    lines.append("    -- " + "-" * 50)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------

def _col_alias(name: str) -> str:
    """SQL-safe alias for a column that may contain spaces or mixed case."""
    safe = sanitize_identifier(name)
    # If sanitized differs from original (spaces, caps), emit AS alias
    if safe != name.lower().replace(" ", "_"):
        return safe
    return safe


def _select_cols(cols: list[Column], prefix: str = "") -> str:
    """Build an explicit SELECT column list from IR Column objects."""
    if not cols:
        return "    *  -- no column metadata in package"
    parts = []
    for c in cols:
        safe = _col_alias(c.name)
        original = c.name
        # Quote names that contain spaces or start with a digit
        if re.search(r"[^a-zA-Z0-9_]", original) or original[0].isdigit():
            src = f'"{original}"'
        else:
            src = original
        alias_part = f" as {safe}" if safe != original.lower().replace(" ", "_").replace("-", "_") else ""
        # Add type hint as comment
        type_hint = f"  -- {_sql_type(c)}" if c.data_type else ""
        parts.append(f"    {prefix}{src}{alias_part}{type_hint}")
    return ",\n".join(parts)


# ---------------------------------------------------------------------------
# Result + context
# ---------------------------------------------------------------------------

@dataclass
class CTEResult:
    body: str
    grade: Grade = Grade.EXACT
    reason_code: Optional[str] = None
    notes: list[str] = field(default_factory=list)
    review_comment: Optional[str] = None
    extra_ctes: list = field(default_factory=list)  # list[tuple[str,str]]: (cte_name, body)


@dataclass
class Ctx:
    dialect: Dialect
    upstreams: list[str]
    source_ref: Callable[[Component], str]
    ref_lookup: Callable[[Component], str]


_REGISTRY: dict[str, Callable[[Component, Ctx], CTEResult]] = {}


def converter(*types: str):
    def deco(fn):
        for t in types:
            _REGISTRY[t] = fn
        return fn
    return deco


def convert_component(comp: Component, ctx: Ctx) -> CTEResult:
    fn = _REGISTRY.get(comp.component_type)
    if fn is None:
        desc = _cte_desc(comp, ["⛔ Unrecognized component type — translate manually"])
        body = f"{desc}\n    select * from {ctx.upstreams[0]}" if ctx.upstreams else f"{desc}\n    select 1"
        return CTEResult(body=body, grade=Grade.MANUAL, reason_code="UNKNOWN_COMPONENT",
                         review_comment=f"Unrecognized SSIS component type '{comp.component_type}'")
    return fn(comp, ctx)


def _first_up(ctx: Ctx) -> str:
    return ctx.upstreams[0] if ctx.upstreams else "(select 1)"


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@converter("OLEDBSource", "ADONETSource")
def _oledb_source(comp: Component, ctx: Ctx) -> CTEResult:
    src = ctx.source_ref(comp)
    col_sql = _select_cols(comp.columns)
    sql_cmd = comp.properties.get("SqlCommand") or comp.properties.get("OpenRowset") or "unknown"
    grade = Grade.EXACT
    reason = None
    extra_lines = [f"Columns: {len(comp.columns)}"]

    # Extract and include WHERE clause from parameterized SqlCommand
    where_clause = ""
    if "?" not in sql_cmd:  # already resolved, or no params
        where_match = re.search(r"\bWHERE\b(.+?)(?:\s*(?:GROUP\s+BY|ORDER\s+BY|HAVING|$))", sql_cmd, re.I | re.S)
        if where_match:
            where_clause = re.sub(r"\b[a-zA-Z_]\w*\.", "", where_match.group(1).strip())
    else:
        # Still has unresolved ? — surface the raw WHERE as a comment
        where_match = re.search(r"\bWHERE\b(.+?)(?:\s*(?:GROUP\s+BY|ORDER\s+BY|HAVING|$))", sql_cmd, re.I | re.S)
        if where_match:
            extra_lines.append(f"⚠️  Unresolved WHERE: {where_match.group(1).strip()[:200]}")
            grade = Grade.WARNING
            reason = "PARAM_UNRESOLVED"

    if "{{ var(" in sql_cmd:
        extra_lines.append("Parameterized query: ? replaced with Jinja vars — verify var names")
        grade = Grade.WARNING
        reason = "PARAM_SUBST"

    desc = _cte_desc(comp, extra_lines)
    if where_clause:
        body = f"{desc}\n    select\n{col_sql}\n    from {src}\n    where {where_clause}"
    else:
        body = f"{desc}\n    select\n{col_sql}\n    from {src}"
    return CTEResult(body=body, grade=grade, reason_code=reason)


@converter("FlatFileSource", "ExcelSource")
def _file_source(comp: Component, ctx: Ctx) -> CTEResult:
    src = ctx.source_ref(comp)
    rowset = comp.properties.get("OpenRowset", "")
    col_sql = _select_cols(comp.columns)
    desc = _cte_desc(comp, [
        f"File/sheet: {rowset}",
        "⚠️  Configure as a dbt seed or external table before running",
        f"Columns: {len(comp.columns)}",
    ])
    body = f"{desc}\n    select\n{col_sql}\n    from {src}"
    return CTEResult(body=body, grade=Grade.WARNING, reason_code="EXTERNAL_SOURCE",
                     review_comment="External file source: configure as a dbt seed or external table")


# ---------------------------------------------------------------------------
# Destinations
# ---------------------------------------------------------------------------

@converter("OLEDBDestination")
def _oledb_dest(comp: Component, ctx: Ctx) -> CTEResult:
    target = comp.properties.get("OpenRowset", "")
    # Use input_columns for the explicit SELECT (what actually lands in the table)
    cols = comp.input_columns or []
    col_sql = _select_cols(cols)
    desc = _cte_desc(comp, [
        f"Target table: {target}",
        f"Input columns: {len(cols)}",
    ])
    body = f"{desc}\n    select\n{col_sql}\n    from {_first_up(ctx)}"
    return CTEResult(body=body)


@converter("FlatFileDestination")
def _file_dest(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, ["⛔ Flat File Destination is outside dbt scope — handle as an export step"])
    body = f"{desc}\n    select * from {_first_up(ctx)}"
    return CTEResult(body=body, grade=Grade.MANUAL, reason_code="EXTERNAL_IO",
                     review_comment="Flat File Destination is outside dbt scope")


# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------

@converter("DerivedColumn")
def _derived(comp: Component, ctx: Ctx) -> CTEResult:
    # New outputColumn expressions (adds new columns)
    new_exprs = _derived_expressions(comp)
    # In-place readWrite replacements (replaces existing columns)
    rw_exprs = comp.readwrite_exprs  # list of (col_name, ssis_expr)

    total = len(new_exprs) + len(rw_exprs)
    desc_lines = [f"Adds/replaces {total} column(s) via SSIS expressions"]
    grade = Grade.EXACT
    reason = None
    notes: list[str] = []
    new_cols: list[str] = []

    for col_name, ssis_expr in new_exprs:
        res = translate_expr(ssis_expr, ctx.dialect)
        alias = sanitize_identifier(col_name)
        if res.confident:
            ssis_tag = f"  -- SSIS: {res.origin}" if res.origin else ""
            new_cols.append(f"    {res.sql} as {alias}{ssis_tag}")
        else:
            grade = Grade.WARNING
            reason = "UNMAPPED_FUNCTION"
            notes.append(f"{alias}: {res.note}")
            new_cols.append(f"    -- REVIEW: {res.note}\n    {res.sql} as {alias}")

    rw_cols: list[str] = []
    rw_names: list[str] = []
    for col_name, ssis_expr in rw_exprs:
        res = translate_expr(ssis_expr, ctx.dialect)
        alias = sanitize_identifier(col_name)
        rw_names.append(alias)
        if res.confident:
            ssis_tag = f"  -- SSIS: {res.origin}" if res.origin else ""
            rw_cols.append(f"    {res.sql} as {alias}{ssis_tag}")
        else:
            if grade == Grade.EXACT:
                grade = Grade.WARNING
            reason = "UNMAPPED_FUNCTION"
            notes.append(f"{alias}: {res.note}")
            rw_cols.append(f"    -- REVIEW: {res.note}\n    {res.sql} as {alias}")

    desc = _cte_desc(comp, desc_lines)
    upstream = _first_up(ctx)

    if rw_cols and not new_cols:
        # Pure in-place replacement: use * EXCLUDE to drop replaced cols, then emit new exprs
        exclude_list = ", ".join(rw_names)
        body = (f"{desc}\n    select\n    * exclude ({exclude_list}),\n"
                + ",\n".join(rw_cols)
                + f"\n    from {upstream}")
    elif rw_cols and new_cols:
        exclude_list = ", ".join(rw_names)
        body = (f"{desc}\n    select\n    * exclude ({exclude_list}),\n"
                + ",\n".join(rw_cols)
                + ",\n"
                + ",\n".join(new_cols)
                + f"\n    from {upstream}")
    elif new_cols:
        body = (f"{desc}\n    select\n    *,\n"
                + ",\n".join(new_cols)
                + f"\n    from {upstream}")
    else:
        body = f"{desc}\n    select * from {upstream}"

    return CTEResult(body=body, grade=grade, reason_code=reason, notes=notes)


@converter("DataConversion")
def _data_conversion(comp: Component, ctx: Ctx) -> CTEResult:
    """Emit explicit CAST for each converted column."""
    cast_lines: list[str] = []
    for out_col in comp.columns:
        # Resolve source input column name from the SourceInputColumnLineageID property
        src_lineage = out_col.props.get("SourceInputColumnLineageID", "")
        src_name = _extract_col_from_lineage(src_lineage)
        if not src_name:
            # fallback: match by position against input_columns
            idx = comp.columns.index(out_col)
            src_name = comp.input_columns[idx].name if idx < len(comp.input_columns) else "unknown_src"
        sql_type = _sql_type(out_col)
        alias = sanitize_identifier(out_col.name)
        cast_lines.append(
            f"    try_cast({sanitize_identifier(src_name)} as {sql_type}) as {alias}"
            f"  -- {src_name} → {out_col.name} ({out_col.data_type}"
            + (f", len={out_col.length}" if out_col.length else "")
            + ")"
        )

    desc = _cte_desc(comp, [
        f"Converts {len(cast_lines)} column(s) to new types",
        "Passthrough columns flow via select *",
    ])
    if cast_lines:
        body = (f"{desc}\n    select\n    *,\n"
                + ",\n".join(cast_lines)
                + f"\n    from {_first_up(ctx)}")
    else:
        body = f"{desc}\n    select * from {_first_up(ctx)}"

    return CTEResult(body=body)


@converter("Lookup")
def _lookup(comp: Component, ctx: Ctx) -> CTEResult:
    ref = ctx.ref_lookup(comp)
    no_match = (comp.properties.get("NoMatchBehavior", "") or "").lower()
    join = "inner join" if "fail" in no_match else "left join"

    if comp.join_keys:
        on_clause = " and ".join(
            f"u.{sanitize_identifier(lk)} = l.{sanitize_identifier(rk)}"
            for lk, rk in comp.join_keys
        )
        grade = Grade.EXACT
        review = None
        desc_extra = [f"Join type: {join.upper()} (no-match: {no_match or 'redirect'})"]
    else:
        on_clause = "/* REVIEW: add join keys here */ 1 = 1"
        grade = Grade.WARNING
        review = "Lookup join keys not found — add ON clause manually"
        desc_extra = [f"Join type: {join.upper()} (no-match: {no_match or 'redirect'})", "⚠️  Verify join keys below"]

    desc = _cte_desc(comp, desc_extra)
    body = (f"{desc}\n"
            f"    select u.*\n    from {_first_up(ctx)} u\n"
            f"    {join} {ref} l\n        on {on_clause}")
    return CTEResult(body=body, grade=grade, review_comment=review)


@converter("Sort")
def _sort(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, [
        "Sort dropped — SQL is set-based; ordering is not guaranteed between CTEs.",
        "Add ORDER BY to the final SELECT if downstream truly requires it.",
    ])
    return CTEResult(
        body=f"{desc}\n    select * from {_first_up(ctx)}",
        grade=Grade.WARNING, reason_code="DROPPED",
    )


@converter("Aggregate")
def _aggregate(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, ["⚠️  Specify GROUP BY keys and aggregate expressions below"])
    body = (f"{desc}\n"
            f"    select\n"
            f"        /* TODO: group-by keys */,\n"
            f"        /* TODO: count(*) / sum(...) etc. */\n"
            f"    from {_first_up(ctx)}\n"
            f"    group by /* TODO */")
    return CTEResult(body=body, review_comment="Specify GROUP BY keys and aggregate expressions")


@converter("ConditionalSplit")
def _conditional_split(comp: Component, ctx: Ctx) -> CTEResult:
    branch_names = [sanitize_identifier(n) for n in comp.output_conditions]
    desc_lines = ["Base passthrough — filter via the branch CTEs below:"]
    desc_lines += [f"  {comp.safe_name}_{n}  (WHERE translated condition)" for n in branch_names]
    if comp.output_conditions:
        desc_lines.append(f"  {comp.safe_name}_default  (WHERE NOT any condition)")
    desc = _cte_desc(comp, desc_lines)
    base_body = f"{desc}\n    select * from {_first_up(ctx)}"

    extra: list[tuple[str, str]] = []
    translated_conditions: list[str] = []

    for out_name, ssis_expr in comp.output_conditions.items():
        branch_name = f"{comp.safe_name}_{sanitize_identifier(out_name)}"
        res = translate_expr(ssis_expr, ctx.dialect)
        where_sql = res.sql if res.sql else f"/* TODO: translate: {ssis_expr} */"
        translated_conditions.append(where_sql)
        branch_body = (
            f"    -- Branch: {out_name}  -- SSIS: {ssis_expr}\n"
            f"    select * from {comp.safe_name}\n"
            f"    where {where_sql}"
        )
        extra.append((branch_name, branch_body))

    # Default branch: rows not captured by any named condition
    if translated_conditions:
        inv = " or ".join(f"not ({c})" for c in translated_conditions)
        default_body = (
            f"    -- Branch: Default Output (rows not matched by any condition)\n"
            f"    select * from {comp.safe_name}\n"
            f"    where {inv}"
        )
        extra.append((f"{comp.safe_name}_default", default_body))

    return CTEResult(body=base_body, extra_ctes=extra)


@converter("Multicast")
def _multicast(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, ["This CTE is referenced by multiple downstream CTEs (fan-out)."])
    return CTEResult(body=f"{desc}\n    select * from {_first_up(ctx)}")


@converter("UnionAll")
def _union_all(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, [
        f"Unions {len(ctx.upstreams)} branch(es) — verify column alignment.",
    ])
    if len(ctx.upstreams) <= 1:
        return CTEResult(body=f"{desc}\n    select * from {_first_up(ctx)}")
    parts = [f"    select * from {u}" for u in ctx.upstreams]
    return CTEResult(
        body=desc + "\n" + "\n    union all\n".join(parts),
        notes=["verify column alignment across UNION ALL branches"],
    )


@converter("MergeJoin")
def _merge_join(comp: Component, ctx: Ctx) -> CTEResult:
    if len(ctx.upstreams) < 2:
        return CTEResult(body=f"    select * from {_first_up(ctx)}")
    left, right = ctx.upstreams[0], ctx.upstreams[1]
    jt = (comp.properties.get("JoinType", "") or "").lower()
    join = {"1": "left join", "2": "inner join", "3": "full outer join"}.get(jt, "inner join")

    if comp.join_keys:
        on_clause = " and ".join(
            f"l.{sanitize_identifier(lk)} = r.{sanitize_identifier(rk)}"
            for lk, rk in comp.join_keys
        )
        grade = Grade.EXACT
        review = None
        desc_extra = [f"Join type: {join.upper()}"]
    else:
        on_clause = "/* REVIEW: add join keys here */ 1 = 1"
        grade = Grade.WARNING
        review = "MergeJoin keys not found — add ON clause manually"
        desc_extra = [f"Join type: {join.upper()} — verify keys below"]

    desc = _cte_desc(comp, desc_extra)
    body = (f"{desc}\n"
            f"    select l.*, r.*\n    from {left} l\n    {join} {right} r\n"
            f"        on {on_clause}")
    return CTEResult(body=body, grade=grade, review_comment=review)


@converter("Merge")
def _merge(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, [
        "⚠️  SSIS Merge (sorted union) became UNION ALL — row ordering is NOT preserved.",
    ])
    parts = [f"    select * from {u}" for u in ctx.upstreams] or [f"    select * from {_first_up(ctx)}"]
    return CTEResult(
        body=desc + "\n" + "\n    union all\n".join(parts),
        grade=Grade.WARNING, reason_code="MERGE_ORDER",
    )


@converter("RowCount")
def _row_count(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, [
        "Row Count dropped — use a dbt post-hook or test if the count is needed.",
    ])
    return CTEResult(body=f"{desc}\n    select * from {_first_up(ctx)}",
                     grade=Grade.WARNING, reason_code="DROPPED")


@converter("Pivot", "Unpivot")
def _pivot(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, ["⚠️  Pivot/Unpivot requires dialect-specific rewrite — see below"])
    return CTEResult(body=f"{desc}\n    select * from {_first_up(ctx)}",
                     grade=Grade.WARNING, reason_code="PIVOT")


@converter("SlowlyChangingDimension")
def _scd(comp: Component, ctx: Ctx) -> CTEResult:
    """SCD is graded Manual.

    The SSIS SCD wizard encodes its entire branching logic (business keys,
    Type-1/Type-2 attributes, OLE DB Commands for UPDATE) in a deeply-nested
    `SCDMetadata` XML blob inside `<PipelineComponentMetadata>`.  The downstream
    OLE DB Command components execute row-by-row UPDATE statements that have no
    set-based SQL equivalent.

    Correct migration path: replace the whole SCD data-flow sub-graph with a
    dbt snapshot (https://docs.getdbt.com/docs/build/snapshots).
    """
    # Try to surface whatever hints we can from SCDMetadata / component properties
    bk  = comp.properties.get("BusinessKey", "")
    t1  = comp.properties.get("ChangingAttributeDefaults", "")
    t2  = comp.properties.get("HistoricalAttributeDefaults", "")
    hints = [
        "⛔  The SSIS SCD wizard produces row-by-row UPDATEs via OLE DB Commands.",
        "    There is no equivalent set-based SQL pattern — use a dbt snapshot.",
        "",
        "    Migration steps:",
        "    1. Create a dbt snapshot in snapshots/<name>.sql",
        "    2. Set strategy: timestamp (or check) based on your updated_at column",
        "    3. Configure unique_key = '<business key>'",
        "    4. Delete this CTE and all downstream OLE DB Command CTEs",
    ]
    if bk:
        hints.append(f"    Business key detected   : {bk}")
    if t1:
        hints.append(f"    Type-1 (overwrite) cols : {t1}")
    if t2:
        hints.append(f"    Type-2 (versioned) cols : {t2}")

    desc = _cte_desc(comp, hints)
    body = (
        f"{desc}\n"
        f"    -- TODO: replace with a dbt snapshot\n"
        f"    -- Example:\n"
        f"    --   {{% snapshot {comp.safe_name} %}}\n"
        f"    --   {{{{ config(target_schema='snapshots', unique_key='{bk or 'id'}',\n"
        f"    --            strategy='timestamp', updated_at='updated_at') }}}}\n"
        f"    --   select * from {{{{ source('raw', '{comp.safe_name}') }}}}\n"
        f"    --   {{% endsnapshot %}}\n"
        f"    select * from {_first_up(ctx)}"
    )
    return CTEResult(body=body, grade=Grade.MANUAL, reason_code="SCD",
                     review_comment="Replace entire SCD sub-graph with a dbt snapshot")


@converter("OLEDBCommand")
def _oledb_command(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, [
        "⚠️  Row-by-row DML — replace with a set-based MERGE or incremental model",
    ])
    return CTEResult(body=f"{desc}\n    select * from {_first_up(ctx)}",
                     grade=Grade.WARNING, reason_code="ROW_BY_ROW_DML")


@converter("ScriptComponent")
def _script(comp: Component, ctx: Ctx) -> CTEResult:
    desc = _cte_desc(comp, [
        "⛔ Script Component (C#/VB) cannot be auto-converted.",
        "Rewrite as SQL/UDF or move to a Python model / external service.",
    ])
    return CTEResult(body=f"{desc}\n    select * from {_first_up(ctx)}",
                     grade=Grade.MANUAL, reason_code="SCRIPT_COMPONENT")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _derived_expressions(comp: Component) -> list[tuple[str, str]]:
    """Return (output_col_name, ssis_expression) pairs for a Derived Column.

    SSIS stores expressions in TWO places depending on how the package was built:
      a) Component-level properties:  "Expression_ColName" -> value  (older packages)
      b) Per-outputColumn nested props:  col.props["Expression"] or
         col.props["FriendlyExpression"]
         -- this is the ground truth written by the SSIS designer.

    Strategy: collect (a) first, then let (b) overwrite for the same column name,
    so the deeply-nested per-column value always wins.
    """
    seen: dict[str, str] = {}

    # (a) component-level expression properties (simple packages / hand-edited XML)
    for key, val in comp.properties.items():
        if key.lower().startswith("expression") and val:
            col_name = key.split("_", 1)[1] if "_" in key else key
            seen[col_name] = val

    # (b) per-outputColumn nested Expression / FriendlyExpression
    #     These live at: outputs/output/outputColumns/outputColumn/properties/property
    #     and are captured into col.props by _read_output_columns in the parser.
    #     FriendlyExpression is the human-readable form; Expression is the raw AST —
    #     prefer FriendlyExpression as it translates more cleanly.
    for col in comp.columns:
        expr = col.props.get("FriendlyExpression") or col.props.get("Expression")
        if expr:
            seen[col.name] = expr   # (b) always wins over (a)

    return list(seen.items())


def _extract_col_from_lineage(lineage_val: str) -> Optional[str]:
    """Extract column name from a SSIS lineage ID reference.

    e.g. '#{Package\\DFT\\Excel Source.Outputs[Output].Columns[calendar_month_name]}'
         -> 'calendar_month_name'
    """
    m = re.search(r"Columns\[([^\]]+)\]", lineage_val or "")
    return m.group(1) if m else None
