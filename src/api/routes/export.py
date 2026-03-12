"""Export API routes (legacy — prefer /courses/{id}/export)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import get_orchestrator
from src.orchestrator import LearningOrchestrator

router = APIRouter()


class ExportRequest(BaseModel):
    """Export body."""
    formats: list[str] = ["obsidian"]


@router.post("/export/{course_id}")
async def export_materials(
    course_id: str,
    req: ExportRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Export learning materials in specified formats."""
    try:
        results = await orch.export_materials(course_id, req.formats)
    except ValueError as e:
        return {"error": str(e)}

    return {fmt: str(path) for fmt, path in results.items()}
