"""Learning content API routes with SSE streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.api.deps import get_orchestrator
from src.logging_config import get_logger
from src.models.assessment import AssessmentProfile
from src.models.content import ResearchSynthesis
from src.models.knowledge_graph import KnowledgeGraph
from src.models.resources import ResourceCollection
from src.models.verification import VerificationReport
from src.orchestrator import LearningOrchestrator

logger = get_logger("api.learning")
router = APIRouter()


@router.get("/learn/{concept_id}/stream")
async def learn_concept_stream(
    concept_id: str,
    field: str = "",
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Stream the 5-step learning process via SSE.

    Each step emits start/complete events so the frontend can render progressively.
    """
    logger.info("GET /learn/%s/stream — starting 5-step learning", concept_id)
    profile = orch.store.load_assessment(AssessmentProfile)
    if not profile:
        logger.warning("Learn stream aborted: no assessment")
        return {"error": "No assessment found."}

    field_name = field or profile.target_field
    graph = orch.store.load_knowledge_graph(field_name, KnowledgeGraph)
    if not graph:
        logger.warning("Learn stream aborted: no graph for '%s'", field_name)
        return {"error": "No knowledge graph found."}

    concept = graph.get_node(concept_id)
    if not concept:
        logger.warning("Learn stream aborted: concept '%s' not found", concept_id)
        return {"error": f"Concept '{concept_id}' not found."}

    async def event_generator():
        progress = orch.tracker.get_or_create_progress(graph.field)
        orch.tracker.start_concept(progress, concept_id)

        # Step 1: Deep Research
        yield {"event": "step_start", "data": json.dumps({
            "step": 1, "name": "deep_research", "message": "正在生成三层内容（直觉/机制/实践）..."
        })}
        synthesis = await orch.researcher.synthesize(concept, graph, profile)
        yield {"event": "step_complete", "data": json.dumps({
            "step": 1, "name": "deep_research",
            "result": json.loads(synthesis.model_dump_json()),
        })}

        # Step 2: Accuracy Verification
        yield {"event": "step_start", "data": json.dumps({
            "step": 2, "name": "accuracy_verify", "message": "正在核验内容准确性..."
        })}
        report = await orch.verifier.verify(synthesis)
        yield {"event": "step_complete", "data": json.dumps({
            "step": 2, "name": "accuracy_verify",
            "result": json.loads(report.model_dump_json()),
        })}

        # Step 3: Resource Curation
        yield {"event": "step_start", "data": json.dumps({
            "step": 3, "name": "resource_curate", "message": "正在搜索推荐资源..."
        })}
        resources = await orch.curator.curate(concept, profile)
        yield {"event": "step_complete", "data": json.dumps({
            "step": 3, "name": "resource_curate",
            "result": json.loads(resources.model_dump_json()),
        })}

        # Step 4: Quiz Generation
        yield {"event": "step_start", "data": json.dumps({
            "step": 4, "name": "quiz_generate", "message": "正在生成测验题目..."
        })}
        prev_scores = progress.concepts.get(concept_id, None)
        prev = prev_scores.quiz_scores if prev_scores else None
        quiz = orch.quiz_engine.generate_quiz(synthesis, profile, prev)
        yield {"event": "step_complete", "data": json.dumps({
            "step": 4, "name": "quiz_generate",
            "result": json.loads(quiz.model_dump_json()),
        })}

        # Step 5: Practice Materials
        yield {"event": "step_start", "data": json.dumps({
            "step": 5, "name": "practice_generate", "message": "正在生成练习材料..."
        })}
        orch.practice.generate_coding_challenge(synthesis, profile)
        yield {"event": "step_complete", "data": json.dumps({
            "step": 5, "name": "practice_generate",
            "result": {"message": "练习材料生成完毕"},
        })}

        yield {"event": "complete", "data": json.dumps({
            "message": "学习内容全部生成完毕",
            "concept_id": concept_id,
        })}

    return EventSourceResponse(event_generator())


class SocraticRequest(BaseModel):
    """Socratic dialogue advance request."""
    student_answer: str
    current_step: int
    dialogue: list[dict]


@router.post("/learn/{concept_id}/socratic")
def advance_socratic(
    concept_id: str,
    req: SocraticRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Advance Socratic dialogue by evaluating student's answer."""
    result = orch.adaptive.advance_socratic(
        concept_id, req.student_answer, req.current_step, req.dialogue
    )
    return result


@router.get("/learn/{concept_id}/content")
def get_content(
    concept_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get previously generated research synthesis for a concept."""
    synthesis = orch.store.load_content(
        concept_id, "research_synthesis.json", ResearchSynthesis
    )
    if not synthesis:
        return {"error": f"No content found for '{concept_id}'. Run learning first."}
    return json.loads(synthesis.model_dump_json())


@router.get("/learn/{concept_id}/resources")
def get_resources(
    concept_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get curated resources for a concept."""
    resources = orch.store.load_content(
        concept_id, "resources.json", ResourceCollection
    )
    if not resources:
        return {"error": f"No resources found for '{concept_id}'."}
    return json.loads(resources.model_dump_json())


@router.get("/learn/{concept_id}/verification")
def get_verification(
    concept_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get verification report for a concept."""
    report = orch.store.load_content(
        concept_id, "verification_report.json", VerificationReport
    )
    if not report:
        return {"error": f"No verification report found for '{concept_id}'."}
    return json.loads(report.model_dump_json())
