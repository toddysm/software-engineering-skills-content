#!/usr/bin/env python3
"""
Generate an interactive dependency graph HTML from openclaw's dependency-graph.json.

Uses Sigma.js (WebGL-based) + Graphology, which handles 10K+ nodes smoothly.

Output: dependency-graph.html (self-contained, no server needed)

Features:
- WebGL rendering via Sigma.js (fast even at 12K nodes / 20K edges)
- Color-coded by node category (src, extensions, ui, npm, node built-ins, …)
- Node size proportional to in-degree (popularity)
- ForceAtlas2 layout (runs in a Web Worker)
- Search / highlight by node name
- Click-to-inspect panel (shows imports_from / imported_by / functions)
- Filter panel to show/hide categories
- "Highlight circular dependencies" toggle
- Zoom, pan, drag nodes
"""

import json
import math
import random
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
GRAPH_JSON = HERE / "dependency-graph.json"
CIRCULAR_JSON = HERE / "circular-dependencies.json"
OUTPUT_HTML = HERE / "dependency-graph.html"

# ── categorise nodes ──────────────────────────────────────────────────────────
NODE_BUILTINS = {
    "fs", "path", "os", "crypto", "http", "https", "net", "stream", "util",
    "events", "url", "buffer", "child_process", "readline", "zlib", "assert",
    "tty", "dns", "vm", "worker_threads", "perf_hooks", "module", "process",
    "timers", "string_decoder", "querystring", "punycode", "cluster", "dgram",
    "domain", "inspector", "repl", "v8",
}

CATEGORY_META = {
    "node-builtin": {"label": "Node.js built-in", "color": "#8b949e"},
    "npm-package":  {"label": "npm package",       "color": "#f85149"},
    "src-test":     {"label": "src/ test",         "color": "#79c0ff"},
    "src-internal": {"label": "src/ internal",     "color": "#1f6feb"},
    "extension":    {"label": "extension",         "color": "#3fb950"},
    "ui":           {"label": "ui/",               "color": "#bc8cff"},
    "scripts":      {"label": "scripts/ / test/",  "color": "#e3b341"},
    "config":       {"label": "config file",       "color": "#39d353"},
}


def categorise(name: str) -> str:
    if name.startswith("node:") or name in NODE_BUILTINS:
        return "node-builtin"
    if name.startswith("src/"):
        return "src-test" if (".test." in name or name.endswith(".spec.ts")) else "src-internal"
    if name.startswith("extensions/"):
        return "extension"
    if name.startswith("ui/") or name.startswith("ui-src/"):
        return "ui"
    if name.startswith("scripts/") or name.startswith("test/"):
        return "scripts"
    # Heuristic: if it has no path separators and no file extension → npm package
    has_ext = any(name.endswith(e) for e in (".ts", ".tsx", ".js", ".mjs", ".cjs", ".json"))
    if not has_ext:
        return "npm-package"
    return "config"


# ── load data ─────────────────────────────────────────────────────────────────
print("Loading dependency-graph.json …")
with open(GRAPH_JSON, encoding="utf-8") as fh:
    raw: dict = json.load(fh)

circular_nodes: set[str] = set()
try:
    with open(CIRCULAR_JSON, encoding="utf-8") as fh:
        for cycle in json.load(fh):
            circular_nodes.update(cycle)
except FileNotFoundError:
    pass

# ── build lightweight graph model ─────────────────────────────────────────────
print("Building graph model …")

node_ids: dict[str, int] = {}
nodes: list[dict] = []
edges: list[dict] = []

# assign stable IDs
for name in raw:
    nid = len(node_ids)
    node_ids[name] = nid

# compute in-degree for sizing
in_degree: dict[str, int] = {n: 0 for n in raw}
for name, info in raw.items():
    for dep in info.get("imports_from", []):
        if dep in in_degree:
            in_degree[dep] += 1

MAX_IN = max(in_degree.values(), default=1) or 1

