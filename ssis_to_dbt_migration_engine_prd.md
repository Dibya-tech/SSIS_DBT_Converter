# Product Requirements Document (PRD): SSIS to dbt Migration Engine

| Field | Value |
|---|---|
| **Document Status** | v3.0 (Enriched Draft) |
| **Based on** | v2.0 (Enriched Draft) |
| **Target Audience** | Data Engineering, DevOps, Product, Security/Compliance |
| **Product Type** | Migration utility (web UI + CLI + parser core) |

> **Convention:** Sections marked _(Proposed)_ are enrichments added beyond the original v2.0 draft (for example, mapping tables, NFRs, risks, and phasing). They are intended as starting points for review, not final commitments.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement, Goals & Non-Goals](#2-problem-statement-goals--non-goals-proposed)
3. [Personas & Key User Journeys](#3-personas--key-user-journeys-proposed)
4. [Core Conversion Architecture](#4-core-conversion-architecture)
5. [SSIS Component to SQL Mapping Reference](#5-ssis-component-to-sql-mapping-reference-proposed)
6. [Target Dialect Support](#6-target-dialect-support)
7. [User Interface & Experience](#7-user-interface--experience-uxui)
8. [Conversion Confidence & Exception Handling](#8-conversion-confidence--exception-handling)
9. [Export Architecture & dbt Project Generation](#9-export-architecture--dbt-project-generation)
10. [Auditing, Logging & Security](#10-auditing-logging--security)
11. [Non-Functional Requirements](#11-non-functional-requirements-proposed)
12. [System Architecture & Processing Pipeline](#12-system-architecture--processing-pipeline-proposed)
13. [Success Metrics](#13-success-metrics-proposed)
14. [Risks & Mitigations](#14-risks--mitigations-proposed)
15. [Phased Roadmap](#15-phased-roadmap-proposed)
16. [Open Questions](#16-open-questions-proposed)
17. [Appendix](#17-appendix)

---

## 1. Executive Summary

The **SSIS to dbt Migration Engine** is a specialized utility designed to accelerate the modernization of legacy SQL Server Integration Services (SSIS) packages into modular, version-controlled **dbt (data build tool)** projects.

By parsing XML-based `.dtsx` files, the tool translates visual ETL pipelines into optimized SQL logic, maintaining data lineage while bridging the gap between traditional on-premise workflows and modern cloud data platforms (Snowflake, Databricks, Fabric/T-SQL).

**Key value propositions**

- **Speed:** Replace weeks of manual re-engineering per package with an automated first pass.
- **Fidelity:** Preserve component naming and lineage so reviewers can trace every CTE back to its SSIS origin.
- **Transparency:** Explicitly grade every component (Exact / Warning / Manual) so nothing is silently dropped.
- **Deployability:** Emit a complete dbt project (models, `schema.yml`, tests, variables) ready for CI/CD.

---

## 2. Problem Statement, Goals & Non-Goals _(Proposed)_

### 2.1 Problem Statement

Organizations running SSIS estate face several compounding issues:

- Logic is locked inside binary-like XML (`.dtsx`) and visual designers, which makes code review, diffing, and version control painful.
- Orchestration (Control Flow) and transformation (Data Flow) are intertwined, which hinders modularity and reuse.
- Lineage is implicit and undocumented; testing is minimal or manual.
- Cloud migration programs require re-platforming hundreds or thousands of packages, and manual rewrites do not scale.

### 2.2 Goals

| # | Goal |
|---|---|
| G1 | Automatically convert SQL-expressible Data Flow logic into dbt models with high fidelity. |
| G2 | Surface unconvertible logic explicitly, with actionable guidance on where it should live instead (ADF, Airflow, etc.). |
| G3 | Preserve lineage and naming so reviewers can validate quickly. |
| G4 | Produce a deployable dbt project structure aligned with Medallion architecture. |
| G5 | Support multiple target dialects from a single parsed representation. |
| G6 | Ensure no secrets leak into generated artifacts. |

### 2.3 Non-Goals

- Executing or scheduling the generated dbt project (handled by dbt Core/Cloud, Airflow, ADF, etc.).
- Migrating data itself (only transformation logic is migrated).
- Fully automatic conversion of Script Components (C#/VB) into SQL.
- Replacing SSIS Control Flow orchestration inside dbt (dbt is not an orchestrator).
- Live connection to SSISDB/catalog in v1 (input is `.dtsx` files).

---

## 3. Personas & Key User Journeys _(Proposed)_

### 3.1 Personas

| Persona | Needs |
|---|---|
| **Migration Engineer** | Bulk convert packages, review generated SQL, fix warnings, export project. |
| **Data Architect** | Validate layering (staging / intermediate / marts) and naming conventions. |
| **DevOps / Platform Engineer** | Wire generated project into CI/CD (Azure DevOps / GitHub Actions) with environment-specific configs. |
| **Reviewer / QA Analyst** | Compare legacy flow visuals and new SQL side-by-side; confirm parity. |
| **Security / Compliance** | Confirm no credentials or connection strings leak into outputs. |

### 3.2 Primary Journey

1. Import one or more `.dtsx` files (and optionally the project parameter file).
2. Review the **Dashboard Metrics** summary to scope effort.
3. Choose target dialect and layering conventions.
4. Click **Convert**; review the **Execution Log** and confidence indicators.
5. Inspect and edit SQL in the **SQL Tab**; resolve Warnings.
6. Review Manual items and route them to external orchestration.
7. **Export** the dbt project and **Conversion Report**.
8. Commit to Git; run `dbt compile` / `dbt build` in CI.

---

## 4. Core Conversion Architecture

Because SSIS intertwines orchestration (Control Flow) with data transformation (Data Flow), the migration engine **strictly enforces modularity** by isolating transformations.

### 4.1 Design Principles

- **1:1 Data Flow Mapping:** Each individual Data Flow Task within a `.dtsx` package generates a distinct, separate dbt `.sql` model.
- **Sequential CTE Chaining:** The execution sequence of components within a data flow is translated into chained Common Table Expressions (CTEs).
- **Traceable Lineage & Naming:** Generated CTEs inherit the exact naming conventions of their source SSIS components (sanitized for SQL validity), preserving historical lineage and easing review.
- **Branching & Merging Logic:** Diverging data paths (e.g., Multicast or Conditional Split) are processed as independent CTE branches, then merged downstream via `JOIN` or `UNION ALL` before the terminal `SELECT`.
- **Jinja Templating:** Output uses standard dbt Jinja: `{{ source() }}` for upstream raw data connections and `{{ ref() }}` for internal downstream dependencies.
- **Target Dialect Configurations:** Dialect-specific SQL generation (see [Section 6](#6-target-dialect-support)).

### 4.2 Example: Generated Model Shape _(Proposed)_

```sql
-- models/staging/stg_sales__orders.sql
-- Source package : LoadSales.dtsx
-- Data Flow Task : DFT_Load_Orders
-- Generated by   : SSIS-to-dbt Migration Engine

with

src_oledb_orders as (
    select * from {{ source('erp', 'orders') }}
),

drv_add_load_date as (
    select
        *,
        cast(order_ts as date) as order_date
    from src_oledb_orders
),

lkp_customer as (
    select
        d.*,
        c.customer_key
    from drv_add_load_date d
    left join {{ ref('stg_erp__customers') }} c
        on d.customer_id = c.customer_id
),

cs_valid_rows as (
    select * from lkp_customer where customer_key is not null
),

cs_invalid_rows as (
    select * from lkp_customer where customer_key is null
),

final as (
    select * from cs_valid_rows
)

select * from final
```

> CTE prefixes (`src_`, `drv_`, `lkp_`, `cs_`) are illustrative; the actual identifier preserves the original SSIS component name per the lineage requirement.

### 4.3 Handling Branching in Detail _(Proposed)_

| SSIS Pattern | Generated SQL Pattern |
|---|---|
| Multicast | One upstream CTE referenced by multiple downstream CTEs. |
| Conditional Split | One CTE per output, each filtering with the mapped condition; default output uses the negation of all other conditions. |
| Union All | `UNION ALL` with explicit column alignment. |
| Merge / Merge Join | `JOIN` with join type derived from the component setting (inner/left/full). |
| Error output (redirect row) | Separate CTE for rejected rows; flagged for review (see Warnings). |

### 4.4 Model Granularity & Naming Rules _(Proposed)_

- Model name = `<layer_prefix>_<source_or_domain>__<entity>` (configurable).
- Collisions resolved deterministically with suffixes and reported in the log.
- Identifiers sanitized: spaces and special characters replaced with `_`, reserved keywords quoted per dialect.

---

## 5. SSIS Component to SQL Mapping Reference _(Proposed)_

Initial mapping proposal. Grade indicates default confidence (see [Section 8](#8-conversion-confidence--exception-handling)).

### 5.1 Sources & Destinations

| SSIS Component | dbt / SQL Equivalent | Default Grade |
|---|---|---|
| OLE DB Source | `{{ source() }}` select (table or SQL command) | Exact |
| ADO.NET Source | `{{ source() }}` select | Exact |
| Flat File Source | `source()` over external/staged table (requires seed or external table config) | Warning |
| Excel Source | External table or seed | Warning |
| OLE DB Destination | Terminal model materialization (`table` / `incremental`) | Exact |
| Flat File Destination | Out of dbt scope (export step) | Manual |

### 5.2 Transformations

| SSIS Component | SQL Equivalent | Default Grade |
|---|---|---|
| Derived Column | `SELECT` expressions | Exact (Warning if uses unsupported functions) |
| Data Conversion | `CAST` / `TRY_CAST` | Exact |
| Lookup | `LEFT JOIN` (inner for "fail on no match") | Exact |
| Sort | `ORDER BY` (dropped when downstream order is irrelevant; noted in log) | Exact |
| Aggregate | `GROUP BY` | Exact |
| Conditional Split | Filter CTEs | Exact |
| Multicast | Shared upstream CTE | Exact |
| Union All | `UNION ALL` | Exact |
| Merge Join | `JOIN` | Exact |
| Merge | `UNION ALL` + `ORDER BY` | Warning |
| Row Count | Post-hook/test or dropped with note | Warning |
| Pivot / Unpivot | `PIVOT` / `UNPIVOT` (dialect-specific) | Warning |
| Slowly Changing Dimension | dbt snapshot / incremental pattern | Warning |
| Fuzzy Lookup / Fuzzy Grouping | No direct equivalent | Manual |
| Script Component (C#/VB) | Not convertible | Manual |
| OLE DB Command | Row-by-row DML; consider `MERGE` / post-hook | Warning / Manual |

### 5.3 Control Flow Tasks

| SSIS Task | Handling |
|---|---|
| Data Flow Task | Converted to dbt model |
| Execute SQL Task | Convert to model, `run-operation` macro, or hook where deterministic; otherwise Warning |
| ForEach Loop / For Loop | Manual: external orchestration or dbt Jinja loops where feasible |
| Send Mail Task | Manual: orchestrator notification |
| File System / FTP Task | Manual: orchestrator or cloud storage tooling |
| Execute Package Task | Manual/Warning: represented as model dependency graph or orchestrator DAG |
| Script Task | Manual |
| Precedence Constraints | Captured as `ref()` dependencies where data-related; the rest documented in the report |

---

## 6. Target Dialect Support

The engine supports dialect-specific SQL generation for **Snowflake**, **Databricks (Spark SQL)**, and standard **T-SQL**.

### 6.1 Dialect Translation Examples _(Proposed)_

| Concern | T-SQL | Snowflake | Databricks |
|---|---|---|---|
| Current timestamp | `GETDATE()` | `CURRENT_TIMESTAMP()` | `current_timestamp()` |
| Null substitution | `ISNULL(a,b)` | `COALESCE(a,b)` / `IFNULL` | `coalesce(a,b)` |
| String length | `LEN(x)` | `LENGTH(x)` | `length(x)` |
| Date add | `DATEADD(day,1,d)` | `DATEADD(day,1,d)` | `date_add(d,1)` |
| Date parse | `CONVERT(date,x,120)` | `TO_DATE(x,'YYYY-MM-DD')` | `to_date(x,'yyyy-MM-dd')` |
| Safe cast | `TRY_CAST` | `TRY_CAST` | `try_cast` |
| Top N | `TOP (n)` | `LIMIT n` | `LIMIT n` |
| String concat | `a + b` | `a \|\| b` | `concat(a,b)` |

### 6.2 SSIS Expression Language Translation _(Proposed)_

SSIS expressions (used in Derived Columns, Conditional Splits, and variables) use a C-like syntax, not T-SQL. The engine should include an expression parser that produces an AST and then emits dialect-specific SQL.

| SSIS Expression | SQL Output (generic) |
|---|---|
| `[Col] == "X"` | `col = 'X'` |
| `[Col] != "X"` | `col <> 'X'` |
| `cond ? a : b` | `CASE WHEN cond THEN a ELSE b END` |
| `ISNULL([Col])` | `col IS NULL` |
| `UPPER([Col])` | `UPPER(col)` |
| `(DT_WSTR,50)[Col]` | `CAST(col AS VARCHAR(50))` |
| `@[User::Var]` | `{{ var('var') }}` (Jinja) |

Expressions that cannot be mapped confidently are emitted as commented placeholders and graded **Warning**.

---

## 7. User Interface & Experience (UX/UI)

The UI acts as both a **migration wizard** and an **analytical dashboard**, allowing engineers to audit packages prior to execution.

### 7.1 Dashboard Metrics

Upon importing a `.dtsx` file, the platform renders a metadata summary of the legacy package:

| Category | Extracted Data Points |
|---|---|
| Control Flow | Total Tasks, Total Precedence Constraints |
| Data Flow | Total Data Flows, Total Transformation Components |
| Connections | Connection Managers (OLEDB, ADO.NET, Flat File) |
| Parameters | Total Package Variables, Total Project Parameters |

_(Proposed additions)_

| Category | Additional Data Points |
|---|---|
| Complexity | Estimated complexity score, component count per data flow |
| Convertibility Forecast | Predicted Exact / Warning / Manual distribution before conversion |
| Dependencies | Cross-package and cross-source dependencies |
| Sources & Targets | Distinct source tables/files and destination tables |

### 7.2 Workspace Capabilities

- **Dual-Pane View:** Legacy `.dtsx` structural reference on the left; the new modular dbt project structure on the right.
- **Global Convert Action:** A primary **Convert** button processes all viable components in the loaded package simultaneously.
- **Holistic SQL Editor:** A dedicated **SQL Tab** in the properties panel shows the complete, chained CTE model for the selected data flow. Supports full inline editing and a one-click **Copy** button.

### 7.3 UX Enhancements _(Proposed)_

- **Click-through traceability:** Selecting a component on the left highlights the corresponding CTE on the right, and vice versa.
- **Diff view:** Compare auto-generated SQL versus user-edited SQL; a reset-to-generated option.
- **Batch mode:** Import a folder of packages and convert in bulk with a summary grid.
- **Per-component filter:** Filter by grade (Exact / Warning / Manual).
- **Dialect selector & preview:** Switch dialect and re-render SQL without re-parsing.
- **SQL syntax validation:** Lint and dialect-aware syntax check, with inline error markers.
- **Accessibility:** Grades conveyed by icon *and* color; keyboard navigation for the editor and panes.

### 7.4 Wireframe (Conceptual) _(Proposed)_

```
+--------------------------------------------------------------------------+
| [Import .dtsx]  Dialect: [Snowflake v]  Layering: [Auto v]  [ CONVERT ]  |
+---------------------------+----------------------------------------------+
| SSIS PACKAGE (Legacy)     | DBT PROJECT (Generated)                      |
|                           |                                              |
|  Control Flow             |  LoadSales/                                  |
|   +- DFT_Load_Orders      |   +- models/staging/stg_sales__orders.sql    |
|   |   OLE DB Source       |   +- models/marts/fct_orders.sql             |
|   |   Derived Column      |   +- schema.yml                              |
|   |   Lookup              |                                              |
|   |   Script Component X  |  [ SQL ] [ Lineage ] [ Log ] [ Report ]      |
|   +- Send Mail Task    X  |  with ... select ...                         |
+---------------------------+----------------------------------------------+
| Execution Log: 14 Exact | 3 Warning | 2 Manual                           |
+--------------------------------------------------------------------------+
```

---

## 8. Conversion Confidence & Exception Handling

Not all SSIS tasks (e.g., Script Components using C#, Send Mail Tasks, ForEach Loops) have direct dbt equivalents. The engine **grades each component** to guide manual intervention.

| Grade | Definition | Examples |
|---|---|---|
| **Exact** | Component logic translates directly to SQL. | Derived Columns, Lookups, Sorts |
| **Warning** | Translates partially, relies on dynamic variables, or needs manual review for optimization. | Dynamic SQL, SCD, Pivot, Flat File sources |
| **Manual (Unconvertible)** | Logic falls outside the scope of SQL/dbt. | Script Components (C#), Send Mail, ForEach Loops |

### 8.1 Manual Component Handling

- **Visual Indicator:** A definitive **red cross / error mark** is displayed directly on the component bar within the visual flow UI.
- **Logging Output:** The logging system outputs a **critical warning** detailing the component name and the exact architectural reason it must be handled outside dbt (e.g., requires external orchestration such as Azure Data Factory or Airflow).

### 8.2 Warning Handling _(Proposed)_

- Warnings emit a **`-- REVIEW:`** comment inline in generated SQL near the affected logic.
- Each warning carries a reason code, a suggested remediation, and a link to documentation.

### 8.3 Reason Code Catalog _(Proposed)_

| Code | Meaning | Suggested Remediation |
|---|---|---|
| `SCRIPT_COMPONENT` | Custom C#/VB logic | Rewrite as SQL/UDF or move to Python model/external service |
| `CONTROL_FLOW_LOOP` | ForEach/For loop | Move to Airflow/ADF or use dbt Jinja loop if applicable |
| `EXTERNAL_IO` | File/FTP/Mail task | Handle via orchestrator or cloud-native tooling |
| `DYNAMIC_SQL` | SQL built from variables | Parameterize with `var()` / macros; review manually |
| `UNMAPPED_FUNCTION` | Expression function has no dialect mapping | Provide manual translation |
| `ROW_BY_ROW_DML` | OLE DB Command | Replace with set-based `MERGE` / incremental model |
| `ERROR_REDIRECT` | Error output routing | Model rejects as separate CTE/table and add tests |

### 8.4 Confidence Rollup _(Proposed)_

- A **data flow grade** equals the lowest grade among its components (any Manual → data flow flagged Manual/Partial).
- A **package score** = percentage of components graded Exact, surfaced in the dashboard and report.

---

## 9. Export Architecture & dbt Project Generation

The export module packages converted assets into a fully deployable directory structure, aligned with **Medallion architecture** principles to separate raw ingested data from transformed business logic.

### 9.1 Directory Structure

- **Root Folder:** Named identically to the source `.dtsx` file.
- **Model-Specific Subfolders:** Each generated model gets a dedicated subfolder containing:
  - The generated `<model_name>.sql` file.
  - A visual image snapshot (`.png`/`.jpg`) of the original SSIS flow (extracted from the DTSX viewer) for historical context and reviewer proof.
- **dbt Layering:** Output is automatically routed into standard dbt directories (`models/staging`, `models/intermediate`, `models/marts`) based on user-defined naming conventions or source vs. destination configuration.

```text
LoadSales/                          <- named after LoadSales.dtsx
├── dbt_project.yml
├── profiles.yml.example
├── packages.yml
├── models/
│   ├── staging/
│   │   └── stg_sales__orders/
│   │       ├── stg_sales__orders.sql
│   │       └── stg_sales__orders_flow.png
│   ├── intermediate/
│   │   └── int_orders_enriched/
│   │       ├── int_orders_enriched.sql
│   │       └── int_orders_enriched_flow.png
│   ├── marts/
│   │   └── fct_orders/
│   │       ├── fct_orders.sql
│   │       └── fct_orders_flow.png
│   ├── sources.yml
│   └── schema.yml
├── macros/
├── seeds/
├── tests/
├── conversion_report.csv
└── README.md
```

> **Note:** dbt discovers models recursively under `models/`, so per-model subfolders are compatible with standard dbt behavior.

### 9.2 Layer Routing Rules _(Proposed)_

| Layer | Routing Heuristic |
|---|---|
| **Staging** | Data flows that read directly from external sources with light cleansing/casting/renaming. |
| **Intermediate** | Data flows with joins, lookups, aggregations, or business rules between staging and final outputs. |
| **Marts** | Data flows whose destination is a reporting/dimension/fact table (based on user-defined naming patterns). |

Users can override the heuristic through a configuration file (e.g., `migration_config.yml`) and in the UI.

### 9.3 Automated Testing & Documentation

The engine extracts schema metadata, primary key constraints, and data types from the SSIS package to generate a foundational `schema.yml`, pre-populated with dbt tests.

```yaml
version: 2

models:
  - name: stg_sales__orders
    description: "Migrated from LoadSales.dtsx / DFT_Load_Orders"
    columns:
      - name: order_id
        description: "Primary key"
        tests:
          - not_null
          - unique
      - name: order_status
        tests:
          - accepted_values:
              values: ['OPEN', 'SHIPPED', 'CLOSED']
      - name: customer_key
        tests:
          - relationships:
              to: ref('stg_erp__customers')
              field: customer_key
```

_(Proposed)_ Additional test generation:

- `relationships` tests derived from Lookup components.
- `accepted_values` derived from Conditional Split literals where reliable.
- Column-level `description` sourced from SSIS metadata/annotations when present.
- Data type comments included as column `data_type` in contracts (for dbt model contracts).

### 9.4 Sources & Materializations _(Proposed)_

- `sources.yml` generated from Source components and Connection Managers (credentials redacted).
- Materialization defaults: staging = `view`, intermediate = `ephemeral` / `view`, marts = `table` or `incremental` (configurable).
- Incremental hints when SSIS logic uses watermark variables/Lookups on last-loaded date (graded Warning).

### 9.5 Environment Variables & Configuration

Legacy SSIS project parameters and variables are mapped into `dbt_project.yml` variables or `profiles.yml` targets, enabling CI/CD integration through Azure DevOps or GitHub Actions.

| SSIS Construct | dbt Target |
|---|---|
| Package Variable (data-related) | `vars:` in `dbt_project.yml`, accessed via `{{ var('name') }}` |
| Project Parameter (environment-related, e.g., server, schema) | `profiles.yml` target / `env_var()` |
| Connection Manager | `sources.yml` + `profiles.yml` target (redacted secrets → `env_var()` placeholders) |

---

## 10. Auditing, Logging & Security

### 10.1 Execution Log

Tracks real-time progress of the migration run, capturing:

- XML parsing errors
- Missing metadata
- System faults

_(Proposed)_ Log format: structured (JSON lines) with severity levels (`INFO`, `WARN`, `ERROR`, `CRITICAL`), timestamps, package/component identifiers, and reason codes. Downloadable from the UI.

### 10.2 Conversion Report

A downloadable post-run summary (`.csv` or `.pdf`) detailing:

- Total component counts
- Successfully generated SQL models
- Itemized breakdown of skipped components with failure reasons

_(Proposed)_ Additional report content: per-package convertibility score, reason-code histogram, list of generated files, dialect used, tool version, and run timestamp.

### 10.3 Credential Redaction

During parsing of Connection Managers, the engine automatically identifies and redacts sensitive information (passwords, connection strings, auth tokens) to prevent leaks in generated documentation.

_(Proposed)_ Implementation guidance:

- Pattern-based and key-based detection (e.g., `Password`, `PWD`, `Token`, `AccountKey`, `SharedAccessSignature`, `Server`/`Data Source` optionally masked).
- Redaction applied at the **parser layer**, so sensitive values never enter downstream models, logs, or reports.
- Encrypted/sensitive DTSX attributes (`ProtectionLevel`) handled gracefully: log that content could not be decrypted, never attempt to bypass.
- Replace redacted values with `env_var('...')` placeholders in generated configs.
- Optional post-generation secret scan before export.

### 10.4 Additional Security Considerations _(Proposed)_

- Uploaded `.dtsx` files processed in an isolated sandbox with size limits and safe XML parsing (disable external entities / DTD to prevent XXE).
- Data retention controls: temporary files purged after the session; no persistent storage without explicit opt-in.
- Role-based access control if deployed as a shared service; audit trail of who converted/exported what.

---

## 11. Non-Functional Requirements _(Proposed)_

| Category | Requirement |
|---|---|
| **Performance** | Parse and convert a typical package (up to ~50 components) in under 10 seconds; support packages with 500+ components without failure. |
| **Scalability** | Batch processing of hundreds of packages via CLI and/or worker queue. |
| **Determinism** | Same input + same configuration must produce byte-identical output (enables diffs and reproducibility). |
| **Reliability** | A failure in one component/package must not abort the entire batch; isolate and report. |
| **Compatibility** | Support SSIS versions 2012 through current (package format versions), project and package deployment models. |
| **Extensibility** | Pluggable component converters and dialect emitters to add new mappings without core changes. |
| **Observability** | Metrics for conversion success rates, latency, and error categories. |
| **Usability** | Full round trip (import → export) achievable without reading documentation. |
| **Portability** | Runs as web app, CLI, and containerized service. |

---

## 12. System Architecture & Processing Pipeline _(Proposed)_

```text
.dtsx / .params / .conmgr
        |
        v
+-------------------+     +---------------------+
|  XML Parser       | --> |  Credential Redactor|
+-------------------+     +---------------------+
        |
        v
+-------------------------------------------+
| Intermediate Representation (IR)          |
| - Control Flow graph                      |
| - Data Flow graph (components, columns)   |
| - Variables, Parameters, Connections      |
+-------------------------------------------+
        |
        v
+---------------------+   +----------------------+
| Component Converters|-->| Expression Translator|
+---------------------+   +----------------------+
        |
        v
+-------------------------------------------+
| SQL Generator (CTE chaining, Jinja)       |
| + Dialect Emitters (Snowflake/DBX/T-SQL)  |
+-------------------------------------------+
        |
        v
+---------------------+   +--------------------+   +---------------------+
| Confidence Grader   |-->| Project Exporter   |-->| Report & Log Writer |
+---------------------+   +--------------------+   +---------------------+
```

**Why an Intermediate Representation (IR)?** A dialect-neutral IR decouples parsing from SQL emission, enabling one parse to serve all three target dialects and making it straightforward to add future targets (BigQuery, Redshift, etc.).

### 12.1 Suggested Data Model (IR) _(Proposed)_

| Entity | Key Attributes |
|---|---|
| Package | id, name, version, protection level, variables, parameters |
| ConnectionManager | id, type, redacted properties |
| Task (Control Flow) | id, type, name, properties, precedence edges |
| DataFlow | id, name, components, paths |
| Component | id, type, name, inputs, outputs, columns (name, type, lineage id), properties |
| Path | source output, target input |
| ConversionResult | component id, grade, reason code, generated snippet |

---

## 13. Success Metrics _(Proposed)_

| Metric | Target (Initial) |
|---|---|
| % of components auto-converted (Exact + Warning) | ≥ 80% |
| % of data flows compiling in `dbt compile` without edits | ≥ 60% |
| Reduction in manual effort per package | ≥ 50% |
| Reviewer time to validate a model | ↓ 40% vs. manual rewrite |
| Credential leaks in output | 0 |
| Silent component drops | 0 (every skip logged) |
| User satisfaction (CSAT) among migration engineers | ≥ 4 / 5 |

---

## 14. Risks & Mitigations _(Proposed)_

| Risk | Impact | Mitigation |
|---|---|---|
| Semantic differences between SSIS row-based execution and SQL set-based logic (e.g., ordering, error handling) | Incorrect results after migration | Flag risky components as Warning; recommend data reconciliation tests |
| SSIS expression language complexity | Incorrect translations | AST-based translator, unit tests per function, fallback to commented placeholders |
| Heavy reliance on Script Components | Low automation rate | Clear Manual guidance, potential future assist for Python model scaffolds |
| Proprietary/encrypted packages | Cannot parse sensitive content | Detect `ProtectionLevel`, prompt user for decrypted export |
| Layering heuristics misclassify models | Rework | Configurable rules + UI overrides |
| Dialect nuances (e.g., type mapping, collation, case sensitivity) | Runtime errors | Dialect test suites; validate against sample warehouses |
| Over-trust in generated output | Production defects | Prominent review workflow; recommend parity testing before cutover |

---

## 15. Phased Roadmap _(Proposed)_

| Phase | Scope |
|---|---|
| **MVP (P0)** | `.dtsx` import; dashboard metrics; Data Flow to CTE model conversion for core components (sources, Derived Column, Lookup, Conditional Split, Union All, Merge Join, Sort, Aggregate); Snowflake output; confidence grading; export with folder structure; execution log. |
| **P1** | Databricks and T-SQL dialects; `schema.yml` with tests; credential redaction; conversion report (CSV/PDF); SQL editor with copy; visual flow snapshots. |
| **P2** | Expression translator coverage expansion; SCD and Pivot support; environment variable/CI mapping; batch mode; diff view. |
| **P3** | Orchestration hints (generate ADF/Airflow DAG skeletons for Manual items); parity/reconciliation test generation; additional dialects (BigQuery, Redshift); catalog (SSISDB) integration. |

---

## 16. Open Questions _(Proposed)_

1. Should the tool generate **orchestrator skeletons** (Airflow/ADF) for Manual items, or only document them?
2. What is the expected treatment of **incremental loads** implemented via variables/watermarks?
3. Is **package-to-package dependency** (Execute Package Task) to be modeled as dbt `ref()` chains or documented only?
4. Which **SSIS versions** and deployment models must be supported at launch?
5. Should the tool deliver as **SaaS, on-prem container, or CLI**, given the sensitivity of source packages?
6. How should **SQL-in-variable / dynamic SQL** be handled beyond flagging it?
7. Are **visual snapshots** generated by rendering the DTSX layout ourselves or captured from an existing viewer?
8. What **SLA** is expected for very large packages?

---

## 17. Appendix

### 17.1 Glossary

| Term | Definition |
|---|---|
| **SSIS** | SQL Server Integration Services, Microsoft's ETL platform. |
| **DTSX** | XML file format for SSIS packages. |
| **Control Flow** | Orchestration layer of an SSIS package (tasks, precedence constraints). |
| **Data Flow** | Transformation pipeline inside a Data Flow Task. |
| **CTE** | Common Table Expression (`WITH ... AS`). |
| **dbt** | Data build tool for SQL-based transformations, testing, and documentation. |
| **Medallion Architecture** | Layered data design (bronze/silver/gold), analogous to staging / intermediate / marts. |
| **Precedence Constraint** | Rule that defines execution order/conditions between control flow tasks. |
| **Connection Manager** | SSIS object storing connection details to a data source. |

### 17.2 Change Log

| Version | Notes |
|---|---|
| v2.0 | Enriched draft covering conversion architecture, UI, grading, export, and auditing. |
| v3.0 | Added goals/non-goals, personas, component mapping tables, dialect and expression translation, wireframe, NFRs, architecture/IR, metrics, risks, roadmap, and open questions. |
