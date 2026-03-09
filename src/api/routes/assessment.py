"""Assessment API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.deps import get_orchestrator
from src.models.assessment import AssessmentProfile, LearningGoal, LearningStyle
from src.orchestrator import LearningOrchestrator

router = APIRouter()


class AssessmentRequest:
    """Assessment form data."""

    def __init__(
        self,
        field: str,
        math_level: int = 3,
        programming_level: int = 3,
        domain_level: int = 0,
        learning_goal: str = "understand_concepts",
        available_hours: float = 10.0,
        learning_style: str = "intuition_first",
    ):
        self.field = field
        self.math_level = math_level
        self.programming_level = programming_level
        self.domain_level = domain_level
        self.learning_goal = learning_goal
        self.available_hours = available_hours
        self.learning_style = learning_style


@router.post("/assessment")
async def create_assessment(
    field: str,
    math_level: int = 3,
    programming_level: int = 3,
    domain_level: int = 0,
    learning_goal: str = "understand_concepts",
    available_hours: float = 10.0,
    learning_style: str = "intuition_first",
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Create or update learner assessment profile."""
    profile = await orch.run_assessment(
        field=field,
        quick=True,
        math_level=math_level,
        programming_level=programming_level,
        domain_level=domain_level,
        learning_goal=learning_goal,
        available_hours=available_hours,
        learning_style=learning_style,
    )
    return profile.model_dump()


@router.get("/assessment")
def get_assessment(
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get current assessment profile."""
    profile = orch.store.load_assessment(AssessmentProfile)
    if not profile:
        return {"error": "No assessment found. Create one first."}
    return profile.model_dump()