# place nodes on a circle initially (ForceAtlas2 will re-layout)
N = len(node_ids)
random.seed(42)
for name, nid in node_ids.items():
    angle = 2 * math.pi * nid / N
    r = 200 + random.uniform(-20, 20)
    cat = categorise(name)
    indeg = in_degree.get(name, 0)
    size = 2 + 12 * math.log1p(indeg) / math.log1p(MAX_IN)
    nodes.append({
        "id": str(nid),
        "label": name,
        "x": r * math.cos(angle),
        "y": r * math.sin(angle),
        "size": round(size, 2),
        "color": CATEGORY_META[cat]["color"],
        "category": cat,
        "circular": name in circular_nodes,
    })

# build edges (only between known nodes to keep graph self-consistent)
eid = 0
for name, info in raw.items():
    src = node_ids[name]
    for dep in info.get("imports_from", []):
        if dep in node_ids:
            edges.append({"id": str(eid), "source": str(src), "target": str(node_ids[dep])})
            eid += 1

print(f"  Nodes: {len(nodes):,}  Edges: {len(edges):,}  Circular: {len(circular_nodes)}")

# ── serialise detail data (shown in the inspector panel) ──────────────────────
# Only include compact data to keep JSON size reasonable
detail: dict[str, dict] = {}
for name, info in raw.items():
    detail[str(node_ids[name])] = {
        "name": name,
        "imports_from": info.get("imports_from", []),
        "imported_by":  info.get("imported_by",  []),
        "functions_used":      list(info.get("functions_used",      {}).keys()),
        "functions_providing": list(info.get("functions_providing", {}).keys()),
        "classes_used":        list(info.get("classes_used",        {}).keys()),
        "classes_providing":   list(info.get("classes_providing",   {}).keys()),
    }

# ── generate HTML ──────────────────────────────────────────────────────────────
print("Generating HTML …")

