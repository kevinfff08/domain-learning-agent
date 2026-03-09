"""GitHub API client for repository quality assessment."""

from __future__ import annotations

from pathlib import Path

from src.apis.base import BaseAPIClient


class GitHubClient(BaseAPIClient):
    """Client for GitHub API - repository quality metrics."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None, cache_dir: Path | None = None):
        super().__init__(
            api_key=token,
            cache_dir=cache_dir,
            requests_per_second=5.0 if token else 0.5,
        )

    @property
    def headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": "NewLearner/0.1",
            "Accept": "application/vnd.github.v3+json",
        }
        if self.api_key:
            headers["Authorization"] = f"token {self.api_key}"
        return headers

    async def get_repo(self, owner: str, repo: str) -> dict:
        """Get repository information."""
        return await self.get(f"/repos/{owner}/{repo}")

    async def get_repo_quality(self, owner: str, repo: str) -> dict:
        """Assess repository quality for learning resource recommendation.

        Returns quality metrics useful for deciding if a repo is a good learning resource.
        """
        repo_data = await self.get_repo(owner, repo)

        return {
            "full_name": repo_data.get("full_name", ""),
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": repo_data.get("language", ""),
            "description": repo_data.get("description", ""),
            "has_readme": True,  # Most repos have README
            "updated_at": repo_data.get("updated_at", ""),
            "created_at": repo_data.get("created_at", ""),
            "license": (repo_data.get("license") or {}).get("spdx_id", ""),
            "archived": repo_data.get("archived", False),
            "topics": repo_data.get("topics", []),
        }

    async def search_repos(
        self,
        query: str,
        language: str = "Python",
        sort: str = "stars",
        limit: int = 10,
    ) -> list[dict]:
        """Search for repositories."""
        search_query = f"{query} language:{language}"
        params = {
            "q": search_query,
            "sort": sort,
            "order": "desc",
            "per_page": min(limit, 30),
        }
        data = await self.get("/search/repositories", params=params)
        return data.get("items", [])

    @staticmethod
    def parse_repo_url(url: str) -> tuple[str, str]:
        """Parse owner and repo name from a GitHub URL.

        Returns (owner, repo) tuple.
        """
        url = url.rstrip("/")
        if "github.com" in url:
            parts = url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        return "", ""
