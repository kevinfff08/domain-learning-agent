"""Skill 2: Domain Mapper - Multi-source knowledge graph construction."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.apis.arxiv_client import ArxivClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.apis.open_alex import OpenAlexClient
from src.llm.client import LLMClient
from src.logging_config import get_logger
from src.utils.json_repair import repair_json, repair_json_array
from src.models.assessment import AssessmentProfile
from src.models.knowledge_graph import (
    ConceptNode,
    ConceptStatus,
    EdgeType,
    GraphEdge,
    KnowledgeGraph,
    PaperReference,
)
from src.storage.local_store import LocalStore

logger = get_logger("skills.domain_mapper")

SYSTEM_PROMPT = """You are an expert AI research curriculum designer.
Your task is to create comprehensive, PhD-level knowledge graphs for AI research domains.
You understand the prerequisite relationships between concepts deeply.
Return valid JSON only."""

CONCEPT_EXTRACTION_PROMPT = """Analyze the following survey papers and domain information to build a comprehensive
knowledge graph for the field: "{field}"

Survey papers found:
{survey_info}

User background:
- Math level: {math_level}/5
- Programming level: {prog_level}/5
- Domain knowledge: {domain_level}
- Learning goal: {learning_goal}

Create a knowledge graph with 30-60 concept nodes covering:
1. Foundational prerequisites the user may need to review
2. Core concepts of the field
3. Key methods and architectures
4. Advanced topics and recent developments
5. Practical implementation concepts

Return a JSON object with this structure:
{{
  "nodes": [
    {{
      "id": "concept_id_snake_case",
      "name": "Human Readable Name",
      "description": "One sentence description",
      "difficulty": 1-5,
      "prerequisites": ["list", "of", "prerequisite", "concept_ids"],
      "estimated_hours": 1.0-8.0,
      "math_requirements": ["calculus", "probability", "linear_algebra", "optimization"],
      "tags": ["foundation", "core", "method", "advanced", "practical"]
    }}
  ],
  "edges": [
    {{
      "source": "concept_a",
      "target": "concept_b",
      "edge_type": "prerequisite|variant|application|extends",
      "label": "optional label"
    }}
  ],
  "learning_path": ["ordered", "list", "of", "concept_ids"],
  "estimated_total_hours": 120
}}

