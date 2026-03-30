"""Skill 4: Deep Researcher - PhD-level three-layer content synthesis.

Generates content via three independent LLM calls (one per layer),
each with a specialized system prompt and quality requirements.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable

from src.apis.arxiv_client import ArxivClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.llm.client import LLMClient
from src.utils.json_repair import repair_json
from src.utils.rag_interface import RAGProvider, SimpleRAG
from src.models.assessment import AssessmentProfile
from src.models.content import (
    AlgorithmBlock,
    CodeAnalysis,
    CrossConceptConnection,
    Equation,
    IntuitionLayer,
    IntuitionResponse,
    MechanismLayer,
    MechanismResponse,
    PracticeLayer,
    PracticeResponse,
    ResearchSynthesis,
    SourceAttribution,
)
from src.models.textbook import Chapter, Textbook
from src.storage.local_store import LocalStore

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], Awaitable[None]] | None

# ---------------------------------------------------------------------------
# System prompts  (one per layer)
# ---------------------------------------------------------------------------

_MECHANISM_SYSTEM = """You are a world-class theoretical machine-learning researcher writing a PhD-level textbook chapter.

Your writing style:
- Continuous mathematical narrative (like Goodfellow's "Deep Learning" or Bishop's "Pattern Recognition and Machine Learning")
- Definitions → Assumptions → Lemmas/Theorems → Full Derivations → Remarks
- Every equation is numbered, sourced, and rigorously derived — no hand-waving
- Use $...$ for inline math, $$...$$ for display math in all markdown fields
- LaTeX equations in the `latex` field of key_equations should be raw LaTeX WITHOUT surrounding $ delimiters

Return valid JSON only. No markdown fencing."""

_INTUITION_SYSTEM = """You are a brilliant research mentor explaining cutting-edge ML concepts to a first-year PhD student.

Your writing style:
- Deep, insightful analogies that map precisely to the mathematical structure (not superficial comparisons)
- Explain WHY things work, not just WHAT they are
- Historical context: what problem was this solving? What came before? Why was this a breakthrough?
- Identify non-obvious insights that even practitioners miss
- All text supports inline LaTeX: use $...$ for math in markdown fields

Return valid JSON only. No markdown fencing."""

_PRACTICE_SYSTEM = """You are a senior ML engineer who has reproduced dozens of papers and mentors PhD students on implementation.

Your writing style:
- Concrete, runnable code with detailed annotations (not toy examples)
- Explain every design decision: "why this loss function?", "why this learning rate schedule?"
- Common pitfalls you've personally encountered
- Practical hyperparameter guidance with reasoning
- All text supports inline LaTeX: use $...$ for math in markdown fields

Return valid JSON only. No markdown fencing."""

# ---------------------------------------------------------------------------
# Layer prompts
# ---------------------------------------------------------------------------

_MECHANISM_PROMPT = """Write the **Mechanism & Theory** layer for: "{concept_name}"

## Context
- Field: {field}
- Chapter description: {description}
- Course-level requirements: {course_requirements}
- Chapter-specific guidance: {chapter_guidance}
- Key papers in this textbook:
{key_papers}
- Retrieved paper abstracts:
{paper_context}
- Related chapters: {related_concepts}
- Student math level: {math_level}/5

