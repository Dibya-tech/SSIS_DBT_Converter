"""Command-line interface for the SSIS-to-dbt Migration Engine.

Examples:
    python -m ssis2dbt.cli.main convert examples/LoadSales.dtsx --dialect snowflake --out ./build
    python -m ssis2dbt.cli.main inspect examples/LoadSales.dtsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import dialects  # noqa: F401
from ..dialects import impls  # noqa: F401
from ..dialects.base import available
from ..engine import convert_file
from ..export.project import write_project


def _cmd_inspect(args) -> int:
    run = convert_file(args.path, dialect=args.dialect)
    m = run.metrics
    print(f"Package: {m.name}")
    print(f"  Data flows      : {m.total_data_flows}")
    print(f"  Components       : {m.total_components}")
    print(f"  Control tasks    : {m.total_tasks}")
    print(f"  Connections      : {m.total_connections}")
    print(f"  Variables/Params : {m.total_variables}/{m.total_parameters}")
    print(f"  Grade counts     : {run.grade_counts()}")
    print(f"  Package score    : {run.package_score()}% Exact")
    return 0


def _cmd_convert(args) -> int:
    run = convert_file(args.path, dialect=args.dialect)
    root = write_project(run, args.out)
    print(f"Wrote dbt project -> {root}")
    print(f"Models: {len(run.models)} | Grades: {run.grade_counts()} "
          f"| Score: {run.package_score()}%")
    if args.verbose:
        for line in run.log:
            print(f"  [{line.severity}] {line.component}: {line.message}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ssis2dbt", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("path", help="Path to a .dtsx file")
    common.add_argument("--dialect", default="snowflake", choices=available())

    pi = sub.add_parser("inspect", parents=[common], help="Show package metrics")
    pi.set_defaults(func=_cmd_inspect)

    pc = sub.add_parser("convert", parents=[common], help="Convert and export a dbt project")
    pc.add_argument("--out", default="./build", help="Output directory")
    pc.add_argument("-v", "--verbose", action="store_true")
    pc.set_defaults(func=_cmd_convert)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not Path(args.path).exists():
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
