"""Data models for learning progress tracking."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConceptProgress(BaseModel):
    """Progress for a single concept."""

    concept_id: str
    status: str = "pending"  # pending, in_progress, completed
    mastery_level: float = Field(default=0.0, ge=0.0, le=1.0)
    quiz_scores: list[float] = Field(default_factory=list)
    time_spent_hours: float = 0.0
    cards_total: int = 0
    cards_due: int = 0
    adaptive_level: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_accessed: datetime | None = None


class WeeklyStats(BaseModel):
    """Weekly statistics snapshot."""

    week_start: datetime
    hours_spent: float = 0.0
    concepts_completed: int = 0
    quiz_average: float = 0.0
    cards_reviewed: int = 0


class LearnerProgress(BaseModel):
    """Complete learning progress state."""

    user_id: str = "default"
    field: str = ""
    concepts: dict[str, ConceptProgress] = Field(
        default_factory=dict, description="concept_id -> ConceptProgress"
    )
    weekly_stats: list[WeeklyStats] = Field(default_factory=list)
    total_hours_spent: float = 0.0
    streak_days: int = 0
    last_active: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def concepts_total(self) -> int:
        return len(self.concepts)

    @property
    def concepts_completed(self) -> int:
        return sum(1 for c in self.concepts.values() if c.status == "completed")

    @property
    def completion_rate(self) -> float:
        if not self.concepts:
            return 0.0
        return self.concepts_completed / self.concepts_total

    @property
    def average_quiz_score(self) -> float:
        all_scores = []
        for c in self.concepts.values():
            all_scores.extend(c.quiz_scores)
        return sum(all_scores) / len(all_scores) if all_scores else 0.0

    def get_or_create_concept(self, concept_id: str) -> ConceptProgress:
        """Get existing concept progress or create a new one."""
        if concept_id not in self.concepts:
            self.concepts[concept_id] = ConceptProgress(concept_id=concept_id)
        return self.concepts[concept_id]
