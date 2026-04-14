#!/usr/bin/env python3
"""
Generate an interactive wiki knowledge graph (HTML + d3.js).
Scans work/life/shared-wiki for all .md files, extracts [[wiki-links]] and tags,
builds a force-directed graph, opens in browser.

Usage: python3 wiki-graph.py [--no-open]
"""

import re, json, os, sys, webbrowser
from pathlib import Path

CLAWD_DIR = Path(os.environ.get("CLAWD_DIR", Path.home() / ".clawd"))
OUTPUT = CLAWD_DIR / "wiki-graph.html"


def scan_wiki_pages():
    """Scan all wiki pages, extract nodes and edges."""
    nodes = {}
    edges = []

    domains = {
        "work": CLAWD_DIR / "work" / "wiki",
        "life": CLAWD_DIR / "life" / "wiki",
        "shared": CLAWD_DIR / "shared-wiki",
    }

    for domain, wiki_dir in domains.items():
        if not wiki_dir.exists():
            continue
        for md in wiki_dir.rglob("*.md"):
            rel = md.relative_to(wiki_dir)
            node_id = str(rel.with_suffix(""))
            label = node_id.split("/")[-1]

            tags = []
            content = md.read_text(encoding="utf-8", errors="replace")

            tag_match = re.search(r"^tags:\s*\[([^\]]*)\]", content, re.MULTILINE)
            if tag_match:
                tags = [t.strip().strip("'\"") for t in tag_match.group(1).split(",") if t.strip()]

            title_match = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
            if title_match:
                label = title_match.group(1).strip()

            full_id = f"{domain}/{node_id}"
            nodes[full_id] = {
                "id": full_id,
                "label": label,
                "domain": domain,
                "tags": tags,
                "path": str(md),
            }

            links = re.findall(r"\[\[([^\]]+)\]\]", content)
            for link in links:
                link = link.strip()
                target_candidates = [
                    f"{domain}/{link}",
                    f"{domain}/projects/{link}",
                    f"{domain}/topics/{link}",
                    f"{domain}/decisions/{link}",
                    f"{domain}/patterns/{link}",
                    f"{domain}/people/{link}",
                    f"{domain}/reflections/{link}",
                ]
                edges.append({
                    "source": full_id,
                    "target_name": link,
                    "candidates": target_candidates,
                })

            lf_match = re.search(r"^linked_from:\s*\[([^\]]*)\]", content, re.MULTILINE)
            if lf_match:
                for lf in lf_match.group(1).split(","):
                    lf = lf.strip().strip("'\"").replace(".md", "")
                    if lf:
                        edges.append({
                            "source": full_id,
                            "target_name": lf,
                            "candidates": [f"{domain}/{lf}", f"{domain}/projects/{lf}"],
                        })

    resolved_edges = []
    for edge in edges:
        resolved = None
        for candidate in edge["candidates"]:
            if candidate in nodes:
                resolved = candidate
                break
        if not resolved:
            for nid in nodes:
                if nid.endswith("/" + edge["target_name"]) or nid.endswith("/projects/" + edge["target_name"]):
                    resolved = nid
                    break
        if resolved and resolved != edge["source"]:
            resolved_edges.append({"source": edge["source"], "target": resolved})

    seen = set()
    unique_edges = []
    for e in resolved_edges:
        key = (e["source"], e["target"])
        rev = (e["target"], e["source"])
        if key not in seen and rev not in seen:
            seen.add(key)
            unique_edges.append(e)

    return list(nodes.values()), unique_edges


