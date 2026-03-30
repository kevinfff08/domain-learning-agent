"""Course management API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import get_orchestrator
from src.logging_config import get_logger
from src.orchestrator import LearningOrchestrator

logger = get_logger("api.courses")
router = APIRouter()


class CreateCourseRequest(BaseModel):
    """Create course request body."""
    field: str
    course_requirements: str = ""
    math_level: int = 3
    programming_level: int = 3
    domain_level: int = 0
    learning_goal: str = "understand_concepts"
    available_hours: float = 10.0
    learning_style: str = "intuition_first"


class CourseSettingsResponse(CreateCourseRequest):
    """Editable course settings payload."""


@router.get("/courses")
def list_courses(
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """List all courses."""
    return {"courses": orch.list_courses()}


@router.post("/courses")
def create_course(
    req: CreateCourseRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Create a new course with assessment."""
    logger.info("POST /courses — field=%s", req.field)
    course, profile = orch.create_course(
        field=req.field,
        assessment_data=req.model_dump(exclude={"field"}),
    )
    return {
        "course": course.model_dump(mode="json"),
        "profile": profile.model_dump(),
    }


@router.get("/courses/{course_id}")
def get_course(
    course_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get course details."""
    course = orch.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found.")
    return course.model_dump(mode="json")


@router.get("/courses/{course_id}/settings")
def get_course_settings(
    course_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get editable settings for an existing course."""
    try:
        settings = orch.get_course_settings(course_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return CourseSettingsResponse(**settings).model_dump()


@router.put("/courses/{course_id}")
def update_course(
    course_id: str,
    req: CreateCourseRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Update course settings and reset derived outline/content artifacts."""
    logger.info("PUT /courses/%s — field=%s", course_id, req.field)
    try:
        course, profile = orch.update_course(
            course_id,
            req.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "course": course.model_dump(mode="json"),
        "profile": profile.model_dump(),
    }


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Delete a course."""
    success = orch.delete_course(course_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found.")
    return {"message": f"Course '{course_id}' deleted."}
