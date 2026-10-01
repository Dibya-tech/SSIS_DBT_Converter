# Graph Report - DBT_SSIS_COnverter  (2026-10-01)

## Corpus Check
- 34 files · ~19,469 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .dtsx 10, (none) 2, .zip 1)

## Summary
- 367 nodes · 829 edges · 29 communities (21 shown, 8 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 114 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `759bc3d4`
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
- cf_diagram.py
- New files
- DataFlow

## God Nodes (most connected - your core abstractions)
1. `Component` - 36 edges
2. `Grade` - 33 edges
3. `Ctx` - 27 edges
4. `ConversionRun` - 24 edges
5. `_cte_desc()` - 23 edges
6. `CTEResult` - 23 edges
7. `Dialect` - 23 edges
8. `converter()` - 22 edges
9. `build_project_files()` - 22 edges
10. `sanitize_identifier()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Graphify community map` --references--> `CTEResult`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/components.py
- `Graphify community map` --references--> `Ctx`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/components.py
- `Graphify community map` --references--> `converter()`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/components.py
- `Graphify community map` --references--> `convert_component()`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/components.py
- `Graphify community map` --references--> `translate()`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/expression.py

## Import Cycles
- None detected.

## Communities (29 total, 8 thin omitted)

### Community 0 - "SSIS to DBT converter"
Cohesion: 0.07
Nodes (28): 1. Heavy Control Flow — What This Means for the Tool, 2. Your Architecture — What This Changes, 3. One Folder Per DTSX, One Model Per Flow, 4. Web UI — Let's Think About What It Needs, Assistant, Assistant, Assistant, Assistant (+20 more)

### Community 1 - "app.py"
Cohesion: 0.07
Nodes (27): build_parser(), _cmd_convert(), _cmd_inspect(), main(), route_layer(), available(), _build_cf_warnings(), ConversionRun (+19 more)

### Community 2 - "dtsx.py"
Cohesion: 0.13
Nodes (24): Column, ConnectionManager, Package, Task, Variable, _attr(), _classify(), _parse_connections() (+16 more)

### Community 3 - "components.py"
Cohesion: 0.20
Nodes (31): _aggregate(), _col_alias(), _conditional_split(), convert_component(), converter(), _cte_desc(), CTEResult, Ctx (+23 more)

### Community 5 - "Dialect"
Cohesion: 0.08
Nodes (8): Dialect, register(), Databricks, Snowflake, TSQL, 6.1 Dialect Translation Examples _(Proposed)_, 6.2 SSIS Expression Language Translation _(Proposed)_, 6. Target Dialect Support

### Community 6 - "Grade"
Cohesion: 0.13
Nodes (13): Graphify community map, ComponentResult, _default_model_name(), generate_model(), GeneratedModel, _ref_lookup(), _source_ref(), _topo_order() (+5 more)

### Community 7 - "test_engine.py"
Cohesion: 0.12
Nodes (14): _col(), ExprResult, translate(), _cast_repl(), _translate_ternary(), get_dialect(), is_sensitive_key(), redact_properties() (+6 more)

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
Cohesion: 0.14
Nodes (13): Architecture, Dialect, Export (bottom), Knowledge graph, Left pane — SSIS package view, Quick start, Right pane — generated dbt project, Security (+5 more)

### Community 26 - "cf_diagram.py"
Cohesion: 0.18
Nodes (6): build_cf_graph_data(), render_cf_html(), render_cf_svg(), _topo(), _trunc(), _xe()

### Community 27 - "New files"
Cohesion: 0.29
Nodes (5): Change Log, Key design decisions tracked in graphify, New files, Session 2026-09-30 — Initial build + column & UI improvements, PackageMetrics

### Community 28 - "DataFlow"
Cohesion: 0.21
Nodes (8): DataFlow, build_graph_data(), _category(), render_html(), render_svg(), _topo_levels(), _trunc(), _xe()

## Knowledge Gaps
- **76 isolated node(s):** `graphify`, `Quick start`, `What it does`, `Left pane — SSIS package view`, `Right pane — generated dbt project` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 178 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Dialect` connect `Dialect` to `components.py`, `New files`, `Grade`, `test_engine.py`?**
  _High betweenness centrality (0.274) - this node is a cross-community bridge._
- **Why does `Product Requirements Document (PRD): SSIS to dbt Migration Engine` connect `Product Requirements Document (PRD): SSIS to dbt Migration Engine` to `Dialect`, `9. Export Architecture & dbt Project Generation`, `10. Auditing, Logging & Security`, `4. Core Conversion Architecture`, `7. User Interface & Experience (UX/UI)`, `8. Conversion Confidence & Exception Handling`, `2. Problem Statement, Goals & Non-Goals _(Proposed)_`, `5. SSIS Component to SQL Mapping Reference _(Proposed)_`, `17. Appendix`, `3. Personas & Key User Journeys _(Proposed)_`?**
  _High betweenness centrality (0.215) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Component` (e.g. with `Graphify community map` and `New files`) actually correct?**
  _`Component` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `Grade` (e.g. with `Graphify community map` and `New files`) actually correct?**
  _`Grade` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Ctx` (e.g. with `Graphify community map` and `Dialect`) actually correct?**
  _`Ctx` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ConversionRun` (e.g. with `Graphify community map` and `New files`) actually correct?**
  _`ConversionRun` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `graphify`, `Quick start`, `What it does` to the rest of the system?**
  _76 weakly-connected nodes found - possible documentation gaps or missing edges._