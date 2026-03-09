"""Workflow orchestrator - wires together all 12 skills into the main learning loop."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

from src.apis.arxiv_client import ArxivClient
from src.apis.crossref import CrossRefClient
from src.apis.github_client import GitHubClient
from src.apis.open_alex import OpenAlexClient
from src.apis.papers_with_code import PapersWithCodeClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.llm.client import LLMClient
from src.models.assessment import AssessmentProfile, LearningGoal, LearningStyle
from src.models.knowledge_graph import ConceptStatus, KnowledgeGraph
from src.models.progress import LearnerProgress
from src.skills.accuracy_verifier import AccuracyVerifier
from src.skills.adaptive_controller import AdaptiveController, AdaptiveLevel
from src.skills.deep_researcher import DeepResearcher
from src.skills.domain_mapper import DomainMapper
from src.skills.material_integrator import MaterialIntegrator
from src.skills.path_visualizer import PathVisualizer
from src.skills.practice_generator import PracticeGenerator
from src.skills.pre_assessor import PreAssessor
from src.skills.progress_tracker import ProgressTracker
from src.skills.quiz_engine import QuizEngine
from src.skills.resource_curator import ResourceCurator
from src.skills.spaced_repetition import SpacedRepetitionManager
from src.storage.local_store import LocalStore
from src.logging_config import get_logger

console = Console()
logger = get_logger("orchestrator")


class LearningOrchestrator:
    """Main workflow engine coordinating all 12 skills."""

    def __init__(
        self,
        data_dir: str = "data",
        api_key: str | None = None,
        s2_api_key: str | None = None,
        github_token: str | None = None,
        llm_model: str = "claude-sonnet-4-20250514",
    ):
        self.store = LocalStore(data_dir)
        logger.info("Orchestrator init: data_dir=%s, model=%s", data_dir, llm_model)
        self.llm = LLMClient(api_key=api_key, model=llm_model)

        # API clients
        cache_dir = self.store.cache_dir
        self.s2 = SemanticScholarClient(api_key=s2_api_key, cache_dir=cache_dir)
        self.arxiv = ArxivClient(cache_dir=cache_dir)
        self.crossref = CrossRefClient(cache_dir=cache_dir)
        self.openalex = OpenAlexClient(cache_dir=cache_dir)
        self.pwc = PapersWithCodeClient(cache_dir=cache_dir)
        self.github = GitHubClient(token=github_token, cache_dir=cache_dir)

        # Skills
        self.assessor = PreAssessor(self.llm, self.store)
        self.mapper = DomainMapper(
            self.llm, self.store,
            semantic_scholar=self.s2, arxiv=self.arxiv, open_alex=self.openalex,
        )
        self.visualizer = PathVisualizer(self.store)
        self.researcher = DeepResearcher(self.llm, self.store)
        self.verifier = AccuracyVerifier(
            self.llm, self.store,
            semantic_scholar=self.s2, crossref=self.crossref,
        )
        self.curator = ResourceCurator(
            self.llm, self.store,
            semantic_scholar=self.s2, papers_with_code=self.pwc, github=self.github,
        )
        self.quiz_engine = QuizEngine(self.llm, self.store)
        self.adaptive = AdaptiveController(self.llm, self.store, self.researcher, self.mapper)
        self.spaced_rep = SpacedRepetitionManager(self.llm, self.store)
        self.practice = PracticeGenerator(self.llm, self.store)
        self.tracker = ProgressTracker(self.store)
        self.integrator = MaterialIntegrator(self.store)

    async def run_assessment(
        self,
        field: str,
        quick: bool = False,
        math_level: int = 3,
        programming_level: int = 3,
        domain_level: int = 0,
        learning_goal: str = "understand_concepts",
        available_hours: float = 10.0,
        learning_style: str = "intuition_first",
    ) -> AssessmentProfile:
        """Phase 1: Run user assessment."""
        logger.info("Phase 1: Assessment — field=%s, quick=%s, goal=%s, style=%s", field, quick, learning_goal, learning_style)
        console.print(Panel(f"[bold]Phase 1: Assessment for '{field}'[/bold]"))

        goal = LearningGoal(learning_goal)
        style = LearningStyle(learning_style)

        if quick:
            profile = self.assessor.quick_assess(
                field, math_level, programming_level, domain_level,
                goal, available_hours, style,
            )
            console.print("[green]Quick assessment complete.[/green]")
        else:
            questions = self.assessor.generate_diagnostic_questions(field)
            console.print(f"Generated {len(questions)} diagnostic questions.")
            # In CLI mode, questions would be presented interactively
            # For now, return the profile with default values
            profile = self.assessor.quick_assess(
                field, math_level, programming_level, domain_level,
                goal, available_hours, style,
            )

        return profile

    async def build_knowledge_graph(
        self,
        profile: AssessmentProfile,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> KnowledgeGraph:
        """Phase 2: Build knowledge graph.

        Args:
            profile: Assessment profile.
            on_progress: Optional ``(step_id, message)`` callback for live
                progress updates (used by SSE route).
        """
        logger.info("Phase 2: Building knowledge graph for '%s'", profile.target_field)
        console.print(Panel(f"[bold]Phase 2: Building Knowledge Graph for '{profile.target_field}'[/bold]"))

        graph = await self.mapper.build_graph(profile, on_progress=on_progress)
        logger.info("Knowledge graph built: %d concepts, %d edges", len(graph.nodes), len(graph.edges))
        console.print(f"[green]Knowledge graph built: {len(graph.nodes)} concepts, "
                      f"{len(graph.edges)} edges[/green]")

        # Initialize progress
        progress = self.tracker.initialize_from_graph(graph)

        # Generate visualization
        html_path = self.visualizer.generate_html(graph, progress)
        md_overview = self.visualizer.generate_markdown(graph, progress)
        console.print(f"Visualization saved to: {html_path}")
        console.print(md_overview)

        return graph

    async def learn_concept(
        self,
        concept_id: str,
        graph: KnowledgeGraph,
        profile: AssessmentProfile,
    ) -> dict:
        """Phase 3: Learn a single concept (main concept loop iteration)."""
        concept = graph.get_node(concept_id)
        if not concept:
            logger.warning("Concept '%s' not found in graph", concept_id)
            return {"error": f"Concept '{concept_id}' not found"}

        progress = self.tracker.get_or_create_progress(graph.field)
        self.tracker.start_concept(progress, concept_id)

        logger.info("Phase 3: Learning concept '%s' (%s)", concept_id, concept.name)
        console.print(Panel(f"[bold]Learning: {concept.name}[/bold]"))

        # Step 1: Deep Research
        logger.info("  Step 1/5: Deep research for '%s'", concept_id)
        console.print("  [1/5] Generating content...")
        synthesis = self.researcher.synthesize(concept, graph, profile)

        # Step 2: Accuracy Verification
        logger.info("  Step 2/5: Accuracy verification for '%s'", concept_id)
        console.print("  [2/5] Verifying accuracy...")
        report = await self.verifier.verify(synthesis)
        if report.needs_human_review:
            console.print(f"  [yellow]Warning: Hallucination risk {report.hallucination_risk_score:.0%}. "
                         f"Flagged items: {len(report.flagged_items)}[/yellow]")

        # Step 3: Resource Curation
        logger.info("  Step 3/5: Resource curation for '%s'", concept_id)
        console.print("  [3/5] Curating resources...")
        resources = await self.curator.curate(concept, profile)
        console.print(f"  Found {resources.total_resources} resources")

        # Step 4: Generate Quiz
        logger.info("  Step 4/5: Quiz generation for '%s'", concept_id)
        console.print("  [4/5] Generating quiz...")
        prev_scores = progress.concepts.get(concept_id, None)
        prev = prev_scores.quiz_scores if prev_scores else None
        quiz = self.quiz_engine.generate_quiz(synthesis, profile, prev)

        # Step 5: Generate practice materials
        logger.info("  Step 5/5: Practice materials for '%s'", concept_id)
        console.print("  [5/5] Generating practice materials...")
        if profile.learning_goal == LearningGoal.REPRODUCE:
            self.practice.generate_reproduction_guide(synthesis)
        self.practice.generate_coding_challenge(synthesis, profile)

        return {
            "concept_id": concept_id,
            "synthesis": synthesis,
            "verification": report,
            "resources": resources,
            "quiz": quiz,
            "status": "ready_for_quiz",
        }

    async def process_quiz_result(
        self,
        concept_id: str,
        graph: KnowledgeGraph,
        profile: AssessmentProfile,
        answers: dict[str, str | int],
    ) -> dict:
        """Process quiz answers and trigger adaptive intervention if needed."""
        from src.models.quiz import Quiz
        quiz = self.store.load_content(concept_id, "quiz.json", Quiz)
        if not quiz:
            return {"error": "No quiz found for this concept"}

        # Evaluate
        result = self.quiz_engine.evaluate_answers(quiz, answers)
        progress = self.tracker.get_or_create_progress(graph.field)
        self.tracker.record_quiz_result(progress, result)

        concept = graph.get_node(concept_id)
        if not concept:
            return {"error": f"Concept '{concept_id}' not found"}

        console.print(f"Quiz score: {result.overall_score:.0%}")

        if result.passed:
            # Generate flashcards
            synthesis = self.store.load_content(
                concept_id, "research_synthesis.json",
                type("RS", (), {"model_validate_json": lambda s: None})  # placeholder
            )
            from src.models.content import ResearchSynthesis
            synthesis = self.store.load_content(concept_id, "research_synthesis.json", ResearchSynthesis)
            if synthesis:
                cards = self.spaced_rep.generate_cards(synthesis)
                console.print(f"[green]Passed! Generated {len(cards)} flashcards.[/green]")

            self.mapper.update_node_status(graph, concept_id, ConceptStatus.COMPLETED, result.overall_score)

            return {
                "status": "passed",
                "score": result.overall_score,
                "next_concept": self._get_next_concept(graph),
            }
        else:
            # Determine adaptive intervention
            level = self.adaptive.determine_level(result, concept)
            synthesis = self.store.load_content(concept_id, "research_synthesis.json",
                                                 __import__("src.models.content", fromlist=["ResearchSynthesis"]).ResearchSynthesis)
            intervention = self.adaptive.intervene(
                level, concept, graph, result, synthesis, profile
            )
            console.print(f"[yellow]Intervention: {intervention['action']}[/yellow]")
            return {
                "status": "needs_intervention",
                "score": result.overall_score,
                "intervention": intervention,
            }

    def _get_next_concept(self, graph: KnowledgeGraph) -> str | None:
        """Get the next concept to learn from the learning path."""
        for concept_id in graph.learning_path:
            node = graph.get_node(concept_id)
            if node and node.status == ConceptStatus.PENDING:
                return concept_id
        return None

    async def export_materials(
        self,
        graph: KnowledgeGraph,
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        """Export learning materials in specified formats."""
        formats = formats or ["obsidian"]
        progress = self.tracker.get_or_create_progress(graph.field)
        results = {}

        if "obsidian" in formats:
            path = self.integrator.export_obsidian(graph, progress)
            results["obsidian"] = path
            console.print(f"[green]Obsidian vault exported to: {path}[/green]")

        if "anki" in formats:
            path = self.spaced_rep.export_anki(graph.field)
            results["anki"] = path
            console.print(f"[green]Anki deck exported to: {path}[/green]")

        if "html" in formats:
            path = self.visualizer.generate_html(graph, progress)
            results["html"] = path

        if "pdf" in formats:
            path = self.integrator.export_pdf(graph)
            if path:
                results["pdf"] = path

        return results

    def get_weekly_report(self, field: str) -> str:
        """Generate and return weekly progress report."""
        progress = self.tracker.get_or_create_progress(field)
        return self.tracker.generate_weekly_report(progress)

    def get_due_reviews(self) -> list:
        """Get all flashcards due for review."""
        return self.spaced_rep.get_due_cards()

    async def cleanup(self) -> None:
        """Close all API clients."""
        await self.s2.close()
        await self.arxiv.close()
        await self.crossref.close()
        await self.openalex.close()
        await self.pwc.close()
        await self.github.close()
