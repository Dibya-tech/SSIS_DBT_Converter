"""Streamlit UI for the SSIS-to-dbt Migration Engine.

Dark, minimal, dual-pane migration workspace (PRD section 7).

Run:  streamlit run ssis2dbt/ui/app.py
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path as _Path

import streamlit as st
import streamlit.components.v1 as components

# Ensure the project root is on sys.path so absolute imports work when
# Streamlit runs this file as a standalone script.
_root = str(_Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

from ssis2dbt import dialects  # noqa: F401
from ssis2dbt.dialects import impls  # noqa: F401
from ssis2dbt.engine import ConversionRun, convert_package
from ssis2dbt.export.project import build_project_files
from ssis2dbt.ir.model import Grade
from ssis2dbt.parser import dtsx
from ssis2dbt.ui.cf_diagram import build_cf_graph_data, render_cf_html
from ssis2dbt.ui.flow_diagram import render_html

# ---------------------------------------------------------------------------
st.set_page_config(page_title="SSIS → dbt", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
      .stApp { background: #0d1117; color: #c9d1d9; }
      section[data-testid="stSidebar"] { background: #010409; }
      h1, h2, h3 { color: #e6edf3 !important; font-weight: 600; }
      div[data-testid="stMetricValue"] { color: #e6edf3; }
      div[data-testid="stMetricLabel"] { color: #8b949e; }
      .stCode, pre { background: #161b22 !important; }
      .pill {
        display: inline-block;
        padding: 3px 10px; border-radius: 12px; font-size: .78rem;
        background: #161b22; border: 1px solid #30363d; margin-right: 6px;
      }
      .grade-exact   { color: #3fb950; }
      .grade-warning { color: #d29922; }
      .grade-manual  { color: #f85149; }
      .stButton>button              { background: #238636; color: #fff; border: 0; border-radius: 6px; }
      .stDownloadButton>button      { background: #1f6feb; color: #fff; border: 0; border-radius: 6px; }
      .stFileUploader               { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
      .stSelectbox > div > div      { background: #161b22 !important; border-color: #30363d !important; }
      .stTabs [data-baseweb="tab"] { background: #161b22; color: #8b949e; border-radius: 6px 6px 0 0; }
      .stTabs [aria-selected="true"] { color: #e6edf3 !important; border-bottom: 2px solid #238636; }
      hr { border-color: #21262d; }
    </style>
    """,
    unsafe_allow_html=True,
)

_ICON = {Grade.EXACT: "✅", Grade.WARNING: "⚠️", Grade.MANUAL: "⛔"}


def _zip_bytes(run: ConversionRun) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        root = run.package.name
        for rel, content in build_project_files(run).items():
            z.writestr(f"{root}/{rel}", content)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Header + controls
# ---------------------------------------------------------------------------
st.markdown("## SSIS → dbt Migration Engine")

dialect = "snowflake"

col_file, col_btn = st.columns([5, 1])
with col_file:
    uploaded = st.file_uploader(
        "Import .dtsx", type=["dtsx"], label_visibility="collapsed")

