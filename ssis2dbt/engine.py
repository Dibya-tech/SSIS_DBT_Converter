"""Top-level orchestration: parse -> convert -> grade -> summarize.

The engine turns a Package into a ConversionRun that the CLI, UI, and exporter
all consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .convert.generator import GeneratedModel, generate_model, route_layer
from .grade.reasons import CATALOG
from .ir.model import Grade, Package
from .parser import dtsx


@dataclass
class PackageMetrics:
    name: str
    total_tasks: int
    total_data_flows: int
    total_components: int
    total_connections: int
    total_variables: int
    total_parameters: int
    total_precedence: int


@dataclass
class LogEntry:
    severity: str  # INFO | WARN | ERROR | CRITICAL
    package: str
    component: str
    reason_code: str
    message: str

    def as_dict(self) -> dict:
        return {
            "severity": self.severity, "package": self.package,
            "component": self.component, "reason_code": self.reason_code,
            "message": self.message,
        }


@dataclass
class ConversionRun:
    package: Package
    dialect: str
    models: list[GeneratedModel] = field(default_factory=list)
    log: list[LogEntry] = field(default_factory=list)

    @property
    def metrics(self) -> PackageMetrics:
        pkg = self.package
        return PackageMetrics(
            name=pkg.name,
            total_tasks=len(pkg.tasks),
            total_data_flows=len(pkg.data_flows),
            total_components=sum(len(df.components) for df in pkg.data_flows),
            total_connections=len(pkg.connections),
            total_variables=sum(1 for v in pkg.variables if not v.is_parameter),
            total_parameters=sum(1 for v in pkg.variables if v.is_parameter),
            total_precedence=sum(len(t.precedence) for t in pkg.tasks),
        )

    def grade_counts(self) -> dict[str, int]:
        counts = {g.value: 0 for g in Grade}
        for m in self.models:
            for r in m.results:
                counts[r.grade.value] += 1
        return counts

    def package_score(self) -> float:
        counts = self.grade_counts()
        total = sum(counts.values())
        return round(100.0 * counts[Grade.EXACT.value] / total, 1) if total else 0.0

    def reason_histogram(self) -> dict[str, int]:
        hist: dict[str, int] = {}
        for m in self.models:
            for r in m.results:
                if r.reason_code:
                    hist[r.reason_code] = hist.get(r.reason_code, 0) + 1
        return hist

    # Control-flow tasks that need external orchestration (PRD 5.3, 8).
    def manual_tasks(self) -> list[tuple[str, str]]:
        out = []
        manual_task_types = {
            "ForEachLoop": "CONTROL_FLOW_LOOP", "ForLoop": "CONTROL_FLOW_LOOP",
            "SendMailTask": "EXTERNAL_IO", "FileSystemTask": "EXTERNAL_IO",
            "FTPTask": "EXTERNAL_IO", "ScriptTask": "SCRIPT_COMPONENT",
            "ExecutePackageTask": "CONTROL_FLOW_LOOP",
        }
        for t in self.package.tasks:
            code = manual_task_types.get(t.task_type)
            if code:
                out.append((t.name, code))
        return out


def convert_package(pkg: Package, dialect: str = "snowflake") -> ConversionRun:
    run = ConversionRun(package=pkg, dialect=dialect)
    run.log.append(LogEntry("INFO", pkg.name, "-", "-",
                            f"Parsed package: {len(pkg.data_flows)} data flow(s), "
                            f"{len(pkg.tasks)} task(s)"))

    for df in pkg.data_flows:
        layer = route_layer(df)
        model = generate_model(df, dialect=dialect, package_name=pkg.name, layer=layer)
        run.models.append(model)
        for r in model.results:
            if r.grade is Grade.EXACT:
                continue
            reason = CATALOG.get(r.reason_code) if r.reason_code else None
            sev = "CRITICAL" if r.grade is Grade.MANUAL else "WARN"
            msg = reason.meaning if reason else f"{r.grade.value} component"
            if reason:
                msg += f" -> {reason.remediation}"
            run.log.append(LogEntry(sev, pkg.name, r.component_name,
                                    r.reason_code or "-", msg))

    for tname, code in run.manual_tasks():
        reason = CATALOG.get(code)
        run.log.append(LogEntry("CRITICAL", pkg.name, tname, code,
                                f"Control-flow task requires external orchestration: "
                                f"{reason.remediation if reason else code}"))
    return run


def convert_file(path: str | Path, dialect: str = "snowflake") -> ConversionRun:
    pkg = dtsx.parse_file(path)
    return convert_package(pkg, dialect=dialect)