## Required JSON structure
{{
  "theoretical_narrative": "<1000-2000 words of continuous mathematical exposition in markdown+LaTeX. Structure: (1) Problem formulation and notation, (2) Key definitions, (3) Main theorem/result statement, (4) Full derivation with intermediate steps, (5) Important special cases and remarks, (6) Connections to related work. This should read like a chapter from a graduate textbook — every step justified, no gaps.>",

  "mathematical_framework": "<500+ words high-level mathematical overview in markdown+LaTeX: the core formulation, objective function, key assumptions, and how the pieces fit together.>",

  "key_equations": [
    {{
      "name": "Descriptive equation name",
      "latex": "raw LaTeX WITHOUT $ delimiters",
      "explanation": "100+ words: what each variable represents, why this form was chosen, connections to other equations. Use markdown with inline $...$ LaTeX.",
      "derivation_steps": ["Step 1: Start from X because...", "Step 2: Apply Y, noting that...", "..."],
      "source_paper": "arXiv ID or paper reference",
      "source_equation_ref": "e.g., Eq. 2"
    }}
  ],

  "algorithms": [
    {{
      "name": "Algorithm N: Name (e.g., 'Algorithm 1: DDPM Training')",
      "inputs": ["$x_0 \\\\sim q(x_0)$: training data sample", "..."],
      "outputs": ["Trained model parameters $\\\\theta$"],
      "steps": [
        "1: **repeat**",
        "2:   Sample $x_0 \\\\sim q(x_0)$, $t \\\\sim \\\\text{{Uniform}}(1,T)$, $\\\\epsilon \\\\sim \\\\mathcal{{N}}(0, I)$",
        "..."
      ],
      "source_paper": "arXiv ID"
    }}
  ],

  "connections": [
    {{
      "target_concept_id": "related_chapter_title",
      "relationship": "Detailed explanation of how this concept relates"
    }}
  ],

  "sources": [
    {{
      "arxiv_id": "2006.11239",
      "title": "Paper title",
      "source_type": "paper",
      "role": "primary_source"
    }}
  ]
}}

## Quality requirements
- **Completeness**: Every derivation step must be explicit. A PhD student should be able to follow from start to finish without consulting another source.
- **Rigor**: State assumptions clearly. If an approximation is made, say so and explain why it's valid.
- **Depth**: Include at least 5-8 key equations with full derivations. Include 1-2 algorithms.
- **Attribution**: Every major equation and claim must cite its source paper.
- **Guidance alignment**: Let `chapter_guidance` determine the emphasis and scope for this chapter. Use `course_requirements` only as background context.
"""

_INTUITION_PROMPT = """Write the **Intuition & Understanding** layer for: "{concept_name}"

## Context
- Field: {field}
- Chapter description: {description}
- Course-level requirements: {course_requirements}
- Chapter-specific guidance: {chapter_guidance}
- Student learning goal: {learning_goal}
- Student learning style: {learning_style}
- Key papers: {key_papers}
- Retrieved paper abstracts:
{paper_context}

## Reference (mechanism layer summary, for consistency)
The theoretical treatment covers: {mechanism_summary}

## Required JSON structure
{{
  "analogy": "<500+ words markdown. Build a detailed analogy that maps precisely to the mathematical structure. Include: (1) The analogy itself, (2) Explicit mapping table: 'In the analogy X corresponds to mathematical concept Y', (3) Where the analogy breaks down and why. Use inline $...$ LaTeX when referencing math.>",

  "why_it_matters": "<300+ words markdown. Cover: (1) Historical context — what problem motivated this work? What approaches failed before? (2) Downstream impact — what breakthroughs did this enable? (3) Current relevance — how is this used today? (4) Open problems — what remains unsolved?>",

  "key_insight": "<200+ words markdown. The single most important non-obvious insight. Explain: (1) What the insight is, (2) Why it's surprising or non-trivial, (3) How it changes how you think about the problem. Use inline $...$ LaTeX.>"
}}

## Quality requirements
- **Depth over breadth**: Go deep into one great analogy rather than listing several shallow ones.
- **Precision**: The analogy must be technically accurate — don't sacrifice correctness for accessibility.
- **Non-triviality**: The key_insight should be something a reader wouldn't get from just reading the abstract.
- **Guidance alignment**: Use `chapter_guidance` to choose the intuition, historical framing, and examples for this chapter.
"""

_PRACTICE_PROMPT = """Write the **Practice & Implementation** layer for: "{concept_name}"

## Context
- Field: {field}
- Chapter description: {description}
- Course-level requirements: {course_requirements}
- Chapter-specific guidance: {chapter_guidance}
- Student learning goal: {learning_goal}
- Retrieved paper abstracts:
{paper_context}

