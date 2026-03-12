"""Workflow orchestrator - wires together skills into the course-based learning loop."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from rich.console import Console

from src.apis.arxiv_client import ArxivClient
from src.apis.crossref import CrossRefClient
from src.apis.github_client import GitHubClient
from src.apis.open_alex import OpenAlexClient
from src.apis.papers_with_code import PapersWithCodeClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.apis.tavily_client import TavilySearchClient
from src.llm.client import LLMClient
from src.models.assessment import AssessmentProfile, LearningGoal, LearningStyle
from src.models.course import Course, CourseStatus
from src.models.textbook import Chapter, ChapterStatus, Textbook
from src.models.progress import LearnerProgress
from src.skills.accuracy_verifier import AccuracyVerifier
from src.skills.adaptive_controller import AdaptiveController
from src.skills.deep_researcher import DeepResearcher
from src.skills.material_integrator import MaterialIntegrator
from src.skills.practice_generator import PracticeGenerator
from src.skills.pre_assessor import PreAssessor
from src.skills.progress_tracker import ProgressTracker
from src.skills.quiz_engine import QuizEngine
from src.skills.resource_curator import ResourceCurator
from src.skills.spaced_repetition import SpacedRepetitionManager
from src.skills.textbook_planner import TextbookPlanner
from src.storage.local_store import LocalStore
from src.logging_config import get_logger

console = Console()
logger = get_logger("orchestrator")


class LearningOrchestrator:
    """Main workflow engine coordinating skills around the course/textbook model."""

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
        self.tavily = TavilySearchClient()

        # Skills
        self.assessor = PreAssessor(self.llm, self.store)
        self.planner = TextbookPlanner(
            self.llm, self.store,
            openalex=self.openalex, arxiv=self.arxiv,
            tavily=self.tavily,
        )
        self.researcher = DeepResearcher(
            self.llm, self.store,
            semantic_scholar=self.s2, arxiv=self.arxiv,
        )
        self.verifier = AccuracyVerifier(
            self.llm, self.store,
            semantic_scholar=self.s2, crossref=self.crossref,
        )
        self.curator = ResourceCurator(
            self.llm, self.store,
            semantic_scholar=self.s2, papers_with_code=self.pwc, github=self.github,
        )
        self.quiz_engine = QuizEngine(self.llm, self.store)
        self.adaptive = AdaptiveController(self.llm, self.store, self.researcher)
        self.spaced_rep = SpacedRepetitionManager(self.llm, self.store)
        self.practice = PracticeGenerator(self.llm, self.store)
        self.tracker = ProgressTracker(self.store)
        self.integrator = MaterialIntegrator(self.store)

    # ── Course management ────────────────────────────────────────────

    def create_course(
        self,
        field: str,
        assessment_data: dict,
    ) -> tuple[Course, AssessmentProfile]:
        """Create a new course: run assessment, register course."""
        import re
        course_id = re.sub(r"[^\w]+", "_", field.lower()).strip("_")

        logger.info("Creating course '%s' (field=%s)", course_id, field)

        # Run assessment
        profile = self.assessor.quick_assess(
            field,
            math_level=assessment_data.get("math_level", 3),
            programming_level=assessment_data.get("programming_level", 3),
            domain_level=assessment_data.get("domain_level", 0),
            learning_goal=LearningGoal(assessment_data.get("learning_goal", "understand_concepts")),
            available_hours=assessment_data.get("available_hours", 10.0),
            learning_style=LearningStyle(assessment_data.get("learning_style", "intuition_first")),
        )

        # Create course directory and save assessment
        self.store.ensure_course_dirs(course_id)
        self.store.save_course_model(course_id, "assessment_profile.json", profile)

        # Create Course record
        course = Course(
            id=course_id,
            title=field,
            status=CourseStatus.CREATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.store.save_course_model(course_id, "course.json", course)

        # Update registry
        registry = self.store.load_courses_registry()
        registry.append(course.model_dump(mode="json"))
        self.store.save_courses_registry(registry)

        return course, profile

    def list_courses(self) -> list[dict]:
        """List all courses from registry."""
        return self.store.load_courses_registry()

    def get_course(self, course_id: str) -> Course | None:
        """Load a course record."""
        return self.store.load_course_model(course_id, "course.json", Course)

    def delete_course(self, course_id: str) -> bool:
        """Delete a course and remove from registry."""
        success = self.store.delete_course(course_id)
        if success:
            registry = self.store.load_courses_registry()
            registry = [c for c in registry if c.get("id") != course_id]
            self.store.save_courses_registry(registry)
        return success

    # ── Assessment ───────────────────────────────────────────────────

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
        logger.info("Phase 1: Assessment — field=%s, quick=%s", field, quick)

        goal = LearningGoal(learning_goal)
        style = LearningStyle(learning_style)

        profile = self.assessor.quick_assess(
            field, math_level, programming_level, domain_level,
            goal, available_hours, style,
        )

        return profile

    # ── Textbook outline ─────────────────────────────────────────────

    async def build_outline(
        self,
        course_id: str,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> Textbook:
        """Phase 2: Build textbook outline for a course."""
        profile = self.store.load_course_model(
            course_id, "assessment_profile.json", AssessmentProfile
        )
        if not profile:
            raise ValueError(f"No assessment profile for course '{course_id}'")

        logger.info("Phase 2: Building textbook outline for '%s'", course_id)

        textbook = await self.planner.generate_outline(
            course_id, profile, on_progress=on_progress,
        )

        # Update course status
        course = self.get_course(course_id)
        if course:
            course.status = CourseStatus.OUTLINE_READY
            course.total_chapters = len(textbook.chapters)
            course.updated_at = datetime.now()
            self.store.save_course_model(course_id, "course.json", course)
            self._update_registry(course)

        # Initialize progress
        self.tracker.initialize_from_textbook(textbook)

        return textbook

    # ── Chapter content generation ───────────────────────────────────

    async def generate_chapter(
        self,
        course_id: str,
        chapter_id: str,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> dict:
        """Generate content for a single chapter (5-step pipeline)."""
        textbook = self.store.load_course_model(course_id, "textbook.json", Textbook)
        if not textbook:
            raise ValueError(f"No textbook for course '{course_id}'")

        chapter = textbook.get_chapter(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter '{chapter_id}' not found")

        profile = self.store.load_course_model(
            course_id, "assessment_profile.json", AssessmentProfile
        )
        if not profile:
            raise ValueError(f"No assessment for course '{course_id}'")

        def _emit(step: str, msg: str) -> None:
            logger.info("generate_chapter [%s] %s", step, msg)
            if on_progress:
                on_progress(step, msg)

        progress = self.tracker.get_or_create_progress(textbook.field)
        self.tracker.start_chapter(progress, chapter_id)

        # Update chapter status
        chapter.status = ChapterStatus.GENERATING
        textbook.updated_at = datetime.now()
        self.store.save_course_model(course_id, "textbook.json", textbook)

        # Step 1: Deep Research (3 specialized LLM calls)
        _emit("deep_research", f"正在生成三层内容：{chapter.title}")

        async def _researcher_progress(msg: str) -> None:
            _emit("deep_research", msg)

        synthesis = await self.researcher.synthesize(
            chapter, textbook, profile, on_progress=_researcher_progress
        )
        self.store.save_course_content(course_id, chapter_id, "research_synthesis.json", synthesis)

        # Step 2: Accuracy Verification
        _emit("accuracy_verify", "正在核验内容准确性…")
        report = await self.verifier.verify(synthesis)
        self.store.save_course_content(course_id, chapter_id, "verification_report.json", report)

        # Step 3: Resource Curation
        _emit("resource_curate", "正在搜索推荐资源…")
        resources = await self.curator.curate(chapter, profile)
        self.store.save_course_content(course_id, chapter_id, "resources.json", resources)

        # Step 4: Quiz Generation
        _emit("quiz_generate", "正在生成测验题目…")
        prev_scores_cp = progress.concepts.get(chapter_id, None)
        prev = prev_scores_cp.quiz_scores if prev_scores_cp else None
        quiz = self.quiz_engine.generate_quiz(synthesis, profile, prev)
        self.store.save_course_content(course_id, chapter_id, "quiz.json", quiz)

        # Step 5: Practice Materials
        _emit("practice_generate", "正在生成练习材料…")
        if profile.learning_goal == LearningGoal.REPRODUCE:
            self.practice.generate_reproduction_guide(synthesis)
        self.practice.generate_coding_challenge(synthesis, profile)

        # Update chapter status
        chapter.status = ChapterStatus.READY
        chapter.has_content = True
        textbook.updated_at = datetime.now()
        self.store.save_course_model(course_id, "textbook.json", textbook)

        _emit("complete", f"章节 '{chapter.title}' 生成完毕")

        return {
            "chapter_id": chapter_id,
            "synthesis": synthesis,
            "verification": report,
            "resources": resources,
            "quiz": quiz,
            "status": "ready",
        }

    async def generate_all_chapters(
        self,
        course_id: str,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> None:
        """Generate content for all pending chapters in order."""
        textbook = self.store.load_course_model(course_id, "textbook.json", Textbook)
        if not textbook:
            raise ValueError(f"No textbook for course '{course_id}'")

        # Update course status
        course = self.get_course(course_id)
        if course:
            course.status = CourseStatus.GENERATING
            course.updated_at = datetime.now()
            self.store.save_course_model(course_id, "course.json", course)

        pending = [ch for ch in textbook.chapters if ch.status == ChapterStatus.PENDING]
        total = len(pending)
        for i, chapter in enumerate(pending, 1):
            if on_progress:
                on_progress("batch_progress", f"[{i}/{total}] 正在生成: {chapter.title}")
            await self.generate_chapter(course_id, chapter.id, on_progress)

        # Update course status
        if course:
            course.status = CourseStatus.ACTIVE
            course.updated_at = datetime.now()
            self.store.save_course_model(course_id, "course.json", course)
            self._update_registry(course)

    # ── Quiz processing ──────────────────────────────────────────────

    async def process_quiz_result(
        self,
        course_id: str,
        chapter_id: str,
        answers: dict[str, str | int],
    ) -> dict:
        """Process quiz answers and trigger adaptive intervention if needed."""
        from src.models.quiz import Quiz
        from src.models.content import ResearchSynthesis

        textbook = self.store.load_course_model(course_id, "textbook.json", Textbook)
        if not textbook:
            return {"error": f"No textbook for course '{course_id}'"}

        chapter = textbook.get_chapter(chapter_id)
        if not chapter:
            return {"error": f"Chapter '{chapter_id}' not found"}

        quiz = self.store.load_course_content(course_id, chapter_id, "quiz.json", Quiz)
        if not quiz:
            quiz = self.store.load_content(chapter_id, "quiz.json", Quiz)
        if not quiz:
            return {"error": "No quiz found for this chapter"}

        # Evaluate
        result = self.quiz_engine.evaluate_answers(quiz, answers)
        progress = self.tracker.get_or_create_progress(textbook.field)
        self.tracker.record_quiz_result(progress, result)

        if result.passed:
            synthesis = self.store.load_course_content(
                course_id, chapter_id, "research_synthesis.json", ResearchSynthesis
            )
            if synthesis:
                cards = self.spaced_rep.generate_cards(synthesis)
                console.print(f"[green]Passed! Generated {len(cards)} flashcards.[/green]")

            chapter.status = ChapterStatus.COMPLETED
            chapter.mastery = result.overall_score
            chapter.quiz_score = result.overall_score
            textbook.updated_at = datetime.now()
            self.store.save_course_model(course_id, "textbook.json", textbook)

            course = self.get_course(course_id)
            if course:
                course.completed_chapters = sum(
                    1 for ch in textbook.chapters if ch.status == ChapterStatus.COMPLETED
                )
                course.updated_at = datetime.now()
                self.store.save_course_model(course_id, "course.json", course)
                self._update_registry(course)

            next_ch = textbook.get_chapter_by_number(chapter.chapter_number + 1)
            return {
                "status": "passed",
                "score": result.overall_score,
                "next_chapter": next_ch.id if next_ch else None,
            }
        else:
            cp = progress.concepts.get(chapter_id)
            bkt_state = cp.bkt_state if cp else None
            level = self.adaptive.determine_level(result, chapter, bkt_state)

            synthesis = self.store.load_course_content(
                course_id, chapter_id, "research_synthesis.json", ResearchSynthesis
            )
            profile = self.store.load_course_model(
                course_id, "assessment_profile.json", AssessmentProfile
            )
            intervention = self.adaptive.intervene(
                level, chapter, textbook, result, synthesis, profile
            )
            return {
                "status": "needs_intervention",
                "score": result.overall_score,
                "intervention": intervention,
            }

    # ── Export ────────────────────────────────────────────────────────

    async def export_materials(
        self,
        course_id: str,
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        """Export learning materials in specified formats."""
        formats = formats or ["obsidian"]
        textbook = self.store.load_course_model(course_id, "textbook.json", Textbook)
        if not textbook:
            raise ValueError(f"No textbook for course '{course_id}'")

        progress = self.tracker.get_or_create_progress(textbook.field)
        results = {}

        if "obsidian" in formats:
            path = self.integrator.export_obsidian(textbook, progress)
            results["obsidian"] = path

        if "anki" in formats:
            path = self.spaced_rep.export_anki(textbook.field)
            results["anki"] = path

        if "pdf" in formats:
            path = self.integrator.export_pdf(textbook)
            if path:
                results["pdf"] = path

        return results

    # ── Review & Progress ────────────────────────────────────────────

    def get_weekly_report(self, field: str) -> str:
        """Generate and return weekly progress report."""
        progress = self.tracker.get_or_create_progress(field)
        return self.tracker.generate_weekly_report(progress)

    def get_due_reviews(self, concept_id: str | None = None) -> list:
        """Get all flashcards due for review."""
        return self.spaced_rep.get_due_cards(concept_id)

    # ── Helpers ───────────────────────────────────────────────────────

    def _update_registry(self, course: Course) -> None:
        """Update a single course entry in the registry."""
        registry = self.store.load_courses_registry()
        for i, entry in enumerate(registry):
            if entry.get("id") == course.id:
                registry[i] = course.model_dump(mode="json")
                break
        self.store.save_courses_registry(registry)

    async def cleanup(self) -> None:
        """Close all API clients."""
        await self.s2.close()
        await self.arxiv.close()
        await self.crossref.close()
        await self.openalex.close()
        await self.pwc.close()
        await self.github.close()
