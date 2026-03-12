"""Skill 6: Resource Curator - Multi-source high-quality resource recommendation."""

from __future__ import annotations

import asyncio

import httpx

from src.apis.github_client import GitHubClient
from src.apis.papers_with_code import PapersWithCodeClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.llm.client import LLMClient
from src.models.assessment import AssessmentProfile
from src.models.textbook import Chapter
from src.models.resources import Resource, ResourceCollection, ResourceType
from src.storage.local_store import LocalStore

# Known high-quality blog sources
QUALITY_BLOG_SOURCES = [
    "lilianweng.github.io",
    "distill.pub",
    "thegradient.pub",
    "jalammar.github.io",
    "sebastianraschka.com",
    "blog.openai.com",
    "www.anthropic.com/research",
    "deepmind.google/discover",
    "ai.meta.com/blog",
    "ai.googleblog.com",
    "huggingface.co/blog",
]


class ResourceCurator:
    """Multi-source resource recommendation skill."""

    def __init__(
        self,
        llm: LLMClient,
        store: LocalStore,
        semantic_scholar: SemanticScholarClient | None = None,
        papers_with_code: PapersWithCodeClient | None = None,
        github: GitHubClient | None = None,
    ):
        self.llm = llm
        self.store = store
        self.s2 = semantic_scholar
        self.pwc = papers_with_code
        self.github = github

    async def curate(
        self,
        chapter: Chapter,
        profile: AssessmentProfile,
    ) -> ResourceCollection:
        """Curate resources for a concept based on user profile."""
        collection = ResourceCollection(concept_id=chapter.id)

        # Search papers
        if self.s2:
            papers = await self._find_papers(chapter)
            collection.papers = papers

        # Search code repositories
        if self.pwc or self.github:
            code = await self._find_code(chapter)
            collection.code = code

        # Generate blog/video/course recommendations via LLM
        other_resources = await self._recommend_other_resources(chapter, profile)
        collection.blogs = [r for r in other_resources if r.resource_type == ResourceType.BLOG]
        collection.videos = [r for r in other_resources if r.resource_type == ResourceType.VIDEO]
        collection.courses = [r for r in other_resources if r.resource_type == ResourceType.COURSE]

        # Save
        self.store.save_content(chapter.id, "resources.json", collection)
        return collection

    async def _find_papers(self, chapter: Chapter) -> list[Resource]:
        """Find relevant papers from Semantic Scholar."""
        resources = []
        if not self.s2:
            return resources

        try:
            papers = await self.s2.search_papers(
                chapter.title, limit=10, fields_of_study=["Computer Science"]
            )
            for p in papers:
                citations = p.get("citationCount", 0) or 0
                year = p.get("year", 0) or 0
                # Filter: citations > 50 or published within last 6 months
                if citations > 50 or year >= 2025:
                    external_ids = p.get("externalIds", {}) or {}
                    arxiv_id = external_ids.get("ArXiv", "")
                    resources.append(Resource(
                        url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
                        title=p.get("title", ""),
                        resource_type=ResourceType.PAPER,
                        source="Semantic Scholar",
                        quality_score=min(1.0, citations / 1000) if citations > 0 else 0.3,
                        difficulty="advanced",
                        description=(p.get("tldr", {}) or {}).get("text", ""),
                        arxiv_id=arxiv_id,
                        citation_count=citations,
                        relevance="primary" if citations > 200 else "related",
                    ))
        except Exception:
            pass

        return sorted(resources, key=lambda r: r.citation_count, reverse=True)[:8]

    async def _find_code(self, chapter: Chapter) -> list[Resource]:
        """Find code repositories from GitHub and PapersWithCode."""
        resources = []

        if self.pwc:
            try:
                pwc_papers = await self.pwc.search_papers(chapter.title)
                for pp in pwc_papers[:5]:
                    repos = await self.pwc.get_paper_repos(pp.get("id", ""))
                    for repo in repos:
                        url = repo.get("url", "")
                        stars = repo.get("stars", 0) or 0
                        resources.append(Resource(
                            url=url,
                            title=repo.get("name", url),
                            resource_type=ResourceType.CODE,
                            source="PapersWithCode",
                            quality_score=min(1.0, stars / 5000) if stars else 0.3,
                            description=pp.get("title", ""),
                            github_stars=stars,
                            language=repo.get("language", "") or "",
                        ))
            except Exception:
                pass

        if self.github:
            try:
                repos = await self.github.search_repos(chapter.title, limit=5)
                for repo in repos:
                    stars = repo.get("stargazers_count", 0)
                    if stars > 100 or (stars > 10 and repo.get("pushed_at", "") > "2025-01-01"):
                        resources.append(Resource(
                            url=repo.get("html_url", ""),
                            title=repo.get("full_name", ""),
                            resource_type=ResourceType.CODE,
                            source="GitHub",
                            quality_score=min(1.0, stars / 5000),
                            description=repo.get("description", "") or "",
                            github_stars=stars,
                            language=repo.get("language", "") or "",
                        ))
            except Exception:
                pass

        return sorted(resources, key=lambda r: r.github_stars, reverse=True)[:8]

    async def _recommend_other_resources(
        self,
        chapter: Chapter,
        profile: AssessmentProfile,
    ) -> list[Resource]:
        """Use LLM to recommend blogs, videos, and courses."""
        from src.utils.json_repair import repair_json_array

        prompt = f"""Recommend high-quality learning resources for the concept "{chapter.title}"
in the field of {profile.target_field}.

Student learning style: {profile.learning_style.value}
Student goal: {profile.learning_goal.value}

Recommend up to:
- 3 blog posts (prefer: {', '.join(QUALITY_BLOG_SOURCES[:5])})
- 2 video lectures (prefer: Stanford/MIT OCW, Yannic Kilcher, Mu Li)
- 1 university course section

Return JSON array:
[
  {{
    "url": "https://...",
    "title": "Resource title",
    "resource_type": "blog|video|course",
    "source": "Lil'Log|Stanford CS236|Yannic Kilcher",
    "quality_score": 0.0-1.0,
    "difficulty": "beginner|intermediate|advanced",
    "description": "Why this resource is useful (1 sentence)"
  }}
]

Only recommend resources you are confident actually exist. If unsure, omit them."""

        try:
            response = self.llm.generate_json(prompt)
            data = repair_json_array(response)
            resources = []
            for item in data:
                rt = item.get("resource_type", "blog")
                resources.append(Resource(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    resource_type=ResourceType(rt),
                    source=item.get("source", ""),
                    quality_score=item.get("quality_score", 0.5),
                    difficulty=item.get("difficulty", "intermediate"),
                    description=item.get("description", ""),
                ))
            # Validate URLs
            resources = await self._validate_urls(resources)
            return resources
        except Exception:
            return []

    @staticmethod
    async def _validate_urls(resources: list[Resource]) -> list[Resource]:
        """Validate URLs by sending HEAD requests, discard 404s and timeouts."""
        validated = []
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            for r in resources:
                if not r.url:
                    continue
                try:
                    resp = await client.head(r.url)
                    if resp.status_code < 400:
                        validated.append(r)
                except (httpx.HTTPError, httpx.TimeoutException):
                    continue
        return validated