Rules:
- IDs must be unique snake_case strings
- Prerequisites must reference existing node IDs
- Learning path must be a valid topological order
- Include math/coding prerequisites only if user's level is below 4
- Difficulty 1 = introductory review, 5 = cutting-edge research
- Be thorough - this is for a PhD student aiming for deep understanding
"""


class DomainMapper:
    """Multi-source knowledge graph construction skill."""

    def __init__(
        self,
        llm: LLMClient,
        store: LocalStore,
        semantic_scholar: SemanticScholarClient | None = None,
        arxiv: ArxivClient | None = None,
        open_alex: OpenAlexClient | None = None,
    ):
        self.llm = llm
        self.store = store
        self.s2 = semantic_scholar
        self.arxiv = arxiv
        self.openalex = open_alex

    async def _search_surveys(self, field: str) -> list[dict]:
        """Search for survey papers across multiple sources."""
        surveys = []

        if self.s2:
            try:
                results = await self.s2.search_papers(
                    f"{field} survey", limit=5, fields_of_study=["Computer Science"]
                )
                surveys.extend(results)
            except Exception:
                pass

        if self.arxiv:
            try:
                results = await self.arxiv.search(
                    f"{field} survey review tutorial",
                    max_results=5,
                    categories=["cs.AI", "cs.LG", "cs.CL", "cs.CV"],
                )
                surveys.extend(results)
            except Exception:
                pass

        return surveys

    async def _search_key_papers(self, field: str) -> list[dict]:
        """Search for highly-cited key papers in the field."""
        papers = []

        if self.s2:
            try:
                results = await self.s2.search_papers(field, limit=20)
                # Sort by citation count
                results.sort(key=lambda p: p.get("citationCount", 0) or 0, reverse=True)
                papers.extend(results[:10])
            except Exception:
                pass

        return papers

    async def build_graph(
        self,
        profile: AssessmentProfile,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> KnowledgeGraph:
        """Build a knowledge graph for the target field based on user profile.

        Uses incremental 4-phase LLM generation to reduce truncation risk.

        Args:
            profile: The assessment profile.
            on_progress: Optional callback ``(step_id, message)`` called at
                each sub-step so callers (e.g. SSE route) can relay live
                progress to the frontend.
        """
        field = profile.target_field

        def _emit(step: str, msg: str) -> None:
            logger.info("graph_build [%s] %s", step, msg)
            if on_progress:
                on_progress(step, msg)

        # --- Step 1: Search surveys ---
        _emit("search_surveys", f"正在搜索 '{field}' 领域综述论文…")
        surveys = await self._search_surveys(field)
        _emit("search_surveys_done", f"找到 {len(surveys)} 篇综述论文")

        # --- Step 2: Search key papers ---
        _emit("search_papers", f"正在搜索 '{field}' 高引论文…")
        key_papers = await self._search_key_papers(field)
        _emit("search_papers_done", f"找到 {len(key_papers)} 篇关键论文")

        # Format survey info
        survey_info = []
        for s in surveys[:5]:
            title = s.get("title", "Unknown")
            abstract = (s.get("abstract") or s.get("summary") or "")[:300]
            citations = s.get("citationCount", s.get("citation_count", "N/A"))
            survey_info.append(f"- {title} (citations: {citations})\n  {abstract}")
        for p in key_papers[:5]:
            title = p.get("title", "Unknown")
            abstract = (p.get("abstract") or p.get("summary") or "")[:200]
            citations = p.get("citationCount", p.get("citation_count", "N/A"))
            survey_info.append(f"- [Key Paper] {title} (citations: {citations})\n  {abstract}")

        survey_text = "\n".join(survey_info) if survey_info else "No surveys found - use your expertise"

        # Calculate average levels
        math_level = round(sum([
            profile.math_foundations.linear_algebra.level,
            profile.math_foundations.probability.level,
            profile.math_foundations.calculus.level,
            profile.math_foundations.optimization.level,
        ]) / 4)
        prog_level = round(sum([
            profile.programming.python.level,
            profile.programming.pytorch.level,
        ]) / 2)

        # --- Phase 1: Generate categories ---
        _emit("generate_categories", "正在生成概念类别…")
        categories = self._generate_categories(field, survey_text, math_level, prog_level, profile)
        _emit("generate_categories_done", f"生成了 {len(categories)} 个概念类别")

        # --- Phase 2: Generate nodes per category ---
        _emit("generate_nodes", "正在逐类生成概念节点…")
        all_nodes_data: list[dict] = []
        for cat in categories:
            cat_name = cat.get("name", "")
            cat_concepts = cat.get("concepts", [])
            nodes_data = self._generate_nodes_for_category(
                field, cat_name, cat_concepts, math_level, prog_level
            )
            all_nodes_data.extend(nodes_data)
        _emit("generate_nodes_done", f"生成了 {len(all_nodes_data)} 个概念节点")

        # --- Phase 3: Generate edges ---
        _emit("generate_edges", "正在生成概念间关系…")
        node_ids = [n.get("id", "") for n in all_nodes_data]
        edges_data = self._generate_edges(field, all_nodes_data)
        _emit("generate_edges_done", f"生成了 {len(edges_data)} 条边")

        # --- Phase 4: Generate learning path ---
        _emit("generate_path", "正在生成学习路径…")
        learning_path = self._generate_learning_path(field, all_nodes_data, edges_data)
        _emit("generate_path_done", "学习路径生成完成")

        # --- Build graph objects ---
        _emit("build_graph", "正在构建知识图谱对象…")
        nodes = []
        for n in all_nodes_data:
            try:
                node = ConceptNode(
                    id=n["id"],
                    name=n.get("name", n["id"]),
                    description=n.get("description", ""),
                    difficulty=n.get("difficulty", 3),
                    prerequisites=n.get("prerequisites", []),
                    estimated_hours=n.get("estimated_hours", 2.0),
                    math_requirements=n.get("math_requirements", []),
                    tags=n.get("tags", []),
                )
                nodes.append(node)
            except Exception as exc:
                logger.warning("Skipping invalid node %s: %s", n.get("id"), exc)

        edges = []
        for e in edges_data:
            try:
                edge = GraphEdge(
                    source=e["source"],
                    target=e["target"],
                    edge_type=EdgeType(e.get("edge_type", "prerequisite")),
                    label=e.get("label", ""),
                )
                edges.append(edge)
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping invalid edge %s: %s", e, exc)

        # Validate and fix learning path topologically
        learning_path = self._validate_and_fix_learning_path(nodes, edges, learning_path)

        # Add paper references
        paper_refs = []
        for p in (surveys + key_papers):
            if self.s2:
                ref = SemanticScholarClient.to_paper_reference(p, role="survey" if p in surveys else "key_paper")
            elif self.arxiv:
                ref = ArxivClient.to_paper_reference(p, role="survey" if p in surveys else "key_paper")
            else:
                continue
            paper_refs.append(ref)

        graph = KnowledgeGraph(
            field=field,
            version=1,
            nodes=nodes,
            edges=edges,
            learning_path=learning_path,
            estimated_total_hours=sum(n.estimated_hours for n in nodes),
            sources_searched=["arxiv", "semantic_scholar", "openalex"],
            survey_papers_used=[r.title for r in paper_refs if r.role == "survey"],
        )
        _emit("build_graph_done", f"图谱构建完成：{len(nodes)} 个概念，{len(edges)} 条边")

        self.store.save_knowledge_graph(field, graph)
        return graph

    def _generate_categories(
        self, field: str, survey_text: str, math_level: int, prog_level: int,
        profile: AssessmentProfile,
    ) -> list[dict]:
        """Phase 1: Generate 5-8 concept categories."""
        prompt = f"""For the field "{field}", generate 5-8 concept categories for a PhD-level learning plan.

