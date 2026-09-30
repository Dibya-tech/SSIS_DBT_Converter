# Graph Report - DBT_SSIS_COnverter  (2026-09-30)

## Corpus Check
- 34 files · ~26,195 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .dtsx 10, (none) 2)

## Summary
- 347 nodes · 794 edges · 28 communities (21 shown, 7 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 112 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `63f6937e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SSIS to DBT converter
- app.py
- dtsx.py
- components.py
- CLAUDE.md
- Dialect
- engine.py
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
- 6. Target Dialect Support
- SSIS to dbt Migration Engine
- cf_diagram.py
- Session 2026-09-30 — Initial build + column & UI improvements

## God Nodes (most connected - your core abstractions)
1. `Component` - 36 edges
2. `Grade` - 33 edges
3. `Ctx` - 27 edges
4. `ConversionRun` - 24 edges
5. `_cte_desc()` - 23 edges
6. `CTEResult` - 23 edges
7. `Dialect` - 23 edges
8. `converter()` - 22 edges
9. `sanitize_identifier()` - 21 edges
10. `SSIS to DBT converter` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Graphify community map` --references--> `translate()`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/expression.py
- `Graphify community map` --references--> `GeneratedModel`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/generator.py
- `Graphify community map` --references--> `generate_model()`  [INFERRED]
  CHANGES.md → ssis2dbt/convert/generator.py
- `Graphify community map` --references--> `Dialect`  [INFERRED]
  CHANGES.md → ssis2dbt/dialects/base.py
- `New files` --references--> `Dialect`  [INFERRED]
  CHANGES.md → ssis2dbt/dialects/base.py

## Import Cycles
- None detected.

## Communities (28 total, 7 thin omitted)

### Community 0 - "SSIS to DBT converter"
Cohesion: 0.07
Nodes (28): 1. Heavy Control Flow — What This Means for the Tool, 2. Your Architecture — What This Changes, 3. One Folder Per DTSX, One Model Per Flow, 4. Web UI — Let's Think About What It Needs, Assistant, Assistant, Assistant, Assistant (+20 more)

### Community 1 - "app.py"
Cohesion: 0.11
Nodes (24): csv, io, pathlib, ConversionRun, build_project_files(), _dbt_project_yml(), _profiles_example(), Export a ConversionRun into a deployable dbt project (PRD section 9). (+16 more)

### Community 2 - "dtsx.py"
Cohesion: 0.15
Nodes (31): FsPath, Column, ConnectionManager, Package, Task, Variable, _attr(), _classify() (+23 more)

### Community 3 - "components.py"
Cohesion: 0.18
Nodes (44): Graphify community map, _aggregate(), _col_alias(), _conditional_split(), convert_component(), converter(), _cte_desc(), CTEResult (+36 more)

### Community 5 - "Dialect"
Cohesion: 0.07
Nodes (19): argparse, ArgumentParser, build_parser(), _cmd_convert(), _cmd_inspect(), main(), Command-line interface for the SSIS-to-dbt Migration Engine. Examples: python…, available() (+11 more)

### Community 6 - "engine.py"
Cohesion: 0.09
Nodes (35): New files, dataclasses, Enum, ComponentResult, _default_model_name(), generate_model(), GeneratedModel, Generate a dbt model (chained CTEs) from a Data Flow (PRD section 4). Design… (+27 more)

### Community 7 - "test_engine.py"
Cohesion: 0.09
Nodes (28): parametrize, pytest, re, _col(), ExprResult, Translate the SSIS expression language into SQL (PRD section 6.2). SSIS…, Normalize a [Column Name] or bare column into a SQL identifier., Convert cond ? a : b into case when cond then a else b end. Handles a single… (+20 more)

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

### Community 24 - "6. Target Dialect Support"
Cohesion: 0.50
Nodes (3): 6.1 Dialect Translation Examples _(Proposed)_, 6.2 SSIS Expression Language Translation _(Proposed)_, 6. Target Dialect Support

### Community 25 - "SSIS to dbt Migration Engine"
Cohesion: 0.25
Nodes (7): Architecture, Quick start, SSIS to dbt Migration Engine, Supported dialects, Supported SSIS components, Tests, What it does

### Community 26 - "cf_diagram.py"
Cohesion: 0.20
Nodes (9): collections, json, build_cf_graph_data(), Render a Package's Control Flow as an interactive HTML/SVG diagram. Mirrors the…, Return self-contained HTML string for the control flow diagram., Return id -> topo depth for the given set of task ids., Build a plain-dict graph description for the control flow diagram., render_cf_html() (+1 more)

### Community 27 - "Session 2026-09-30 — Initial build + column & UI improvements"
Cohesion: 0.50
Nodes (3): Change Log, Key design decisions tracked in graphify, Session 2026-09-30 — Initial build + column & UI improvements

## Knowledge Gaps
- **71 isolated node(s):** `graphify`, `Quick start`, `What it does`, `Supported dialects`, `Supported SSIS components` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 167 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Dialect` connect `Dialect` to `6. Target Dialect Support`, `components.py`, `engine.py`, `test_engine.py`?**
  _High betweenness centrality (0.292) - this node is a cross-community bridge._
- **Why does `Product Requirements Document (PRD): SSIS to dbt Migration Engine` connect `Product Requirements Document (PRD): SSIS to dbt Migration Engine` to `9. Export Architecture & dbt Project Generation`, `10. Auditing, Logging & Security`, `4. Core Conversion Architecture`, `7. User Interface & Experience (UX/UI)`, `8. Conversion Confidence & Exception Handling`, `2. Problem Statement, Goals & Non-Goals _(Proposed)_`, `5. SSIS Component to SQL Mapping Reference _(Proposed)_`, `17. Appendix`, `3. Personas & Key User Journeys _(Proposed)_`, `6. Target Dialect Support`?**
  _High betweenness centrality (0.230) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Component` (e.g. with `Graphify community map` and `New files`) actually correct?**
  _`Component` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `Grade` (e.g. with `Graphify community map` and `New files`) actually correct?**
  _`Grade` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Ctx` (e.g. with `Graphify community map` and `Dialect`) actually correct?**
  _`Ctx` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ConversionRun` (e.g. with `Graphify community map` and `New files`) actually correct?**
  _`ConversionRun` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `graphify`, `Quick start`, `What it does` to the rest of the system?**
  _71 weakly-connected nodes found - possible documentation gaps or missing edges._