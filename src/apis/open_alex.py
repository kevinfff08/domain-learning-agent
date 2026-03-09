"""OpenAlex API client for academic data."""

from __future__ import annotations

from pathlib import Path

from src.apis.base import BaseAPIClient


class OpenAlexClient(BaseAPIClient):
    """Client for OpenAlex API - free open academic graph."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: str = "", cache_dir: Path | None = None):
        super().__init__(
            cache_dir=cache_dir,
            requests_per_second=10.0,
        )
        self.email = email

    @property
    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": "NewLearner/0.1 (research learning agent)"}
        if self.email:
            headers["User-Agent"] = f"NewLearner/0.1 (mailto:{self.email})"
        return headers

    async def search_works(
        self,
        query: str,
        limit: int = 25,
        sort: str = "cited_by_count:desc",
        from_year: int | None = None,
    ) -> list[dict]:
        """Search for academic works."""
        params: dict = {
            "search": query,
            "per_page": min(limit, 50),
            "sort": sort,
        }
        if from_year:
            params["filter"] = f"from_publication_date:{from_year}-01-01"

        data = await self.get("/works", params=params)
        return data.get("results", [])

    async def get_concept(self, concept_name: str) -> dict | None:
        """Search for an academic concept/topic."""
        params = {"search": concept_name, "per_page": 1}
        data = await self.get("/concepts", params=params)
        results = data.get("results", [])
        return results[0] if results else None

    async def get_topic(self, topic_name: str) -> dict | None:
        """Search for a topic in OpenAlex's topic taxonomy."""
        params = {"search": topic_name, "per_page": 1}
        data = await self.get("/topics", params=params)
        results = data.get("results", [])
        return results[0] if results else None

    async def get_related_concepts(self, concept_id: str) -> list[dict]:
        """Get concepts related to a given concept."""
        data = await self.get(f"/concepts/{concept_id}")
        return data.get("related_concepts", [])

    async def get_trending_works(
        self,
        topic: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get trending/recent high-impact works for a topic."""
        params: dict = {
            "search": topic,
            "per_page": min(limit, 50),
            "sort": "publication_date:desc",
            "filter": "from_publication_date:2025-01-01,cited_by_count:>5",
        }
        data = await self.get("/works", params=params)
        return data.get("results", [])
