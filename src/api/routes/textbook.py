"""Textbook & chapter API routes with SSE streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.api.deps import get_orchestrator
from src.logging_config import get_logger
from src.models.content import ResearchSynthesis
from src.models.resources import ResourceCollection
from src.models.textbook import Textbook
from src.models.verification import VerificationReport
from src.orchestrator import LearningOrchestrator

logger = get_logger("api.textbook")
router = APIRouter()


# ── Textbook outline ─────────────────────────────────────────────────

@router.get("/courses/{course_id}/textbook")
def get_textbook(
    course_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get textbook outline for a course."""
    textbook = orch.store.load_course_model(course_id, "textbook.json", Textbook)
    if not textbook:
        raise HTTPException(status_code=404, detail="No textbook found. Build outline first.")
    return json.loads(textbook.model_dump_json())


@router.get("/courses/{course_id}/textbook/build")
async def build_outline(
    course_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Build textbook outline via SSE (search papers + LLM generate)."""
    logger.info("GET /courses/%s/textbook/build — starting outline generation", course_id)

    async def event_generator():
        progress_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

        def _on_progress(step_id: str, message: str) -> None:
            progress_queue.put_nowait((step_id, message))

        build_task = asyncio.create_task(
            orch.build_outline(course_id, on_progress=_on_progress)
        )

        while not build_task.done():
            try:
                step_id, message = await asyncio.wait_for(
                    progress_queue.get(), timeout=0.5
                )
                yield {
                    "event": "step_progress",
                    "data": json.dumps({"step": step_id, "message": message}),
                }
            except (asyncio.TimeoutError, TimeoutError):
                continue

        while not progress_queue.empty():
            step_id, message = progress_queue.get_nowait()
            yield {
                "event": "step_progress",
                "data": json.dumps({"step": step_id, "message": message}),
            }

        try:
            textbook = build_task.result()
            logger.info("Outline build complete: %d chapters", len(textbook.chapters))
            yield {
                "event": "complete",
                "data": json.dumps({
                    "message": f"教材大纲生成完成：{len(textbook.chapters)} 章",
                    "chapter_count": len(textbook.chapters),
                    "total_hours": textbook.total_estimated_hours,
                }),
            }
        except Exception as exc:
            logger.error("Outline build failed: %s", exc, exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(event_generator())


# ── Batch chapter generation ─────────────────────────────────────────

# Active batch generation cancel events, keyed by course_id
_batch_cancel_events: dict[str, asyncio.Event] = {}


@router.get("/courses/{course_id}/textbook/generate")
async def generate_all_chapters(
    course_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Generate content for all pending chapters via SSE."""
    logger.info("GET /courses/%s/textbook/generate — batch generation", course_id)

    # Create cancellation event for this batch
    cancel_event = asyncio.Event()
    _batch_cancel_events[course_id] = cancel_event

    async def event_generator():
        progress_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

        def _on_progress(step_id: str, message: str) -> None:
            progress_queue.put_nowait((step_id, message))

        gen_task = asyncio.create_task(
            orch.generate_all_chapters(
                course_id, on_progress=_on_progress, cancel_event=cancel_event,
            )
        )

        try:
            while not gen_task.done():
                try:
                    step_id, message = await asyncio.wait_for(
                        progress_queue.get(), timeout=0.5
                    )
                    # Emit chapter_complete as a dedicated event type
                    if step_id == "chapter_complete":
                        yield {
                            "event": "chapter_complete",
                            "data": json.dumps({"chapter_id": message}),
                        }
                    else:
                        yield {
                            "event": "step_progress",
                            "data": json.dumps({"step": step_id, "message": message}),
                        }
                except (asyncio.TimeoutError, TimeoutError):
                    continue

            while not progress_queue.empty():
                step_id, message = progress_queue.get_nowait()
                if step_id == "chapter_complete":
                    yield {
                        "event": "chapter_complete",
                        "data": json.dumps({"chapter_id": message}),
                    }
                else:
                    yield {
                        "event": "step_progress",
                        "data": json.dumps({"step": step_id, "message": message}),
                    }

            try:
                gen_task.result()
                if cancel_event.is_set():
                    yield {
                        "event": "paused",
                        "data": json.dumps({"message": "生成已暂停"}),
                    }
                else:
                    yield {
                        "event": "complete",
                        "data": json.dumps({"message": "全部章节生成完毕"}),
                    }
            except Exception as exc:
                logger.error("Batch generation failed: %s", exc, exc_info=True)
                yield {"event": "error", "data": json.dumps({"message": str(exc)})}
        finally:
            _batch_cancel_events.pop(course_id, None)

    return EventSourceResponse(event_generator())


@router.post("/courses/{course_id}/textbook/generate/pause")
async def pause_batch_generation(course_id: str):
    """Signal the running batch generation to pause after the current chapter."""
    cancel_event = _batch_cancel_events.get(course_id)
    if cancel_event:
        cancel_event.set()
        logger.info("Pause requested for batch generation: %s", course_id)
        return {"message": "暂停信号已发送，将在当前章节完成后停止"}
    raise HTTPException(status_code=404, detail="No active batch generation for this course")


# ── Single chapter ───────────────────────────────────────────────────

@router.get("/courses/{course_id}/chapters/{chapter_id}")
def get_chapter_content(
    course_id: str,
    chapter_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get chapter content (synthesis, resources, verification)."""
    synthesis = orch.store.load_course_content(
        course_id, chapter_id, "research_synthesis.json", ResearchSynthesis
    )
    if not synthesis:
        # Fallback: legacy path
        synthesis = orch.store.load_content(chapter_id, "research_synthesis.json", ResearchSynthesis)
    if not synthesis:
        raise HTTPException(status_code=404, detail="No content for this chapter. Generate it first.")

    resources = orch.store.load_course_content(
        course_id, chapter_id, "resources.json", ResourceCollection
    )
    verification = orch.store.load_course_content(
        course_id, chapter_id, "verification_report.json", VerificationReport
    )

    result = {"synthesis": json.loads(synthesis.model_dump_json())}
    if resources:
        result["resources"] = json.loads(resources.model_dump_json())
    if verification:
        result["verification"] = json.loads(verification.model_dump_json())
    return result


@router.get("/courses/{course_id}/chapters/{chapter_id}/stream")
async def stream_chapter(
    course_id: str,
    chapter_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Generate single chapter content via SSE (5-step pipeline)."""
    logger.info("GET /courses/%s/chapters/%s/stream", course_id, chapter_id)

    async def event_generator():
        progress_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

        def _on_progress(step_id: str, message: str) -> None:
            progress_queue.put_nowait((step_id, message))

        gen_task = asyncio.create_task(
            orch.generate_chapter(course_id, chapter_id, on_progress=_on_progress)
        )

        while not gen_task.done():
            try:
                step_id, message = await asyncio.wait_for(
                    progress_queue.get(), timeout=0.5
                )
                yield {
                    "event": "step_progress",
                    "data": json.dumps({"step": step_id, "message": message}),
                }
            except (asyncio.TimeoutError, TimeoutError):
                continue

        while not progress_queue.empty():
            step_id, message = progress_queue.get_nowait()
            yield {
                "event": "step_progress",
                "data": json.dumps({"step": step_id, "message": message}),
            }

        try:
            result = gen_task.result()
            yield {
                "event": "complete",
                "data": json.dumps({
                    "message": f"章节生成完毕",
                    "chapter_id": chapter_id,
                }),
            }
        except Exception as exc:
            logger.error("Chapter generation failed: %s", exc, exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(event_generator())


# ── Delete chapter content ───────────────────────────────────────────

@router.delete("/courses/{course_id}/chapters/{chapter_id}")
def delete_chapter_content(
    course_id: str,
    chapter_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Delete all generated content for a chapter, resetting to pending."""
    logger.info("DELETE /courses/%s/chapters/%s", course_id, chapter_id)
    try:
        orch.delete_chapter_content(course_id, chapter_id)
        return {"message": f"Chapter {chapter_id} content deleted", "chapter_id": chapter_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Quiz ─────────────────────────────────────────────────────────────

class QuizSubmitRequest(BaseModel):
    """Quiz submission body."""
    answers: dict[str, str]


@router.post("/courses/{course_id}/chapters/{chapter_id}/quiz/submit")
async def submit_quiz(
    course_id: str,
    chapter_id: str,
    req: QuizSubmitRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Submit quiz answers and get results with adaptive feedback."""
    result = await orch.process_quiz_result(course_id, chapter_id, req.answers)
    return result


# ── Review ───────────────────────────────────────────────────────────

@router.get("/courses/{course_id}/review/due")
def get_due_cards(
    course_id: str,
    chapter_id: str | None = None,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get flashcards due for review."""
    due = orch.get_due_reviews(chapter_id)
    return {
        "count": len(due),
        "cards": [json.loads(card.model_dump_json()) for card in due],
    }


class ReviewCardRequest(BaseModel):
    """Review card request body."""
    rating: int
    chapter_id: str


@router.post("/courses/{course_id}/review/{card_id}")
def review_card(
    course_id: str,
    card_id: str,
    req: ReviewCardRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Submit a review rating for a flashcard."""
    from src.models.cards import CardDeck

    deck = orch.store.load_course_content(
        course_id, req.chapter_id, "cards.json", CardDeck
    )
    if not deck:
        deck = orch.store.load_content(req.chapter_id, "cards.json", CardDeck)
    if not deck:
        return {"error": f"No cards found for chapter '{req.chapter_id}'."}

    card = next((c for c in deck.cards if c.id == card_id), None)
    if not card:
        return {"error": f"Card '{card_id}' not found."}

    card = orch.spaced_rep.review_card(card, req.rating)
    return {
        "card_id": card.id,
        "next_review": str(card.fsrs_state.due),
        "stability": card.fsrs_state.stability,
        "difficulty": card.fsrs_state.difficulty,
        "state": card.fsrs_state.state,
    }


# ── Progress ─────────────────────────────────────────────────────────

@router.get("/courses/{course_id}/progress")
def get_progress(
    course_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get learning progress for a course."""
    textbook = orch.store.load_course_model(course_id, "textbook.json", Textbook)
    if not textbook:
        raise HTTPException(status_code=404, detail="No textbook found.")

    progress = orch.tracker.get_or_create_progress(textbook.field)
    return json.loads(progress.model_dump_json())


# ── Export ────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    """Export body."""
    formats: list[str] = Field(default_factory=lambda: ["obsidian"])


class ExportResponse(BaseModel):
    """Export response payload."""
    items: dict[str, str]
    errors: dict[str, str] = Field(default_factory=dict)


class UpdateChapterGuidanceRequest(BaseModel):
    """Chapter guidance update body."""
    chapter_guidance: str = ""


@router.patch("/courses/{course_id}/chapters/{chapter_id}/guidance")
def update_chapter_guidance(
    course_id: str,
    chapter_id: str,
    req: UpdateChapterGuidanceRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Update chapter-level guidance inside the textbook outline."""
    try:
        textbook = orch.update_chapter_guidance(
            course_id,
            chapter_id,
            req.chapter_guidance,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return json.loads(textbook.model_dump_json())


@router.post("/courses/{course_id}/export")
async def export_materials(
    course_id: str,
    req: ExportRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Export learning materials in specified formats."""
    try:
        results = await orch.export_materials(course_id, req.formats)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    items = {
        fmt: str(path)
        for fmt, path in results["items"].items()
    }
    errors = {
        fmt: message
        for fmt, message in results["errors"].items()
    }
    return ExportResponse(items=items, errors=errors)


# ── Socratic dialogue ────────────────────────────────────────────────

class SocraticRequest(BaseModel):
    """Socratic dialogue advance request."""
    student_answer: str
    current_step: int
    dialogue: list[dict]


@router.post("/courses/{course_id}/chapters/{chapter_id}/socratic")
def advance_socratic(
    course_id: str,
    chapter_id: str,
    req: SocraticRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Advance Socratic dialogue by evaluating student's answer."""
    result = orch.adaptive.advance_socratic(
        chapter_id, req.student_answer, req.current_step, req.dialogue
    )
    return result
