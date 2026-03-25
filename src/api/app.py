"""FastAPI application for NewLearner."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.llm.client import is_llm_ready, resolve_llm_provider
from src.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger("api")

from src.api.routes import assessment, courses, textbook, quiz, review, progress, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    llm_mode = os.environ.get("LLM_MODE", "api-key")
    llm_model = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
    llm_provider = resolve_llm_provider(model=llm_model)
    logger.info(
        "FastAPI server starting - LLM_PROVIDER=%s, LLM_MODE=%s, LLM_MODEL=%s",
        llm_provider,
        llm_mode,
        llm_model,
    )

    # Record server boot timestamp for frontend restart detection
    import time
    app.state.boot_time = time.time()

    # Recover chapters stuck in GENERATING status from a previous crash
    _recover_interrupted_chapters()

    yield
    logger.info("FastAPI server shutting down")


def _recover_interrupted_chapters() -> None:
    """Reset chapters stuck in 'generating' to 'interrupted' on startup."""
    from src.api.deps import get_orchestrator
    from src.models.textbook import Textbook, ChapterStatus

    try:
        orch = get_orchestrator()
        registry = orch.list_courses()
        for entry in registry:
            course_id = entry.get("id")
            if not course_id:
                continue
            textbook = orch.store.load_course_model(course_id, "textbook.json", Textbook)
            if not textbook:
                continue
            changed = False
            for ch in textbook.chapters:
                if ch.status == ChapterStatus.GENERATING:
                    logger.warning(
                        "Recovering chapter '%s' in course '%s': generating → interrupted",
                        ch.id, course_id,
                    )
                    ch.status = ChapterStatus.INTERRUPTED
                    changed = True
            if changed:
                from datetime import datetime
                textbook.updated_at = datetime.now()
                orch.store.save_course_model(course_id, "textbook.json", textbook)
    except Exception:
        logger.error("Failed to recover interrupted chapters", exc_info=True)


app = FastAPI(
    title="NewLearner API",
    description="PhD-level AI research domain learning system",
    version="0.2.3",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assessment.router, prefix="/api", tags=["assessment"])
app.include_router(courses.router, prefix="/api", tags=["courses"])
app.include_router(textbook.router, prefix="/api", tags=["textbook"])
app.include_router(quiz.router, prefix="/api", tags=["quiz"])
app.include_router(review.router, prefix="/api", tags=["review"])
app.include_router(progress.router, prefix="/api", tags=["progress"])
app.include_router(export.router, prefix="/api", tags=["export"])


@app.get("/api/boot-time")
def get_boot_time():
    """Return server boot timestamp for frontend restart detection."""
    return {"boot_time": getattr(app.state, "boot_time", 0)}


@app.get("/api/status")
def get_status():
    """System status check."""
    import os
    from src.api.deps import get_orchestrator

    orch = get_orchestrator()
    courses_list = orch.list_courses()

    llm_mode = os.environ.get("LLM_MODE", "api-key").strip().lower()
    llm_model = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
    llm_provider = resolve_llm_provider(model=llm_model)
    llm_ready = is_llm_ready(provider=llm_provider, model=llm_model, mode=llm_mode)

    return {
        "llm_provider": llm_provider,
        "llm_mode": llm_mode,
        "llm_model": llm_model,
        "llm_ready": llm_ready,
        "semantic_scholar_api_key": bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY")),
        "github_token": bool(os.environ.get("GITHUB_TOKEN")),
        "course_count": len(courses_list),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
