"""Data models for quizzes and assessments."""

from __future__ import annotations

from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class BloomLevel(str, Enum):
    """Bloom's taxonomy levels for question classification."""

    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class QuestionType(str, Enum):
    """Type of quiz question."""

    MULTIPLE_CHOICE = "multiple_choice"
    DERIVATION = "derivation"
    CODE_COMPLETION = "code_completion"
    CONCEPT_COMPARISON = "concept_comparison"
    FREE_RESPONSE = "free_response"


class Question(BaseModel):
    """A single quiz question."""

    id: str
    question_type: QuestionType
    bloom_level: BloomLevel
    question: str
    difficulty: int = Field(ge=1, le=5)
    concept_id: str = Field(description="Which concept this tests")

    # For multiple choice
    options: list[str] = Field(default_factory=list)
    correct_answer: int = Field(default=0, description="Index of correct option for MC")

    # For derivation / code completion
    solution_steps: list[str] = Field(default_factory=list)
    code_template: str = ""
    expected_solution: str = ""

    # For concept comparison
    concepts_to_compare: list[str] = Field(default_factory=list)

    explanation: str = ""
    source_paper: str = Field(default="", description="Source for the answer")


class QuestionResult(BaseModel):
    """Result of answering a single question."""

    question_id: str
    user_answer: str
    is_correct: bool
    score: float = Field(ge=0.0, le=1.0, description="Partial credit score")
    time_spent_seconds: float = 0.0
    feedback: str = ""


class Quiz(BaseModel):
    """A complete quiz for a concept."""

    id: str
    concept_id: str
    questions: list[Question] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class QuizResult(BaseModel):
    """Aggregated quiz results."""

    quiz_id: str
    concept_id: str
    results: list[QuestionResult] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=1.0)
    completed_at: datetime = Field(default_factory=datetime.now)
    bloom_scores: dict[str, float] = Field(
        default_factory=dict, description="Score per Bloom level"
    )

    @property
    def passed(self) -> bool:
        """Whether the quiz was passed (score >= 70%)."""
        return self.overall_score >= 0.7

    @property
    def needs_level1_intervention(self) -> bool:
        """Score between 40-70%, needs alternative explanation."""
        return 0.4 <= self.overall_score < 0.7

    @property
    def needs_level2_intervention(self) -> bool:
        """Score below 40%, needs prerequisite review."""
        return self.overall_score < 0.4