nodes_json   = json.dumps(nodes,   separators=(",", ":"))
edges_json   = json.dumps(edges,   separators=(",", ":"))
detail_json  = json.dumps(detail,  separators=(",", ":"))
cat_meta_json = json.dumps(CATEGORY_META, separators=(",", ":"))

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>OpenClaw — Dependency Graph</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #0d1117; color: #c9d1d9; display: flex; height: 100vh; overflow: hidden; }}

  /* ── sidebar ── */
  #sidebar {{
    width: 300px; min-width: 260px; max-width: 400px;
    background: #161b22; border-right: 1px solid #30363d;
    display: flex; flex-direction: column; overflow: hidden;
    resize: horizontal;
  }}
  #sidebar-header {{
    padding: 12px 16px; border-bottom: 1px solid #30363d;
    font-size: 14px; font-weight: 600; color: #e6edf3;
    display: flex; align-items: center; gap: 8px;
  }}
  #sidebar-header svg {{ flex-shrink: 0; }}
  #search-wrap {{ padding: 10px 12px; border-bottom: 1px solid #30363d; }}
  #search {{
    width: 100%; padding: 6px 10px; border-radius: 6px;
    border: 1px solid #30363d; background: #0d1117; color: #c9d1d9;
    font-size: 13px; outline: none;
  }}
  #search:focus {{ border-color: #388bfd; }}
  #search-hits {{ font-size: 11px; color: #8b949e; padding: 4px 12px; min-height: 18px; }}

  /* ── filter panel ── */
  #filter-panel {{ padding: 10px 12px; border-bottom: 1px solid #30363d; }}
  #filter-panel h3 {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
    color: #8b949e; margin-bottom: 8px; }}
  .cat-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
    cursor: pointer; user-select: none; }}
  .cat-swatch {{ width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }}
  .cat-label {{ font-size: 12px; flex: 1; }}
  .cat-count {{ font-size: 11px; color: #8b949e; }}
  .cat-row.dimmed .cat-label, .cat-row.dimmed .cat-count {{ opacity: .4; }}

  /* ── controls ── */
  #controls {{ padding: 10px 12px; border-bottom: 1px solid #30363d; display: flex;
    gap: 8px; flex-wrap: wrap; }}
  button {{
    padding: 5px 10px; border-radius: 6px; border: 1px solid #30363d;
    background: #21262d; color: #c9d1d9; font-size: 12px; cursor: pointer;
  }}
  button:hover {{ background: #30363d; }}
  button.active {{ background: #1f6feb; border-color: #388bfd; color: #fff; }}

  /* ── inspector panel ── */
  #inspector {{ flex: 1; overflow-y: auto; padding: 12px; }}
  #inspector h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
    color: #8b949e; margin: 0 0 8px; }}
  #inspector-placeholder {{ color: #6e7681; font-size: 13px; margin-top: 8px; }}
  .insp-name {{ font-size: 13px; font-weight: 600; color: #e6edf3;
    word-break: break-all; margin-bottom: 10px; line-height: 1.4; }}
  .insp-badge {{ display: inline-block; padding: 2px 7px; border-radius: 12px;
    font-size: 11px; margin-bottom: 10px; }}
  .insp-section {{ margin-bottom: 12px; }}
  .insp-section h4 {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
    color: #8b949e; margin-bottom: 4px; }}
  .insp-list {{ list-style: none; }}
  .insp-list li {{ font-size: 11px; padding: 2px 0; color: #79c0ff; cursor: pointer;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .insp-list li:hover {{ text-decoration: underline; }}
  .insp-empty {{ font-size: 11px; color: #6e7681; font-style: italic; }}

  /* ── stats bar ── */
  #stats {{
    padding: 6px 12px; border-top: 1px solid #30363d;
    font-size: 11px; color: #8b949e; display: flex; gap: 14px;
  }}

  /* ── canvas area ── */
  #graph-area {{ flex: 1; position: relative; }}
  #sigma-container {{ width: 100%; height: 100%; }}

  /* ── tooltip ── */
  #tooltip {{
    position: absolute; background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 8px 12px; pointer-events: none;
    font-size: 12px; max-width: 280px; z-index: 100; display: none;
    box-shadow: 0 4px 16px rgba(0,0,0,.5);
  }}
  #tooltip .tt-name {{ font-weight: 600; color: #e6edf3; word-break: break-all; margin-bottom: 4px; }}
  #tooltip .tt-cat  {{ color: #8b949e; margin-bottom: 2px; }}
  #tooltip .tt-deg  {{ color: #8b949e; }}

  /* ── loading overlay ── */
  #loading {{
    position: absolute; inset: 0; background: #0d1117;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    z-index: 200; gap: 16px;
  }}
  #loading-text {{ color: #8b949e; font-size: 14px; }}
  .spinner {{
    width: 40px; height: 40px; border: 3px solid #30363d;
    border-top-color: #1f6feb; border-radius: 50%; animation: spin .8s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

  /* ── minimap ── */
  #minimap-area {{
    position: absolute; bottom: 16px; right: 16px;
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    overflow: hidden; width: 180px; height: 120px;
  }}
</style>
</head>
<body>

<!-- sidebar -->
<div id="sidebar">
  <div id="sidebar-header">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#388bfd" stroke-width="2">
      <circle cx="12" cy="12" r="3"/><circle cx="3" cy="3" r="2"/>
      <circle cx="21" cy="3" r="2"/><circle cx="3" cy="21" r="2"/><circle cx="21" cy="21" r="2"/>
      <line x1="12" y1="9" x2="3" y2="3"/><line x1="12" y1="9" x2="21" y2="3"/>
      <line x1="12" y1="15" x2="3" y2="21"/><line x1="12" y1="15" x2="21" y2="21"/>
    </svg>
    OpenClaw — Dependency Graph
  </div>

  <div id="search-wrap">
    <input id="search" type="search" placeholder="Search nodes…" autocomplete="off"/>
    <div id="search-hits"></div>
  </div>

  <div id="filter-panel">
    <h3>Node categories</h3>
    <div id="cat-filters"></div>
  </div>

  <div id="controls">
    <button id="btn-layout" title="Run ForceAtlas2 layout">&#9654; Layout</button>
    <button id="btn-stop"   title="Stop layout">&#9646;&#9646; Stop</button>
    <button id="btn-circular" title="Highlight circular dependencies">&#8635; Circular deps</button>
    <button id="btn-reset" title="Reset view">&#8635; Reset</button>
    <button id="btn-labels" class="active" title="Toggle labels">Labels</button>
  </div>

  <div id="inspector">
    <h3>Inspector</h3>
    <div id="inspector-placeholder">Click a node to inspect it.</div>
    <div id="inspector-content" style="display:none"></div>
  </div>

  <div id="stats">
    <span id="stat-nodes"></span>
    <span id="stat-edges"></span>
    <span id="stat-visible"></span>
  </div>
</div>

<!-- graph canvas -->
<div id="graph-area">
  <div id="loading">
    <div class="spinner"></div>
    <div id="loading-text">Loading graph…</div>
  </div>
  <div id="sigma-container"></div>
  <div id="tooltip">
    <div class="tt-name" id="tt-name"></div>
    <div class="tt-cat"  id="tt-cat"></div>
    <div class="tt-deg"  id="tt-deg"></div>
  </div>
  <div id="minimap-area"><canvas id="minimap"></canvas></div>
</div>

<!-- ── CDN libraries ── -->
<script src="https://cdn.jsdelivr.net/npm/graphology@0.25.4/dist/graphology.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology-layout@0.6.1/dist/graphology-layout.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology-layout-forceatlas2@0.10.1/dist/graphology-layout-forceatlas2.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js"></script>

<!-- ── embedded graph data ── -->
<script>
const NODES      = {nodes_json};
const EDGES      = {edges_json};
const DETAIL     = {detail_json};
const CAT_META   = {cat_meta_json};
const CIRCULAR   = new Set({json.dumps(sorted(circular_nodes))});
</script>

<script>
// ── helpers ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

// ── build graphology graph ───────────────────────────────────────────────────
const graph = new graphology.Graph({{ type: "directed", multi: false }});
NODES.forEach(n => graph.addNode(n.id, n));
EDGES.forEach(e => {{
  try {{ graph.addEdge(e.source, e.target, {{ id: e.id, size: 0.5, color: "#30363d" }}); }} catch(_) {{}}
}});

// ── category filter state ────────────────────────────────────────────────────
const hiddenCats = new Set();
const catCounts  = {{}};
graph.nodes().forEach(n => {{
  const c = graph.getNodeAttribute(n, "category");
  catCounts[c] = (catCounts[c] || 0) + 1;
}});

// build filter rows
const filterWrap = $("cat-filters");
Object.entries(CAT_META).forEach(([cat, meta]) => {{
  if (!catCounts[cat]) return;
  const row = document.createElement("div");
  row.className = "cat-row";
  row.dataset.cat = cat;
  row.innerHTML = `
    <div class="cat-swatch" style="background:${{meta.color}}"></div>
    <span class="cat-label">${{meta.label}}</span>
    <span class="cat-count">${{catCounts[cat] || 0}}</span>`;
  row.addEventListener("click", () => toggleCat(cat, row));
  filterWrap.appendChild(row);
}});

function toggleCat(cat, row) {{
  if (hiddenCats.has(cat)) {{
    hiddenCats.delete(cat);
    row.classList.remove("dimmed");
  }} else {{
    hiddenCats.add(cat);
    row.classList.add("dimmed");
  }}
  applyFilter();
}}

function applyFilter() {{
  graph.nodes().forEach(n => {{
    const cat  = graph.getNodeAttribute(n, "category");
    const circ = graph.getNodeAttribute(n, "circular");
    const hidden = hiddenCats.has(cat) && !(circularHighlight && circ);
    graph.setNodeAttribute(n, "hidden", hidden);
  }});
  graph.edges().forEach(e => {{
    const src = graph.source(e);
    const tgt = graph.target(e);
    graph.setEdgeAttribute(e, "hidden",
      graph.getNodeAttribute(src, "hidden") || graph.getNodeAttribute(tgt, "hidden"));
  }});
  updateStats();
  if (renderer) renderer.refresh();
}}

// ── sigma renderer ───────────────────────────────────────────────────────────
let renderer = null;
let faLayout = null;
let showLabels = true;
let circularHighlight = false;

const LABEL_THRESHOLD = 0.08; // only show labels when zoomed in

function buildRenderer() {{
  renderer = new Sigma(graph, $("sigma-container"), {{
    renderEdgeLabels: false,
    labelThreshold: LABEL_THRESHOLD,
    defaultEdgeColor: "#30363d",
    defaultNodeColor: "#1f6feb",
    labelFont: "monospace",
    labelSize: 10,
    labelColor: {{ attribute: "color" }},
    edgeReducer(edge, data) {{
      if (data.hidden) return {{ ...data, hidden: true }};
      return data;
    }},
    nodeReducer(node, data) {{
      if (data.hidden) return {{ ...data, hidden: true }};
      const result = {{ ...data }};
      if (highlightedNodes.size > 0 && !highlightedNodes.has(node)) {{
        result.color = "#30363d";
        result.label = undefined;
      }}
      return result;
    }},
  }});

  renderer.on("enterNode", ({{ node, event }}) => {{
    const d = DETAIL[node];
    if (!d) return;
    const cat = graph.getNodeAttribute(node, "category");
    const indeg = (d.imported_by || []).length;
    const outdeg = (d.imports_from || []).length;
    $("tt-name").textContent = d.name;
    $("tt-cat").textContent  = CAT_META[cat]?.label || cat;
    $("tt-deg").textContent  = `in: ${{indeg}}  out: ${{outdeg}}`;
    const tip = $("tooltip");
    tip.style.display = "block";
    repositionTooltip(event);
  }});

  renderer.on("leaveNode", () => {{ $("tooltip").style.display = "none"; }});

  renderer.on("moveBody", (e) => {{
    const tip = $("tooltip");
    if (tip.style.display === "block") repositionTooltip(e.original);
  }});

  renderer.on("clickNode", ({{ node }}) => showInspector(node));
  renderer.on("clickStage", () => clearHighlight());
}}

function repositionTooltip(event) {{
  const tip = $("tooltip");
  const rect = $("graph-area").getBoundingClientRect();
  let x = (event.clientX || event.x || 0) - rect.left + 14;
  let y = (event.clientY || event.y || 0) - rect.top + 14;
  if (x + 290 > rect.width)  x -= 300;
  if (y + 100 > rect.height) y -= 110;
  tip.style.left = x + "px";
  tip.style.top  = y + "px";
}}

// ── inspector ────────────────────────────────────────────────────────────────
let highlightedNodes = new Set();

function showInspector(nodeId) {{
  const d    = DETAIL[nodeId];
  const cat  = graph.getNodeAttribute(nodeId, "category");
  const meta = CAT_META[cat] || {{}};

  highlightedNodes = new Set([nodeId,
    ...(d.imports_from || []).map(n => Object.keys(DETAIL).find(k => DETAIL[k].name === n) || ""),
    ...(d.imported_by  || []).map(n => Object.keys(DETAIL).find(k => DETAIL[k].name === n) || ""),
  ].filter(Boolean));

  if (renderer) renderer.refresh();

  $("inspector-placeholder").style.display = "none";
  const c = $("inspector-content");
  c.style.display = "block";

  function listItems(arr, clickable = true) {{
    if (!arr || arr.length === 0) return '<span class="insp-empty">none</span>';
    return '<ul class="insp-list">' + arr.map(item => {{
      const nodeEntry = Object.entries(DETAIL).find(([,v]) => v.name === item);
      const nId = nodeEntry ? nodeEntry[0] : null;
      return `<li ${{nId ? `data-nid="${{nId}}"` : ""}} title="${{item}}">${{item}}</li>`;
    }}).join("") + "</ul>";
  }}

  c.innerHTML = `
    <div class="insp-name">${{d.name}}</div>
    <span class="insp-badge" style="background:${{meta.color}}22;color:${{meta.color}};border:1px solid ${{meta.color}}44">
      ${{meta.label || cat}}
    </span>
    ${{CIRCULAR.has(d.name) ? '<span class="insp-badge" style="background:#f8514922;color:#f85149;border:1px solid #f8514944;margin-left:4px">⟳ circular</span>' : ""}}
    <div class="insp-section">
      <h4>Imports from (${{(d.imports_from||[]).length}})</h4>
      ${{listItems(d.imports_from)}}
    </div>
    <div class="insp-section">
      <h4>Imported by (${{(d.imported_by||[]).length}})</h4>
      ${{listItems(d.imported_by)}}
    </div>
    <div class="insp-section">
      <h4>Functions used from (${{(d.functions_used||[]).length}})</h4>
      ${{d.functions_used.length ? '<ul class="insp-list">' + d.functions_used.map(x=>`<li>${{x}}</li>`).join("") + "</ul>" : '<span class="insp-empty">—</span>'}}
    </div>
    <div class="insp-section">
      <h4>Functions providing (${{(d.functions_providing||[]).length}})</h4>
      ${{d.functions_providing.length ? '<ul class="insp-list">' + d.functions_providing.map(x=>`<li>${{x}}</li>`).join("") + "</ul>" : '<span class="insp-empty">—</span>'}}
    </div>
  `;

  // click items to navigate
  c.querySelectorAll("[data-nid]").forEach(li => {{
    li.addEventListener("click", () => {{
      const nid = li.dataset.nid;
      if (!graph.hasNode(nid)) return;
      showInspector(nid);
      const cam = renderer.getCamera();
      const pos = renderer.getNodeDisplayData(nid);
      if (pos) cam.animate({{ x: pos.x, y: pos.y, ratio: 0.05 }}, {{ duration: 500 }});
    }});
  }});
}}

function clearHighlight() {{
  highlightedNodes.clear();
  $("inspector-placeholder").style.display = "block";
  $("inspector-content").style.display = "none";
  if (renderer) renderer.refresh();
}}

// ── search ───────────────────────────────────────────────────────────────────
$("search").addEventListener("input", e => {{
  const q = e.target.value.trim().toLowerCase();
  if (!q) {{
    highlightedNodes.clear();
    $("search-hits").textContent = "";
    if (renderer) renderer.refresh();
    return;
  }}
  const matches = graph.nodes().filter(n => {{
    const label = graph.getNodeAttribute(n, "label") || "";
    return label.toLowerCase().includes(q);
  }});
  highlightedNodes = new Set(matches);
  $("search-hits").textContent = `${{matches.length}} match${{matches.length !== 1 ? "es" : ""}}`;
  if (renderer) renderer.refresh();
  if (matches.length === 1) {{
    const pos = renderer.getNodeDisplayData(matches[0]);
    if (pos) renderer.getCamera().animate({{ x: pos.x, y: pos.y, ratio: 0.04 }}, {{ duration: 400 }});
  }}
}});

// ── layout ───────────────────────────────────────────────────────────────────
const FA2_SETTINGS = {{
  iterations: 0,  // 0 = run until stopped
  settings: {{
    gravity: 1,
    barnesHutOptimize: true,
    barnesHutTheta: 0.5,
    scalingRatio: 2,
    slowDown: 10,
    adjustSizes: true,
  }},
}};

$("btn-layout").addEventListener("click", () => {{
  if (faLayout) faLayout.kill();
  faLayout = graphologyLayoutForceatlas2.inferSettings
    ? graphologyLayoutForceatlas2.ForceAtlas2Layout
    : null;
  // Use synchronous layout supervisor
  const FA2 = graphologyLayoutForceatlas2;
  if (FA2.ForceAtlas2Layout) {{
    faLayout = new FA2.ForceAtlas2Layout(graph, FA2_SETTINGS);
    faLayout.start();
    $("btn-layout").classList.add("active");
  }} else {{
    // fallback: run for fixed iterations
    FA2(graph, {{ iterations: 200, settings: FA2_SETTINGS.settings }});
    if (renderer) renderer.refresh();
  }}
}});

$("btn-stop").addEventListener("click", () => {{
  if (faLayout && faLayout.stop) {{ faLayout.stop(); faLayout = null; }}
  $("btn-layout").classList.remove("active");
}});

// ── circular highlight ───────────────────────────────────────────────────────
$("btn-circular").addEventListener("click", () => {{
  circularHighlight = !circularHighlight;
  $("btn-circular").classList.toggle("active", circularHighlight);
  graph.nodes().forEach(n => {{
    if (graph.getNodeAttribute(n, "circular")) {{
      graph.setNodeAttribute(n, "color", circularHighlight ? "#f85149" : NODES.find(x=>x.id===n)?.color);
    }}
  }});
  if (renderer) renderer.refresh();
}});

// ── reset ────────────────────────────────────────────────────────────────────
$("btn-reset").addEventListener("click", () => {{
  if (renderer) renderer.getCamera().animate({{ x: 0, y: 0, ratio: 1 }}, {{ duration: 400 }});
  clearHighlight();
  highlightedNodes.clear();
  if (renderer) renderer.refresh();
}});

// ── labels toggle ────────────────────────────────────────────────────────────
$("btn-labels").addEventListener("click", () => {{
  showLabels = !showLabels;
  $("btn-labels").classList.toggle("active", showLabels);
  if (renderer) {{
    renderer.setSetting("labelThreshold", showLabels ? LABEL_THRESHOLD : Infinity);
    renderer.refresh();
  }}
}});

// ── stats ────────────────────────────────────────────────────────────────────
function updateStats() {{
  const visible = graph.nodes().filter(n => !graph.getNodeAttribute(n, "hidden")).length;
  const vedges  = graph.edges().filter(e => !graph.getEdgeAttribute(e, "hidden")).length;
  $("stat-nodes").textContent   = `Nodes: ${{graph.order.toLocaleString()}}`;
  $("stat-edges").textContent   = `Edges: ${{graph.size.toLocaleString()}}`;
  $("stat-visible").textContent = `Visible: ${{visible.toLocaleString()}}`;
}}

// ── minimap ──────────────────────────────────────────────────────────────────
function drawMinimap() {{
  if (!renderer) return;
  const canvas = $("minimap");
  const area   = $("minimap-area");
  canvas.width  = area.clientWidth;
  canvas.height = area.clientHeight;
  const ctx  = canvas.getContext("2d");
  ctx.fillStyle = "#0d1117";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // find extents
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  graph.nodes().forEach(n => {{
    if (graph.getNodeAttribute(n, "hidden")) return;
    const d = renderer.getNodeDisplayData(n);
    if (!d) return;
    minX = Math.min(minX, d.x); minY = Math.min(minY, d.y);
    maxX = Math.max(maxX, d.x); maxY = Math.max(maxY, d.y);
  }});
  if (!isFinite(minX)) return;
  const scaleX = canvas.width  / (maxX - minX || 1);
  const scaleY = canvas.height / (maxY - minY || 1);
  const scale  = Math.min(scaleX, scaleY) * 0.9;

  graph.nodes().forEach(n => {{
    if (graph.getNodeAttribute(n, "hidden")) return;
    const d = renderer.getNodeDisplayData(n);
    if (!d) return;
    ctx.fillStyle = d.color || "#1f6feb";
    ctx.beginPath();
    ctx.arc(
      (d.x - minX) * scale + 5,
      (d.y - minY) * scale + 5,
      1.2, 0, Math.PI * 2
    );
    ctx.fill();
  }});
}}

// ── init ─────────────────────────────────────────────────────────────────────
window.addEventListener("load", () => {{
  $("loading-text").textContent = "Building renderer…";
  setTimeout(() => {{
    buildRenderer();
    updateStats();
    $("loading").style.display = "none";
    setInterval(drawMinimap, 1000);
    drawMinimap();
  }}, 50);
}});
</script>
</body>
</html>
"""

OUTPUT_HTML.write_text(html, encoding="utf-8")
print(f"Done! → {OUTPUT_HTML}")
print(f"  File size: {OUTPUT_HTML.stat().st_size / 1024 / 1024:.1f} MB")
print()
print("Open the HTML file in a browser to explore the graph:")
print(f"  open {OUTPUT_HTML}")
