from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from src.models.assessment import AssessmentProfile
from src.models.course import Course
from src.models.progress import LearnerProgress
from src.models.progress import ConceptProgress
from src.models.textbook import Chapter, PaperReference, Textbook
from src.orchestrator import LearningOrchestrator
from src.skills.deep_researcher import DeepResearcher
from src.skills.textbook_planner import TextbookPlanner
from src.storage.local_store import LocalStore


class _DummyLLM:
    def __init__(self, response: str = "[]") -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
        self.prompts.append(prompt)
        return self.response


def _workspace_temp_dir(name: str) -> Path:
    base_dir = Path(".tmp") / "textbook_guidance_tests"
    target = base_dir / f"{name}_{uuid4().hex}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_textbook_and_chapter_guidance_defaults() -> None:
    chapter = Chapter(id="ch01_foundations", chapter_number=1, title="Foundations")
    textbook = Textbook(course_id="diffusion_models", field="Diffusion Models", title="Guide")

    assert chapter.chapter_guidance == ""
    assert textbook.course_requirements == ""


def test_textbook_planner_includes_course_requirements_and_chapter_guidance() -> None:
    tmp_path = _workspace_temp_dir("planner")
    store = LocalStore(tmp_path / "data")
    llm = _DummyLLM(
        json.dumps([
            {
                "chapter_number": 1,
                "title": "Foundations",
                "description": "Build the core intuition and notation.",
                "chapter_guidance": "Use this opening chapter to translate the course's practice-first requirement into shared intuition, terminology, and simple image-generation examples.",
                "difficulty": 2,
                "estimated_hours": 3.0,
                "key_topics": ["notation", "intuition"],
                "tags": ["foundation"],
            }
        ])
    )
    planner = TextbookPlanner(llm=llm, store=store)

    async def _empty_results(field: str) -> list[dict]:
        return []

    planner._search_web = _empty_results  # type: ignore[method-assign]
    planner._search_surveys = _empty_results  # type: ignore[method-assign]
    planner._search_key_papers = _empty_results  # type: ignore[method-assign]

    profile = AssessmentProfile(
        target_field="Diffusion Models",
        course_requirements="Emphasize image-generation practice and reduce pure mathematical proofs.",
    )

    import asyncio

    textbook = asyncio.run(planner.generate_outline("diffusion_models", profile))

    assert profile.course_requirements in llm.prompts[0]
    assert textbook.course_requirements == profile.course_requirements
    assert textbook.chapters[0].chapter_guidance.startswith("Use this opening chapter")


def test_deep_researcher_shared_context_includes_guidance_fields() -> None:
    tmp_path = _workspace_temp_dir("researcher")
    store = LocalStore(tmp_path / "data")
    researcher = DeepResearcher(llm=_DummyLLM(), store=store)
    chapter = Chapter(
        id="ch01_foundations",
        chapter_number=1,
        title="Foundations",
        description="Core setup",
        chapter_guidance="Focus this chapter on intuitive setup and lightweight examples.",
    )
    textbook = Textbook(
        course_id="diffusion_models",
        field="Diffusion Models",
        course_requirements="Prioritize practice over long proofs.",
        title="Diffusion Models: from theory to practice",
        chapters=[
            chapter,
            Chapter(id="ch02_training", chapter_number=2, title="Training", description="Optimization"),
        ],
        survey_papers=[
            PaperReference(title="A Survey", year=2024, citation_count=12, role="survey"),
        ],
    )
    profile = AssessmentProfile(target_field="Diffusion Models")

    ctx = researcher._build_shared_context(
        chapter=chapter,
        textbook=textbook,
        profile=profile,
        paper_context="paper context",
    )

    assert ctx["course_requirements"] == "Prioritize practice over long proofs."
    assert ctx["chapter_guidance"] == "Focus this chapter on intuitive setup and lightweight examples."


