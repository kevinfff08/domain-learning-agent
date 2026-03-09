"""Data models for learning resources."""

from __future__ import annotations

from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Type of learning resource."""

    PAPER = "paper"
    BLOG = "blog"
    VIDEO = "video"
    CODE = "code"
    COURSE = "course"


class Resource(BaseModel):
    """A single learning resource."""

    url: str
    title: str
    resource_type: ResourceType
    source: str = Field(default="", description="e.g., 'Lil\\'Log', 'Stanford CS236'")
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    difficulty: str = Field(default="intermediate", description="beginner/intermediate/advanced")
    description: str = ""

    # Paper-specific
    arxiv_id: str = ""
    citation_count: int = 0
    relevance: str = ""

    # Code-specific
    github_stars: int = 0
    language: str = ""
    framework: str = ""

    # Video-specific
    channel: str = ""
    duration_minutes: int = 0


class ResourceCollection(BaseModel):
    """Resources curated for a specific concept."""

    concept_id: str
    papers: list[Resource] = Field(default_factory=list)
    blogs: list[Resource] = Field(default_factory=list)
    videos: list[Resource] = Field(default_factory=list)
    code: list[Resource] = Field(default_factory=list)
    courses: list[Resource] = Field(default_factory=list)
    curated_at: datetime = Field(default_factory=datetime.now)

    @property
    def total_resources(self) -> int:
        return len(self.papers) + len(self.blogs) + len(self.videos) + len(self.code) + len(self.courses)