## Reference (mechanism layer summary, for consistency)
The theoretical treatment covers: {mechanism_summary}

## Required JSON structure
{{
  "code_analysis": [
    {{
      "title": "Descriptive title (e.g., 'DDPM Training Loop — PyTorch')",
      "language": "python",
      "source_url": "GitHub URL or reference if applicable",
      "code": "<50-150 lines of complete, runnable code. Include imports, class/function definitions, and a __main__ or usage example. Use real library calls (PyTorch, JAX, etc.), not pseudocode.>",
      "line_annotations": [
        "Lines 1-5: Import dependencies — we use ... because ...",
        "Lines 7-15: Define the noise schedule — this implements Eq. X from the theory section",
        "..."
      ],
      "key_design_decisions": [
        "We use cosine schedule instead of linear because ... (see [paper])",
        "The EMA update rate of 0.9999 balances ..."
      ]
    }}
  ],

  "reference_implementations": [
    "https://github.com/org/repo — Brief description of what this implements"
  ],

  "key_hyperparameters": {{
    "parameter_name": "Typical value and WHY — e.g., 'Learning rate: 2e-4. Lower than standard because the loss landscape of diffusion models is...'",
    "...": "..."
  }},

  "common_pitfalls": [
    "Detailed pitfall description with explanation of why it happens and how to fix it (50+ words each)"
  ],

  "reproduction_checklist": [
    "Step 1: ...",
    "Step 2: ..."
  ]
}}

