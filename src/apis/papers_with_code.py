"""Papers With Code API client."""

from __future__ import annotations

from pathlib import Path

from src.apis.base import BaseAPIClient


class PapersWithCodeClient(BaseAPIClient):
    """Client for Papers With Code API - linking papers to implementations."""

    BASE_URL = "https://paperswithcode.com/api/v1"

    def __init__(self, cache_dir: Path | None = None):
        super().__init__(
            cache_dir=cache_dir,
            requests_per_second=2.0,
        )

    async def search_papers(self, query: str, limit: int = 10) -> list[dict]:
        """Search for papers."""
        params = {"q": query, "page": 1, "items_per_page": min(limit, 50)}
        data = await self.get("/papers/", params=params)
        return data.get("results", [])

    async def get_paper_repos(self, paper_id: str) -> list[dict]:
        """Get code repositories for a paper."""
        data = await self.get(f"/papers/{paper_id}/repositories/")
        return data.get("results", [])

    async def search_methods(self, query: str, limit: int = 10) -> list[dict]:
        """Search for ML methods/techniques."""
        params = {"q": query, "page": 1, "items_per_page": min(limit, 50)}
        data = await self.get("/methods/", params=params)
        return data.get("results", [])

    async def get_method(self, method_id: str) -> dict:
        """Get details about a specific method."""
        return await self.get(f"/methods/{method_id}/")

    async def search_datasets(self, query: str, limit: int = 10) -> list[dict]:
        """Search for datasets."""
        params = {"q": query, "page": 1, "items_per_page": min(limit, 50)}
        data = await self.get("/datasets/", params=params)
        return data.get("results", [])

    async def get_sota_results(self, task: str, dataset: str) -> list[dict]:
        """Get state-of-the-art results for a task/dataset combination."""
        params = {"q": f"{task} {dataset}"}
        data = await self.get("/evaluations/", params=params)
        return data.get("results", [])