def test_update_chapter_guidance_updates_only_target_chapter() -> None:
    tmp_path = _workspace_temp_dir("update_guidance")
    store = LocalStore(tmp_path / "data")
    textbook = Textbook(
        course_id="diffusion_models",
        field="Diffusion Models",
        title="Diffusion Models",
        chapters=[
            Chapter(id="ch01_foundations", chapter_number=1, title="Foundations"),
            Chapter(id="ch02_training", chapter_number=2, title="Training"),
        ],
    )
    store.ensure_course_dirs("diffusion_models")
    store.save_course_model("diffusion_models", "textbook.json", textbook)

    orch = LearningOrchestrator.__new__(LearningOrchestrator)
    orch.store = store

    updated = LearningOrchestrator.update_chapter_guidance(
        orch,
        "diffusion_models",
        "ch02_training",
        "Focus on optimization tradeoffs and implementation pitfalls.",
    )

    assert updated.chapters[0].chapter_guidance == ""
    assert updated.chapters[1].chapter_guidance == "Focus on optimization tradeoffs and implementation pitfalls."

    persisted = store.load_course_model("diffusion_models", "textbook.json", Textbook)
    assert persisted is not None
    assert persisted.chapters[1].chapter_guidance == "Focus on optimization tradeoffs and implementation pitfalls."


def test_create_course_saves_course_requirements() -> None:
    tmp_path = _workspace_temp_dir("create_course")
    store = LocalStore(tmp_path / "data")
    profile = AssessmentProfile(target_field="Diffusion Models")

    class _Assessor:
        def quick_assess(self, *args, **kwargs) -> AssessmentProfile:
            return profile.model_copy(deep=True)

    orch = LearningOrchestrator.__new__(LearningOrchestrator)
    orch.store = store
    orch.assessor = _Assessor()

    course, saved_profile = LearningOrchestrator.create_course(
        orch,
        "Diffusion Models",
        {
            "course_requirements": "Emphasize image-generation practice and implementation tradeoffs.",
            "math_level": 3,
            "programming_level": 3,
            "domain_level": 1,
            "learning_goal": "understand_concepts",
            "available_hours": 10.0,
            "learning_style": "intuition_first",
        },
    )

    assert course.description == "Emphasize image-generation practice and implementation tradeoffs."
    assert saved_profile.course_requirements == "Emphasize image-generation practice and implementation tradeoffs."

    persisted = store.load_course_model("diffusion_models", "assessment_profile.json", AssessmentProfile)
    assert persisted is not None
    assert persisted.course_requirements == "Emphasize image-generation practice and implementation tradeoffs."


def test_update_course_resets_previous_outline_artifacts() -> None:
    tmp_path = _workspace_temp_dir("update_course")
    store = LocalStore(tmp_path / "data")
    previous_textbook = Textbook(
        course_id="diffusion_models",
        field="Diffusion Models",
        title="Old Outline",
        chapters=[
            Chapter(id="ch01_foundations", chapter_number=1, title="Foundations"),
        ],
    )
    store.ensure_course_dirs("diffusion_models")
    store.save_course_model(
        "diffusion_models",
        "course.json",
        Course(
            id="diffusion_models",
            title="Diffusion Models",
            description="old requirements",
        ),
    )
    store.save_course_model("diffusion_models", "assessment_profile.json", AssessmentProfile(target_field="Diffusion Models"))
    store.save_course_model("diffusion_models", "textbook.json", previous_textbook)
    store.save_progress(
        LearnerProgress(
            field="Diffusion Models",
            concepts={
                "ch01_foundations": ConceptProgress(
                    concept_id="ch01_foundations",
                    status="completed",
                ),
            },
        )
    )
    legacy_content = store.data_dir / "content" / "ch01_foundations"
    legacy_content.mkdir(parents=True, exist_ok=True)
    (legacy_content / "research_synthesis.json").write_text("{}", encoding="utf-8")

    profile = AssessmentProfile(target_field="Diffusion Models")

    class _Assessor:
        def quick_assess(self, *args, **kwargs) -> AssessmentProfile:
            return profile.model_copy(deep=True)

    orch = LearningOrchestrator.__new__(LearningOrchestrator)
    orch.store = store
    orch.assessor = _Assessor()

    updated_course, updated_profile = LearningOrchestrator.update_course(
        orch,
        "diffusion_models",
        {
            "field": "Diffusion Models",
            "course_requirements": "New course requirements",
            "math_level": 4,
            "programming_level": 4,
            "domain_level": 2,
            "learning_goal": "understand_concepts",
            "available_hours": 12.0,
            "learning_style": "intuition_first",
        },
    )

    assert updated_course.status.value == "created"
    assert updated_course.description == "New course requirements"
    assert updated_profile.course_requirements == "New course requirements"
    assert not (store.get_course_dir("diffusion_models") / "textbook.json").exists()
    assert not legacy_content.exists()

    progress = store.load_progress(LearnerProgress)
    assert progress is not None
    assert "ch01_foundations" not in progress.concepts
