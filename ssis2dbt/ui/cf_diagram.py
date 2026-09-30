"""Render a Package's Control Flow as an HTML/SVG diagram.

Mirrors the SSIS Control Flow designer tab:
  - Green rounded box  = ForEach / Sequence container (with children inside)
  - Blue node          = DataFlow task
  - Orange node        = ExecuteSQL task
  - Gray node          = other task types
  - Bezier arrows      = precedence constraints
  - Parallel branches at the same depth are centred side-by-side
"""
from __future__ import annotations

from collections import defaultdict

from ..ir.model import Package

_TASK_HEADER: dict[str, str] = {
    "ExecuteSQLTask":     "#b45309",
    "DataFlowTask":       "#1158a6",
    "ForEachLoop":        "#1a6334",
    "ForLoop":            "#1a6334",
    "SendMailTask":       "#6a0000",
    "FileSystemTask":     "#5c3317",
    "ScriptTask":         "#4a1d6b",
    "ExecutePackageTask": "#2d3748",
}
_DEFAULT_HEADER = "#374151"

_TYPE_LABEL: dict[str, str] = {
    "ExecuteSQLTask":     "Execute SQL",
    "DataFlowTask":       "Data Flow",
    "ForEachLoop":        "ForEach Loop",
    "ForLoop":            "For Loop",
    "SendMailTask":       "Send Mail",
    "FileSystemTask":     "File System",
    "ScriptTask":         "Script",
    "ExecutePackageTask": "Execute Package",
    "UnknownTask":        "Unknown",
}

# Layout constants
NODE_W        = 200
NODE_H        = 68
MARGIN        = 50
ROW_GAP       = 100   # vertical gap between top-level task rows
BRANCH_GAP    = 50    # horizontal gap between sibling tasks at the same depth
INNER_ROW_GAP = 80    # vertical gap between rows inside a container
INNER_COL_GAP = 50    # horizontal gap between columns inside a container
CONTAINER_PAD = 30    # padding inside container around children
CONTAINER_HDR = 30    # container header band height


