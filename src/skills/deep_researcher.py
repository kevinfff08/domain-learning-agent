"""Skill 4: Deep Researcher - PhD-level three-layer content synthesis."""

from __future__ import annotations

from src.apis.arxiv_client import ArxivClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.llm.client import LLMClient
from src.utils.json_repair import repair_json
from src.utils.rag_interface import RAGProvider, SimpleRAG
from src.models.assessment import AssessmentProfile
from src.models.content import (
    CrossConceptConnection,
    Equation,
    IntuitionLayer,
    MechanismLayer,
    PracticeLayer,
    ResearchSynthesis,
    SourceAttribution,
)
from src.models.knowledge_graph import ConceptNode, KnowledgeGraph
from src.storage.local_store import LocalStore

SYSTEM_PROMPT = """You are a world-class AI researcher and educator creating PhD-level learning materials.
Your explanations must be mathematically rigorous yet accessible.
Every equation must be traceable to a source paper.
Return valid JSON only."""

SYNTHESIS_PROMPT = """Create a comprehensive, PhD-level learning document for the concept: "{concept_name}"

Concept description: {description}
Field: {field}
Key papers: {key_papers}
Retrieved paper abstracts:
{paper_context}
User's learning goal: {learning_goal}
User's math level: {math_level}/5
User's learning style: {learning_style}

Related concepts in the knowledge graph: {related_concepts}

Generate a three-layer research synthesis as JSON:
{{
  "intuition": {{
    "analogy": "A vivid, accurate analogy that builds on common knowledge",
    "visual_description": "How to visualize this concept (describe a diagram or mental model)",
    "why_it_matters": "Why this concept is important in the field (2-3 sentences)",
    "key_insight": "The single most important insight to grasp (1 sentence)"
  }},
  "mechanism": {{
    "mathematical_framework": "LaTeX-formatted mathematical overview (use $...$ for inline, $$...$$ for display)",
    "key_equations": [
      {{
        "name": "Equation name",
        "latex": "LaTeX formula",
        "explanation": "What each variable means and why this equation matters",
        "derivation_steps": ["Step 1: Start from...", "Step 2: Apply..."],
        "source_paper": "arXiv ID or paper reference",
        "source_equation_ref": "e.g., Eq. 2 in the paper"
      }}
    ],
    "pseudocode": "Clear pseudocode for the core algorithm",
    "algorithm_steps": ["Step 1: ...", "Step 2: ..."],
    "connections": [
      {{
        "target_concept_id": "related_concept_id",
        "relationship": "How this concept connects to the other (1-2 sentences)"
      }}
    ]
  }},
  "practice": {{
    "reference_implementations": ["GitHub repo URLs"],
    "key_hyperparameters": {{"param_name": "description and typical values"}},
    "common_pitfalls": ["Pitfall 1", "Pitfall 2"],
    "reproduction_checklist": ["Step 1: Set up environment", "Step 2: ..."]
  }},
  "sources": [
    {{
      "arxiv_id": "2006.11239",
      "title": "Paper title",
      "source_type": "paper|blog|code|course",
      "role": "primary_source|builds_upon|reference"
    }}
  ]
}}

Requirements:
- Mathematical rigor: every equation must be correctly stated
- Source attribution: tag each equation and key claim with its source paper
- For "reproduce_papers" goal: include detailed reproduction checklist
- Cross-concept connections: explicitly link to related concepts in the graph
- Be comprehensive but clear - this is PhD-level content
- Base your content on the provided paper abstracts when available. Cite specific papers.
"""


