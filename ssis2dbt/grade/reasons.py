"""Reason-code catalog for Warning / Manual components (PRD section 8.3)."""
from __future__ import annotations

from dataclasses import dataclass

from ..ir.model import Grade


@dataclass
class Reason:
    code: str
    meaning: str
    remediation: str
    grade: Grade


CATALOG: dict[str, Reason] = {
    "SCRIPT_COMPONENT": Reason(
        "SCRIPT_COMPONENT", "Custom C#/VB logic",
        "Rewrite as SQL/UDF or move to a Python model / external service",
        Grade.MANUAL),
    "CONTROL_FLOW_LOOP": Reason(
        "CONTROL_FLOW_LOOP", "ForEach/For loop",
        "Move to Airflow/ADF, or use a dbt Jinja loop if applicable",
        Grade.MANUAL),
    "EXTERNAL_IO": Reason(
        "EXTERNAL_IO", "File/FTP/Mail task",
        "Handle via orchestrator or cloud-native tooling", Grade.MANUAL),
    "DYNAMIC_SQL": Reason(
        "DYNAMIC_SQL", "SQL built from variables",
        "Parameterize with var()/macros; review manually", Grade.WARNING),
    "UNMAPPED_FUNCTION": Reason(
        "UNMAPPED_FUNCTION", "Expression function has no dialect mapping",
        "Provide a manual translation", Grade.WARNING),
    "ROW_BY_ROW_DML": Reason(
        "ROW_BY_ROW_DML", "OLE DB Command",
        "Replace with a set-based MERGE / incremental model", Grade.WARNING),
    "ERROR_REDIRECT": Reason(
        "ERROR_REDIRECT", "Error output routing",
        "Model rejects as a separate CTE/table and add tests", Grade.WARNING),
    "EXTERNAL_SOURCE": Reason(
        "EXTERNAL_SOURCE", "Flat file / Excel source",
        "Configure as a dbt seed or external table", Grade.WARNING),
    "SCD": Reason(
        "SCD", "Slowly Changing Dimension (Type 1/2 wizard)",
        "Replace entire SCD sub-graph with a dbt snapshot "
        "(snapshots/<name>.sql, strategy=timestamp, unique_key=<business_key>). "
        "Delete all downstream OLE DB Command CTEs — they issue row-by-row UPDATEs "
        "with no set-based equivalent.", Grade.MANUAL),
    "PIVOT": Reason(
        "PIVOT", "Pivot/Unpivot",
        "Use dialect-specific PIVOT/UNPIVOT; verify output", Grade.WARNING),
    "MERGE_ORDER": Reason(
        "MERGE_ORDER", "Merge (sorted union)",
        "UNION ALL loses row ordering; verify downstream", Grade.WARNING),
    "DROPPED": Reason(
        "DROPPED", "Component dropped (no data effect)",
        "Confirmed no-op in set-based SQL (e.g. Sort/RowCount)", Grade.WARNING),
    "UNKNOWN_COMPONENT": Reason(
        "UNKNOWN_COMPONENT", "Unrecognized component type",
        "Inspect the SSIS component and translate manually", Grade.MANUAL),
}


def get(code: str) -> Reason:
    return CATALOG[code]
