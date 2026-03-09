"""Assessment API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import get_orchestrator
from src.logging_config import get_logger
from src.models.assessment import AssessmentProfile, LearningGoal, LearningStyle
from src.orchestrator import LearningOrchestrator

logger = get_logger("api.assessment")
router = APIRouter()


class AssessmentRequest(BaseModel):
    """Assessment form data (JSON body)."""

    field: str
    math_level: int = 3
    programming_level: int = 3
    domain_level: int = 0
    learning_goal: str = "understand_concepts"
    available_hours: float = 10.0
    learning_style: str = "intuition_first"


@router.post("/assessment")
async def create_assessment(
    req: AssessmentRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Create or update learner assessment profile."""
    logger.info("POST /assessment — field=%s, goal=%s, style=%s", req.field, req.learning_goal, req.learning_style)
    profile = await orch.run_assessment(
        field=req.field,
        quick=True,
        math_level=req.math_level,
        programming_level=req.programming_level,
        domain_level=req.domain_level,
        learning_goal=req.learning_goal,
        available_hours=req.available_hours,
        learning_style=req.learning_style,
    )
    return profile.model_dump()


@router.get("/assessment")
def get_assessment(
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get current assessment profile."""
    profile = orch.store.load_assessment(AssessmentProfile)
    if not profile:
        raise HTTPException(status_code=404, detail="No assessment found.")
    return profile.model_dump()
