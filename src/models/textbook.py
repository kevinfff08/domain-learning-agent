"""Data models for textbook structure — replaces knowledge_graph.py."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ChapterStatus(str, Enum):
    """Status of a textbook chapter."""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Chapter(BaseModel):
    """A textbook chapter — replaces ConceptNode."""

    id: str = Field(description="Slug identifier, e.g. 'ch01_intro_to_diffusion'")
    chapter_number: int = Field(ge=1, description="1-based chapter number")
    title: str
    description: str = ""
    difficulty: int = Field(default=3, ge=1, le=5)
    estimated_hours: float = Field(default=2.0, ge=0.5)
    status: ChapterStatus = ChapterStatus.PENDING
    mastery: float = Field(default=0.0, ge=0.0, le=1.0)
    has_content: bool = False
    quiz_score: float | None = None
    tags: list[str] = Field(default_factory=list)
    key_topics: list[str] = Field(
        default_factory=list,
        description="Key concepts for this chapter, used by LLM for content generation",
    )


class PaperReference(BaseModel):
    """A reference to an academic paper."""

    arxiv_id: str = ""
    doi: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    venue: str = ""
    citation_count: int = 0
    role: str = Field(
        default="related",
        description="Role: survey, key_paper, related",
    )


class Textbook(BaseModel):
    """A complete textbook for a learning domain — replaces KnowledgeGraph."""

    course_id: str
    field: str = Field(description="Target learning domain")
    title: str = Field(description="Textbook title, e.g. '扩散模型：从理论到实践'")
    chapters: list[Chapter] = Field(default_factory=list)
    survey_papers: list[PaperReference] = Field(default_factory=list)
    total_estimated_hours: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_chapter(self, chapter_id: str) -> Chapter | None:
        """Get a chapter by ID."""
        for ch in self.chapters:
            if ch.id == chapter_id:
                return ch
        return None

    def get_chapter_by_number(self, number: int) -> Chapter | None:
        """Get a chapter by its number."""
        for ch in self.chapters:
            if ch.chapter_number == number:
                return ch
        return None

    def completion_rate(self) -> float:
        """Calculate overall completion rate."""
        if not self.chapters:
            return 0.0
        completed = sum(1 for ch in self.chapters if ch.status == ChapterStatus.COMPLETED)
        return completed / len(self.chapters)
