"""Local file-based storage for project data."""

from __future__ import annotations

import json
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
            self.data_dir / "graphs",
            self.data_dir / "content",
            self.data_dir / "cards",
            self.data_dir / "exercises",
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

    # Convenience methods for common data types

    def save_assessment(self, profile: BaseModel) -> Path:
        return self.save_model("user/assessment_profile.json", profile)

    def load_assessment(self, model_class: Type[T]) -> T | None:
        return self.load_model("user/assessment_profile.json", model_class)

    def save_knowledge_graph(self, field: str, graph: BaseModel) -> Path:
        safe_name = field.lower().replace(" ", "_")
        return self.save_model(f"graphs/{safe_name}_knowledge_graph.json", graph)

    def load_knowledge_graph(self, field: str, model_class: Type[T]) -> T | None:
        safe_name = field.lower().replace(" ", "_")
        return self.load_model(f"graphs/{safe_name}_knowledge_graph.json", model_class)

    def save_progress(self, progress: BaseModel) -> Path:
        return self.save_model("user/progress.json", progress)

    def load_progress(self, model_class: Type[T]) -> T | None:
        return self.load_model("user/progress.json", model_class)

    def save_content(self, concept_id: str, filename: str, model: BaseModel) -> Path:
        return self.save_model(f"content/{concept_id}/{filename}", model)

    def load_content(self, concept_id: str, filename: str, model_class: Type[T]) -> T | None:
        return self.load_model(f"content/{concept_id}/{filename}", model_class)
