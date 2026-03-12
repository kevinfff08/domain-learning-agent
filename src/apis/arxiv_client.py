"""arXiv API client."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from src.apis.base import RateLimiter, ResponseCache
from src.models.textbook import PaperReference

# arXiv API uses Atom XML, not JSON
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivClient:
    """Client for arXiv API (Atom XML-based)."""

    BASE_URL = "http://export.arxiv.org/api"

    def __init__(self, cache_dir: Path | None = None):
        self.rate_limiter = RateLimiter(requests_per_second=0.33)  # 3 sec between requests
        self.cache = ResponseCache(cache_dir) if cache_dir else None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def search(
        self,
        query: str,
        max_results: int = 20,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        categories: list[str] | None = None,
    ) -> list[dict]:
        """Search arXiv papers.

        Args:
            query: Search query (supports arXiv query syntax)
            max_results: Maximum number of results
            sort_by: 'relevance', 'lastUpdatedDate', 'submittedDate'
            sort_order: 'ascending', 'descending'
            categories: Filter by arXiv categories, e.g. ['cs.AI', 'cs.LG']
        """
        search_query = query
        if categories:
            cat_filter = " OR ".join(f"cat:{c}" for c in categories)
            search_query = f"({query}) AND ({cat_filter})"

        params = {
            "search_query": f"all:{search_query}",
            "start": 0,
            "max_results": min(max_results, 100),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        url = f"{self.BASE_URL}/query"
        cache_key = url

        if self.cache:
            cached = self.cache.get(cache_key, params)
            if cached is not None:
                return cached

        await self.rate_limiter.acquire()
        client = await self._get_client()
        response = await client.get(url, params=params)
        response.raise_for_status()

        papers = self._parse_atom_response(response.text)

        if self.cache:
            self.cache.set(cache_key, params, papers)

        return papers

    async def get_paper(self, arxiv_id: str) -> dict | None:
        """Get a specific paper by arXiv ID."""
        results = await self.search(f"id:{arxiv_id}", max_results=1)
        return results[0] if results else None

    def _parse_atom_response(self, xml_text: str) -> list[dict]:
        """Parse arXiv Atom XML response into list of dicts."""
        root = ET.fromstring(xml_text)
        papers = []

        for entry in root.findall("atom:entry", ARXIV_NS):
            paper = self._parse_entry(entry)
            if paper:
                papers.append(paper)

        return papers

    def _parse_entry(self, entry: ET.Element) -> dict:
        """Parse a single Atom entry."""
        title = entry.findtext("atom:title", "", ARXIV_NS).strip().replace("\n", " ")
        summary = entry.findtext("atom:summary", "", ARXIV_NS).strip()
        published = entry.findtext("atom:published", "", ARXIV_NS)
        updated = entry.findtext("atom:updated", "", ARXIV_NS)

        # Extract arXiv ID from the entry ID URL
        entry_id = entry.findtext("atom:id", "", ARXIV_NS)
        arxiv_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id

        # Remove version suffix for cleaner ID
        arxiv_id_clean = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id

        authors = []
        for author in entry.findall("atom:author", ARXIV_NS):
            name = author.findtext("atom:name", "", ARXIV_NS)
            if name:
                authors.append(name)

        categories = []
        for cat in entry.findall("atom:category", ARXIV_NS):
            term = cat.get("term", "")
            if term:
                categories.append(term)

        # Get PDF link
        pdf_url = ""
        for link in entry.findall("atom:link", ARXIV_NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
                break

        year = int(published[:4]) if published else 0

        return {
            "arxiv_id": arxiv_id_clean,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "published": published,
            "updated": updated,
            "pdf_url": pdf_url,
            "year": year,
        }

    @staticmethod
    def to_paper_reference(paper_data: dict, role: str = "related") -> PaperReference:
        """Convert API response to PaperReference model."""
        return PaperReference(
            arxiv_id=paper_data.get("arxiv_id", ""),
            title=paper_data.get("title", ""),
            authors=paper_data.get("authors", [])[:5],
            year=paper_data.get("year", 0),
            role=role,
        )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
