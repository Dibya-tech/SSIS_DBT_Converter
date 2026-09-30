# SSIS to dbt Migration Engine

Convert SSIS `.dtsx` packages into deployable dbt projects — automatically.

## Quick start

```bash
pip install -r requirements.txt

# Web UI (dark mode)
streamlit run ssis2dbt/ui/app.py

# CLI: inspect a package
python -m ssis2dbt.cli.main inspect examples/LoadSales.dtsx

# CLI: convert and export
python -m ssis2dbt.cli.main convert examples/LoadSales.dtsx --dialect snowflake --out ./build
```

## What it does

1. **Parses** `.dtsx` XML (safe, XXE-proof) into a dialect-neutral IR
2. **Converts** Data Flow components into chained-CTE dbt models with explicit column lists
3. **Grades** every component (Exact / Warning / Manual) — nothing is silently dropped
4. **Exports** a complete dbt project: models, `schema.yml`, `sources.yml`, tests, variables
5. **Redacts** credentials at the parser layer — secrets never enter generated output

## Supported dialects

- **Snowflake** (default)
- **T-SQL** (SQL Server / Fabric)
- **Databricks** (Spark SQL)

## Supported SSIS components

| Category | Components |
|---|---|
| Sources | OLE DB, ADO.NET, Flat File, Excel |
| Destinations | OLE DB, Flat File |
| Transforms | Derived Column, Data Conversion, Lookup, Sort, Aggregate, Conditional Split, Multicast, Union All, Merge Join, Merge, Pivot/Unpivot, SCD, Row Count, OLE DB Command |
| Manual | Script Component (C#/VB), Send Mail, ForEach/For Loop, FTP, File System |

## Architecture

```text
.dtsx -> XML Parser -> Credential Redactor -> IR -> Component Converters
    -> Expression Translator -> SQL Generator (CTE + Jinja) -> Dialect Emitter
    -> Confidence Grader -> Project Exporter -> Report Writer
```

## Tests

```bash
python -m pytest tests/ -q
```
