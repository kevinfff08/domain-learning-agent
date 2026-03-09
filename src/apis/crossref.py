"""CrossRef API client for citation verification."""

from __future__ import annotations

from pathlib import Path

from src.apis.base import BaseAPIClient


class CrossRefClient(BaseAPIClient):
    """Client for CrossRef API - used for DOI verification."""

    BASE_URL = "https://api.crossref.org"

    def __init__(self, cache_dir: Path | None = None):
        super().__init__(
            cache_dir=cache_dir,
            requests_per_second=5.0,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": "NewLearner/0.1 (mailto:research@example.com; research learning agent)",
        }

    async def verify_doi(self, doi: str) -> dict | None:
        """Verify a DOI exists and return metadata."""
        try:
            data = await self.get(f"/works/{doi}")
            return data.get("message", {})
        except Exception:
            return None

    async def search_works(self, query: str, limit: int = 10) -> list[dict]:
        """Search for works by query."""
        params = {
            "query": query,
            "rows": min(limit, 50),
            "select": "DOI,title,author,published-print,container-title,is-referenced-by-count",
        }
        data = await self.get("/works", params=params)
        return data.get("message", {}).get("items", [])

    async def verify_citation(self, doi: str) -> dict:
        """Verify a citation and return structured result.

        Returns:
            dict with keys: exists, title, authors, year, venue, citation_count
        """
        metadata = await self.verify_doi(doi)
        if not metadata:
            return {"exists": False}

        authors = []
        for author in metadata.get("author", []):
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            if name:
                authors.append(name)

        title_list = metadata.get("title", [])
        title = title_list[0] if title_list else ""

        date_parts = metadata.get("published-print", {}).get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else 0

        venue_list = metadata.get("container-title", [])
        venue = venue_list[0] if venue_list else ""

        return {
            "exists": True,
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "citation_count": metadata.get("is-referenced-by-count", 0),
        }
