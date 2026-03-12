"""Skill: Textbook Planner — generates textbook outline from paper search + LLM."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime

from src.apis.arxiv_client import ArxivClient
from src.apis.open_alex import OpenAlexClient
from src.apis.tavily_client import TavilySearchClient
from src.llm.client import LLMClient
from src.logging_config import get_logger
from src.utils.json_repair import repair_json_array
from src.models.assessment import AssessmentProfile
from src.models.textbook import Chapter, ChapterStatus, PaperReference, Textbook
from src.storage.local_store import LocalStore

logger = get_logger("skills.textbook_planner")

SYSTEM_PROMPT = """You are an expert textbook author for PhD-level technical domains.
You design comprehensive, well-structured learning curricula.
Return valid JSON only."""


class TextbookPlanner:
    """Generates textbook outlines by combining paper search results with LLM."""

    def __init__(
        self,
        llm: LLMClient,
        store: LocalStore,
        openalex: OpenAlexClient | None = None,
        arxiv: ArxivClient | None = None,
        tavily: TavilySearchClient | None = None,
    ):
        self.llm = llm
        self.store = store
        self.openalex = openalex
        self.arxiv = arxiv
        self.tavily = tavily

    # ------------------------------------------------------------------
    # Search methods
    # ------------------------------------------------------------------

    async def _search_web(self, field: str) -> list[dict]:
        """Search the web for tutorials, surveys, and blog posts via Tavily."""
        if not self.tavily or not self.tavily.available:
            return []
        results: list[dict] = []
        queries = [
            f"{field} tutorial introduction guide",
            f"{field} survey overview comprehensive",
        ]
        for query in queries:
            hits = await self.tavily.search(query, max_results=5)
            results.extend(hits)
        return results

    async def _search_surveys(self, field: str) -> list[dict]:
        """Search for survey papers. Priority: OpenAlex > arXiv."""
        surveys: list[dict] = []

        if self.openalex:
            try:
                results = await self.openalex.search_works(
                    f"{field} survey", limit=5, sort="cited_by_count:desc",
                )
                surveys.extend(OpenAlexClient.normalize_work(r) for r in results)
            except Exception:
                pass

        if self.arxiv:
            try:
                results = await self.arxiv.search(
                    f"{field} survey review tutorial",
                    max_results=5,
                    categories=["cs.AI", "cs.LG", "cs.CL", "cs.CV"],
                )
                surveys.extend(results)
            except Exception:
                pass

        return surveys

    async def _search_key_papers(self, field: str) -> list[dict]:
        """Search for highly-cited key papers. Priority: OpenAlex."""
        papers: list[dict] = []

        if self.openalex:
            try:
                results = await self.openalex.search_works(
                    field, limit=20, sort="cited_by_count:desc",
                )
                papers.extend(OpenAlexClient.normalize_work(r) for r in results[:10])
            except Exception:
                pass

        return papers

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_references(
        self,
        surveys: list[dict],
        key_papers: list[dict],
        web_results: list[dict] | None = None,
    ) -> str:
        """Format all search results into a text block for the LLM prompt."""
        lines: list[str] = []

        # Web results first — tutorials and blogs are great for outline design
        for w in (web_results or [])[:10]:
            title = w.get("title", "Unknown")
            content = (w.get("content") or "")[:300]
            url = w.get("url", "")
            lines.append(f"- [网络资源] {title}\n  {url}\n  {content}")

        for s in surveys[:5]:
            title = s.get("title", "Unknown")
            abstract = (s.get("abstract") or s.get("summary") or "")[:300]
            citations = s.get("citationCount", s.get("citation_count", "N/A"))
            lines.append(f"- [综述] {title} (citations: {citations})\n  {abstract}")

        for p in key_papers[:10]:
            title = p.get("title", "Unknown")
            abstract = (p.get("abstract") or p.get("summary") or "")[:200]
            citations = p.get("citationCount", p.get("citation_count", "N/A"))
            lines.append(f"- [关键论文] {title} (citations: {citations})\n  {abstract}")

        return "\n".join(lines) if lines else "No references found — use your expertise."

    def _build_paper_refs(self, surveys: list[dict], key_papers: list[dict]) -> list[PaperReference]:
        """Convert paper dicts to PaperReference models."""
        refs: list[PaperReference] = []
        for p in surveys:
            refs.append(self._to_paper_ref(p, "survey"))
        for p in key_papers:
            refs.append(self._to_paper_ref(p, "key_paper"))
        return refs

    @staticmethod
    def _to_paper_ref(p: dict, role: str) -> PaperReference:
        source = p.get("_source", "")
        if source == "openalex":
            return OpenAlexClient.to_paper_reference(p, role=role)
        elif "arxiv_id" in p:
            return ArxivClient.to_paper_reference(p, role=role)
        return PaperReference(
            title=p.get("title", ""),
            authors=p.get("authors", [])[:5] if isinstance(p.get("authors"), list) else [],
            year=p.get("year", 0),
            citation_count=p.get("citationCount", 0) or p.get("citation_count", 0),
            role=role,
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def generate_outline(
        self,
        course_id: str,
        profile: AssessmentProfile,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> Textbook:
        """Generate a textbook outline by searching papers then using LLM.

        Args:
            course_id: The course this textbook belongs to.
            profile: User assessment profile.
            on_progress: Optional ``(step_id, message)`` callback for SSE.
        """
        field = profile.target_field

        def _emit(step: str, msg: str) -> None:
            logger.info("outline [%s] %s", step, msg)
            if on_progress:
                on_progress(step, msg)

        # --- Step 1: Search all sources in parallel ---
        _emit("search", f"正在搜索 '{field}' 相关资料（论文、教程、博客）…")

        web_results, surveys, key_papers = await asyncio.gather(
            self._search_web(field),
            self._search_surveys(field),
            self._search_key_papers(field),
        )

        total = len(web_results) + len(surveys) + len(key_papers)
        _emit("search_done", f"找到 {total} 条参考资料（网络 {len(web_results)}, 综述 {len(surveys)}, 论文 {len(key_papers)}）")

        references = self._format_references(surveys, key_papers, web_results)

        # --- Step 2: LLM generate outline ---
        _emit("generate_outline", "正在生成教材大纲…")

        math_level = round(sum([
            profile.math_foundations.linear_algebra.level,
            profile.math_foundations.probability.level,
            profile.math_foundations.calculus.level,
            profile.math_foundations.optimization.level,
        ]) / 4)
        prog_level = round(sum([
            profile.programming.python.level,
            profile.programming.pytorch.level,
        ]) / 2)

        prompt = f"""你是一位 {field} 领域的教材编写专家。基于以下领域参考资料（包含论文、教程、博客等），
