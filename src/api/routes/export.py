"""Export API routes (legacy — prefer /courses/{id}/export)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_orchestrator
from src.orchestrator import LearningOrchestrator

router = APIRouter()


class ExportRequest(BaseModel):
    """Export body."""
    formats: list[str] = Field(default_factory=lambda: ["obsidian"])


class ExportResponse(BaseModel):
    """Export response payload."""
    items: dict[str, str]
    errors: dict[str, str] = Field(default_factory=dict)


@router.post("/export/{course_id}")
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

    return ExportResponse(
        items={fmt: str(path) for fmt, path in results["items"].items()},
        errors={fmt: message for fmt, message in results["errors"].items()},
    )
