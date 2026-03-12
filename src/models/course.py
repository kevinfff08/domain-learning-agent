"""Data models for course management."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CourseStatus(str, Enum):
    """Status of a course."""

    CREATED = "created"
    OUTLINE_READY = "outline_ready"
    GENERATING = "generating"
    ACTIVE = "active"
    COMPLETED = "completed"


class Course(BaseModel):
    """A learning course that wraps a textbook, assessment, and progress."""

    id: str = Field(description="Slug identifier, e.g. 'diffusion_models'")
    title: str = Field(description="Display name, e.g. '扩散模型'")
    description: str = ""
    status: CourseStatus = CourseStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime | None = None
    total_chapters: int = 0
    completed_chapters: int = 0