为一位数学水平 {math_level}/5、编程水平 {prog_level}/5 的学生设计一本系统的学习教材大纲。

学习目标: {profile.learning_goal.value}

领域参考资料（论文、教程、博客）:
{references}

要求:
- 从基础到前沿，循序渐进
- 每章有明确的标题、描述和关键概念列表
- 包含理论分析、实验方法、代码实践相关章节
- 总共 15-30 章
- 难度 1-5 (1=入门, 5=前沿研究)
- 预估每章学习时间(小时)

返回 JSON 数组，每个元素格式:
{{
  "chapter_number": 1,
  "title": "章节标题",
  "description": "章节描述和学习目标",
  "difficulty": 3,
  "estimated_hours": 2.0,
  "key_topics": ["关键概念1", "关键概念2"],
  "tags": ["标签1"]
}}"""

        response = self.llm.generate(prompt, system=SYSTEM_PROMPT, max_tokens=8192)
        chapters_data = repair_json_array(response)
        _emit("generate_outline_done", f"生成了 {len(chapters_data)} 个章节")

        # --- Step 3: Build Textbook ---
        _emit("build_textbook", "正在构建教材结构…")
        chapters: list[Chapter] = []
        for i, ch_data in enumerate(chapters_data, 1):
            ch_num = ch_data.get("chapter_number", i)
            ch_id = f"ch{ch_num:02d}_{self._slugify(ch_data.get('title', f'chapter_{i}'))}"
            chapters.append(Chapter(
                id=ch_id,
                chapter_number=ch_num,
                title=ch_data.get("title", f"Chapter {i}"),
                description=ch_data.get("description", ""),
                difficulty=ch_data.get("difficulty", 3),
                estimated_hours=ch_data.get("estimated_hours", 2.0),
                key_topics=ch_data.get("key_topics", []),
                tags=ch_data.get("tags", []),
            ))

        paper_refs = self._build_paper_refs(surveys, key_papers)

        textbook = Textbook(
            course_id=course_id,
            field=field,
            title=f"{field}：从理论到实践",
            chapters=chapters,
            survey_papers=paper_refs,
            total_estimated_hours=sum(ch.estimated_hours for ch in chapters),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.store.save_course_model(course_id, "textbook.json", textbook)
        _emit("build_textbook_done", f"教材构建完成：{len(chapters)} 章，预计 {textbook.total_estimated_hours:.0f} 小时")
        return textbook

    @staticmethod
    def _slugify(text: str) -> str:
        """Create a simple slug from text."""
        import re
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "_", slug).strip("_")
        return slug[:40]
