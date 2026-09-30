"""Integration test: convert every example .dtsx and report results."""
from __future__ import annotations

import re
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from ssis2dbt.engine import convert_file
from ssis2dbt.export.project import build_project_files

# Real credential pattern: key=<non-placeholder value>
_CRED_RE = re.compile(
    r"(?i)(password|pwd|accountkey|sharedaccesssignature|token)\s*=\s*"
    r"(?!(\*\*\*|env_var|\"\"|''))[^\s;\"']{4,}"
)

EXAMPLES = sorted(Path(__file__).parents[1].glob("examples/*.dtsx"))


def _test_package(dtsx: Path) -> dict:
    run = convert_file(dtsx, "snowflake")
    files = build_project_files(run)
    leaked = [rel for rel, content in files.items() if _CRED_RE.search(content)]
    m = run.metrics
    g = run.grade_counts()
    return {
        "name": dtsx.name,
        "flows": m.total_data_flows,
        "components": m.total_components,
        "tasks": m.total_tasks,
        "exact": g["Exact"],
        "warning": g["Warning"],
        "manual": g["Manual"],
        "score": run.package_score(),
        "leaked": leaked,
        "log_criticals": [e for e in run.log if e.severity == "CRITICAL"],
        "issues": [(r.component_name, r.reason_code)
                   for mod in run.models for r in mod.results if r.reason_code],
        "manual_tasks": run.manual_tasks(),
    }


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    hdr = f"{'Package':<30} {'Fl':>2} {'Co':>3} {'Tk':>2} {'Ex':>3} {'Wn':>3} {'Mn':>3} {'Score':>6}  Creds"
    out.write(hdr + "\n")
    out.write("-" * 70 + "\n")

    failures = []
    for dtsx in EXAMPLES:
        try:
            r = _test_package(dtsx)
            safe = "PASS" if not r["leaked"] else f"LEAK:{r['leaked']}"
            out.write(
                f"{r['name']:<30} {r['flows']:>2} {r['components']:>3} {r['tasks']:>2} "
                f"{r['exact']:>3} {r['warning']:>3} {r['manual']:>3} {r['score']:>5.1f}%  {safe}\n"
            )
        except Exception as exc:
            out.write(f"{dtsx.name:<30}  ERROR: {exc}\n")
            failures.append(dtsx.name)

    out.write("\nWarnings / Manual items:\n")
    for dtsx in EXAMPLES:
        try:
            r = _test_package(dtsx)
            rows = r["issues"] + [(t, f"CTRL:{c}") for t, c in r["manual_tasks"]]
            if rows:
                out.write(f"  {r['name']}:\n")
                for cname, code in rows:
                    out.write(f"    [{code}]  {cname}\n")
        except Exception:
            pass

    out.write(f"\n{'All PASSED' if not failures else 'FAILED: ' + str(failures)}\n")
    out.flush()
    return len(failures)


if __name__ == "__main__":
    raise SystemExit(main())
