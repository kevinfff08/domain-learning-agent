"""Skill 2: Domain Mapper - Multi-source knowledge graph construction."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from src.apis.arxiv_client import ArxivClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.apis.open_alex import OpenAlexClient
from src.llm.client import LLMClient
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

    async def build_graph(self, profile: AssessmentProfile) -> KnowledgeGraph:
        """Build a knowledge graph for the target field based on user profile."""
        field = profile.target_field

        # Gather survey and key paper information
        surveys = await self._search_surveys(field)
        key_papers = await self._search_key_papers(field)

        # Format survey info for LLM
        survey_info = []
        for s in surveys[:5]:
            title = s.get("title", "Unknown")
            abstract = s.get("abstract", s.get("summary", ""))[:300]
            citations = s.get("citationCount", s.get("citation_count", "N/A"))
            survey_info.append(f"- {title} (citations: {citations})\n  {abstract}")

        for p in key_papers[:5]:
            title = p.get("title", "Unknown")
            abstract = p.get("abstract", p.get("summary", ""))[:200]
            citations = p.get("citationCount", p.get("citation_count", "N/A"))
            survey_info.append(f"- [Key Paper] {title} (citations: {citations})\n  {abstract}")

        # Calculate average levels for prompt
        math_level = round(
            sum([
                profile.math_foundations.linear_algebra.level,
                profile.math_foundations.probability.level,
                profile.math_foundations.calculus.level,
                profile.math_foundations.optimization.level,
            ]) / 4
        )
        prog_level = round(
            sum([
                profile.programming.python.level,
                profile.programming.pytorch.level,
            ]) / 2
        )

        prompt = CONCEPT_EXTRACTION_PROMPT.format(
            field=field,
            survey_info="\n".join(survey_info) if survey_info else "No surveys found - use your expertise",
            math_level=math_level,
            prog_level=prog_level,
            domain_level=json.dumps(profile.domain_knowledge),
            learning_goal=profile.learning_goal.value,
        )

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT, temperature=0.3)

        try:
            graph_data = json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                graph_data = json.loads(response[start:end])
            else:
                raise ValueError(f"Failed to parse knowledge graph response: {response[:200]}")

        # Build knowledge graph
        nodes = []
        for n in graph_data.get("nodes", []):
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

        edges = []
        for e in graph_data.get("edges", []):
            edge = GraphEdge(
                source=e["source"],
                target=e["target"],
                edge_type=EdgeType(e.get("edge_type", "prerequisite")),
                label=e.get("label", ""),
            )
            edges.append(edge)

        # Build learning path
        learning_path = graph_data.get("learning_path", [n.id for n in nodes])

        # Add paper references to nodes
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
            estimated_total_hours=graph_data.get("estimated_total_hours", sum(n.estimated_hours for n in nodes)),
            sources_searched=["arxiv", "semantic_scholar", "openalex"],
            survey_papers_used=[r.title for r in paper_refs if r.role == "survey"],
        )

        # Save graph
        self.store.save_knowledge_graph(field, graph)
        return graph

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
