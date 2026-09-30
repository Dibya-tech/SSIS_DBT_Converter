"""Parse an SSIS `.dtsx` (XML) package into the dialect-neutral IR.

Safe XML parsing: external entities and DTDs are disabled to prevent XXE
(PRD section 10.4).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path as FsPath

from ..ir.model import (
    Column,
    Component,
    ConnectionManager,
    DataFlow,
    Package,
    Path,
    Task,
    Variable,
)
from .redact import redact_properties

DTS_NS = "www.microsoft.com/SqlServer/Dts"

# Map SSIS pipeline componentClassID substrings -> canonical short type.
_COMPONENT_MAP = {
    "OLEDBSource": "OLEDBSource",
    "ADONETSource": "ADONETSource",
    "FlatFileSource": "FlatFileSource",
    "ExcelSource": "ExcelSource",
    "OLEDBDestination": "OLEDBDestination",
    "FlatFileDestination": "FlatFileDestination",
    "DerivedColumn": "DerivedColumn",
    "DataConvert": "DataConversion",
    "Lookup": "Lookup",
    "Sort": "Sort",
    "Aggregate": "Aggregate",
    "ConditionalSplit": "ConditionalSplit",
    "Multicast": "Multicast",
    "UnionAll": "UnionAll",
    "MergeJoin": "MergeJoin",
    "Merge": "Merge",
    "RowCount": "RowCount",
    "Pivot": "Pivot",
    "UnPivot": "Unpivot",
    "ScriptComponent": "ScriptComponent",
    "OLEDBCommand": "OLEDBCommand",
    "SCD": "SlowlyChangingDimension",
}

# Control Flow ExecutableType substrings -> canonical.
_TASK_MAP = {
    "Pipeline": "DataFlowTask",
    "ExecuteSQLTask": "ExecuteSQLTask",
    "ForEachLoop": "ForEachLoop",
    "ForLoop": "ForLoop",
    "SendMailTask": "SendMailTask",
    "FileSystemTask": "FileSystemTask",
    "FTPTask": "FTPTask",
    "ExecutePackageTask": "ExecutePackageTask",
    "ScriptTask": "ScriptTask",
}


def _q(tag: str) -> str:
    return f"{{{DTS_NS}}}{tag}"


def _attr(el, name: str, default=None):
    """Read a DTS-namespaced attribute, falling back to unqualified."""
    return el.get(_q(name), el.get(name, default))


def _classify(class_id: str, table: dict, default: str) -> str:
    if not class_id:
        return default
    for needle, canonical in table.items():
        if needle.lower() in class_id.lower():
            return canonical
    return default


def parse_file(path: str | FsPath) -> Package:
    parser = ET.XMLParser()
    # Disable DTD / entity expansion where the underlying expat allows it.
    try:  # pragma: no cover - depends on platform expat
        parser.parser.DefaultHandler = lambda data: None
        parser.entity = {}
    except Exception:
        pass
    tree = ET.parse(str(path), parser=parser)
    root = tree.getroot()
    return parse_root(root, name=FsPath(path).stem)


def parse_string(xml: str, name: str = "package") -> Package:
    root = ET.fromstring(xml)
    return parse_root(root, name=name)


def parse_root(root, name: str) -> Package:
    pkg = Package(
        name=_attr(root, "ObjectName", name) or name,
        version=_attr(root, "VersionBuild"),
        protection_level=_attr(root, "ProtectionLevel"),
    )
    _parse_variables(root, pkg)
    _parse_connections(root, pkg)
    _parse_executables(root, pkg)
    return pkg


def _parse_variables(root, pkg: Package) -> None:
    container = root.find(_q("Variables"))
    if container is None:
        return
    for v in container.findall(_q("Variable")):
        ns = _attr(v, "Namespace", "User")
        vname = _attr(v, "ObjectName", "")
        value_el = v.find(_q("VariableValue"))
        value = value_el.text if value_el is not None else None
        pkg.variables.append(
            Variable(name=vname, namespace=ns, value=value,
                     is_parameter=(ns or "").lower() == "project")
        )


def _parse_connections(root, pkg: Package) -> None:
    container = root.find(_q("ConnectionManagers"))
    if container is None:
        return
    for cm in container.findall(_q("ConnectionManager")):
        props = {}
        obj = cm.find(_q("ObjectData"))
        if obj is not None:
            inner = obj.find(_q("ConnectionManager"))
            if inner is not None:
                props.update(_strip_ns(inner.attrib))
        pkg.connections.append(
            ConnectionManager(
                id=_attr(cm, "DTSID", _attr(cm, "refId", "")),
                cm_type=_attr(cm, "CreationName", "") or "",
                name=_attr(cm, "ObjectName", "") or "",
                properties=redact_properties(props),
            )
        )


def _parse_executables(root, pkg: Package) -> None:
    container = root.find(_q("Executables"))
    if container is None:
        return
    _walk_executables(container, pkg)


_SQLTASK_NS = "www.microsoft.com/sqlserver/dts/tasks/sqltask"


def _read_sql_task(ex, task: Task) -> None:
    """Extract SqlStatementSource from an ExecuteSQLTask ObjectData element."""
    obj = ex.find(_q("ObjectData"))
    if obj is None:
        return
    for child in obj.iter():
        sql = child.get(f"{{{_SQLTASK_NS}}}SqlStatementSource")
        if sql:
            task.properties["SqlStatementSource"] = sql.strip()
            break


def _walk_executables(container, pkg: Package) -> None:
    """Recursively walk a DTS:Executables element, discovering DataFlow tasks at
    any nesting depth (e.g. inside ForEachLoop / Sequence containers)."""
    for ex in container.findall(_q("Executable")):
        etype = _attr(ex, "ExecutableType", "") or ""
        task_type = _classify(etype, _TASK_MAP, "UnknownTask")
        task = Task(
            id=_attr(ex, "DTSID", _attr(ex, "refId", "")),
            task_type=task_type,
            name=_attr(ex, "ObjectName", "") or "",
        )
        pkg.tasks.append(task)
        if task_type == "DataFlowTask":
            df = _parse_pipeline(ex, task)
            if df is not None:
                pkg.data_flows.append(df)
        elif task_type == "ExecuteSQLTask":
            _read_sql_task(ex, task)
        # Recurse into any nested Executables block (ForEach/Sequence/etc.)
        nested = ex.find(_q("Executables"))
        if nested is not None:
            _walk_executables(nested, pkg)
    _parse_precedence(container, pkg)


def _parse_precedence(container, pkg: Package) -> None:
    """Resolve precedence constraints into upstream-task edges."""
    id_by_ref = {}
    for ex in container.findall(_q("Executable")):
        ref = _attr(ex, "refId")
        did = _attr(ex, "DTSID", ref)
        if ref:
            id_by_ref[ref] = did
    pcs = container.find(_q("PrecedenceConstraints"))
    if pcs is None:
        return
    task_by_id = {t.id: t for t in pkg.tasks}
    for pc in pcs.findall(_q("PrecedenceConstraint")):
        frm = _attr(pc, "From")
        to = _attr(pc, "To")
        frm_id = id_by_ref.get(frm, frm)
        to_id = id_by_ref.get(to, to)
        if to_id in task_by_id and frm_id:
            task_by_id[to_id].precedence.append(frm_id)


def _parse_pipeline(executable, task: Task) -> DataFlow | None:
    obj = executable.find(_q("ObjectData"))
    if obj is None:
        return None
    pipeline = obj.find("pipeline")
    if pipeline is None:
        return None
    df = DataFlow(id=task.id, name=task.name)

    comps_el = pipeline.find("components")
    ref_to_id: dict[str, str] = {}
    output_owner: dict[str, str] = {}   # output refId -> component id
    input_owner: dict[str, str] = {}    # input refId  -> component id
    output_name: dict[str, str] = {}    # output refId -> output name

    if comps_el is not None:
        for comp in comps_el.findall("component"):
            cid = comp.get("refId") or comp.get("name")
            ctype = _classify(comp.get("componentClassID", ""), _COMPONENT_MAP, "Unknown")
            component = Component(
                id=cid,
                component_type=ctype,
                name=comp.get("name", cid),
                description=comp.get("description", ""),
                properties=_read_properties(comp),
                columns=_read_output_columns(comp),
                input_columns=_read_input_columns(comp),
            )
            # ConditionalSplit: capture per-output filter expressions
            if ctype == "ConditionalSplit":
                for out in comp.findall("outputs/output"):
                    is_default = out.get("isDefaultOut", "false").lower() == "true"
                    oname = out.get("name", "")
                    if not is_default and oname:
                        for prop in out.findall("properties/property"):
                            if prop.get("name") == "FriendlyExpression":
                                component.output_conditions[oname] = (prop.text or "").strip()

            df.components.append(component)
            ref_to_id[cid] = cid
            for outs in comp.findall("outputs/output"):
                oref = outs.get("refId")
                if oref:
                    output_owner[oref] = cid
                    output_name[oref] = outs.get("name", "")
            for ins in comp.findall("inputs/input"):
                iref = ins.get("refId")
                if iref:
                    input_owner[iref] = cid

    paths_el = pipeline.find("paths")
    if paths_el is not None:
        for p in paths_el.findall("path"):
            start = p.get("startId")   # an output refId
            end = p.get("endId")       # an input refId
            src = output_owner.get(start)
            tgt = input_owner.get(end)
            if src and tgt:
                df.paths.append(
                    Path(source_id=src, target_id=tgt,
                         source_output=output_name.get(start))
                )
                sc = df.component(src)
                tc = df.component(tgt)
                if sc and tgt not in sc.outputs:
                    sc.outputs.append(tgt)
                if tc and src not in tc.inputs:
                    tc.inputs.append(src)
    return df


def _read_properties(comp) -> dict:
    props = {}
    for prop in comp.findall("properties/property"):
        pname = prop.get("name")
        if pname:
            props[pname] = (prop.text or "").strip()
    return redact_properties(props)


def _read_output_columns(comp) -> list[Column]:
    """Read non-error output columns; capture length and per-column properties."""
    cols: list[Column] = []
    seen: set[str] = set()
    for output in comp.findall("outputs/output"):
        # Skip error outputs — they carry ErrorCode/ErrorColumn, not real data
        if output.get("isErrorOut", "false").lower() == "true":
            continue
        for col in output.findall("outputColumns/outputColumn"):
            cname = col.get("name")
            if not cname or cname in seen:
                continue
            seen.add(cname)
            length_raw = col.get("length")
            col_props: dict[str, str] = {}
            for prop in col.findall("properties/property"):
                pname = prop.get("name")
                if pname:
                    col_props[pname] = (prop.text or "").strip()
            prec_raw = col.get("precision")
            scale_raw = col.get("scale")
            cols.append(Column(
                name=cname,
                data_type=col.get("dataType"),
                lineage_id=col.get("lineageId"),
                length=int(length_raw) if length_raw else None,
                precision=int(prec_raw) if prec_raw else None,
                scale=int(scale_raw) if scale_raw else None,
                props=col_props,
            ))
    return cols


def _read_input_columns(comp) -> list[Column]:
    """Read cached input column metadata (name, type, length)."""
    cols: list[Column] = []
    seen: set[str] = set()
    for col in comp.findall("inputs/input/inputColumns/inputColumn"):
        cname = col.get("cachedName")
        if not cname or cname in seen:
            continue
        seen.add(cname)
        length_raw = col.get("cachedLength")
        cols.append(Column(
            name=cname,
            data_type=col.get("cachedDataType"),
            lineage_id=col.get("lineageId"),
            length=int(length_raw) if length_raw else None,
        ))
    return cols


def _strip_ns(attrib: dict) -> dict:
    out = {}
    for k, v in attrib.items():
        out[k.split("}")[-1]] = v
    return out
