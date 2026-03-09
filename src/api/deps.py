"""Dependency injection for FastAPI routes."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from src.orchestrator import LearningOrchestrator

load_dotenv()


@lru_cache()
def get_orchestrator() -> LearningOrchestrator:
    """Create a singleton orchestrator instance."""
    return LearningOrchestrator(
        data_dir=os.environ.get("DATA_DIR", "data"),
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        s2_api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
        github_token=os.environ.get("GITHUB_TOKEN"),
        llm_model=os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514"),
    )
