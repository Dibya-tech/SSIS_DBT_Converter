# SSIS → dbt Migration Engine

Convert SSIS `.dtsx` packages into deployable Snowflake dbt projects — automatically, with visual flow diagrams and a confidence grade on every component.

## Quick start

```bash
pip install -r requirements.txt

# Web UI (recommended)
streamlit run ssis2dbt/ui/app.py

# CLI: inspect a package
python -m ssis2dbt.cli.main inspect examples/"Package 1.dtsx"

# CLI: convert and export
python -m ssis2dbt.cli.main convert examples/"Package 1.dtsx" --out ./build
```

## What it does

1. **Parses** `.dtsx` XML safely (XXE-proof, external entities disabled) into a dialect-neutral IR
2. **Converts** Data Flow components into chained-CTE dbt SQL models with explicit column lists
3. **Translates** SSIS expressions into Snowflake SQL (`GETDATE()` → `CURRENT_TIMESTAMP()`, `NULL(DT_WSTR,50)` → `CAST(NULL AS VARCHAR(50))`, string `+` → `||`, etc.) with inline `-- SSIS: <original>` annotations
4. **Grades** every component — **Exact / Warning / Manual** — nothing is silently dropped
5. **Exports** a complete dbt project: models, `schema.yml`, `sources.yml`, `dbt_project.yml`, `profiles.yml.example`, `conversion_report.csv`, `execution_log.jsonl`
6. **Exports flow chart PNGs** (`flowcharts/control_flow.png`, `flowcharts/<df_name>.png`) inside the zip
7. **Redacts** credentials at the parser layer — secrets never enter generated output, logs, or reports

## UI

Upload any `.dtsx` file at `http://localhost:8501`.

### Left pane — SSIS package view

One tabbed card with:

| Tab | Content |
|---|---|
| **🔄 Control Flow** | Topological diagram of tasks and containers. Green box = ForEach/Sequence container, blue = Data Flow, orange = Execute SQL. Precedence arrows show execution order and branching. |
| **\<DataFlow name\>** | Pipeline graph for each data flow — source → transforms → destination — with branch paths centred at each depth level and output-port edge labels. |

### Right pane — generated dbt project

One tab per model showing: layer, confidence grade, full SQL with CTEs.

### Export (bottom)

| Button | Contents |
|---|---|
| ⬇ dbt project (.zip) | All SQL models + YAML files + `flowcharts/*.png` |
| ⬇ Conversion report (.csv) | Per-component grade, reason code, notes |
| ⬇ Execution log (.jsonl) | Parser and converter events |

## Supported SSIS components

| Category | Components |
|---|---|
| Sources | OLE DB Source, ADO.NET Source, Flat File Source, Excel Source |
| Destinations | OLE DB Destination, Flat File Destination |
| Transforms | Derived Column, Data Conversion, Lookup, Sort, Aggregate, Conditional Split (branching CTEs), Multicast, Union All, Merge Join, Merge, Pivot, Unpivot, SCD, Row Count, OLE DB Command |
| Control flow | Execute SQL Task (SQL embedded as `/* CONVERSION WARNING */` comment), ForEach Loop (recursive), Sequence Container |
| Manual review | Script Component, Send Mail, FTP, File System |

## Architecture

```
.dtsx (XML)
  └─ Parser (XXE-safe)
       ├─ Credential Redactor          # secrets stripped before IR
       └─ IR Builder (Package / DataFlow / Component / Task)
            ├─ parent_id tracking      # ForEach / Sequence container nesting
            └─ PrecedenceConstraint    # control-flow ordering
                 │
                 ▼
           Component Converters
             ├─ Expression Translator  # SSIS expr → Snowflake SQL + origin annotations
             ├─ CTE Generator          # topo sort → chained CTEs
             └─ Confidence Grader      # Exact / Warning / Manual
                  │
                  ▼
            Project Exporter
              ├─ SQL models + YAML
              ├─ Conversion report CSV
              └─ Flow chart PNGs       # SVG → PNG via svglib + reportlab
                   │
                   ▼
             Streamlit UI
               ├─ CF diagram  (Python SVG, vertical topo layout)
               └─ DF diagrams (Python SVG, centred branch layout)
```

## Dialect

Snowflake is the target dialect (hardcoded). Output uses:
- `CURRENT_TIMESTAMP()` for `GETDATE()`
- `CAST(NULL AS <type>)` for `NULL(DT_*)` typed nulls
- `||` for string concatenation
- `NUMERIC(p, s)` for `DT_NUMERIC` with precision/scale preserved
- `VARCHAR(n)` / `CHAR(n)` / `BOOLEAN` / `DATE` / `TIMESTAMP_NTZ` type mappings

## Security

- XXE-safe XML parsing: `xml.etree.ElementTree` with no external entity or DTD resolution
- Credentials redacted at the parser layer via `redact.py` — connection string secrets never enter the IR, generated SQL, logs, or reports
- `profiles.yml.example` uses `env_var(...)` placeholders only

## Tests

```bash
python -m pytest tests/ -q
```

## Knowledge graph

```bash
python -m graphify update .      # rebuild after code changes (AST-only, no API cost)
python -m graphify query "<q>"   # scoped subgraph lookup
python -m graphify path "A" "B"  # relationship between two nodes
python -m graphify explain "<c>" # focused concept explanation
```

Graph stats: 361 nodes · 823 edges · 28 communities (as of 2026-10-01).
