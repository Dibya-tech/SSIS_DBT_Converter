# Graph Report - DBT_SSIS_COnverter  (2026-09-30)

## Corpus Check
- 29 files · ~15,349 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: .dtsx 9, (none) 2)

## Summary
- 317 nodes · 706 edges · 25 communities (18 shown, 7 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 81 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d5e0f574`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SSIS to DBT converter
- app.py
- dtsx.py
- components.py
- CLAUDE.md
- Dialect
- Grade
- test_engine.py
- Product Requirements Document (PRD): SSIS to dbt Migration Engine
- 9. Export Architecture & dbt Project Generation
- 10. Auditing, Logging & Security
- 4. Core Conversion Architecture
- 7. User Interface & Experience (UX/UI)
- 8. Conversion Confidence & Exception Handling
- 2. Problem Statement, Goals & Non-Goals _(Proposed)_
- 5. SSIS Component to SQL Mapping Reference _(Proposed)_
- 17. Appendix
- 3. Personas & Key User Journeys _(Proposed)_
- SSIS → dbt Migration Engine

## God Nodes (most connected - your core abstractions)
1. `Component` - 34 edges
2. `Grade` - 31 edges
3. `Ctx` - 26 edges
4. `_cte_desc()` - 23 edges
5. `CTEResult` - 22 edges
6. `ConversionRun` - 22 edges
7. `converter()` - 21 edges
8. `Dialect` - 21 edges
9. `sanitize_identifier()` - 20 edges
10. `SSIS to DBT converter` - 20 edges

## Surprising Connections (you probably didn't know these)
- `test_convert_produces_model_and_grades()` --calls--> `convert_file()`  [EXTRACTED]
  tests/test_engine.py → ssis2dbt/engine.py
- `test_redact_properties()` --calls--> `redact_properties()`  [EXTRACTED]
  tests/test_engine.py → ssis2dbt/parser/redact.py
- `test_dialect_differences()` --calls--> `get_dialect()`  [EXTRACTED]
  tests/test_engine.py → ssis2dbt/dialects/base.py
- `test_no_secret_in_any_generated_file()` --calls--> `convert_file()`  [EXTRACTED]
  tests/test_engine.py → ssis2dbt/engine.py
- `test_sanitize_identifier()` --calls--> `sanitize_identifier()`  [EXTRACTED]
  tests/test_engine.py → ssis2dbt/ir/model.py

## Import Cycles
- None detected.

## Communities (25 total, 7 thin omitted)

### Community 0 - "SSIS to DBT converter"
Cohesion: 0.07
Nodes (28): 1. Heavy Control Flow — What This Means for the Tool, 2. Your Architecture — What This Changes, 3. One Folder Per DTSX, One Model Per Flow, 4. Web UI — Let's Think About What It Needs, Assistant, Assistant, Assistant, Assistant (+20 more)

### Community 1 - "app.py"
Cohesion: 0.08
Nodes (33): argparse, ArgumentParser, csv, io, pathlib, build_parser(), _cmd_convert(), _cmd_inspect() (+25 more)

### Community 2 - "dtsx.py"
Cohesion: 0.13
Nodes (34): re, Column, ConnectionManager, Package, Path, Dialect-neutral Intermediate Representation (IR) for a parsed SSIS package. The…, An edge in the data flow graph: source component output -> target input., Task (+26 more)

### Community 3 - "components.py"
Cohesion: 0.21
Nodes (38): _aggregate(), _col_alias(), _conditional_split(), convert_component(), converter(), _cte_desc(), CTEResult, Ctx (+30 more)

### Community 5 - "Dialect"
Cohesion: 0.08
Nodes (10): Dialect, Dialect emitters translate dialect-neutral concerns into target SQL. Adding a…, register(), Databricks, Concrete dialect implementations (PRD section 6.1)., Snowflake, TSQL, 6.1 Dialect Translation Examples _(Proposed)_ (+2 more)

### Community 6 - "Grade"
Cohesion: 0.08
Nodes (36): collections, dataclasses, Enum, json, ComponentResult, _default_model_name(), generate_model(), GeneratedModel (+28 more)

### Community 7 - "test_engine.py"
Cohesion: 0.13
Nodes (22): FsPath, parametrize, pytest, _col(), ExprResult, Translate the SSIS expression language into SQL (PRD section 6.2). SSIS…, Normalize a [Column Name] or bare column into a SQL identifier., Convert cond ? a : b into case when cond then a else b end. Handles a single… (+14 more)

### Community 8 - "Product Requirements Document (PRD): SSIS to dbt Migration Engine"
Cohesion: 0.18
Nodes (10): 11. Non-Functional Requirements _(Proposed)_, 12.1 Suggested Data Model (IR) _(Proposed)_, 12. System Architecture & Processing Pipeline _(Proposed)_, 13. Success Metrics _(Proposed)_, 14. Risks & Mitigations _(Proposed)_, 15. Phased Roadmap _(Proposed)_, 16. Open Questions _(Proposed)_, 1. Executive Summary (+2 more)

### Community 9 - "9. Export Architecture & dbt Project Generation"
Cohesion: 0.33
Nodes (6): 9.1 Directory Structure, 9.2 Layer Routing Rules _(Proposed)_, 9.3 Automated Testing & Documentation, 9.4 Sources & Materializations _(Proposed)_, 9.5 Environment Variables & Configuration, 9. Export Architecture & dbt Project Generation

### Community 10 - "10. Auditing, Logging & Security"
Cohesion: 0.40
Nodes (5): 10.1 Execution Log, 10.2 Conversion Report, 10.3 Credential Redaction, 10.4 Additional Security Considerations _(Proposed)_, 10. Auditing, Logging & Security

### Community 11 - "4. Core Conversion Architecture"
Cohesion: 0.40
Nodes (5): 4.1 Design Principles, 4.2 Example: Generated Model Shape _(Proposed)_, 4.3 Handling Branching in Detail _(Proposed)_, 4.4 Model Granularity & Naming Rules _(Proposed)_, 4. Core Conversion Architecture

### Community 12 - "7. User Interface & Experience (UX/UI)"
Cohesion: 0.40
Nodes (5): 7.1 Dashboard Metrics, 7.2 Workspace Capabilities, 7.3 UX Enhancements _(Proposed)_, 7.4 Wireframe (Conceptual) _(Proposed)_, 7. User Interface & Experience (UX/UI)

### Community 13 - "8. Conversion Confidence & Exception Handling"
Cohesion: 0.40
Nodes (5): 8.1 Manual Component Handling, 8.2 Warning Handling _(Proposed)_, 8.3 Reason Code Catalog _(Proposed)_, 8.4 Confidence Rollup _(Proposed)_, 8. Conversion Confidence & Exception Handling

### Community 14 - "2. Problem Statement, Goals & Non-Goals _(Proposed)_"
Cohesion: 0.50
Nodes (4): 2.1 Problem Statement, 2.2 Goals, 2.3 Non-Goals, 2. Problem Statement, Goals & Non-Goals _(Proposed)_

### Community 15 - "5. SSIS Component to SQL Mapping Reference _(Proposed)_"
Cohesion: 0.50
Nodes (4): 5.1 Sources & Destinations, 5.2 Transformations, 5.3 Control Flow Tasks, 5. SSIS Component to SQL Mapping Reference _(Proposed)_

### Community 16 - "17. Appendix"
Cohesion: 0.67
Nodes (3): 17.1 Glossary, 17.2 Change Log, 17. Appendix

### Community 17 - "3. Personas & Key User Journeys _(Proposed)_"
Cohesion: 0.67
Nodes (3): 3.1 Personas, 3.2 Primary Journey, 3. Personas & Key User Journeys _(Proposed)_

### Community 25 - "SSIS → dbt Migration Engine"
Cohesion: 0.25
Nodes (7): Architecture, Quick start, SSIS → dbt Migration Engine, Supported dialects, Supported SSIS components, Tests, What it does

## Knowledge Gaps
- **71 isolated node(s):** `graphify`, `Quick start`, `What it does`, `Supported dialects`, `Supported SSIS components` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 155 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Dialect` connect `Dialect` to `components.py`, `Grade`, `test_engine.py`?**
  _High betweenness centrality (0.303) - this node is a cross-community bridge._
- **Why does `Product Requirements Document (PRD): SSIS to dbt Migration Engine` connect `Product Requirements Document (PRD): SSIS to dbt Migration Engine` to `Dialect`, `9. Export Architecture & dbt Project Generation`, `10. Auditing, Logging & Security`, `4. Core Conversion Architecture`, `7. User Interface & Experience (UX/UI)`, `8. Conversion Confidence & Exception Handling`, `2. Problem Statement, Goals & Non-Goals _(Proposed)_`, `5. SSIS Component to SQL Mapping Reference _(Proposed)_`, `17. Appendix`, `3. Personas & Key User Journeys _(Proposed)_`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Component` (e.g. with `_aggregate()` and `_conditional_split()`) actually correct?**
  _`Component` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Grade` (e.g. with `convert_component()` and `CTEResult`) actually correct?**
  _`Grade` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Ctx` (e.g. with `Dialect` and `Component`) actually correct?**
  _`Ctx` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `graphify`, `Quick start`, `What it does` to the rest of the system?**
  _71 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SSIS to DBT converter` be split into smaller, more focused modules?**
  _Cohesion score 0.06896551724137931 - nodes in this community are weakly interconnected._