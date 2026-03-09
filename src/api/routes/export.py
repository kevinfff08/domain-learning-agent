"""Export API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from src.api.deps import get_orchestrator
from src.models.knowledge_graph import KnowledgeGraph
from src.orchestrator import LearningOrchestrator

router = APIRouter()


@router.post("/export/{field}")
async def export_materials(
    field: str,
    formats: str = "obsidian",
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Export learning materials in specified formats."""
    graph = orch.store.load_knowledge_graph(field, KnowledgeGraph)
    if not graph:
        return {"error": f"No knowledge graph found for '{field}'."}

    fmt_list = [f.strip() for f in formats.split(",")]
    results = await orch.export_materials(graph, fmt_list)

    return {
        fmt: str(path) for fmt, path in results.items()
    }
