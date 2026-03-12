"""OpenAlex API client for academic data."""

from __future__ import annotations

from pathlib import Path

from src.apis.base import BaseAPIClient
from src.models.textbook import PaperReference


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

    @staticmethod
    def reconstruct_abstract(inverted_index: dict | None) -> str:
        """Reconstruct plain-text abstract from OpenAlex abstract_inverted_index."""
        if not inverted_index:
            return ""
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        return " ".join(w for _, w in word_positions)

    @staticmethod
    def to_paper_reference(work: dict, role: str = "related") -> PaperReference:
        """Convert an OpenAlex work dict (raw or normalized) to PaperReference."""
        # Handle both raw OpenAlex format and normalize_work() output
        if "authorships" in work:
            # Raw OpenAlex format
            authorships = work.get("authorships", []) or []
            authors = [
                a.get("author", {}).get("display_name", "")
                for a in authorships[:5]
                if a.get("author")
            ]
            year = work.get("publication_year", 0) or 0
            citation_count = work.get("cited_by_count", 0) or 0
            doi_raw = work.get("doi") or ""
            doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""
        else:
            # Normalized format (from normalize_work)
            authors = work.get("authors", [])[:5]
            year = work.get("year", 0) or 0
            citation_count = work.get("citationCount", 0) or 0
            doi = work.get("doi", "")
        return PaperReference(
            arxiv_id="",
            doi=doi,
            title=work.get("title", ""),
            authors=authors,
            year=year,
            venue="",
            citation_count=citation_count,
            role=role,
        )

    @staticmethod
    def normalize_work(work: dict) -> dict:
        """Normalize an OpenAlex work to the common dict format used by domain_mapper."""
        authorships = work.get("authorships", []) or []
        abstract = OpenAlexClient.reconstruct_abstract(
            work.get("abstract_inverted_index")
        )
        doi_raw = work.get("doi") or ""
        return {
            "title": work.get("title", ""),
            "authors": [
                a.get("author", {}).get("display_name", "")
                for a in authorships[:5]
                if a.get("author")
            ],
            "year": work.get("publication_year", 0) or 0,
            "abstract": abstract,
            "citationCount": work.get("cited_by_count", 0) or 0,
            "doi": doi_raw.replace("https://doi.org/", "") if doi_raw else "",
            "_source": "openalex",
        }

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
