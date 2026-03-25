"""Tests for export material integration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.content import IntuitionLayer, MechanismLayer, PracticeLayer, ResearchSynthesis
from src.models.quiz import BloomLevel, Question, QuestionType, Quiz
from src.models.resources import Resource, ResourceCollection, ResourceType
from src.models.textbook import Chapter, Textbook
from src.orchestrator import LearningOrchestrator
from src.skills.material_integrator import MaterialIntegrator
from src.storage.local_store import LocalStore


def _build_textbook() -> Textbook:
    return Textbook(
        course_id="course_export",
        field="Diffusion Models",
        title="Diffusion Models Guide",
        chapters=[
            Chapter(
                id="ch01_intro",
                chapter_number=1,
                title="Intro/Chapter",
                description="Foundations of the topic.",
            )
        ],
    )


def _save_course_content(store: LocalStore, textbook: Textbook) -> None:
    chapter = textbook.chapters[0]
    synthesis = ResearchSynthesis(
        concept_id=chapter.id,
        title=chapter.title,
        intuition=IntuitionLayer(
            analogy="Like restoring a noisy image step by step.",
            key_insight="Noise removal can be learned as a reverse process.",
            why_it_matters="This lets us generate high-quality samples.",
        ),
        mechanism=MechanismLayer(
            mathematical_framework="x_t = alpha_t * x_0 + sigma_t * epsilon",
            algorithm_steps=["Sample noise", "Predict clean signal"],
        ),
        practice=PracticeLayer(
            reference_implementations=["https://github.com/example/diffusion"],
            common_pitfalls=["Using an unstable noise schedule."],
            reproduction_checklist=["Verify the sampler settings."],
        ),
    )
    resources = ResourceCollection(
        concept_id=chapter.id,
        papers=[
            Resource(
                url="https://arxiv.org/abs/2006.11239",
                title="DDPM",
                resource_type=ResourceType.PAPER,
            )
        ],
    )
    quiz = Quiz(
        id="quiz_1",
        concept_id=chapter.id,
        questions=[
            Question(
                id="q1",
                question_type=QuestionType.MULTIPLE_CHOICE,
                bloom_level=BloomLevel.UNDERSTAND,
                question="What does the reverse process learn?",
                difficulty=2,
                concept_id=chapter.id,
                options=["A denoising transition", "A sorting rule"],
            )
        ],
    )

    store.save_course_content(textbook.course_id, chapter.id, "research_synthesis.json", synthesis)
    store.save_course_content(textbook.course_id, chapter.id, "resources.json", resources)
    store.save_course_content(textbook.course_id, chapter.id, "quiz.json", quiz)


def _workspace_temp_dir(name: str) -> Path:
    base_dir = Path(".tmp") / "material_integrator_tests"
    target = base_dir / f"{name}_{uuid4().hex}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_resolve_reportlab_cjk_font_returns_registered_font() -> None:
    from reportlab.pdfbase import pdfmetrics

    font_name = MaterialIntegrator._resolve_reportlab_cjk_font()

    assert font_name
    assert font_name in pdfmetrics.getRegisteredFontNames()


def test_export_obsidian_uses_course_scoped_content() -> None:
    tmp_path = _workspace_temp_dir("obsidian")
    store = LocalStore(tmp_path / "data")
    textbook = _build_textbook()
    _save_course_content(store, textbook)
    integrator = MaterialIntegrator(store)

    vault_path = integrator.export_obsidian(textbook, output_dir=tmp_path / "output" / "obsidian")
    chapter_path = vault_path / "chapters" / "Intro-Chapter.md"

    assert vault_path.exists()
    assert chapter_path.exists()
    chapter_text = chapter_path.read_text(encoding="utf-8")
    assert "Noise removal can be learned as a reverse process." in chapter_text
    assert "DDPM" in chapter_text


def test_export_html_writes_file_with_actual_content() -> None:
    tmp_path = _workspace_temp_dir("html")
    store = LocalStore(tmp_path / "data")
    textbook = _build_textbook()
    _save_course_content(store, textbook)
    integrator = MaterialIntegrator(store)

    html_path = integrator.export_html(textbook, output_dir=tmp_path / "output" / "html")

    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "Diffusion Models Guide" in html
    assert "Self-Assessment" in html
    assert "What does the reverse process learn?" in html


@pytest.mark.asyncio
async def test_orchestrator_export_materials_returns_items_and_errors() -> None:
    tmp_path = _workspace_temp_dir("orchestrator")
    textbook = _build_textbook()

    def _raise_pdf_error(_textbook: Textbook) -> Path:
        raise RuntimeError("reportlab not installed")

    orch = LearningOrchestrator.__new__(LearningOrchestrator)
    orch.store = SimpleNamespace(
        load_course_model=lambda course_id, relative_path, model_class: textbook
    )
    orch.tracker = SimpleNamespace(get_or_create_progress=lambda field: object())
    orch.integrator = SimpleNamespace(
        export_obsidian=lambda export_textbook, progress: tmp_path / "vault",
        export_html=lambda export_textbook: tmp_path / "guide.html",
        export_pdf=_raise_pdf_error,
    )
    orch.spaced_rep = SimpleNamespace(export_anki=lambda field_name: tmp_path / "cards.apkg")

    result = await LearningOrchestrator.export_materials(
        orch,
        textbook.course_id,
        ["html", "pdf"],
    )

    assert result["items"]["html"] == (tmp_path / "guide.html").resolve()
    assert "pdf" in result["errors"]
    assert "reportlab not installed" in result["errors"]["pdf"]


@pytest.mark.asyncio
async def test_orchestrator_export_materials_raises_when_everything_fails() -> None:
    textbook = _build_textbook()

    orch = LearningOrchestrator.__new__(LearningOrchestrator)
    orch.store = SimpleNamespace(
        load_course_model=lambda course_id, relative_path, model_class: textbook
    )
    orch.tracker = SimpleNamespace(get_or_create_progress=lambda field: object())
    orch.integrator = SimpleNamespace(
        export_obsidian=lambda export_textbook, progress: Path("unused"),
        export_html=lambda export_textbook: Path("unused"),
        export_pdf=lambda export_textbook: (_ for _ in ()).throw(RuntimeError("pdf failed")),
    )
    orch.spaced_rep = SimpleNamespace(
        export_anki=lambda field_name: (_ for _ in ()).throw(RuntimeError("anki failed"))
    )

    with pytest.raises(ValueError, match="pdf failed"):
        await LearningOrchestrator.export_materials(orch, textbook.course_id, ["pdf"])
