"""Export API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.deps import get_orchestrator
from src.models.knowledge_graph import KnowledgeGraph
from src.orchestrator import LearningOrchestrator

router = APIRouter()


class ExportRequest(BaseModel):
    """Export body."""
    formats: list[str] = ["obsidian"]


@router.post("/export/{field}")
async def export_materials(
    field: str,
    req: ExportRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Export learning materials in specified formats."""
    graph = orch.store.load_knowledge_graph(field, KnowledgeGraph)
    if not graph:
        return {"error": f"No knowledge graph found for '{field}'."}

    results = await orch.export_materials(graph, req.formats)

    return {
        fmt: str(path) for fmt, path in results.items()
    }
