"""RAG Provider interface for pluggable retrieval backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RAGProvider(Protocol):
    """Protocol for retrieval-augmented generation providers."""

    async def query(self, text: str, mode: str = "hybrid") -> list[dict]:
        """Query the RAG backend.

        Args:
            text: Query text.
            mode: Retrieval mode (e.g. "hybrid", "semantic", "keyword").

        Returns:
            List of dicts with at least "title", "content", and "source" keys.
        """
        ...


class SimpleRAG:
    """Wraps S2 + arXiv search as a RAG provider (default implementation)."""

    def __init__(self, semantic_scholar=None, arxiv=None):
        self.s2 = semantic_scholar
        self.arxiv = arxiv

    async def query(self, text: str, mode: str = "hybrid") -> list[dict]:
        results: list[dict] = []

        if self.s2:
            try:
                papers = await self.s2.search_papers(text, limit=5)
                for p in papers:
                    abstract = (p.get("abstract") or p.get("summary") or "")[:300]
                    results.append({
                        "title": p.get("title", ""),
                        "content": abstract,
                        "source": f"S2:{p.get('paperId', '')}",
                        "year": p.get("year", 0),
                    })
            except Exception:
                pass

        if self.arxiv:
            try:
                papers = await self.arxiv.search(text, max_results=3)
                for p in papers:
                    abstract = (p.get("abstract") or p.get("summary") or "")[:300]
                    results.append({
                        "title": p.get("title", ""),
                        "content": abstract,
                        "source": f"arXiv:{p.get('arxiv_id', '')}",
                        "year": p.get("year", 0),
                    })
            except Exception:
                pass

        return results
