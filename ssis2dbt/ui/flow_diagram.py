"""Render a DataFlow as an interactive HTML/JS node graph.

Produces a self-contained HTML snippet (no external dependencies) that can be
embedded in Streamlit via st.components.v1.html().

Visual design matches the reference screenshot:
  - Dark background (#0d1117)
  - Blue header band per node showing component category
  - Darker body with component name and grade icon
  - Orange outline for Warnings, red for Manual
  - SVG arrows with mid-path edge labels (output port names)
  - Topological layout: column = depth, row = branch index
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Optional

from ..ir.model import DataFlow, Grade

# colour palette
_CAT_HEADER = {
    "source":      "#1158a6",
    "transform":   "#a65c00",
    "destination": "#6a0000",
    "unknown":     "#333",
}
_GRADE_BORDER = {
    Grade.EXACT:   "#21262d",
    Grade.WARNING: "#d29922",
    Grade.MANUAL:  "#f85149",
}
_SOURCE_TYPES = {"OLEDBSource", "ADONETSource", "FlatFileSource", "ExcelSource"}
_DEST_TYPES   = {"OLEDBDestination", "FlatFileDestination"}
_GRADE_ICON   = {Grade.EXACT: "✅", Grade.WARNING: "⚠️", Grade.MANUAL: "⛔"}


def _category(comp_type: str) -> str:
    if comp_type in _SOURCE_TYPES:
        return "source"
    if comp_type in _DEST_TYPES:
        return "destination"
    return "transform"


def _topo_levels(df: DataFlow) -> dict[str, int]:
    """Return component_id -> depth (column in layout)."""
    indeg = {c.id: 0 for c in df.components}
    adj: dict[str, list[str]] = defaultdict(list)
    for p in df.paths:
        if p.source_id in indeg and p.target_id in indeg:
            adj[p.source_id].append(p.target_id)
            indeg[p.target_id] += 1
    queue = [cid for cid, d in indeg.items() if d == 0]
    level: dict[str, int] = {}
    while queue:
        cid = queue.pop(0)
        level[cid] = level.get(cid, 0)
        for nxt in adj[cid]:
            level[nxt] = max(level.get(nxt, 0), level[cid] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    for c in df.components:
        if c.id not in level:
            level[c.id] = 0
    return level


def build_graph_data(
    df: DataFlow,
    results: Optional[list] = None,  # list[ComponentResult]
) -> dict:
    """Build a plain-dict graph description suitable for JSON serialisation."""
    grade_by_id = {}
    if results:
        grade_by_id = {r.component_id: r.grade for r in results}

    levels = _topo_levels(df)
    # bucket by level
    by_level: dict[int, list[str]] = defaultdict(list)
    for cid, lvl in levels.items():
        by_level[lvl].append(cid)

    # Vertical layout: depth → Y, branches spread → X
    NODE_W, NODE_H = 200, 68
    COL_GAP = 220   # horizontal gap between sibling branches
    ROW_GAP = 110   # vertical gap between depth levels
    MARGIN  = 32

    positions: dict[str, dict] = {}
    for lvl, ids in sorted(by_level.items()):
        y = MARGIN + lvl * ROW_GAP
        count = len(ids)
        total_w = count * NODE_W + (count - 1) * (COL_GAP - NODE_W)
        start_x = MARGIN
        for col, cid in enumerate(ids):
            x = start_x + col * COL_GAP
            positions[cid] = {"x": x, "y": y}

    # canvas size
    max_x = max((p["x"] for p in positions.values()), default=0) + NODE_W + MARGIN
    max_y = max((p["y"] for p in positions.values()), default=0) + NODE_H + MARGIN

    nodes = []
    for c in df.components:
        pos = positions.get(c.id, {"x": 0, "y": 0})
        grade = grade_by_id.get(c.id, Grade.EXACT)
        cat = _category(c.component_type)
        nodes.append({
            "id": c.id,
            "name": c.name,
            "type": c.component_type,
            "category": cat,
            "grade": grade.value,
            "icon": _GRADE_ICON[grade],
            "headerColor": _CAT_HEADER[cat],
            "borderColor": _GRADE_BORDER[grade],
            "x": pos["x"],
            "y": pos["y"],
            "w": NODE_W,
            "h": NODE_H,
        })

    edges = []
    for p in df.paths:
        if p.source_id in positions and p.target_id in positions:
            edges.append({
                "from": p.source_id,
                "to": p.target_id,
                "label": p.source_output or "",
            })

    return {"nodes": nodes, "edges": edges, "width": max_x, "height": max_y}


_HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; overflow: auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  svg { display: block; }
  .node-header { font-size: 9px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; fill: #ffffffcc; }
  .node-name   { font-size: 11px; font-weight: 500; fill: #c9d1d9; }
  .node-type   { font-size: 9px; fill: #8b949e; }
  .edge-label  { font-size: 9px; fill: #8b949e; }
  .grade-icon  { font-size: 11px; }
</style>
</head>
<body>
<svg id="canvas" xmlns="http://www.w3.org/2000/svg">
<defs>
  <marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
    <path d="M0,0 L0,6 L8,3 z" fill="#444c56"/>
  </marker>
  <filter id="glow">
    <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
    <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<script type="text/javascript">
const G = __GRAPH_JSON__;

window.onload = function() {
  const svg = document.getElementById('canvas');
  const PAD = 20;
  svg.setAttribute('width',  G.width  + PAD*2);
  svg.setAttribute('height', G.height + PAD*2);
  svg.setAttribute('viewBox', `0 0 ${G.width + PAD*2} ${G.height + PAD*2}`);

  const byId = {};
  G.nodes.forEach(n => byId[n.id] = n);

  // Edges first (under nodes)
  const edgeGroup = svgEl('g');
  G.edges.forEach(e => {
    const s = byId[e.from], t = byId[e.to];
    if (!s || !t) return;
    // exit bottom-center of source, enter top-center of target
    const x1 = PAD + s.x + s.w/2, y1 = PAD + s.y + s.h;
    const x2 = PAD + t.x + t.w/2, y2 = PAD + t.y;
    const mx = (x1+x2)/2,          my = (y1+y2)/2;
    const cy1 = y1 + (y2-y1)*0.45, cy2 = y2 - (y2-y1)*0.45;

    const path = svgEl('path');
    path.setAttribute('d', `M${x1},${y1} C${x1},${cy1} ${x2},${cy2} ${x2},${y2}`);
    path.setAttribute('stroke', '#444c56');
    path.setAttribute('stroke-width', '1.5');
    path.setAttribute('fill', 'none');
    path.setAttribute('marker-end', 'url(#arr)');
    edgeGroup.appendChild(path);

    if (e.label) {
      const txt = svgEl('text');
      txt.setAttribute('x', mx);
      txt.setAttribute('y', my - 4);
      txt.setAttribute('text-anchor', 'middle');
      txt.setAttribute('class', 'edge-label');
      txt.textContent = e.label;
      edgeGroup.appendChild(txt);
    }
  });
  svg.appendChild(edgeGroup);

  // Nodes
  const nodeGroup = svgEl('g');
  G.nodes.forEach(n => {
    const g = svgEl('g');
    g.setAttribute('transform', `translate(${PAD+n.x}, ${PAD+n.y})`);
    g.style.cursor = 'default';

    // outer rect
    const rect = svgEl('rect');
    rect.setAttribute('width',  n.w);
    rect.setAttribute('height', n.h);
    rect.setAttribute('rx', '4');
    rect.setAttribute('fill', '#161b22');
    rect.setAttribute('stroke', n.borderColor);
    rect.setAttribute('stroke-width', n.grade==='Exact' ? '1' : '2');
    if (n.grade !== 'Exact') rect.setAttribute('filter', 'url(#glow)');
    g.appendChild(rect);

    // header band
    const HEADER_H = 18;
    const header = svgEl('rect');
    header.setAttribute('width',  n.w);
    header.setAttribute('height', HEADER_H);
    header.setAttribute('rx', '4');
    header.setAttribute('fill', n.headerColor);
    g.appendChild(header);
    // fix bottom corners of header
    const headerFix = svgEl('rect');
    headerFix.setAttribute('y', HEADER_H/2);
    headerFix.setAttribute('width',  n.w);
    headerFix.setAttribute('height', HEADER_H/2);
    headerFix.setAttribute('fill', n.headerColor);
    g.appendChild(headerFix);

    // header text (category)
    const htxt = svgEl('text');
    htxt.setAttribute('x', n.w/2);
    htxt.setAttribute('y', 12);
    htxt.setAttribute('text-anchor', 'middle');
    htxt.setAttribute('class', 'node-header');
    htxt.textContent = n.category.toUpperCase();
    g.appendChild(htxt);

    // name (truncated)
    const nameEl = svgEl('text');
    nameEl.setAttribute('x', n.w/2);
    nameEl.setAttribute('y', HEADER_H + 16);
    nameEl.setAttribute('text-anchor', 'middle');
    nameEl.setAttribute('class', 'node-name');
    nameEl.textContent = truncate(n.name, 28);
    g.appendChild(nameEl);

    // type subtitle
    const typeEl = svgEl('text');
    typeEl.setAttribute('x', n.w/2);
    typeEl.setAttribute('y', HEADER_H + 32);
    typeEl.setAttribute('text-anchor', 'middle');
    typeEl.setAttribute('class', 'node-type');
    typeEl.textContent = truncate(n.type, 30);
    g.appendChild(typeEl);

    // grade icon (top-right)
    const icon = svgEl('text');
    icon.setAttribute('x', n.w - 6);
    icon.setAttribute('y', n.h - 6);
    icon.setAttribute('text-anchor', 'end');
    icon.setAttribute('class', 'grade-icon');
    icon.textContent = n.icon;
    g.appendChild(icon);

    nodeGroup.appendChild(g);
  });
  svg.appendChild(nodeGroup);
};

function svgEl(tag) {
  return document.createElementNS('http://www.w3.org/2000/svg', tag);
}
function truncate(s, n) {
  return s && s.length > n ? s.slice(0,n-1)+'…' : (s||'');
}
</script>
</svg>
</body>
</html>
"""


def render_html(df: DataFlow, results=None) -> str:
    """Return self-contained HTML string for the flow diagram."""
    data = build_graph_data(df, results)
    graph_json = json.dumps(data)
    return _HTML_TEMPLATE.replace("__GRAPH_JSON__", graph_json)
