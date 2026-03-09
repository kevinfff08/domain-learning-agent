"""Skill 3: Path Visualizer - Learning path visualization."""

from __future__ import annotations

from pathlib import Path

from src.models.knowledge_graph import ConceptStatus, KnowledgeGraph
from src.models.progress import LearnerProgress
from src.storage.local_store import LocalStore

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Learning Path: {field}</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
body {{ font-family: system-ui, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
h1 {{ color: #e94560; }}
.stats {{ display: flex; gap: 20px; margin: 20px 0; }}
.stat {{ background: #16213e; padding: 15px 25px; border-radius: 8px; text-align: center; }}
.stat-value {{ font-size: 2em; font-weight: bold; color: #e94560; }}
.stat-label {{ color: #888; font-size: 0.9em; }}
svg {{ border: 1px solid #333; border-radius: 8px; background: #0f3460; }}
.node circle {{ stroke: #fff; stroke-width: 2; cursor: pointer; }}
.node text {{ font-size: 11px; fill: #eee; }}
.link {{ stroke: #555; stroke-opacity: 0.6; fill: none; marker-end: url(#arrow); }}
.tooltip {{ position: absolute; background: #16213e; border: 1px solid #e94560;
           padding: 10px; border-radius: 6px; pointer-events: none; max-width: 300px; }}
</style>
</head>
<body>
<h1>Learning Path: {field}</h1>
<div class="stats">
  <div class="stat"><div class="stat-value">{completed}/{total}</div><div class="stat-label">Completed</div></div>
  <div class="stat"><div class="stat-value">{completion_pct}%</div><div class="stat-label">Progress</div></div>
  <div class="stat"><div class="stat-value">{hours_remaining}h</div><div class="stat-label">Est. Remaining</div></div>
</div>
<svg id="graph" width="1200" height="800"></svg>
<script>
const data = {graph_json};
const svg = d3.select("#graph");
const width = 1200, height = 800;

svg.append("defs").append("marker")
  .attr("id", "arrow").attr("viewBox", "0 -5 10 10")
  .attr("refX", 25).attr("refY", 0)
  .attr("markerWidth", 6).attr("markerHeight", 6)
  .attr("orient", "auto")
  .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#555");

const color = d => {{ if(d.status==="completed") return "#00b894";
                       if(d.status==="in_progress") return "#fdcb6e";
                       return "#636e72"; }};

const simulation = d3.forceSimulation(data.nodes)
  .force("link", d3.forceLink(data.edges).id(d=>d.id).distance(120))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width/2, height/2))
  .force("collision", d3.forceCollide().radius(40));

const link = svg.selectAll(".link").data(data.edges).join("line").attr("class","link");
const node = svg.selectAll(".node").data(data.nodes).join("g").attr("class","node")
  .call(d3.drag().on("start",ds).on("drag",dd).on("end",de));

node.append("circle").attr("r", d=>10+d.difficulty*3).attr("fill", color);
node.append("text").attr("dy","-1.5em").attr("text-anchor","middle").text(d=>d.name);

const tooltip = d3.select("body").append("div").attr("class","tooltip").style("display","none");
node.on("mouseover",(e,d)=>{{tooltip.style("display","block")
  .html(`<b>${{d.name}}</b><br>Difficulty: ${{d.difficulty}}/5<br>Status: ${{d.status}}<br>Est: ${{d.hours}}h`)
  .style("left",(e.pageX+10)+"px").style("top",(e.pageY-10)+"px")}})
  .on("mouseout",()=>tooltip.style("display","none"));

simulation.on("tick",()=>{{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y)
      .attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  node.attr("transform",d=>`translate(${{d.x}},${{d.y}})`);
}});

function ds(e,d){{if(!e.active)simulation.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;}}
function dd(e,d){{d.fx=e.x;d.fy=e.y;}}
function de(e,d){{if(!e.active)simulation.alphaTarget(0);d.fx=null;d.fy=null;}}
</script>
</body>
</html>"""


class PathVisualizer:
    """Learning path visualization skill."""

    def __init__(self, store: LocalStore):
        self.store = store

    def generate_html(
        self,
        graph: KnowledgeGraph,
        progress: LearnerProgress | None = None,
        output_dir: Path | str = "output",
    ) -> Path:
        """Generate interactive HTML visualization."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Build D3-compatible data
        nodes = []
        for node in graph.nodes:
            cp = progress.concepts.get(node.id) if progress else None
            nodes.append({
                "id": node.id,
                "name": node.name,
                "difficulty": node.difficulty,
                "status": (cp.status if cp else node.status.value),
                "hours": node.estimated_hours,
                "mastery": cp.mastery_level if cp else node.mastery,
            })

        edges = []
        node_ids = {n["id"] for n in nodes}
        for edge in graph.edges:
            if edge.source in node_ids and edge.target in node_ids:
                edges.append({
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.edge_type.value,
                })

        import json
        graph_json = json.dumps({"nodes": nodes, "edges": edges})

        # Calculate stats
        completed = sum(1 for n in nodes if n["status"] == "completed")
        total = len(nodes)
        pct = round(completed / total * 100) if total else 0
        remaining = sum(n["hours"] for n in nodes if n["status"] != "completed")

        html = HTML_TEMPLATE.format(
            field=graph.field,
            completed=completed,
            total=total,
            completion_pct=pct,
            hours_remaining=f"{remaining:.0f}",
            graph_json=graph_json,
        )

        html_path = output_path / "learning_path.html"
        html_path.write_text(html, encoding="utf-8")
        return html_path

    def generate_markdown(
        self,
        graph: KnowledgeGraph,
        progress: LearnerProgress | None = None,
    ) -> str:
        """Generate markdown text overview of the learning path."""
        lines = [f"# Learning Path: {graph.field}\n"]

        completed = sum(1 for n in graph.nodes if n.status == ConceptStatus.COMPLETED)
        total = len(graph.nodes)
        lines.append(f"**Progress:** {completed}/{total} concepts ({completed/total*100:.0f}%)\n")
        lines.append(f"**Estimated total hours:** {graph.estimated_total_hours:.0f}h\n")

        lines.append("\n## Learning Sequence\n")

        for i, concept_id in enumerate(graph.learning_path, 1):
            node = graph.get_node(concept_id)
            if not node:
                continue

            cp = progress.concepts.get(concept_id) if progress else None
            status = cp.status if cp else node.status.value

            status_icon = {"completed": "[x]", "in_progress": "[~]", "pending": "[ ]"}.get(
                status, "[ ]"
            )
            current_marker = " <-- YOU ARE HERE" if status == "in_progress" else ""

            prereqs = ""
            if node.prerequisites:
                prereqs = f" (requires: {', '.join(node.prerequisites)})"

            lines.append(
                f"{i}. {status_icon} **{node.name}** "
                f"(difficulty: {node.difficulty}/5, ~{node.estimated_hours}h)"
                f"{prereqs}{current_marker}"
            )

        return "\n".join(lines)

    def print_ascii_tree(
        self,
        graph: KnowledgeGraph,
        progress: LearnerProgress | None = None,
    ) -> str:
        """Generate ASCII tree representation."""
        lines = [f"=== Learning Path: {graph.field} ===\n"]

        for i, concept_id in enumerate(graph.learning_path, 1):
            node = graph.get_node(concept_id)
            if not node:
                continue

            cp = progress.concepts.get(concept_id) if progress else None
            status = cp.status if cp else node.status.value

            icon = {"completed": "+", "in_progress": ">", "pending": "o"}.get(status, "o")
            bar = "#" * int(node.mastery * 10) + "-" * (10 - int(node.mastery * 10))

            lines.append(f"  [{icon}] {i:2d}. {node.name:<40s} [{bar}] {node.estimated_hours:.1f}h")

        return "\n".join(lines)
