"""Generate a dbt model (chained CTEs) from a Data Flow (PRD section 4).

Design principles implemented here:
  * 1:1 Data Flow -> model.
  * Sequential CTE chaining in topological order.
  * CTE names preserve sanitized SSIS component names (lineage).
  * Branching (Conditional Split / Multicast) -> independent CTE branches
    merged downstream.
  * {{ source() }} for external inputs, {{ ref() }} for lookups.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..dialects.base import Dialect, get_dialect
from ..ir.model import Component, DataFlow, Grade, sanitize_identifier
from ..grade.reasons import CATALOG
from .components import Ctx, convert_component

_SOURCE_TYPES = {"OLEDBSource", "ADONETSource", "FlatFileSource", "ExcelSource"}


@dataclass
class ComponentResult:
    component_id: str
    component_name: str
    component_type: str
    cte_name: str
    grade: Grade
    reason_code: Optional[str] = None
    notes: list[str] = field(default_factory=list)


@dataclass
class GeneratedModel:
    data_flow_id: str
    model_name: str
    layer: str
    sql: str
    results: list[ComponentResult] = field(default_factory=list)

    @property
    def grade(self) -> Grade:
        """Data-flow grade = lowest grade among components (PRD 8.4)."""
        if not self.results:
            return Grade.EXACT
        return min((r.grade for r in self.results), key=lambda g: g.rank)


def _topo_order(df: DataFlow) -> list[Component]:
    indeg = {c.id: 0 for c in df.components}
    adj: dict[str, list[str]] = {c.id: [] for c in df.components}
    for p in df.paths:
        if p.source_id in indeg and p.target_id in indeg:
            adj[p.source_id].append(p.target_id)
            indeg[p.target_id] += 1
    queue = [cid for cid, d in indeg.items() if d == 0]
    order: list[str] = []
    while queue:
        cid = queue.pop(0)
        order.append(cid)
        for nxt in adj[cid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    # append any remaining (cycles / detached) in declaration order
    order += [c.id for c in df.components if c.id not in order]
    by_id = {c.id: c for c in df.components}
    return [by_id[cid] for cid in order]


def _source_ref(comp: Component) -> str:
    src = comp.properties.get("OpenRowset") or comp.properties.get("TableName")
    if src:
        parts = [p.strip("[]\" ") for p in str(src).split(".") if p.strip("[]\" ")]
        if len(parts) >= 2:
            return f"{{{{ source('{sanitize_identifier(parts[-2])}', '{sanitize_identifier(parts[-1])}') }}}}"
        return f"{{{{ source('raw', '{sanitize_identifier(parts[-1])}') }}}}"
    return f"{{{{ source('raw', '{comp.safe_name}') }}}}"


def _ref_lookup(comp: Component) -> str:
    tbl = comp.properties.get("SqlCommand") or comp.properties.get("TableName") or comp.name
    ident = sanitize_identifier(str(tbl).split(".")[-1].strip("[]\" ")) or comp.safe_name
    return f"{{{{ ref('stg_{ident}') }}}}"


def generate_model(df: DataFlow, dialect: Dialect | str = "snowflake",
                   package_name: str = "", layer: str = "staging",
                   model_name: Optional[str] = None) -> GeneratedModel:
    dia = get_dialect(dialect) if isinstance(dialect, str) else dialect
    ordered = _topo_order(df)

    cte_names: dict[str, str] = {}
    used: set[str] = set()
    for comp in ordered:
        base = comp.safe_name
        name = base
        i = 1
        while name in used:
            i += 1
            name = f"{base}_{i}"
        used.add(name)
        cte_names[comp.id] = name

    results: list[ComponentResult] = []
    cte_blocks: list[str] = []

    for comp in ordered:
        upstreams = [cte_names[i] for i in comp.inputs if i in cte_names]
        ctx = Ctx(dialect=dia, upstreams=upstreams,
                  source_ref=_source_ref, ref_lookup=_ref_lookup)
        res = convert_component(comp, ctx)

        # Converters embed their own description block; just clean up indentation.
        # Strip leading blank lines, then ensure every line has exactly 4-space indent.
        body_lines = res.body.rstrip()
        # Remove double-indent if body already has 4 spaces (converters write 4-space lines)
        cte_blocks.append(f"{cte_names[comp.id]} as (\n{body_lines}\n)")

        results.append(ComponentResult(
            component_id=comp.id, component_name=comp.name,
            component_type=comp.component_type, cte_name=cte_names[comp.id],
            grade=res.grade, reason_code=res.reason_code, notes=res.notes,
        ))

    # terminal CTE = last in topo order (typically a destination or final xform)
    terminal = cte_names[ordered[-1].id] if ordered else "final"
    mname = model_name or _default_model_name(layer, package_name, df.name)

    header = [
        f"-- {mname}.sql",
        f"-- Source package : {package_name}" if package_name else None,
        f"-- Data Flow Task : {df.name}",
        f"-- Target dialect : {dia.name}",
        "-- Generated by   : SSIS-to-dbt Migration Engine",
    ]
    header_txt = "\n".join(h for h in header if h)
    body = "with\n\n" + ",\n\n".join(cte_blocks) + f"\n\nselect * from {terminal}\n"
    sql = f"{header_txt}\n\n{body}"

    return GeneratedModel(data_flow_id=df.id, model_name=mname, layer=layer,
                          sql=sql, results=results)


def _default_model_name(layer: str, package: str, df_name: str) -> str:
    prefix = {"staging": "stg", "intermediate": "int", "marts": "fct"}.get(layer, "stg")
    domain = sanitize_identifier(package) or "src"
    entity = sanitize_identifier(df_name) or "model"
    return f"{prefix}_{domain}__{entity}"


def route_layer(df: DataFlow) -> str:
    """Heuristic layer routing (PRD 9.2)."""
    types = {c.component_type for c in df.components}
    has_dest_mart = any(
        kw in (df.name or "").lower() for kw in ("fact", "dim", "fct", "dim_", "mart", "report"))
    joiny = types & {"Lookup", "MergeJoin", "Merge", "Aggregate", "UnionAll"}
    if has_dest_mart:
        return "marts"
    if joiny:
        return "intermediate"
    return "staging"
