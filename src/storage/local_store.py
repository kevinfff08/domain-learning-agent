"""Local file-based storage for project data."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TypeVar, Type

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LocalStore:
    """Manages JSON file storage for all project data."""

    def __init__(self, data_dir: Path | str = "data"):
        self.data_dir = Path(data_dir)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create required directory structure."""
        dirs = [
            self.data_dir / "user",
            self.data_dir / "courses",
            self.data_dir / "cache",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path within the data directory."""
        return self.data_dir / relative_path

    def save_json(self, relative_path: str, data: dict | list) -> Path:
        """Save raw JSON data."""
        path = self._resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path

    def load_json(self, relative_path: str) -> dict | list | None:
        """Load raw JSON data."""
        path = self._resolve_path(relative_path)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_model(self, relative_path: str, model: BaseModel) -> Path:
        """Save a Pydantic model as JSON."""
        path = self._resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_model(self, relative_path: str, model_class: Type[T]) -> T | None:
        """Load a Pydantic model from JSON."""
        path = self._resolve_path(relative_path)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        return model_class.model_validate_json(raw)

    def exists(self, relative_path: str) -> bool:
        """Check if a file exists."""
        return self._resolve_path(relative_path).exists()

    def list_files(self, relative_dir: str, pattern: str = "*.json") -> list[Path]:
        """List files in a directory matching a pattern."""
        dir_path = self._resolve_path(relative_dir)
        if not dir_path.exists():
            return []
        return sorted(dir_path.glob(pattern))

    # --- Legacy convenience methods (kept for backward compat with tests) ---

    def save_assessment(self, profile: BaseModel) -> Path:
        return self.save_model("user/assessment_profile.json", profile)

    def load_assessment(self, model_class: Type[T]) -> T | None:
        return self.load_model("user/assessment_profile.json", model_class)

    def save_progress(self, progress: BaseModel) -> Path:
        return self.save_model("user/progress.json", progress)

    def load_progress(self, model_class: Type[T]) -> T | None:
        return self.load_model("user/progress.json", model_class)

    def save_content(self, concept_id: str, filename: str, model: BaseModel) -> Path:
        return self.save_model(f"content/{concept_id}/{filename}", model)

    def load_content(self, concept_id: str, filename: str, model_class: Type[T]) -> T | None:
        return self.load_model(f"content/{concept_id}/{filename}", model_class)

    # --- Course-scoped storage ---

    def save_courses_registry(self, courses: list[dict]) -> Path:
        """Save the courses registry list."""
        return self.save_json("courses.json", courses)

    def load_courses_registry(self) -> list[dict]:
        """Load the courses registry list."""
        data = self.load_json("courses.json")
        return data if isinstance(data, list) else []

    def get_course_dir(self, course_id: str) -> Path:
        """Get the directory path for a course."""
        return self.data_dir / "courses" / course_id

    def ensure_course_dirs(self, course_id: str) -> None:
        """Create directory structure for a course."""
        base = self.get_course_dir(course_id)
        for sub in ["content", "cards", "quizzes"]:
            (base / sub).mkdir(parents=True, exist_ok=True)

    def list_courses(self) -> list[str]:
        """List all course IDs (directory names)."""
        courses_dir = self.data_dir / "courses"
        if not courses_dir.exists():
            return []
        return sorted(d.name for d in courses_dir.iterdir() if d.is_dir())

    def delete_course(self, course_id: str) -> bool:
        """Delete a course directory and all its data."""
        course_dir = self.get_course_dir(course_id)
        if course_dir.exists():
            shutil.rmtree(course_dir)
            return True
        return False

    def save_course_model(self, course_id: str, relative_path: str, model: BaseModel) -> Path:
        """Save a Pydantic model within a course directory."""
        return self.save_model(f"courses/{course_id}/{relative_path}", model)

    def load_course_model(self, course_id: str, relative_path: str, model_class: Type[T]) -> T | None:
        """Load a Pydantic model from a course directory."""
        return self.load_model(f"courses/{course_id}/{relative_path}", model_class)

    def save_course_content(self, course_id: str, chapter_id: str, filename: str, model: BaseModel) -> Path:
        """Save content for a chapter within a course."""
        return self.save_model(f"courses/{course_id}/content/{chapter_id}/{filename}", model)

    def load_course_content(self, course_id: str, chapter_id: str, filename: str, model_class: Type[T]) -> T | None:
        """Load content for a chapter within a course."""
        return self.load_model(f"courses/{course_id}/content/{chapter_id}/{filename}", model_class)
