"""Data models for user assessment profiles."""

from __future__ import annotations

from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class SkillLevel(BaseModel):
    """A skill dimension with level and identified gaps."""

    level: int = Field(ge=0, le=5, description="Proficiency level 0-5")
    gaps: list[str] = Field(default_factory=list, description="Specific knowledge gaps identified")


class LearningGoal(str, Enum):
    """What the user aims to achieve."""

    UNDERSTAND = "understand_concepts"
    REPRODUCE = "reproduce_papers"
    IMPROVE = "improve_methods"


class LearningStyle(str, Enum):
    """Preferred learning approach."""

    MATH_FIRST = "mathematical_first"
    CODE_FIRST = "code_first"
    INTUITION_FIRST = "intuition_first"
    BALANCED = "balanced"


class MathFoundations(BaseModel):
    """Math background assessment."""

    linear_algebra: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))
    probability: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))
    calculus: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))
    optimization: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))


class ProgrammingSkills(BaseModel):
    """Programming background assessment."""

    python: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))
    pytorch: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))
    jax: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))
    distributed_training: SkillLevel = Field(default_factory=lambda: SkillLevel(level=0))


class DiagnosticQuestion(BaseModel):
    """A diagnostic question used during assessment."""

    id: str
    dimension: str = Field(description="Which dimension this tests (e.g., 'probability', 'pytorch')")
    question: str
    options: list[str]
    correct_answer: int = Field(ge=0, description="Index of correct option")
    difficulty: int = Field(ge=1, le=5)
    explanation: str = ""


class DiagnosticResult(BaseModel):
    """Result of a single diagnostic question."""

    question_id: str
    selected_answer: int
    is_correct: bool
    time_spent_seconds: float = 0.0


class AssessmentProfile(BaseModel):
    """Complete user assessment profile, the foundation for all downstream skills."""

    user_id: str = "default"
    target_field: str = Field(description="The domain to learn, e.g., 'Diffusion Models'")
    math_foundations: MathFoundations = Field(default_factory=MathFoundations)
    programming: ProgrammingSkills = Field(default_factory=ProgrammingSkills)
    domain_knowledge: dict[str, int] = Field(
        default_factory=dict,
        description="Related domain knowledge scores, e.g., {'generative_models': 2, 'variational_inference': 1}",
    )
    learning_goal: LearningGoal = LearningGoal.UNDERSTAND
    available_hours_per_week: float = Field(default=10.0, ge=1.0)
    learning_style: LearningStyle = LearningStyle.INTUITION_FIRST
    diagnostic_results: list[DiagnosticResult] = Field(default_factory=list)
    calibration_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="How confident we are in the assessment"
    )
    seed_papers: list[str] = Field(
        default_factory=list, description="User-specified seed papers (arXiv IDs or titles)"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
