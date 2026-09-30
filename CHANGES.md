# Change Log

## Session 2026-09-30 — Initial build + column & UI improvements

### New files

| File | Purpose |
|---|---|
| `ssis2dbt/__init__.py` | Package entry-point; imports dialect registry |
| `ssis2dbt/ir/model.py` | Dialect-neutral IR: `Package`, `DataFlow`, `Component`, `Column` (with `length`, `props`, `input_columns`), `Grade` |
| `ssis2dbt/parser/dtsx.py` | XXE-safe XML parser; reads output cols (filters error outputs), input cols, per-column props |
| `ssis2dbt/parser/redact.py` | Credential redaction at parse layer (passwords, tokens, keys) |
| `ssis2dbt/dialects/base.py` | `Dialect` base class + registry (`get_dialect`, `available`) |
| `ssis2dbt/dialects/impls.py` | Snowflake, T-SQL, Databricks concrete dialects |
| `ssis2dbt/convert/expression.py` | SSIS expression → SQL translator (ternary, casts, ISNULL, operators, Jinja vars) |
| `ssis2dbt/convert/components.py` | 18 SSIS component converters; explicit column SELECTs, real CAST in DataConversion, CTE description blocks |
| `ssis2dbt/convert/generator.py` | Topo-sort CTE chainer; `{{ source() }}` / `{{ ref() }}`; layer routing |
| `ssis2dbt/engine.py` | Top-level orchestrator: parse → convert → grade → log (`ConversionRun`, `PackageMetrics`) |
| `ssis2dbt/grade/reasons.py` | Reason-code catalog (13 codes) with grade + remediation text |
| `ssis2dbt/export/project.py` | dbt project exporter: `dbt_project.yml`, `schema.yml`, `sources.yml`, `packages.yml`, `profiles.yml.example`, `conversion_report.csv`, `README.md` |
| `ssis2dbt/cli/main.py` | CLI: `inspect` (metrics) and `convert` (export) sub-commands |
| `ssis2dbt/ui/app.py` | Dark-mode Streamlit UI: metrics dashboard, dual-pane, SQL tabs, log, 3× download buttons |
| `ssis2dbt/ui/flow_diagram.py` | Self-contained SVG flow diagram (vertical topo layout, typed node colours, labelled edges) |
| `tests/test_engine.py` | 15 pytest tests: parse, redaction, conversion, expression translation, dialects |
| `examples/LoadSales.dtsx` | Sample SSIS package (OLE DB source, Derived Column, Lookup, Destination) |
| `examples/DimDateETL.dtsx` | Real-world Dim Date package (Excel source, Data Conversion, OLE DB Destination) |
| `requirements.txt` | `streamlit>=1.30`, `pytest>=7.0` |
| `README.md` | Project README with quick-start, architecture, component table |
| `CHANGES.md` | This file |

### Key design decisions tracked in graphify

| Decision | Where |
|---|---|
| Dialect-neutral IR decouples parse from SQL emission | `ir/model.py` → `dialects/` |
| Credential redaction at parser layer — secrets never enter IR | `parser/redact.py` called inside `_read_properties` |
| Error outputs filtered before column extraction | `parser/dtsx.py:_read_output_columns` |
| `SourceInputColumnLineageID` used to resolve DataConversion source column | `convert/components.py:_data_conversion` |
| CTE description block in every converter (not in generator) | `convert/components.py:_cte_desc` |
| Vertical SVG flow (depth→Y, branches→X) | `ui/flow_diagram.py:build_graph_data` |

### Graphify community map

| Community | Key nodes |
|---|---|
| `dtsx.py` | `Package`, `Column`, `dtsx.py`, `redact.py`, `model.py` |
| `components.py` | `Component`, `Grade`, `CTEResult`, `Ctx`, `converter()`, `convert_component()` |
| `Grade` | `generate_model()`, `generator.py`, `engine.py`, `reasons.py`, `flow_diagram.py`, `GeneratedModel` |
| `app.py` | `app.py`, `main.py`, `project.py`, `build_project_files()`, `ConversionRun` |
| `Dialect` | `Dialect`, `base.py`, `impls.py` |
| `test_engine.py` | `test_engine.py`, `expression.py`, `translate()`, `get_dialect()` |