def _topo(task_ids: list[str], precedence_map: dict[str, list[str]]) -> dict[str, int]:
    """Return id -> topo depth for the given set of task ids."""
    ids = set(task_ids)
    indeg: dict[str, int] = {tid: 0 for tid in ids}
    adj: dict[str, list[str]] = {tid: [] for tid in ids}
    for tid in ids:
        for pred in precedence_map.get(tid, []):
            if pred in ids:
                adj[pred].append(tid)
                indeg[tid] += 1
    queue = [tid for tid, d in indeg.items() if d == 0]
    level: dict[str, int] = {}
    while queue:
        tid = queue.pop(0)
        level[tid] = level.get(tid, 0)
        for nxt in adj[tid]:
            level[nxt] = max(level.get(nxt, 0), level[tid] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    for tid in task_ids:
        if tid not in level:
            level[tid] = 0
    return level


def build_cf_graph_data(pkg: Package) -> dict:
    """Build a plain-dict graph description for the control flow diagram."""
    precedence_map = {t.id: list(t.precedence) for t in pkg.tasks}

    # Separate top-level tasks from children (inside containers)
    top_ids = [t.id for t in pkg.tasks if t.parent_id is None]
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for t in pkg.tasks:
        if t.parent_id:
            children_by_parent[t.parent_id].append(t.id)

    # Preserve original task order for consistent sibling ordering
    task_order = {t.id: i for i, t in enumerate(pkg.tasks)}
    task_by_id = {t.id: t for t in pkg.tasks}

    # ── Step 1: compute container inner layouts (bottom-up) ──────────────────
    inner_rel: dict[str, dict] = {}       # task_id -> relative {x, y} inside parent
    container_size: dict[str, dict] = {}  # container_id -> {w, h}

    for container_id, child_list in children_by_parent.items():
        child_levels = _topo(child_list, precedence_map)
        by_lvl: dict[int, list[str]] = defaultdict(list)
        for cid, lvl in child_levels.items():
            by_lvl[lvl].append(cid)

        # Sort siblings by original task order
        for ids in by_lvl.values():
            ids.sort(key=lambda cid: task_order.get(cid, 999))

        max_siblings = max((len(v) for v in by_lvl.values()), default=1)
        num_levels   = max(child_levels.values(), default=0) + 1 if child_levels else 1

        inner_w = (CONTAINER_PAD * 2
                   + max_siblings * NODE_W
                   + (max_siblings - 1) * INNER_COL_GAP)
        inner_w = max(inner_w, NODE_W + CONTAINER_PAD * 2)
        inner_h = (CONTAINER_HDR + CONTAINER_PAD
                   + num_levels * NODE_H
                   + (num_levels - 1) * INNER_ROW_GAP
                   + CONTAINER_PAD)
        container_size[container_id] = {"w": inner_w, "h": inner_h}

        # Relative positions of children inside the container (centred)
        for lvl, cids in sorted(by_lvl.items()):
            count   = len(cids)
            span    = count * NODE_W + (count - 1) * INNER_COL_GAP
            start_x = CONTAINER_PAD + (inner_w - CONTAINER_PAD * 2 - span) / 2
            rel_y   = CONTAINER_HDR + CONTAINER_PAD + lvl * (NODE_H + INNER_ROW_GAP)
            for i, cid in enumerate(cids):
                inner_rel[cid] = {"x": start_x + i * (NODE_W + INNER_COL_GAP), "y": rel_y}

    # ── Step 2: top-level topo sort ──────────────────────────────────────────
    top_levels = _topo(top_ids, precedence_map)
    by_top_lvl: dict[int, list[str]] = defaultdict(list)
    for tid, lvl in top_levels.items():
        by_top_lvl[lvl].append(tid)

    # Sort top-level siblings by original task order
    for ids in by_top_lvl.values():
        ids.sort(key=lambda tid: task_order.get(tid, 999))

    def _node_w(tid: str) -> float:
        return float(container_size[tid]["w"]) if tid in container_size else float(NODE_W)

    def _node_h(tid: str) -> float:
        return float(container_size[tid]["h"]) if tid in container_size else float(NODE_H)

    # ── Step 3: canvas width driven by the widest level ──────────────────────
    max_level_w = max(
        (sum(_node_w(tid) for tid in tids) + (len(tids) - 1) * BRANCH_GAP
         for tids in by_top_lvl.values()),
        default=float(NODE_W),
    )
    canvas_w = max(max_level_w + MARGIN * 2, NODE_W + MARGIN * 2)

    # ── Step 4: assign absolute positions to top-level tasks (centred) ───────
    positions: dict[str, dict] = {}
    current_y = float(MARGIN)
    for lvl in sorted(by_top_lvl.keys()):
        tids  = by_top_lvl[lvl]
        total = sum(_node_w(tid) for tid in tids) + (len(tids) - 1) * BRANCH_GAP
        cur_x = (canvas_w - total) / 2
        for tid in tids:
            positions[tid] = {"x": cur_x, "y": current_y}
            cur_x += _node_w(tid) + BRANCH_GAP
        max_h     = max(_node_h(tid) for tid in tids)
        current_y += max_h + ROW_GAP

    canvas_h = current_y - ROW_GAP + MARGIN

    # ── Step 5: absolute positions for inner (child) tasks ───────────────────
    abs_positions: dict[str, dict] = dict(positions)
    for t in pkg.tasks:
        if t.parent_id and t.id in inner_rel:
            parent_pos = positions.get(t.parent_id, {"x": 0.0, "y": 0.0})
            rel        = inner_rel[t.id]
            abs_positions[t.id] = {
                "x": parent_pos["x"] + rel["x"],
                "y": parent_pos["y"] + rel["y"],
            }

    # ── Step 6: build output dicts ───────────────────────────────────────────
    nodes = []
    for t in pkg.tasks:
        if t.id not in abs_positions:
            continue
        if t.id in container_size:
            continue  # containers rendered separately
        pos = abs_positions[t.id]
        nodes.append({
            "id":          t.id,
            "name":        t.name,
            "type":        t.task_type,
            "typeLabel":   _TYPE_LABEL.get(t.task_type, t.task_type),
            "headerColor": _TASK_HEADER.get(t.task_type, _DEFAULT_HEADER),
            "x":   pos["x"],
            "y":   pos["y"],
            "w":   NODE_W,
            "h":   NODE_H,
        })

    containers = []
    for t in pkg.tasks:
        if t.id in container_size and t.id in positions:
            pos = positions[t.id]
            sz  = container_size[t.id]
            containers.append({
                "id":        t.id,
                "name":      t.name,
                "typeLabel": _TYPE_LABEL.get(t.task_type, t.task_type),
                "x":  pos["x"],
                "y":  pos["y"],
                "w":  sz["w"],
                "h":  sz["h"],
            })

    edges = []
    for t in pkg.tasks:
        if t.id not in abs_positions:
            continue
        for pred_id in t.precedence:
            if pred_id in abs_positions:
                edges.append({"from": pred_id, "to": t.id})

    return {
        "nodes":      nodes,
        "containers": containers,
        "edges":      edges,
        "width":      canvas_w,
        "height":     canvas_h,
    }


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


def render_cf_svg(pkg: Package) -> str:
    """Return a self-contained SVG string for the control flow diagram."""
    data = build_cf_graph_data(pkg)
    W = int(data["width"])
    H = int(data["height"])
    HEADER_H = 18

    p: list[str] = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">')
    p.append(f'<rect width="{W}" height="{H}" fill="#0d1117"/>')
    p.append(
        '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L8,3 z" fill="#444c56"/></marker></defs>'
    )

    by_id: dict = {}
    for n in data["nodes"]:
        by_id[n["id"]] = n
    for c in data["containers"]:
        by_id[c["id"]] = c

    # 1. Container boxes (behind everything)
    for c in data["containers"]:
        x, y, cw, ch = c["x"], c["y"], c["w"], c["h"]
        p.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" rx="6" '
            f'fill="#0d2b1a" stroke="#238636" stroke-width="1.5"/>'
        )
        p.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="30" rx="6" fill="#1a6334"/>'
        )
        p.append(
            f'<rect x="{x:.1f}" y="{y + 15:.1f}" width="{cw:.1f}" height="15" fill="#1a6334"/>'
        )
        cx = x + cw / 2
        p.append(
            f'<text x="{cx:.1f}" y="{y + 11:.1f}" text-anchor="middle" '
            f'font-size="9" font-weight="700" fill="#7ee787cc" '
            f'font-family="Arial,sans-serif" letter-spacing="0.6">'
            f'{_xe(c["typeLabel"].upper())}</text>'
        )
        p.append(
            f'<text x="{cx:.1f}" y="{y + 23:.1f}" text-anchor="middle" '
            f'font-size="9" fill="#56d36499" font-family="Arial,sans-serif">'
            f'{_xe(_trunc(c["name"], 36))}</text>'
        )

    # 2. Edges
    for e in data["edges"]:
        s = by_id.get(e["from"])
        t = by_id.get(e["to"])
        if not s or not t:
            continue
        x1 = s["x"] + s["w"] / 2
        y1 = s["y"] + s["h"]
        x2 = t["x"] + t["w"] / 2
        y2 = t["y"]
        dy = (y2 - y1) * 0.45
        p.append(
            f'<path d="M{x1:.1f},{y1:.1f} C{x1:.1f},{y1+dy:.1f} '
            f'{x2:.1f},{y2-dy:.1f} {x2:.1f},{y2:.1f}" '
            f'stroke="#444c56" stroke-width="1.5" fill="none" marker-end="url(#arr)"/>'
        )

    # 3. Task nodes
    for n in data["nodes"]:
        x, y, nw, nh = n["x"], n["y"], n["w"], n["h"]
        cx = x + nw / 2
        p.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{nw}" height="{nh}" rx="4" '
            f'fill="#161b22" stroke="#30363d" stroke-width="1"/>'
        )
        p.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{nw}" height="{HEADER_H}" '
            f'rx="4" fill="{n["headerColor"]}"/>'
        )
        p.append(
            f'<rect x="{x:.1f}" y="{y + HEADER_H / 2:.1f}" width="{nw}" '
            f'height="{HEADER_H / 2:.1f}" fill="{n["headerColor"]}"/>'
        )
        p.append(
            f'<text x="{cx:.1f}" y="{y + 12:.1f}" text-anchor="middle" '
            f'font-size="9" font-weight="700" fill="#ffffffcc" font-family="Arial,sans-serif">'
            f'{_xe(n["typeLabel"].upper())}</text>'
        )
        line1 = _xe(_trunc(n["name"], 26))
        p.append(
            f'<text x="{cx:.1f}" y="{y + 34:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#c9d1d9" font-family="Arial,sans-serif">{line1}</text>'
        )
        if len(n["name"]) > 26:
            line2 = _xe(_trunc(n["name"][26:], 26))
            p.append(
                f'<text x="{cx:.1f}" y="{y + 48:.1f}" text-anchor="middle" '
                f'font-size="9" fill="#8b949e" font-family="Arial,sans-serif">{line2}</text>'
            )

    p.append('</svg>')
    return '\n'.join(p)


def render_cf_html(pkg: Package) -> str:
    """Return self-contained HTML for embedding in Streamlit."""
    svg = render_cf_svg(pkg)
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
        '<style>*{box-sizing:border-box;margin:0;padding:0}'
        'body{background:#0d1117;overflow:auto}</style></head>'
        f'<body>{svg}</body></html>'
    )
