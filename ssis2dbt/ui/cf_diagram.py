"""Render a Package's Control Flow as an interactive HTML/SVG diagram.

Mirrors the SSIS Control Flow designer tab:
  - Green rounded box  = ForEach / Sequence container (with children inside)
  - Blue node          = DataFlow task
  - Orange node        = ExecuteSQL task
  - Gray node          = other task types
  - Bezier arrows      = precedence constraints
"""
from __future__ import annotations

import json
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
INNER_ROW_GAP = 80    # vertical gap between rows inside a container
INNER_COL_GAP = 220   # horizontal gap between columns inside a container
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
    top_ids  = [t.id for t in pkg.tasks if t.parent_id is None]
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for t in pkg.tasks:
        if t.parent_id:
            children_by_parent[t.parent_id].append(t.id)

    task_by_id = {t.id: t for t in pkg.tasks}

    # ── Step 1: compute container inner layouts (bottom-up) ──────────────────
    inner_rel: dict[str, dict] = {}       # task_id -> relative {x, y} inside parent
    container_size: dict[str, dict] = {}  # container_id -> {w, h}

    for container_id, child_list in children_by_parent.items():
        child_levels = _topo(child_list, precedence_map)
        by_lvl: dict[int, list[str]] = defaultdict(list)
        for cid, lvl in child_levels.items():
            by_lvl[lvl].append(cid)

        max_siblings = max((len(v) for v in by_lvl.values()), default=1)
        num_levels   = max(child_levels.values(), default=0) + 1 if child_levels else 1

        inner_w = CONTAINER_PAD * 2 + max_siblings * NODE_W + (max_siblings - 1) * (INNER_COL_GAP - NODE_W)
        inner_w = max(inner_w, NODE_W + CONTAINER_PAD * 2)
        inner_h = (CONTAINER_HDR + CONTAINER_PAD
                   + num_levels * NODE_H + (num_levels - 1) * INNER_ROW_GAP
                   + CONTAINER_PAD)
        container_size[container_id] = {"w": inner_w, "h": inner_h}

        # Relative positions of children inside the container
        for lvl, cids in sorted(by_lvl.items()):
            count     = len(cids)
            span      = count * NODE_W + (count - 1) * (INNER_COL_GAP - NODE_W)
            start_x   = CONTAINER_PAD + (inner_w - CONTAINER_PAD * 2 - span) / 2
            rel_y     = CONTAINER_HDR + CONTAINER_PAD + lvl * (NODE_H + INNER_ROW_GAP)
            for i, cid in enumerate(cids):
                inner_rel[cid] = {"x": start_x + i * INNER_COL_GAP, "y": rel_y}

    # ── Step 2: top-level topo sort ──────────────────────────────────────────
    top_levels = _topo(top_ids, precedence_map)
    by_top_lvl: dict[int, list[str]] = defaultdict(list)
    for tid, lvl in top_levels.items():
        by_top_lvl[lvl].append(tid)

    def _node_w(tid: str) -> float:
        return container_size[tid]["w"] if tid in container_size else float(NODE_W)

    def _node_h(tid: str) -> float:
        return container_size[tid]["h"] if tid in container_size else float(NODE_H)

    # ── Step 3: compute canvas width ─────────────────────────────────────────
    max_level_w = max(
        (sum(_node_w(tid) for tid in tids) + (len(tids) - 1) * 40
         for tids in by_top_lvl.values()),
        default=float(NODE_W),
    )
    canvas_w = max(max_level_w + MARGIN * 2, NODE_W + MARGIN * 2)

    # ── Step 4: assign absolute positions to top-level tasks ─────────────────
    positions: dict[str, dict] = {}
    current_y = float(MARGIN)
    for lvl in sorted(by_top_lvl.keys()):
        tids  = by_top_lvl[lvl]
        total = sum(_node_w(tid) for tid in tids) + (len(tids) - 1) * 40
        cur_x = (canvas_w - total) / 2
        for tid in tids:
            positions[tid] = {"x": cur_x, "y": current_y}
            cur_x += _node_w(tid) + 40
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


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; overflow: auto;
         font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  svg  { display: block; }
  .nh  { font-size: 9px; font-weight: 700; letter-spacing: .08em;
         text-transform: uppercase; fill: #ffffffcc; }
  .nn  { font-size: 11px; font-weight: 500; fill: #c9d1d9; }
  .nt  { font-size: 9px; fill: #8b949e; }
  .ch  { font-size: 9px; font-weight: 700; letter-spacing: .06em;
         text-transform: uppercase; fill: #7ee787cc; }
  .cn  { font-size: 9px; fill: #56d36499; }
</style>
</head>
<body>
<svg id="cv" xmlns="http://www.w3.org/2000/svg">
<defs>
  <marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
    <path d="M0,0 L0,6 L8,3 z" fill="#444c56"/>
  </marker>
</defs>
<script>
const G = __GRAPH_JSON__;
window.onload = () => {
  const svg = document.getElementById('cv');
  svg.setAttribute('width',   G.width);
  svg.setAttribute('height',  G.height);
  svg.setAttribute('viewBox', `0 0 ${G.width} ${G.height}`);

  // id -> bbox (containers have full w/h; nodes have NODE_W/NODE_H)
  const byId = {};
  G.nodes.forEach(n => byId[n.id] = n);
  G.containers.forEach(c => byId[c.id] = c);

  // 1. Container boxes (behind everything)
  const cg = se('g');
  G.containers.forEach(c => {
    // background
    const bg = se('rect');
    attr(bg, {x:c.x, y:c.y, width:c.w, height:c.h, rx:6,
              fill:'#0d2b1a', stroke:'#238636', 'stroke-width':'1.5'});
    cg.appendChild(bg);
    // header band
    const hdr = se('rect');
    attr(hdr, {x:c.x, y:c.y, width:c.w, height:30, rx:6, fill:'#1a6334'});
    cg.appendChild(hdr);
    // fix bottom corners of header
    const fix = se('rect');
    attr(fix, {x:c.x, y:c.y+15, width:c.w, height:15, fill:'#1a6334'});
    cg.appendChild(fix);
    // type label
    const tl = se('text');
    attr(tl, {x:c.x+c.w/2, y:c.y+11, 'text-anchor':'middle', class:'ch'});
    tl.textContent = c.typeLabel.toUpperCase();
    cg.appendChild(tl);
    // container name
    const nl = se('text');
    attr(nl, {x:c.x+c.w/2, y:c.y+23, 'text-anchor':'middle', class:'cn'});
    nl.textContent = trunc(c.name, 36);
    cg.appendChild(nl);
  });
  svg.appendChild(cg);

  // 2. Edges
  const eg = se('g');
  G.edges.forEach(e => {
    const s = byId[e.from], t = byId[e.to];
    if (!s || !t) return;
    const x1 = s.x + s.w/2, y1 = s.y + s.h;
    const x2 = t.x + t.w/2, y2 = t.y;
    const mid = (y2-y1)*0.45;
    const p = se('path');
    attr(p, {
      d: `M${x1},${y1} C${x1},${y1+mid} ${x2},${y2-mid} ${x2},${y2}`,
      stroke:'#444c56', 'stroke-width':'1.5', fill:'none',
      'marker-end':'url(#arr)'
    });
    eg.appendChild(p);
  });
  svg.appendChild(eg);

  // 3. Task nodes
  const ng = se('g');
  G.nodes.forEach(n => {
    const g = se('g');
    g.setAttribute('transform', `translate(${n.x},${n.y})`);
    const box = se('rect');
    attr(box, {width:n.w, height:n.h, rx:4,
               fill:'#161b22', stroke:'#30363d', 'stroke-width':'1'});
    g.appendChild(box);
    // header band
    const hdr = se('rect');
    attr(hdr, {width:n.w, height:18, rx:4, fill:n.headerColor});
    g.appendChild(hdr);
    const fix = se('rect');
    attr(fix, {y:9, width:n.w, height:9, fill:n.headerColor});
    g.appendChild(fix);
    // type in header
    const ht = se('text');
    attr(ht, {x:n.w/2, y:12, 'text-anchor':'middle', class:'nh'});
    ht.textContent = n.typeLabel.toUpperCase();
    g.appendChild(ht);
    // task name (up to two lines)
    const line1 = trunc(n.name, 26);
    const nt = se('text');
    attr(nt, {x:n.w/2, y:34, 'text-anchor':'middle', class:'nn'});
    nt.textContent = line1;
    g.appendChild(nt);
    if (n.name.length > 26) {
      const nt2 = se('text');
      attr(nt2, {x:n.w/2, y:48, 'text-anchor':'middle', class:'nt'});
      nt2.textContent = trunc(n.name.slice(26), 26);
      g.appendChild(nt2);
    }
    ng.appendChild(g);
  });
  svg.appendChild(ng);
};

function se(tag) {
  return document.createElementNS('http://www.w3.org/2000/svg', tag);
}
function attr(el, map) {
  Object.entries(map).forEach(([k, v]) => el.setAttribute(k, v));
}
function trunc(s, n) {
  return s && s.length > n ? s.slice(0, n-1)+'…' : (s||'');
}
</script>
</svg>
</body>
</html>
"""


def render_cf_html(pkg: Package) -> str:
    """Return self-contained HTML string for the control flow diagram."""
    data = build_cf_graph_data(pkg)
    return _HTML_TEMPLATE.replace("__GRAPH_JSON__", json.dumps(data))
