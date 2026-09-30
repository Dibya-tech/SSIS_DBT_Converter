"""Dialect-neutral Intermediate Representation (IR) for a parsed SSIS package.

The IR decouples parsing (.dtsx XML) from SQL emission so that one parse can
serve every target dialect. See PRD section 12.1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Grade(str, Enum):
    """Conversion confidence grade (PRD section 8)."""

    EXACT = "Exact"
    WARNING = "Warning"
    MANUAL = "Manual"

    @property
    def rank(self) -> int:
        # Lower rank == lower confidence. Used for rollups.
        return {"Exact": 2, "Warning": 1, "Manual": 0}[self.value]


@dataclass
class Column:
    name: str
    data_type: Optional[str] = None
    lineage_id: Optional[str] = None
    length: Optional[int] = None
    precision: Optional[int] = None  # for numeric/decimal types
    scale: Optional[int] = None      # for numeric/decimal types
    props: dict = field(default_factory=dict)   # per-column SSIS properties


@dataclass
class Component:
    """A single component inside a Data Flow (Source, Derived Column, Lookup...)."""

    id: str
    component_type: str  # canonical SSIS componentClassID short name
    name: str
    inputs: list[str] = field(default_factory=list)   # upstream component ids
    outputs: list[str] = field(default_factory=list)  # downstream component ids
    columns: list[Column] = field(default_factory=list)       # output columns
    input_columns: list[Column] = field(default_factory=list) # input columns
    properties: dict = field(default_factory=dict)
    description: str = ""   # SSIS component description attribute
    output_conditions: dict = field(default_factory=dict)  # ConditionalSplit: output_name -> ssis_expr

    @property
    def safe_name(self) -> str:
        return sanitize_identifier(self.name)


@dataclass
class Path:
    """An edge in the data flow graph: source component output -> target input."""

    source_id: str
    target_id: str
    source_output: Optional[str] = None  # e.g. Conditional Split output name


@dataclass
class DataFlow:
    id: str
    name: str
    components: list[Component] = field(default_factory=list)
    paths: list[Path] = field(default_factory=list)
    cf_warnings: list[str] = field(default_factory=list)  # control-flow warning blocks

    def component(self, cid: str) -> Optional[Component]:
        return next((c for c in self.components if c.id == cid), None)


@dataclass
class Task:
    """A Control Flow task."""

    id: str
    task_type: str
    name: str
    properties: dict = field(default_factory=dict)
    precedence: list[str] = field(default_factory=list)  # upstream task ids
    parent_id: Optional[str] = None  # set when task lives inside a container


@dataclass
class ConnectionManager:
    id: str
    cm_type: str
    name: str
    properties: dict = field(default_factory=dict)  # already redacted


@dataclass
class Variable:
    name: str
    namespace: str = "User"
    value: Optional[str] = None
    is_parameter: bool = False


@dataclass
class Package:
    name: str
    version: Optional[str] = None
    protection_level: Optional[str] = None
    tasks: list[Task] = field(default_factory=list)
    data_flows: list[DataFlow] = field(default_factory=list)
    connections: list[ConnectionManager] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)


# --- helpers ---------------------------------------------------------------

import re

_RESERVED = {
    "select", "from", "where", "table", "order", "group", "by", "join",
    "user", "case", "when", "then", "else", "end",
}


def sanitize_identifier(name: str) -> str:
    """Sanitize an SSIS component name into a SQL-safe identifier.

    Spaces and special chars -> underscore; collapse repeats; lowercase.
    """
    if not name:
        return "unnamed"
    s = re.sub(r"[^0-9a-zA-Z_]", "_", name.strip())
    s = re.sub(r"_+", "_", s).strip("_").lower()
    if not s:
        return "unnamed"
    if s[0].isdigit():
        s = "_" + s
    return s
