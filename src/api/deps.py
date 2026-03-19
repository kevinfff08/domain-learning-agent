"""Dependency injection for FastAPI routes."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from src.llm.client import resolve_llm_api_key
from src.orchestrator import LearningOrchestrator

load_dotenv()


@lru_cache()
def get_orchestrator() -> LearningOrchestrator:
    """Create a singleton orchestrator instance."""
    verification_enabled = os.environ.get("VERIFICATION_ENABLED", "true").strip().lower() not in ("false", "0", "no")
    llm_model = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
    return LearningOrchestrator(
        data_dir=os.environ.get("DATA_DIR", "data"),
        api_key=resolve_llm_api_key(model=llm_model),
        s2_api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
        github_token=os.environ.get("GITHUB_TOKEN"),
        llm_model=llm_model,
        verification_enabled=verification_enabled,
        verification_model=os.environ.get("VERIFICATION_MODEL"),
    )