## Quality requirements
- **Runnable code**: The code should be as close to runnable as possible. Use real APIs, real tensor shapes.
- **Line-by-line analysis**: Every non-trivial block of code must have an annotation explaining the design choice.
- **At least 1 code analysis block** with 50+ lines.
- **At least 5 hyperparameters** with reasoning (not just values).
- **At least 5 common pitfalls** with detailed explanations.
- **Guidance alignment**: Let `chapter_guidance` steer the practice focus, examples, and implementation tradeoffs for this chapter.
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

    async def _fetch_paper_context(self, chapter: Chapter) -> str:
        """Fetch real paper abstracts from S2/arXiv for grounding."""
        query = " ".join(chapter.key_topics[:3]) if chapter.key_topics else chapter.title
        try:
            results = await self.rag.query(query)
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

    def _build_shared_context(
        self,
        chapter: Chapter,
        textbook: Textbook,
        profile: AssessmentProfile,
        paper_context: str,
    ) -> dict[str, str]:
        """Build the shared template variables used across all three prompts."""
        related = []
        for ch in textbook.chapters:
            if ch.id != chapter.id and abs(ch.chapter_number - chapter.chapter_number) <= 2:
                related.append(ch.title)

        key_papers_text = "\n".join(
            f"- {p.title} ({p.arxiv_id or p.doi}, {p.year}, citations: {p.citation_count})"
            for p in textbook.survey_papers[:5]
        ) if textbook.survey_papers else "No specific papers listed - use your knowledge"

        math_level = round(sum([
            profile.math_foundations.linear_algebra.level,
            profile.math_foundations.probability.level,
            profile.math_foundations.calculus.level,
            profile.math_foundations.optimization.level,
        ]) / 4)

        return {
            "concept_name": chapter.title,
            "description": chapter.description,
            "chapter_guidance": chapter.chapter_guidance or "No chapter-specific guidance provided.",
            "course_requirements": textbook.course_requirements or profile.course_requirements or "No course-level requirements provided.",
            "field": textbook.field,
            "key_papers": key_papers_text,
            "paper_context": paper_context,
            "related_concepts": ", ".join(related) if related else "None identified",
            "math_level": str(math_level),
            "learning_goal": profile.learning_goal.value,
            "learning_style": profile.learning_style.value,
        }

    # ------------------------------------------------------------------
    # Individual layer generators
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Content validation helpers
    # ------------------------------------------------------------------

    _MIN_FIELD_CHARS: dict[str, int] = {
        # Minimum acceptable character count per field (prompt asks for 200-500 words)
        "analogy": 400,
        "why_it_matters": 200,
        "key_insight": 150,
        "theoretical_narrative": 500,
        "mathematical_framework": 300,
    }

    @staticmethod
    def _is_content_adequate(resp, min_chars: dict[str, int]) -> bool:
        """Check whether key string fields meet minimum length thresholds."""
        for field, threshold in min_chars.items():
            val = getattr(resp, field, None)
            if isinstance(val, str) and len(val) < threshold:
                logger.warning(
                    "Field '%s' too short: %d chars (min %d)",
                    field, len(val), threshold,
                )
                return False
        return True

    # ------------------------------------------------------------------
    # Individual layer generators (run via asyncio.to_thread for true parallelism)
    # ------------------------------------------------------------------

    async def _generate_mechanism(
        self, ctx: dict[str, str], on_progress: ProgressCallback = None,
    ) -> tuple[MechanismResponse, list[SourceAttribution]]:
        """Generate mechanism layer (call 1 — most important, runs first)."""
        if on_progress:
            await on_progress("Generating mechanism & theory layer (rigorous mathematical derivations)...")

        prompt = _MECHANISM_PROMPT.format(**ctx)
        resp = await asyncio.to_thread(
            self.llm.generate_structured,
            prompt, MechanismResponse, system=_MECHANISM_SYSTEM, temperature=0.2,
        )
        return resp, resp.sources

    async def _generate_intuition(
        self, ctx: dict[str, str], mechanism_summary: str, on_progress: ProgressCallback = None,
        _max_retries: int = 2,
    ) -> IntuitionResponse:
        """Generate intuition layer (call 2 — uses mechanism summary for consistency)."""
        if on_progress:
            await on_progress("Generating intuition & understanding layer (analogies, insights)...")

        ctx_with_mechanism = {**ctx, "mechanism_summary": mechanism_summary}
        prompt = _INTUITION_PROMPT.format(**ctx_with_mechanism)
        checks = {k: v for k, v in self._MIN_FIELD_CHARS.items() if k in IntuitionResponse.model_fields}

        for attempt in range(_max_retries + 1):
            resp = await asyncio.to_thread(
                self.llm.generate_structured,
                prompt, IntuitionResponse, system=_INTUITION_SYSTEM, temperature=0.4,
            )
            if self._is_content_adequate(resp, checks):
                return resp
            if attempt < _max_retries:
                logger.warning("Intuition layer content too short, retrying (%d/%d)...", attempt + 1, _max_retries)
                if on_progress:
                    await on_progress(f"Intuition content too short, retrying ({attempt + 1}/{_max_retries})...")
        logger.warning("Intuition layer still short after %d retries, using best result", _max_retries)
        return resp

    async def _generate_practice(
        self, ctx: dict[str, str], mechanism_summary: str, on_progress: ProgressCallback = None,
    ) -> PracticeResponse:
        """Generate practice layer (call 3 — uses mechanism summary for consistency)."""
        if on_progress:
            await on_progress("Generating practice & implementation layer (code analysis, pitfalls)...")

        ctx_with_mechanism = {**ctx, "mechanism_summary": mechanism_summary}
        prompt = _PRACTICE_PROMPT.format(**ctx_with_mechanism)
        return await asyncio.to_thread(
            self.llm.generate_structured,
            prompt, PracticeResponse, system=_PRACTICE_SYSTEM, temperature=0.2,
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def synthesize(
        self,
        chapter: Chapter,
        textbook: Textbook,
        profile: AssessmentProfile,
        on_progress: ProgressCallback = None,
    ) -> ResearchSynthesis:
        """Generate comprehensive three-layer content for a chapter.

        Pipeline:
          1. Mechanism layer (first, as other layers reference it)
          2. Intuition + Practice layers (in parallel, both use mechanism summary)
        """
        paper_context = await self._fetch_paper_context(chapter)
        ctx = self._build_shared_context(chapter, textbook, profile, paper_context)

        # --- Call 1: Mechanism (must complete first) ---
        if on_progress:
            await on_progress("Starting PhD-level content generation (3 specialized LLM calls)...")

        mechanism_resp, sources = await self._generate_mechanism(ctx, on_progress)

        # Build a short summary of the mechanism layer for the other two prompts
        mechanism_summary = mechanism_resp.mathematical_framework[:500]
        eq_names = [eq.name for eq in mechanism_resp.key_equations[:5]]
        if eq_names:
            mechanism_summary += f"\nKey equations: {', '.join(eq_names)}"

        # --- Calls 2 & 3: Intuition + Practice (parallel) ---
        intuition_resp, practice_resp = await asyncio.gather(
            self._generate_intuition(ctx, mechanism_summary, on_progress),
            self._generate_practice(ctx, mechanism_summary, on_progress),
        )

        if on_progress:
            await on_progress("Assembling final synthesis...")

        # --- Assemble ---
        synthesis = ResearchSynthesis(
            concept_id=chapter.id,
            title=chapter.title,
            intuition=IntuitionLayer(
                analogy=intuition_resp.analogy,
                why_it_matters=intuition_resp.why_it_matters,
                key_insight=intuition_resp.key_insight,
            ),
            mechanism=MechanismLayer(
                theoretical_narrative=mechanism_resp.theoretical_narrative,
                mathematical_framework=mechanism_resp.mathematical_framework,
                key_equations=mechanism_resp.key_equations,
                algorithms=mechanism_resp.algorithms,
                connections=mechanism_resp.connections,
            ),
            practice=PracticeLayer(
                code_analysis=practice_resp.code_analysis,
                reference_implementations=practice_resp.reference_implementations,
                key_hyperparameters=practice_resp.key_hyperparameters,
                common_pitfalls=practice_resp.common_pitfalls,
                reproduction_checklist=practice_resp.reproduction_checklist,
            ),
            sources=sources,
        )

        # Save
        self.store.save_content(chapter.id, "research_synthesis.json", synthesis)
        logger.info("Saved synthesis for chapter %s (%s)", chapter.id, chapter.title)
        return synthesis

    def generate_alternative_explanation(
        self,
        chapter: Chapter,
        previous_synthesis: ResearchSynthesis,
        struggle_areas: list[str] | None = None,
    ) -> ResearchSynthesis:
        """Generate an alternative explanation for Level 1 adaptive intervention."""
        prompt = f"""The student is struggling with the concept "{chapter.title}".

Previous explanation approach:
- Analogy used: {previous_synthesis.intuition.analogy[:200]}
- Key insight: {previous_synthesis.intuition.key_insight[:200]}

{f"Specific areas of confusion: {', '.join(struggle_areas)}" if struggle_areas else ""}

Generate a COMPLETELY DIFFERENT explanation using:
1. A different analogy/metaphor
2. Worked examples instead of abstract definitions
3. Step-by-step walkthrough of a concrete case

Return JSON with keys: "intuition" (with "analogy", "why_it_matters", "key_insight") and "mechanism" (with "pseudocode", "algorithm_steps").
Focus on the intuition and mechanism layers."""

        response = self.llm.generate_json(prompt, system=_INTUITION_SYSTEM)

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
                why_it_matters=intuition_data.get("why_it_matters", alt.intuition.why_it_matters),
                key_insight=intuition_data.get("key_insight", alt.intuition.key_insight),
            )
        if mechanism_data:
            alt.mechanism.pseudocode = mechanism_data.get("pseudocode", alt.mechanism.pseudocode)
            alt.mechanism.algorithm_steps = mechanism_data.get("algorithm_steps", alt.mechanism.algorithm_steps)

        self.store.save_content(chapter.id, "research_synthesis_alt.json", alt)
        return alt
