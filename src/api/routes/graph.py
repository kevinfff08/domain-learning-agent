"""Knowledge graph API routes."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.api.deps import get_orchestrator
from src.logging_config import get_logger
from src.models.assessment import AssessmentProfile
from src.models.knowledge_graph import KnowledgeGraph
from src.orchestrator import LearningOrchestrator

logger = get_logger("api.graph")
router = APIRouter()


@router.get("/graph/{field}/build")
async def build_graph(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Build knowledge graph from assessment profile. Returns SSE stream."""
    logger.info("GET /graph/%s/build — starting graph construction", field)
    profile = orch.store.load_assessment(AssessmentProfile)
    if not profile:
        logger.warning("Graph build failed: no assessment profile found")
        raise HTTPException(status_code=404, detail="No assessment found. Run assessment first.")

    async def event_generator():
        # Queue for progress events from the synchronous mapper callback
        progress_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

        def _on_progress(step_id: str, message: str) -> None:
            progress_queue.put_nowait((step_id, message))

        # Run the blocking build in a background task
        build_task = asyncio.create_task(
            orch.build_knowledge_graph(profile, on_progress=_on_progress)
        )

        # Relay progress events as SSE while build is running
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
                # No new progress event yet — just loop
                continue

        # Drain any remaining events in the queue
        while not progress_queue.empty():
            step_id, message = progress_queue.get_nowait()
            yield {
                "event": "step_progress",
                "data": json.dumps({"step": step_id, "message": message}),
            }

        # Check build result
        try:
            graph = build_task.result()
            logger.info("Graph build complete: %d nodes, %d edges", len(graph.nodes), len(graph.edges))
            yield {
                "event": "complete",
                "data": json.dumps({
                    "message": f"知识图谱构建完成：{len(graph.nodes)} 个概念节点",
                    "field": graph.field,
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                }),
            }
        except Exception as exc:
            logger.error("Graph build failed: %s", exc, exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(event_generator())


@router.get("/graph/{field}")
def get_graph(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get knowledge graph data for visualization."""
    graph = orch.store.load_knowledge_graph(field, KnowledgeGraph)
    if not graph:
        raise HTTPException(status_code=404, detail=f"No knowledge graph found for '{field}'.")

    # Format for D3.js visualization
    nodes = []
    for node in graph.nodes:
        nodes.append({
            "id": node.id,
            "name": node.name,
            "description": node.description,
            "difficulty": node.difficulty,
            "status": node.status.value,
            "mastery": node.mastery,
            "estimated_hours": node.estimated_hours,
            "prerequisites": node.prerequisites,
            "tags": node.tags,
            "adaptive_level": node.adaptive_level,
        })

    edges = []
    for edge in graph.edges:
        edges.append({
            "source": edge.source,
            "target": edge.target,
            "edge_type": edge.edge_type.value,
            "label": edge.label,
        })

    return {
        "field": graph.field,
        "version": graph.version,
        "nodes": nodes,
        "edges": edges,
        "learning_path": graph.learning_path,
        "estimated_total_hours": graph.estimated_total_hours,
        "completion_rate": graph.completion_rate,
    }


@router.get("/graph/{field}/path")
def get_learning_path(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get ordered learning path with status."""
    graph = orch.store.load_knowledge_graph(field, KnowledgeGraph)
    if not graph:
        raise HTTPException(status_code=404, detail=f"No knowledge graph found for '{field}'.")

    path = []
    for cid in graph.learning_path:
        node = graph.get_node(cid)
        if node:
            path.append({
                "id": node.id,
                "name": node.name,
                "difficulty": node.difficulty,
                "status": node.status.value,
                "mastery": node.mastery,
                "estimated_hours": node.estimated_hours,
            })

    return {"field": graph.field, "path": path}


@router.get("/concepts/{field}")
def list_concepts(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """List all concepts in a field."""
    graph = orch.store.load_knowledge_graph(field, KnowledgeGraph)
    if not graph:
        raise HTTPException(status_code=404, detail=f"No knowledge graph found for '{field}'.")

    return {
        "field": graph.field,
        "concepts": [
            {
                "id": n.id,
                "name": n.name,
                "difficulty": n.difficulty,
                "status": n.status.value,
                "mastery": n.mastery,
            }
            for n in graph.nodes
        ],
    }