class DeepResearcher:
    """PhD-level three-layer content synthesis skill."""

    def __init__(
        self,
        llm: LLMClient,
        store: LocalStore,
        semantic_scholar: SemanticScholarClient | None = None,
        arxiv: ArxivClient | None = None,
        rag_provider: RAGProvider | None = None,
    ):
        self.llm = llm
        self.store = store
        self.s2 = semantic_scholar
        self.arxiv = arxiv
        self.rag = rag_provider or SimpleRAG(semantic_scholar, arxiv)

    async def _fetch_paper_context(self, concept: ConceptNode) -> str:
        """Fetch real paper abstracts from S2/arXiv for grounding."""
        try:
            results = await self.rag.query(concept.name)
        except Exception:
            results = []

        if not results:
            return "No papers retrieved - use your knowledge"

        lines = []
        for r in results[:8]:
            title = r.get("title", "")
            content = r.get("content", "")[:300]
            source = r.get("source", "")
            year = r.get("year", "")
            lines.append(f"- [{source}] {title} ({year}): {content}")
        return "\n".join(lines)

    async def synthesize(
        self,
        concept: ConceptNode,
        graph: KnowledgeGraph,
        profile: AssessmentProfile,
    ) -> ResearchSynthesis:
        """Generate comprehensive three-layer content for a concept."""
        # Gather context
        related = []
        for edge in graph.edges:
            if edge.source == concept.id or edge.target == concept.id:
                other_id = edge.target if edge.source == concept.id else edge.source
                other = graph.get_node(other_id)
                if other:
                    related.append(f"{other.name} ({edge.edge_type.value})")

        key_papers_text = "\n".join(
            f"- {p.title} ({p.arxiv_id}, {p.year}, citations: {p.citation_count})"
            for p in concept.key_papers
        ) if concept.key_papers else "No specific papers listed - use your knowledge"

        # Fetch real paper context
        paper_context = await self._fetch_paper_context(concept)

        math_level = round(sum([
            profile.math_foundations.linear_algebra.level,
            profile.math_foundations.probability.level,
            profile.math_foundations.calculus.level,
            profile.math_foundations.optimization.level,
        ]) / 4)

        prompt = SYNTHESIS_PROMPT.format(
            concept_name=concept.name,
            description=concept.description,
            field=graph.field,
            key_papers=key_papers_text,
            paper_context=paper_context,
            learning_goal=profile.learning_goal.value,
            math_level=math_level,
            learning_style=profile.learning_style.value,
            related_concepts=", ".join(related) if related else "None identified",
        )

        response = self.llm.generate_json(
            prompt, system=SYSTEM_PROMPT, temperature=0.3
        )

        data = repair_json(response)

        # Build synthesis
        intuition_data = data.get("intuition", {})
        mechanism_data = data.get("mechanism", {})
        practice_data = data.get("practice", {})

        synthesis = ResearchSynthesis(
            concept_id=concept.id,
            title=concept.name,
            intuition=IntuitionLayer(
                analogy=intuition_data.get("analogy", ""),
                visual_description=intuition_data.get("visual_description", ""),
                why_it_matters=intuition_data.get("why_it_matters", ""),
                key_insight=intuition_data.get("key_insight", ""),
            ),
            mechanism=MechanismLayer(
                mathematical_framework=mechanism_data.get("mathematical_framework", ""),
                key_equations=[
                    Equation(**eq) for eq in mechanism_data.get("key_equations", [])
                ],
                pseudocode=mechanism_data.get("pseudocode", ""),
                algorithm_steps=mechanism_data.get("algorithm_steps", []),
                connections=[
                    CrossConceptConnection(**c)
                    for c in mechanism_data.get("connections", [])
                ],
            ),
            practice=PracticeLayer(
                reference_implementations=practice_data.get("reference_implementations", []),
                key_hyperparameters=practice_data.get("key_hyperparameters", {}),
                common_pitfalls=practice_data.get("common_pitfalls", []),
                reproduction_checklist=practice_data.get("reproduction_checklist", []),
            ),
            sources=[
                SourceAttribution(**s) for s in data.get("sources", [])
            ],
        )

        # Save
        self.store.save_content(concept.id, "research_synthesis.json", synthesis)
        return synthesis

    def generate_alternative_explanation(
        self,
        concept: ConceptNode,
        previous_synthesis: ResearchSynthesis,
        struggle_areas: list[str] | None = None,
    ) -> ResearchSynthesis:
        """Generate an alternative explanation for Level 1 adaptive intervention."""
        prompt = f"""The student is struggling with the concept "{concept.name}".

Previous explanation approach:
- Analogy used: {previous_synthesis.intuition.analogy[:200]}
- Key insight: {previous_synthesis.intuition.key_insight}

{f"Specific areas of confusion: {', '.join(struggle_areas)}" if struggle_areas else ""}

Generate a COMPLETELY DIFFERENT explanation using:
1. A different analogy/metaphor
2. A different visual model
3. Worked examples instead of abstract definitions
4. Step-by-step walkthrough of a concrete case

Return JSON with the same structure as before but with fresh, alternative content.
Focus on the intuition and mechanism layers."""

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)

        try:
            data = repair_json(response)
        except ValueError:
            return previous_synthesis  # Fallback to original

        intuition_data = data.get("intuition", {})
        mechanism_data = data.get("mechanism", {})

        alt = previous_synthesis.model_copy(deep=True)
        if intuition_data:
            alt.intuition = IntuitionLayer(
                analogy=intuition_data.get("analogy", alt.intuition.analogy),
                visual_description=intuition_data.get("visual_description", alt.intuition.visual_description),
                why_it_matters=intuition_data.get("why_it_matters", alt.intuition.why_it_matters),
                key_insight=intuition_data.get("key_insight", alt.intuition.key_insight),
            )
        if mechanism_data:
            alt.mechanism.pseudocode = mechanism_data.get("pseudocode", alt.mechanism.pseudocode)
            alt.mechanism.algorithm_steps = mechanism_data.get("algorithm_steps", alt.mechanism.algorithm_steps)

        self.store.save_content(concept.id, "research_synthesis_alt.json", alt)
        return alt
