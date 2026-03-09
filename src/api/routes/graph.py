"""Knowledge graph API routes."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from src.api.deps import get_orchestrator
from src.models.assessment import AssessmentProfile
from src.models.knowledge_graph import KnowledgeGraph
from src.orchestrator import LearningOrchestrator

router = APIRouter()


@router.post("/graph/build")
async def build_graph(
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Build knowledge graph from assessment profile. Returns SSE stream."""
    profile = orch.store.load_assessment(AssessmentProfile)
    if not profile:
        return {"error": "No assessment found. Run assessment first."}

    async def event_generator():
        yield {"event": "step_start", "data": json.dumps({"message": "正在搜索领域论文..."})}

        graph = await orch.build_knowledge_graph(profile)

        yield {
            "event": "complete",
            "data": json.dumps({
                "message": f"知识图谱构建完成：{len(graph.nodes)} 个概念节点",
                "field": graph.field,
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges),
            }),
        }

    return EventSourceResponse(event_generator())


@router.get("/graph/{field}")
def get_graph(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get knowledge graph data for visualization."""
    graph = orch.store.load_knowledge_graph(field, KnowledgeGraph)
    if not graph:
        return {"error": f"No knowledge graph found for '{field}'."}

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
        return {"error": f"No knowledge graph found for '{field}'."}

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
        return {"error": f"No knowledge graph found for '{field}'."}

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
