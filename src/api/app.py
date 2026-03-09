"""FastAPI application for NewLearner."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger("api")

from src.api.routes import assessment, graph, learning, quiz, review, progress, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    llm_mode = os.environ.get("LLM_MODE", "api-key")
    llm_model = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
    logger.info("FastAPI server starting — LLM_MODE=%s, LLM_MODEL=%s", llm_mode, llm_model)
    yield
    logger.info("FastAPI server shutting down")


app = FastAPI(
    title="NewLearner API",
    description="PhD-level AI research domain learning system",
    version="0.1.0",
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
app.include_router(graph.router, prefix="/api", tags=["graph"])
app.include_router(learning.router, prefix="/api", tags=["learning"])
app.include_router(quiz.router, prefix="/api", tags=["quiz"])
app.include_router(review.router, prefix="/api", tags=["review"])
app.include_router(progress.router, prefix="/api", tags=["progress"])
app.include_router(export.router, prefix="/api", tags=["export"])


@app.get("/api/status")
def get_status():
    """System status check."""
    import os
    from src.api.deps import get_orchestrator
    from src.models.assessment import AssessmentProfile

    orch = get_orchestrator()
    profile = orch.store.load_assessment(AssessmentProfile)

    llm_mode = os.environ.get("LLM_MODE", "api-key").strip().lower()
    llm_ready = (
        llm_mode == "setup-token"
        or bool(os.environ.get("ANTHROPIC_API_KEY"))
    )

    return {
        "llm_mode": llm_mode,
        "llm_ready": llm_ready,
        "semantic_scholar_api_key": bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY")),
        "github_token": bool(os.environ.get("GITHUB_TOKEN")),
        "has_assessment": profile is not None,
        "target_field": profile.target_field if profile else None,
    }
