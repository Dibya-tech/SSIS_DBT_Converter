"""Export a ConversionRun into a deployable dbt project (PRD section 9)."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from ..engine import ConversionRun
from ..ir.model import sanitize_identifier

_MATERIALIZATION = {"staging": "view", "intermediate": "view", "marts": "table"}


def build_project_files(run: ConversionRun) -> dict[str, str]:
    """Return {relative_path: file_contents} for the whole dbt project."""
    pkg_name = sanitize_identifier(run.package.name) or "migrated_package"
    files: dict[str, str] = {}

    files["dbt_project.yml"] = _dbt_project_yml(pkg_name, run)
    files["profiles.yml.example"] = _profiles_example(pkg_name, run.dialect)
    files["packages.yml"] = "packages:\n  - package: dbt-labs/dbt_utils\n    version: [\">=1.0.0\", \"<2.0.0\"]\n"

    # models, one subfolder per model (PRD 9.1)
    for m in run.models:
        rel = f"models/{m.layer}/{m.model_name}/{m.model_name}.sql"
        files[rel] = m.sql
    files["models/sources.yml"] = _sources_yml(run)
    files["models/schema.yml"] = _schema_yml(run)

    files["conversion_report.csv"] = report_csv(run)
    files["execution_log.jsonl"] = "\n".join(
        __import__("json").dumps(e.as_dict()) for e in run.log)
    files["README.md"] = _readme(pkg_name, run)
    for keep in ("macros", "seeds", "tests"):
        files[f"{keep}/.gitkeep"] = ""
    return files


def write_project(run: ConversionRun, out_dir: str | Path) -> Path:
    root = Path(out_dir) / (sanitize_identifier(run.package.name) or "migrated_package")
    for rel, content in build_project_files(run).items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return root


def _dbt_project_yml(pkg_name: str, run: ConversionRun) -> str:
    lines = [
        "name: '%s'" % pkg_name,
        "version: '1.0.0'",
        "config-version: 2",
        "profile: '%s'" % pkg_name,
        "model-paths: [\"models\"]",
        "target-path: \"target\"",
        "clean-targets: [\"target\", \"dbt_packages\"]",
        "models:",
        "  %s:" % pkg_name,
    ]
    for layer, mat in _MATERIALIZATION.items():
        lines.append(f"    {layer}:")
        lines.append(f"      +materialized: {mat}")
    data_vars = [v for v in run.package.variables if not v.is_parameter]
    if data_vars:
        lines.append("vars:")
        for v in data_vars:
            lines.append(f"  {sanitize_identifier(v.name)}: \"{v.value or ''}\"")
    return "\n".join(lines) + "\n"


def _profiles_example(pkg_name: str, dialect: str) -> str:
    typ = {"snowflake": "snowflake", "tsql": "sqlserver", "databricks": "databricks"}.get(
        dialect, "snowflake")
    return (
        f"{pkg_name}:\n"
        f"  target: dev\n"
        f"  outputs:\n"
        f"    dev:\n"
        f"      type: {typ}\n"
        f"      # Credentials via env_var (never commit secrets)\n"
        f"      account: \"{{{{ env_var('DBT_ACCOUNT') }}}}\"\n"
        f"      user: \"{{{{ env_var('DBT_USER') }}}}\"\n"
        f"      password: \"{{{{ env_var('DBT_PASSWORD') }}}}\"\n"
        f"      database: \"{{{{ env_var('DBT_DATABASE') }}}}\"\n"
        f"      schema: \"{{{{ env_var('DBT_SCHEMA') }}}}\"\n"
    )


def _sources_yml(run: ConversionRun) -> str:
    lines = ["version: 2", "", "sources:", "  - name: raw",
             "    description: \"Migrated from SSIS connection managers (secrets redacted)\"",
             "    tables:"]
    seen = set()
    for cm in run.package.connections:
        t = sanitize_identifier(cm.name)
        if t and t not in seen:
            seen.add(t)
            lines.append(f"      - name: {t}")
    if not seen:
        lines.append("      - name: placeholder")
    return "\n".join(lines) + "\n"


def _schema_yml(run: ConversionRun) -> str:
    lines = ["version: 2", "", "models:"]
    for m in run.models:
        lines.append(f"  - name: {m.model_name}")
        lines.append(f"    description: \"Migrated from {run.package.name} / {m.data_flow_id}\"")
        # emit review markers for non-exact components as model meta
        non_exact = [r for r in m.results if r.reason_code]
        if non_exact:
            lines.append("    meta:")
            lines.append("      migration_reviews:")
            for r in non_exact:
                lines.append(f"        - {{component: \"{r.component_name}\", reason: {r.reason_code}}}")
    return "\n".join(lines) + "\n"


def report_csv(run: ConversionRun) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["model", "layer", "component", "type", "grade", "reason_code", "notes"])
    for m in run.models:
        for r in m.results:
            w.writerow([m.model_name, m.layer, r.component_name, r.component_type,
                        r.grade.value, r.reason_code or "", "; ".join(r.notes)])
    return buf.getvalue()


def _readme(pkg_name: str, run: ConversionRun) -> str:
    counts = run.grade_counts()
    return (
        f"# {pkg_name} (migrated from SSIS)\n\n"
        f"Generated by the SSIS-to-dbt Migration Engine.\n\n"
        f"- Target dialect: **{run.dialect}**\n"
        f"- Package score (Exact): **{run.package_score()}%**\n"
        f"- Components: {counts}\n\n"
        f"## Next steps\n\n"
        f"1. Review `-- REVIEW:` markers in the generated models.\n"
        f"2. Resolve Manual/Warning items in `conversion_report.csv`.\n"
        f"3. Set credentials via env vars (see `profiles.yml.example`).\n"
        f"4. Run `dbt deps && dbt compile`.\n"
    )
