"""Progress tracking API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from src.api.deps import get_orchestrator
from src.models.progress import LearnerProgress
from src.orchestrator import LearningOrchestrator

router = APIRouter()


@router.get("/progress/{field}")
def get_progress(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get learning progress for a field."""
    progress = orch.tracker.get_or_create_progress(field)
    return json.loads(progress.model_dump_json())


@router.get("/progress/{field}/report")
def get_weekly_report(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get weekly progress report as Markdown."""
    report = orch.get_weekly_report(field)
    return {"report": report}


@router.post("/progress/{field}/time")
def record_time(
    field: str,
    concept_id: str,
    hours: float,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Record study time for a concept."""
    progress = orch.tracker.get_or_create_progress(field)
    progress = orch.tracker.record_time(progress, concept_id, hours)
    return {"message": f"Recorded {hours}h for '{concept_id}'."}