Survey papers:
{survey_text}

Student math level: {math_level}/5, programming: {prog_level}/5
Learning goal: {profile.learning_goal.value}

Return JSON array:
[
  {{
    "name": "Category Name",
    "description": "What this category covers",
    "concepts": ["concept_1_name", "concept_2_name", "concept_3_name"]
  }}
]

Each category should have 3-6 concept names. Cover: foundations, core methods, advanced topics, practical skills."""

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT, temperature=0.3)
        try:
            return repair_json_array(response)
        except ValueError:
            return [{"name": field, "concepts": [field], "description": "Main concepts"}]

    def _generate_nodes_for_category(
        self, field: str, category: str, concepts: list[str],
        math_level: int, prog_level: int,
    ) -> list[dict]:
        """Phase 2: Generate detailed nodes for a single category."""
        prompt = f"""For the field "{field}", category "{category}", define these concepts in detail:
{chr(10).join(f'- {c}' for c in concepts)}

Return JSON array:
[
  {{
    "id": "concept_id_snake_case",
    "name": "Human Readable Name",
    "description": "One sentence description",
    "difficulty": 1-5,
    "prerequisites": ["other_concept_ids"],
    "estimated_hours": 1.0-8.0,
    "math_requirements": [],
    "tags": ["category_tag"]
  }}
]

Rules:
- IDs must be unique snake_case
- Only reference prerequisites from known concept names in this field
- Student math level: {math_level}/5, programming: {prog_level}/5"""

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT, temperature=0.3)
        try:
            return repair_json_array(response)
        except ValueError:
            return [{"id": c.lower().replace(" ", "_"), "name": c, "difficulty": 3} for c in concepts]

    def _generate_edges(self, field: str, nodes_data: list[dict]) -> list[dict]:
        """Phase 3: Generate edges between all nodes."""
        node_summary = "\n".join(
            f"- {n.get('id')}: {n.get('name')} (difficulty: {n.get('difficulty', 3)})"
            for n in nodes_data
        )
        prompt = f"""For the field "{field}", given these concept nodes:
{node_summary}

Generate edges (relationships) between them.
Return JSON array:
[
  {{
    "source": "concept_a_id",
    "target": "concept_b_id",
    "edge_type": "prerequisite|variant|application|extends",
    "label": "optional label"
  }}
]

Rules:
- "prerequisite" means source must be learned before target
- Only reference existing node IDs
- Ensure the prerequisite graph is a DAG (no cycles)"""

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT, temperature=0.3)
        try:
            return repair_json_array(response)
        except ValueError:
            return []

    def _generate_learning_path(
        self, field: str, nodes_data: list[dict], edges_data: list[dict],
    ) -> list[str]:
        """Phase 4: Generate a valid learning path."""
        node_ids = [n.get("id", "") for n in nodes_data]
        prereq_edges = [
            f"{e['source']} -> {e['target']}"
            for e in edges_data if e.get("edge_type") == "prerequisite"
        ]
        prompt = f"""For the field "{field}", given these concepts: {', '.join(node_ids)}
And prerequisite relationships:
{chr(10).join(prereq_edges) if prereq_edges else 'None'}

