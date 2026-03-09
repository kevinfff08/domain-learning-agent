---
name: path-visualizer
description: |
  Learning path visualization in multiple output formats.
  Trigger: "visualize learning path", "show knowledge graph", "render graph",
    "display progress map", "generate path overview", "learning roadmap"
  DO NOT USE: for building the knowledge graph (use domain-mapper),
    for tracking progress metrics (use progress-tracker),
    for exporting to Obsidian/PDF (use material-integrator)
---

# Path Visualizer

Generates visual representations of the knowledge graph and learning progress
in three formats: interactive D3.js HTML (force-directed graph), Markdown
overview with checkboxes and "YOU ARE HERE" markers, and ASCII tree for
terminal display.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 1 - Assessment & Planning |
| CLI command | (invoked via `newlearner map --visualize` or programmatically) |
| Python module | `src/skills/path_visualizer.py` |
| Key class | `PathVisualizer` |
| Input | `KnowledgeGraph` with current `ConceptStatus` per node |
| Output | `output/path.html`, `output/path.md`, or terminal ASCII |
| Data models | Uses `src/models/knowledge_graph.py` types |

## Step-by-Step Instructions

### Generate Interactive HTML Visualization

1. Load the knowledge graph from `data/graphs/{field}_knowledge_graph.json`.
2. Call `PathVisualizer.generate_html(graph, output_path="output/path.html")`.
   - Renders a D3.js force-directed graph.
   - Nodes color-coded by status: grey (NOT_STARTED), blue (IN_PROGRESS),
     green (LEARNED), gold (MASTERED), light grey (SKIPPED).
   - Node size reflects difficulty_level.
   - Edges drawn as directed arrows; PREREQUISITE edges are solid,
     RELATED edges are dashed.
   - Click a node to see description, key papers, and status.
3. Open `output/path.html` in a browser to interact.

### Generate Markdown Overview

1. Call `PathVisualizer.generate_markdown(graph, output_path="output/path.md")`.
   - Outputs a structured Markdown document with:
     - Sections grouped by category (Prerequisites, Core, Methods, Advanced, Practical).
     - Checkboxes: `[ ]` for NOT_STARTED, `[~]` for IN_PROGRESS,
       `[x]` for LEARNED/MASTERED.
     - `<-- YOU ARE HERE` marker on the current IN_PROGRESS concept.
     - Estimated time and difficulty for each concept.
2. Useful for quick terminal review or pasting into notes.

### Print ASCII Tree

1. Call `PathVisualizer.print_ascii_tree(graph)`.
   - Prints a tree representation to the terminal using `rich.tree.Tree`.
   - Shows prerequisite chains as nested branches.
   - Status indicated by icons and colors via Rich markup.
   - Best for quick orientation during a CLI session.

## Key Implementation Details

- HTML template lives in `templates/path_visualization.html.j2` (Jinja2).
- D3.js is loaded from CDN in the HTML template.
- Markdown generation uses Jinja2 template `templates/path_overview.md.j2`.
- ASCII tree uses `rich.tree.Tree` and `rich.console.Console` for rendering.
- All three formats respect the same topological ordering from the graph.

## Anti-Patterns

- **Do not generate visualizations from stale graphs.** Always reload the
  graph from disk before visualizing to reflect the latest status updates
  from Progress Tracker and Adaptive Controller.

- **Do not use HTML visualization for large graphs (>80 nodes) without
  filtering.** The force-directed layout becomes unreadable. Filter by
  category or show only the active learning frontier.

- **Do not treat the Markdown overview as a progress report.** It shows
  structure and current position but lacks metrics like quiz scores and
  time spent. Use Progress Tracker for quantitative reporting.