if uploaded is None:
    st.markdown(
        "<div style='text-align:center;color:#8b949e;padding:60px 0;font-size:1rem;'>"
        "⬆ Import a <code>.dtsx</code> package to begin"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Parse + convert
# ---------------------------------------------------------------------------
xml = uploaded.getvalue().decode("utf-8", errors="replace")
try:
    pkg = dtsx.parse_string(xml, name=_Path(uploaded.name).stem)
except Exception as exc:  # noqa: BLE001
    st.error(f"Failed to parse package: {exc}")
    st.stop()

run = convert_package(pkg, dialect=dialect)

# ---------------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------------
m = run.metrics
counts = run.grade_counts()
c = st.columns(7)
c[0].metric("Data flows",       m.total_data_flows)
c[1].metric("Components",       m.total_components)
c[2].metric("Control tasks",    m.total_tasks)
c[3].metric("Connections",      m.total_connections)
c[4].metric("Variables",        m.total_variables)
c[5].metric("Parameters",       m.total_parameters)
c[6].metric("Score (Exact %)",  f"{run.package_score()}%")

st.markdown(
    f"<div style='margin:6px 0 12px'>"
    f"<span class='pill grade-exact'>✅ {counts['Exact']} Exact</span>"
    f"<span class='pill grade-warning'>⚠️ {counts['Warning']} Warning</span>"
    f"<span class='pill grade-manual'>⛔ {counts['Manual']} Manual</span>"
    f"</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dual-pane
# ---------------------------------------------------------------------------
left_col, right_col = st.columns([5, 7], gap="medium")

result_by_df: dict[str, list] = {
    m.data_flow_id: m.results for m in run.models
}

with left_col:
    st.markdown("#### SSIS package")
    st.caption(f"📄 {uploaded.name}  ·  dialect: **{dialect}**")

    # Control flow diagram (task execution order + containers)
    with st.expander("🔄 Control Flow", expanded=True):
        cf_gd  = build_cf_graph_data(pkg)
        cf_h   = min(max(int(cf_gd["height"]) + 40, 180), 800)
        components.html(render_cf_html(pkg), height=cf_h, scrolling=True)

    st.markdown("<hr style='border-color:#21262d;margin:8px 0'/>",
                unsafe_allow_html=True)

    # One flow-diagram tab per data flow
    df_list = pkg.data_flows
    if df_list:
        df_tabs = st.tabs([df.name for df in df_list])
        for tab, df in zip(df_tabs, df_list):
            with tab:
                diagram_html = render_html(df, result_by_df.get(df.id, []))
                # derive canvas size from graph data
                from ssis2dbt.ui.flow_diagram import build_graph_data
                gd = build_graph_data(df, result_by_df.get(df.id, []))
                h = min(max(gd["height"] + 60, 220), 700)
                components.html(diagram_html, height=h, scrolling=True)
    else:
        st.info("No data flows found in this package.")

    # Control-flow tasks (manual) listed below the diagram
    manual = run.manual_tasks()
    if manual:
        st.markdown("**Control-flow tasks (external orchestration)**")
        for tname, code in manual:
            st.markdown(
                f"<span style='color:#f85149'>⛔</span> **{tname}** "
                f"<span style='color:#8b949e;font-size:.8rem'>· {code}</span>",
                unsafe_allow_html=True,
            )

with right_col:
    st.markdown("#### dbt project (generated)")
    if not run.models:
        st.warning("No data flows to convert in this package.")
    else:
        model_tabs = st.tabs([m.model_name for m in run.models])
        for tab, model in zip(model_tabs, run.models):
            with tab:
                grade_color = {
                    "Exact": "#3fb950", "Warning": "#d29922", "Manual": "#f85149"
                }.get(model.grade.value, "#8b949e")
                st.markdown(
                    f"<div style='margin-bottom:8px;font-size:.82rem;color:#8b949e'>"
                    f"layer: <b style='color:#c9d1d9'>{model.layer}</b> &nbsp;·&nbsp; "
                    f"grade: <b style='color:{grade_color}'>{model.grade.value}</b>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.code(model.sql, language="sql")

# ---------------------------------------------------------------------------
# Execution log + export
# ---------------------------------------------------------------------------
st.markdown("<hr/>", unsafe_allow_html=True)
log_col, export_col = st.columns([3, 1], gap="medium")

with log_col:
    with st.expander("Execution log", expanded=False):
        sev_color = {
            "CRITICAL": "#f85149", "ERROR": "#f85149",
            "WARN": "#d29922", "INFO": "#8b949e",
        }
        for e in run.log:
            color = sev_color.get(e.severity, "#8b949e")
            st.markdown(
                f"<div style='font-size:.85rem;margin-bottom:4px'>"
                f"<span style='color:{color};font-weight:600'>[{e.severity}]</span> "
                f"<span style='color:#c9d1d9'>{e.component}</span>"
                f"<span style='color:#8b949e'> — {e.message}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

with export_col:
    st.download_button(
        "⬇ dbt project (.zip)",
        data=_zip_bytes(run),
        file_name=f"{pkg.name}_dbt.zip",
        mime="application/zip",
        use_container_width=True,
    )
    st.download_button(
        "⬇ Conversion report (.csv)",
        data=build_project_files(run)["conversion_report.csv"],
        file_name="conversion_report.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "⬇ Execution log (.jsonl)",
        data=build_project_files(run)["execution_log.jsonl"],
        file_name="execution_log.jsonl",
        mime="application/jsonl",
        use_container_width=True,
    )