def generate_html(nodes, edges):
    """Generate HTML with d3.js force-directed graph."""
    conn_count = {}
    for e in edges:
        conn_count[e["source"]] = conn_count.get(e["source"], 0) + 1
        conn_count[e["target"]] = conn_count.get(e["target"], 0) + 1

    for n in nodes:
        n["connections"] = conn_count.get(n["id"], 0)

    graph_data = json.dumps({"nodes": nodes, "links": edges}, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>intern-clawd Wiki Graph</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; overflow: hidden; }}
  svg {{ width: 100vw; height: 100vh; }}
  .legend {{ position: fixed; top: 16px; right: 16px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; font-size: 13px; }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  .stats {{ position: fixed; bottom: 16px; left: 16px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; font-size: 13px; }}
  .tooltip {{ position: fixed; background: #1c2128; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; font-size: 12px; pointer-events: none; display: none; max-width: 300px; z-index: 10; }}
  .tooltip .tags {{ color: #8b949e; margin-top: 4px; }}
  h3 {{ font-size: 14px; margin-bottom: 8px; color: #58a6ff; }}
</style>
</head>
<body>

<div class="legend">
  <h3>intern-clawd Wiki</h3>
  <div class="legend-item"><div class="legend-dot" style="background:#58a6ff"></div> work</div>
  <div class="legend-item"><div class="legend-dot" style="background:#3fb950"></div> life</div>
  <div class="legend-item"><div class="legend-dot" style="background:#8b949e"></div> shared</div>
</div>

<div class="stats" id="stats"></div>
<div class="tooltip" id="tooltip"></div>
<svg id="graph"></svg>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = {graph_data};

const domainColor = {{ work: "#58a6ff", life: "#3fb950", shared: "#8b949e" }};

document.getElementById("stats").innerHTML =
  `<b>${{data.nodes.length}}</b> pages &middot; <b>${{data.links.length}}</b> links`;

const svg = d3.select("#graph");
const width = window.innerWidth;
const height = window.innerHeight;
const tooltip = document.getElementById("tooltip");

const simulation = d3.forceSimulation(data.nodes)
  .force("link", d3.forceLink(data.links).id(d => d.id).distance(80))
  .force("charge", d3.forceManyBody().strength(-200))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collision", d3.forceCollide().radius(d => 8 + d.connections * 2));

const g = svg.append("g");

svg.call(d3.zoom().scaleExtent([0.2, 5]).on("zoom", e => g.attr("transform", e.transform)));

const link = g.append("g")
  .selectAll("line")
  .data(data.links)
  .join("line")
  .attr("stroke", "#21262d")
  .attr("stroke-width", 1);

const node = g.append("g")
  .selectAll("circle")
  .data(data.nodes)
  .join("circle")
  .attr("r", d => 5 + d.connections * 2)
  .attr("fill", d => domainColor[d.domain] || "#8b949e")
  .attr("stroke", "#0d1117")
  .attr("stroke-width", 1.5)
  .style("cursor", "pointer")
  .call(d3.drag()
    .on("start", (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on("drag", (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on("end", (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }}));

const label = g.append("g")
  .selectAll("text")
  .data(data.nodes)
  .join("text")
  .text(d => d.label)
  .attr("font-size", d => 9 + d.connections)
  .attr("fill", "#c9d1d9")
  .attr("dx", d => 8 + d.connections * 2)
  .attr("dy", 4)
  .style("pointer-events", "none");

node.on("mouseover", (e, d) => {{
  tooltip.style.display = "block";
  tooltip.innerHTML = `<b>${{d.label}}</b><br>${{d.domain}} &middot; ${{d.connections}} links`
    + (d.tags.length ? `<div class="tags">${{d.tags.join(", ")}}</div>` : "");
}}).on("mousemove", e => {{
  tooltip.style.left = (e.clientX + 12) + "px";
  tooltip.style.top = (e.clientY + 12) + "px";
}}).on("mouseout", () => {{ tooltip.style.display = "none"; }});

simulation.on("tick", () => {{
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("cx", d => d.x).attr("cy", d => d.y);
  label.attr("x", d => d.x).attr("y", d => d.y);
}});
</script>
</body>
</html>"""
    return html


def main():
    no_open = "--no-open" in sys.argv

    print("=== intern-clawd Wiki Graph ===\n")

    nodes, edges = scan_wiki_pages()
    print(f"Scan complete: {len(nodes)} pages, {len(edges)} links")

    if not nodes:
        print("Wiki is empty. Import some history or use the system for a while, then try again.")
        sys.exit(0)

    for domain in ["work", "life", "shared"]:
        count = sum(1 for n in nodes if n["domain"] == domain)
        if count:
            print(f"  {domain}: {count} pages")

    html = generate_html(nodes, edges)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"\n✓ Generated: {OUTPUT}")

    if not no_open:
        webbrowser.open(f"file://{OUTPUT}")
        print("  Opened in browser")


if __name__ == "__main__":
    main()
