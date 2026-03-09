"""External API client wrappers."""

from src.apis.arxiv_client import ArxivClient
from src.apis.crossref import CrossRefClient
from src.apis.github_client import GitHubClient
from src.apis.open_alex import OpenAlexClient
from src.apis.papers_with_code import PapersWithCodeClient
from src.apis.semantic_scholar import SemanticScholarClient

__all__ = [
    "ArxivClient",
    "CrossRefClient",
    "GitHubClient",
    "OpenAlexClient",
    "PapersWithCodeClient",
    "SemanticScholarClient",
]
