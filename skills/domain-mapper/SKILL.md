---
name: domain-mapper
description: |
  Multi-source knowledge graph construction for a research domain.
  Trigger: "build knowledge graph", "map domain", "concept graph",
    "create learning map", "prerequisite graph", "newlearner map"
  DO NOT USE: for visualizing an existing graph (use path-visualizer),
    for generating learning content (use deep-researcher),
    for tracking completion (use progress-tracker)
---

# Domain Mapper

Searches academic APIs (arXiv, Semantic Scholar, OpenAlex) for survey papers
and key publications, then uses LLM to construct a concept dependency graph
with 30-60 nodes. The graph defines prerequisite relationships and learning
order for all downstream skills.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 1 - Assessment & Planning |
| CLI command | `newlearner map` |
| Python module | `src/skills/domain_mapper.py` |
| Key class | `DomainMapper` |
| Input | `AssessmentProfile` from Pre-Assessor |
| Output | `data/graphs/{field}_knowledge_graph.json` |
| Data models | `src/models/knowledge_graph.py` (KnowledgeGraph, ConceptNode, GraphEdge, ConceptStatus, EdgeType) |
| External APIs | ArxivClient, SemanticScholarClient, OpenAlexClient |

## Step-by-Step Instructions

### Build a New Knowledge Graph

1. Ensure `data/user/assessment_profile.json` exists (run Pre-Assessor first).
2. Call `DomainMapper.build_graph(profile)`.
   - Searches arXiv, Semantic Scholar, OpenAlex for survey papers on the field.
   - Passes survey abstracts + user profile to LLM.
   - LLM returns 30-60 `ConceptNode` objects with prerequisite edges.
   - Nodes include: id, name, description, category (PREREQUISITE, CORE,
     METHOD, ADVANCED, PRACTICAL), difficulty_level, key_papers.
   - Edges typed as PREREQUISITE, RELATED, or EXTENDS.
3. Graph is topologically sorted and saved to
   `data/graphs/{field}_knowledge_graph.json`.

### Update Node Status

1. Call `DomainMapper.update_node_status(graph, node_id, new_status)`.
   - `ConceptStatus` enum: NOT_STARTED, IN_PROGRESS, LEARNED, MASTERED, SKIPPED.
   - Progress Tracker calls this as the learner advances.

### Add Prerequisite Node (Adaptive Controller Integration)

1. When Adaptive Controller detects a learner struggling (Level 2 intervention),
   it calls `DomainMapper.add_prerequisite_node(graph, parent_node_id, new_concept)`.
   - Inserts a new prerequisite node and PREREQUISITE edge into the graph.
   - Recalculates topological ordering.

### Split a Concept (Adaptive Controller Integration)

1. When a concept proves too complex even after alternative explanations,
   Adaptive Controller calls `DomainMapper.split_concept(graph, node_id, sub_concepts)`.
   - Replaces one node with multiple finer-grained sub-concept nodes.
   - Preserves incoming/outgoing edges on the boundary nodes.

## Key Implementation Details

- Graph stored as `KnowledgeGraph` Pydantic model with `nodes: list[ConceptNode]`
  and `edges: list[GraphEdge]`.
- Each `ConceptNode` has `key_papers: list[PaperReference]` linking to source literature.
- `PaperReference` includes title, authors, arxiv_id, semantic_scholar_id, year.
- Topological sort uses `networkx.topological_sort` on the prerequisite subgraph.
- API calls are async via `httpx.AsyncClient` for parallel survey search.

## Anti-Patterns

- **Do not build a graph without an assessment profile.** The graph depth
  and prerequisite inclusion depend on the learner's current levels.
  A novice needs more foundational nodes than an expert.

- **Do not manually edit the JSON graph file.** Use the class methods
  (`update_node_status`, `add_prerequisite_node`, `split_concept`) to
  maintain topological consistency and edge integrity.

- **Do not exceed 60 nodes in initial construction.** Graphs larger than
  60 nodes become unwieldy for learning path visualization and overwhelm
  the learner. Use concept splitting later for targeted expansion.
