"""Semantic Scholar API client."""

from __future__ import annotations

from pathlib import Path

from src.apis.base import BaseAPIClient
from src.models.textbook import PaperReference


class SemanticScholarClient(BaseAPIClient):
    """Client for Semantic Scholar Academic Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    PAPER_FIELDS = "title,authors,year,venue,citationCount,externalIds,abstract,tldr"

    def __init__(self, api_key: str | None = None, cache_dir: Path | None = None):
        super().__init__(
            api_key=api_key,
            cache_dir=cache_dir,
            requests_per_second=10.0 if api_key else 1.0,
        )

    @property
    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": "NewLearner/0.1 (research learning agent)"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def search_papers(
        self,
        query: str,
        limit: int = 20,
        year: str | None = None,
        fields_of_study: list[str] | None = None,
    ) -> list[dict]:
        """Search for papers by keyword query."""
        params: dict = {
            "query": query,
            "limit": min(limit, 100),
            "fields": self.PAPER_FIELDS,
        }
        if year:
            params["year"] = year
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)

        data = await self.get("/paper/search", params=params)
        return data.get("data", [])

    async def get_paper(self, paper_id: str) -> dict:
        """Get paper details by Semantic Scholar ID, arXiv ID, or DOI.

        paper_id formats: S2 ID, 'ARXIV:2006.11239', 'DOI:10.xxx'
        """
        params = {"fields": self.PAPER_FIELDS}
        return await self.get(f"/paper/{paper_id}", params=params)

    async def get_paper_citations(self, paper_id: str, limit: int = 50) -> list[dict]:
        """Get papers that cite this paper."""
        params = {"fields": self.PAPER_FIELDS, "limit": min(limit, 100)}
        data = await self.get(f"/paper/{paper_id}/citations", params=params)
        return [item.get("citingPaper", {}) for item in data.get("data", [])]

    async def get_paper_references(self, paper_id: str, limit: int = 50) -> list[dict]:
        """Get papers referenced by this paper."""
        params = {"fields": self.PAPER_FIELDS, "limit": min(limit, 100)}
        data = await self.get(f"/paper/{paper_id}/references", params=params)
        return [item.get("citedPaper", {}) for item in data.get("data", [])]

    async def get_recommended_papers(self, paper_id: str, limit: int = 20) -> list[dict]:
        """Get recommended papers based on a given paper."""
        params = {"fields": self.PAPER_FIELDS, "limit": min(limit, 100)}
        data = await self.get(f"/recommendations/v1/papers/forpaper/{paper_id}", params=params)
        return data.get("recommendedPapers", [])

    @staticmethod
    def to_paper_reference(paper_data: dict, role: str = "related") -> PaperReference:
        """Convert API response to PaperReference model."""
        external_ids = paper_data.get("externalIds", {}) or {}
        authors = paper_data.get("authors", []) or []
        return PaperReference(
            arxiv_id=external_ids.get("ArXiv", ""),
            doi=external_ids.get("DOI", ""),
            title=paper_data.get("title", ""),
            authors=[a.get("name", "") for a in authors[:5]],
            year=paper_data.get("year", 0) or 0,
            venue=paper_data.get("venue", "") or "",
            citation_count=paper_data.get("citationCount", 0) or 0,
            role=role,
        )