Return a valid topological ordering (learning path) as a JSON array of concept IDs.
Earlier items should be prerequisites. Return JSON: ["id1", "id2", ...]"""

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT, temperature=0.2)
        try:
            path = repair_json_array(response)
            if isinstance(path, list) and all(isinstance(x, str) for x in path):
                return path
        except ValueError:
            pass
        return node_ids

    @staticmethod
    def _validate_and_fix_learning_path(
        nodes: list[ConceptNode],
        edges: list[GraphEdge],
        learning_path: list[str],
    ) -> list[str]:
        """Validate learning path respects prerequisites using Kahn's algorithm.

        If the path is invalid, generates a valid topological sort.
        """
        node_ids = {n.id for n in nodes}
        # Build adjacency for prerequisite edges only
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        adj: dict[str, list[str]] = {nid: [] for nid in node_ids}

        for e in edges:
            if e.edge_type == EdgeType.PREREQUISITE and e.source in node_ids and e.target in node_ids:
                adj[e.source].append(e.target)
                in_degree[e.target] = in_degree.get(e.target, 0) + 1

        # Check if learning_path is a valid topological order
        path_set = set(learning_path)
        if path_set == node_ids:
            # Verify each node appears after all its prerequisites
            position = {nid: i for i, nid in enumerate(learning_path)}
            valid = True
            for e in edges:
                if e.edge_type == EdgeType.PREREQUISITE:
                    src_pos = position.get(e.source)
                    tgt_pos = position.get(e.target)
                    if src_pos is not None and tgt_pos is not None and src_pos >= tgt_pos:
                        valid = False
                        break
            if valid:
                return learning_path

        # Invalid path - generate valid topological sort via Kahn's algorithm
        from collections import deque
        queue = deque(nid for nid in node_ids if in_degree.get(nid, 0) == 0)
        result: list[str] = []
        remaining = dict(in_degree)

        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            for neighbor in adj.get(node_id, []):
                remaining[neighbor] -= 1
                if remaining[neighbor] == 0:
                    queue.append(neighbor)

        # Add any nodes not reached (cycle or disconnected)
        for nid in node_ids:
            if nid not in result:
                result.append(nid)

        return result

    def update_node_status(
        self,
        graph: KnowledgeGraph,
        concept_id: str,
        status: ConceptStatus,
        mastery: float = 0.0,
    ) -> KnowledgeGraph:
        """Update a node's status in the graph."""
        node = graph.get_node(concept_id)
        if node:
            node.status = status
            node.mastery = mastery
            graph.updated_at = datetime.now()
            self.store.save_knowledge_graph(graph.field, graph)
        return graph

    def add_prerequisite_node(
        self,
        graph: KnowledgeGraph,
        new_node: ConceptNode,
        dependent_concept_id: str,
    ) -> KnowledgeGraph:
        """Add a new prerequisite node to the graph (used by Adaptive Controller)."""
        graph.nodes.append(new_node)
        graph.edges.append(
            GraphEdge(
                source=new_node.id,
                target=dependent_concept_id,
                edge_type=EdgeType.PREREQUISITE,
            )
        )
        # Update dependent node's prerequisites
        dep_node = graph.get_node(dependent_concept_id)
        if dep_node and new_node.id not in dep_node.prerequisites:
            dep_node.prerequisites.append(new_node.id)

        # Insert into learning path before the dependent concept
        if dependent_concept_id in graph.learning_path:
            idx = graph.learning_path.index(dependent_concept_id)
            graph.learning_path.insert(idx, new_node.id)
        else:
            graph.learning_path.append(new_node.id)

        graph.version += 1
        graph.updated_at = datetime.now()
        self.store.save_knowledge_graph(graph.field, graph)
        return graph

    def split_concept(
        self,
        graph: KnowledgeGraph,
        concept_id: str,
        sub_concepts: list[ConceptNode],
    ) -> KnowledgeGraph:
        """Split a concept into finer-grained sub-concepts (used by Adaptive Controller Level 3)."""
        original = graph.get_node(concept_id)
        if not original:
            return graph

        # Add sub-concepts
        for i, sub in enumerate(sub_concepts):
            graph.nodes.append(sub)
            if i > 0:
                # Each sub-concept depends on the previous
                graph.edges.append(
                    GraphEdge(
                        source=sub_concepts[i - 1].id,
                        target=sub.id,
                        edge_type=EdgeType.PREREQUISITE,
                    )
                )

        # Replace original in learning path with sub-concepts
        if concept_id in graph.learning_path:
            idx = graph.learning_path.index(concept_id)
            graph.learning_path[idx:idx + 1] = [s.id for s in sub_concepts]

        # Update edges: anything that depended on the original now depends on the last sub-concept
        for edge in graph.edges:
            if edge.source == concept_id:
                edge.source = sub_concepts[-1].id

        # Remove original node
        graph.nodes = [n for n in graph.nodes if n.id != concept_id]

        graph.version += 1
        graph.updated_at = datetime.now()
        self.store.save_knowledge_graph(graph.field, graph)
        return graph
