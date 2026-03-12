"""Tavily web search client for academic/tutorial content discovery."""

from __future__ import annotations

import asyncio
import os

from src.logging_config import get_logger

logger = get_logger("apis.tavily")


class TavilySearchClient:
    """Thin async wrapper around the Tavily Python SDK.

    Used by TextbookPlanner to find surveys, tutorials, and blog posts
    that complement traditional academic paper search.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self.api_key)
            except ImportError:
                logger.warning("tavily-python not installed — Tavily search disabled")

    @property
    def available(self) -> bool:
        return self._client is not None

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web. Returns list of {title, content, url}.

        The Tavily SDK is synchronous, so we run it in a thread.
        """
        if not self._client:
            return []
        try:
            response = await asyncio.to_thread(
                self._client.search,
                query=query,
                max_results=max_results,
                search_depth="basic",
            )
            results = response.get("results", [])
            logger.info("Tavily search '%s': %d results", query, len(results))
            return results
        except Exception as exc:
            logger.warning("Tavily search failed for '%s': %s", query, exc)
            return []
