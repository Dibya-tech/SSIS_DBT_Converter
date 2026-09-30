"""Render a DataFlow as an HTML/SVG node graph.

Produces a self-contained HTML snippet (no external dependencies) that can be
embedded in Streamlit via st.components.v1.html(), and a pure-Python SVG string
for PNG export.

Visual design:
  - Dark background (#0d1117)
  - Coloured header band per node (source=blue, transform=orange, destination=red)
  - Orange outline for Warnings, red for Manual
  - SVG bezier arrows with edge labels (output port names)
  - Topological layout: depth level = Y, branches spread centred = X
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from ..ir.model import DataFlow, Grade

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
_GRADE_ICON   = {Grade.EXACT: "E", Grade.WARNING: "W", Grade.MANUAL: "M"}
_GRADE_ICON_COLOR = {Grade.EXACT: "#3fb950", Grade.WARNING: "#d29922", Grade.MANUAL: "#f85149"}

NODE_W   = 200
NODE_H   = 68
NODE_GAP = 60   # horizontal gap between sibling branches
ROW_GAP  = 110  # vertical gap between depth levels
MARGIN   = 40


def _category(comp_type: str) -> str:
    if comp_type in _SOURCE_TYPES:
        return "source"
    if comp_type in _DEST_TYPES:
        return "destination"
    return "transform"


def _topo_levels(df: DataFlow) -> dict[str, int]:
    """Return component_id -> depth (row in layout)."""
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
    results: Optional[list] = None,
) -> dict:
    """Build a plain-dict graph description suitable for JSON serialisation."""
    grade_by_id = {}
    if results:
        grade_by_id = {r.component_id: r.grade for r in results}

    levels = _topo_levels(df)
    by_level: dict[int, list[str]] = defaultdict(list)
    for cid, lvl in levels.items():
        by_level[lvl].append(cid)

    # Sort siblings by original component order for consistent branch ordering
    comp_order = {c.id: i for i, c in enumerate(df.components)}
    for ids in by_level.values():
        ids.sort(key=lambda cid: comp_order.get(cid, 999))

    # Canvas width driven by the widest level
    max_count = max((len(ids) for ids in by_level.values()), default=1)
    canvas_w = MARGIN * 2 + max_count * NODE_W + (max_count - 1) * NODE_GAP
    canvas_w = max(canvas_w, NODE_W + MARGIN * 2)

    # Place nodes: each level is centred within canvas_w
    positions: dict[str, dict] = {}
    for lvl, ids in sorted(by_level.items()):
        y = MARGIN + lvl * ROW_GAP
        count = len(ids)
        level_span = count * NODE_W + (count - 1) * NODE_GAP
        start_x = (canvas_w - level_span) / 2
        for col, cid in enumerate(ids):
            x = start_x + col * (NODE_W + NODE_GAP)
            positions[cid] = {"x": x, "y": y}

    max_depth = max(levels.values(), default=0)
    canvas_h = MARGIN + (max_depth + 1) * NODE_H + max_depth * ROW_GAP + MARGIN

    nodes = []
    for c in df.components:
        pos = positions.get(c.id, {"x": 0.0, "y": 0.0})
        grade = grade_by_id.get(c.id, Grade.EXACT)
        cat = _category(c.component_type)
        nodes.append({
            "id": c.id,
            "name": c.name,
            "type": c.component_type,
            "category": cat,
            "grade": grade.value,
            "icon": _GRADE_ICON[grade],
            "iconColor": _GRADE_ICON_COLOR[grade],
            "headerColor": _CAT_HEADER[cat],
            "borderColor": _GRADE_BORDER[grade],
            "borderWidth": 1 if grade == Grade.EXACT else 2,
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

    return {"nodes": nodes, "edges": edges, "width": canvas_w, "height": canvas_h}


# ── Pure-Python SVG rendering ─────────────────────────────────────────────────

def _xe(s: object) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _trunc(s: str, n: int) -> str:
    if not s:
        return ""
    return s[:n - 1] + "…" if len(s) > n else s


def render_svg(df: DataFlow, results=None) -> str:
    """Return a self-contained SVG string for the data flow diagram."""
    data = build_graph_data(df, results)
    PAD = 20
    W = int(data["width"]) + PAD * 2
    H = int(data["height"]) + PAD * 2
    HEADER_H = 18

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
    )
    p.append(f'<rect width="{W}" height="{H}" fill="#0d1117"/>')
    p.append(
        '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L8,3 z" fill="#444c56"/></marker></defs>'
    )

    by_id = {n["id"]: n for n in data["nodes"]}

    # Edges (drawn below nodes)
    for e in data["edges"]:
        s = by_id.get(e["from"])
        t = by_id.get(e["to"])
        if not s or not t:
            continue
        x1 = PAD + s["x"] + s["w"] / 2
        y1 = PAD + s["y"] + s["h"]
        x2 = PAD + t["x"] + t["w"] / 2
        y2 = PAD + t["y"]
        dy = (y2 - y1) * 0.45
        p.append(
            f'<path d="M{x1:.1f},{y1:.1f} C{x1:.1f},{y1+dy:.1f} '
            f'{x2:.1f},{y2-dy:.1f} {x2:.1f},{y2:.1f}" '
            f'stroke="#444c56" stroke-width="1.5" fill="none" marker-end="url(#arr)"/>'
        )
        if e.get("label"):
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2 - 4
            lbl = _xe(e["label"])
            p.append(
                f'<text x="{mx:.1f}" y="{my:.1f}" text-anchor="middle" '
                f'font-size="9" fill="#8b949e" font-family="Arial,sans-serif">{lbl}</text>'
            )

    # Nodes
    for n in data["nodes"]:
        nx = PAD + n["x"]
        ny = PAD + n["y"]
        nw, nh = n["w"], n["h"]
        cx = nx + nw / 2

        # outer rect
        p.append(
            f'<rect x="{nx:.1f}" y="{ny:.1f}" width="{nw}" height="{nh}" rx="4" '
            f'fill="#161b22" stroke="{n["borderColor"]}" stroke-width="{n["borderWidth"]}"/>'
        )
        # header band (rounded top only)
        p.append(
            f'<rect x="{nx:.1f}" y="{ny:.1f}" width="{nw}" height="{HEADER_H}" '
            f'rx="4" fill="{n["headerColor"]}"/>'
        )
        p.append(
            f'<rect x="{nx:.1f}" y="{ny + HEADER_H / 2:.1f}" width="{nw}" '
            f'height="{HEADER_H / 2:.1f}" fill="{n["headerColor"]}"/>'
        )
        # category label in header
        p.append(
            f'<text x="{cx:.1f}" y="{ny + 12:.1f}" text-anchor="middle" '
            f'font-size="9" font-weight="700" fill="#ffffffcc" '
            f'font-family="Arial,sans-serif" letter-spacing="0.5">'
            f'{_xe(n["category"].upper())}</text>'
        )
        # component name
        p.append(
            f'<text x="{cx:.1f}" y="{ny + HEADER_H + 16:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#c9d1d9" font-family="Arial,sans-serif">'
            f'{_xe(_trunc(n["name"], 28))}</text>'
        )
        # component type
        p.append(
            f'<text x="{cx:.1f}" y="{ny + HEADER_H + 32:.1f}" text-anchor="middle" '
            f'font-size="9" fill="#8b949e" font-family="Arial,sans-serif">'
            f'{_xe(_trunc(n["type"], 30))}</text>'
        )
        # grade badge (bottom-right)
        p.append(
            f'<text x="{nx + nw - 7:.1f}" y="{ny + nh - 5:.1f}" text-anchor="end" '
            f'font-size="10" font-weight="700" fill="{n["iconColor"]}" '
            f'font-family="Arial,sans-serif">{_xe(n["icon"])}</text>'
        )

    p.append('</svg>')
    return '\n'.join(p)


def render_html(df: DataFlow, results=None) -> str:
    """Return self-contained HTML for embedding in Streamlit."""
    svg = render_svg(df, results)
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
        '<style>*{box-sizing:border-box;margin:0;padding:0}'
        'body{background:#0d1117;overflow:auto}</style></head>'
        f'<body>{svg}</body></html>'
    )
