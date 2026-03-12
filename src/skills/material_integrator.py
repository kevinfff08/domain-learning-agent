"""Skill 12: Material Integrator - Assemble content into multiple output formats."""

from __future__ import annotations

from pathlib import Path

from src.models.content import ResearchSynthesis
from src.models.textbook import Chapter, Textbook
from src.models.progress import LearnerProgress
from src.models.quiz import Quiz
from src.models.resources import ResourceCollection
from src.storage.local_store import LocalStore


class MaterialIntegrator:
    """Assembles all generated content into cohesive output formats."""

    def __init__(self, store: LocalStore):
        self.store = store

    def export_obsidian(
        self,
        textbook: Textbook,
        progress: LearnerProgress | None = None,
        output_dir: Path | str = "output/obsidian",
    ) -> Path:
        """Export as Obsidian vault with wikilinks and frontmatter."""
        vault = Path(output_dir)
        (vault / "chapters").mkdir(parents=True, exist_ok=True)
        (vault / "resources").mkdir(parents=True, exist_ok=True)

        # Generate MOC (Map of Content)
        moc_lines = [f"# {textbook.title} - Table of Contents\n"]
        moc_lines.append(f"Field: {textbook.field}\n")
        moc_lines.append(f"Total chapters: {len(textbook.chapters)}\n")
        moc_lines.append("## Chapters\n")
        for chapter in textbook.chapters:
            moc_lines.append(f"{chapter.chapter_number}. [[{chapter.title}]] (difficulty: {chapter.difficulty}/5)")
        (vault / "_MOC.md").write_text("\n".join(moc_lines), encoding="utf-8")

        # Generate chapter pages
        glossary_terms: dict[str, str] = {}
        for chapter in textbook.chapters:
            synthesis = self.store.load_content(
                chapter.id, "research_synthesis.json", ResearchSynthesis
            )
            resources = self.store.load_content(
                chapter.id, "resources.json", ResourceCollection
            )

            page = self._build_chapter_page(chapter, textbook, synthesis, resources)
            safe_name = chapter.title.replace("/", "-").replace("\\", "-")
            (vault / "chapters" / f"{safe_name}.md").write_text(page, encoding="utf-8")

            # Collect glossary terms
            if synthesis and synthesis.intuition.key_insight:
                glossary_terms[chapter.title] = synthesis.intuition.key_insight

        # Generate glossary
        glossary_lines = ["# Glossary\n"]
        for term, definition in sorted(glossary_terms.items()):
            glossary_lines.append(f"**{term}**: {definition}\n")
        (vault / "_Glossary.md").write_text("\n".join(glossary_lines), encoding="utf-8")

        return vault

    def _build_chapter_page(
        self,
        chapter: Chapter,
        textbook: Textbook,
        synthesis: ResearchSynthesis | None,
        resources: ResourceCollection | None,
    ) -> str:
        """Build a single chapter page in Obsidian format."""
        # Frontmatter
        lines = [
            "---",
            f"chapter_id: {chapter.id}",
            f"chapter_number: {chapter.chapter_number}",
            f"difficulty: {chapter.difficulty}",
            f"status: {chapter.status.value}",
            f"mastery: {chapter.mastery}",
            f"estimated_hours: {chapter.estimated_hours}",
            f"tags: [{', '.join(chapter.tags)}]",
            f"key_topics: [{', '.join(chapter.key_topics)}]",
            "---",
            "",
            f"# {chapter.chapter_number}. {chapter.title}",
            "",
        ]

        if chapter.description:
            lines.append(f"> {chapter.description}\n")

        # Previous chapter link
        prev_ch = textbook.get_chapter_by_number(chapter.chapter_number - 1)
        next_ch = textbook.get_chapter_by_number(chapter.chapter_number + 1)
        if prev_ch:
            lines.append(f"Previous: [[{prev_ch.title}]]\n")

        if synthesis:
            # Intuition layer
            lines.append("## Intuition\n")
            if synthesis.intuition.analogy:
                lines.append(f"**Analogy:** {synthesis.intuition.analogy}\n")
            if synthesis.intuition.why_it_matters:
                lines.append(f"**Why it matters:** {synthesis.intuition.why_it_matters}\n")
            if synthesis.intuition.key_insight:
                lines.append(f"**Key insight:** {synthesis.intuition.key_insight}\n")

            # Mechanism layer
            lines.append("## Mechanism\n")
            if synthesis.mechanism.mathematical_framework:
                lines.append(synthesis.mechanism.mathematical_framework)
                lines.append("")

            if synthesis.mechanism.key_equations:
                lines.append("### Key Equations\n")
                for eq in synthesis.mechanism.key_equations:
                    lines.append(f"**{eq.name}**: ${eq.latex}$")
                    if eq.explanation:
                        lines.append(f"  {eq.explanation}")
                    lines.append("")

            if synthesis.mechanism.pseudocode:
                lines.append("### Algorithm\n")
                lines.append(f"```\n{synthesis.mechanism.pseudocode}\n```\n")

            # Connections
            if synthesis.mechanism.connections:
                lines.append("### Connections to Other Chapters\n")
                for conn in synthesis.mechanism.connections:
                    target = textbook.get_chapter(conn.target_concept_id)
                    target_name = target.title if target else conn.target_concept_id
                    lines.append(f"- **[[{target_name}]]**: {conn.relationship}")
                lines.append("")

            # Practice layer
            lines.append("## Practice\n")
            if synthesis.practice.reference_implementations:
                lines.append("### Reference Implementations")
                for impl in synthesis.practice.reference_implementations:
                    lines.append(f"- {impl}")
                lines.append("")

            if synthesis.practice.common_pitfalls:
                lines.append("### Common Pitfalls")
                for pitfall in synthesis.practice.common_pitfalls:
                    lines.append(f"- {pitfall}")
                lines.append("")

        # Resources
        if resources and resources.total_resources > 0:
            lines.append("## Resources\n")
            for paper in resources.papers[:5]:
                lines.append(f"- [{paper.title}]({paper.url}) (citations: {paper.citation_count})")
            for blog in resources.blogs[:3]:
                lines.append(f"- [{blog.title}]({blog.url}) ({blog.source})")
            for video in resources.videos[:2]:
                lines.append(f"- [{video.title}]({video.url}) ({video.channel})")
            lines.append("")

        # Next chapter link
        if next_ch:
            lines.append(f"\n---\nNext: [[{next_ch.title}]]\n")

        return "\n".join(lines)

    def export_pdf(
        self,
        textbook: Textbook,
        output_dir: Path | str = "output/pdf",
    ) -> Path | None:
        """Export as PDF study guide (requires pypandoc)."""
        try:
            import pypandoc
        except ImportError:
            return None

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Build combined markdown
        md_content = f"# {textbook.title}\n\n"
        md_content += f"Field: {textbook.field}\n\n"
        md_content += f"Generated: {textbook.created_at}\n\n"
        md_content += "---\n\n"

        for chapter in textbook.chapters:
            synthesis = self.store.load_content(
                chapter.id, "research_synthesis.json", ResearchSynthesis
            )
            resources = self.store.load_content(
                chapter.id, "resources.json", ResourceCollection
            )
            quiz = self.store.load_content(chapter.id, "quiz.json", Quiz)

            if synthesis:
                md_content += f"## {chapter.chapter_number}. {chapter.title}\n\n"

                # Intuition layer
                if synthesis.intuition.analogy:
                    md_content += f"**Analogy:** {synthesis.intuition.analogy}\n\n"
                if synthesis.intuition.key_insight:
                    md_content += f"**Key Insight:** {synthesis.intuition.key_insight}\n\n"
                if synthesis.intuition.why_it_matters:
                    md_content += f"{synthesis.intuition.why_it_matters}\n\n"

                # Mechanism layer
                if synthesis.mechanism.mathematical_framework:
                    md_content += f"### Mathematical Framework\n\n{synthesis.mechanism.mathematical_framework}\n\n"
                if synthesis.mechanism.key_equations:
                    md_content += "### Key Equations\n\n"
                    for eq in synthesis.mechanism.key_equations:
                        md_content += f"**{eq.name}**: ${eq.latex}$\n\n"
                        if eq.explanation:
                            md_content += f"{eq.explanation}\n\n"
                if synthesis.mechanism.pseudocode:
                    md_content += f"### Algorithm\n\n```\n{synthesis.mechanism.pseudocode}\n```\n\n"
                if synthesis.mechanism.algorithm_steps:
                    md_content += "### Steps\n\n"
                    for i, step in enumerate(synthesis.mechanism.algorithm_steps, 1):
                        md_content += f"{i}. {step}\n"
                    md_content += "\n"

                # Practice layer
                if synthesis.practice.reference_implementations:
                    md_content += "### Reference Implementations\n\n"
                    for impl in synthesis.practice.reference_implementations:
                        md_content += f"- {impl}\n"
                    md_content += "\n"
                if synthesis.practice.common_pitfalls:
                    md_content += "### Common Pitfalls\n\n"
                    for pitfall in synthesis.practice.common_pitfalls:
                        md_content += f"- {pitfall}\n"
                    md_content += "\n"
                if synthesis.practice.reproduction_checklist:
                    md_content += "### Reproduction Checklist\n\n"
                    for i, step in enumerate(synthesis.practice.reproduction_checklist, 1):
                        md_content += f"{i}. {step}\n"
                    md_content += "\n"

            # Resources
            if resources and resources.total_resources > 0:
                md_content += "### Resources\n\n"
                for paper in resources.papers[:5]:
                    md_content += f"- [{paper.title}]({paper.url})\n"
                for blog in resources.blogs[:3]:
                    md_content += f"- [{blog.title}]({blog.url})\n"
                md_content += "\n"

            # Quiz questions
            if quiz and quiz.questions:
                md_content += "### Self-Assessment\n\n"
                for i, q in enumerate(quiz.questions[:3], 1):
                    md_content += f"**Q{i}:** {q.question}\n\n"
                    if q.options:
                        for j, opt in enumerate(q.options):
                            md_content += f"  {chr(65 + j)}. {opt}\n"
                        md_content += "\n"
                md_content += "\n"

            md_content += "---\n\n"

        pdf_path = output_path / f"{textbook.field.replace(' ', '_').lower()}_guide.pdf"
        pypandoc.convert_text(md_content, "pdf", format="md", outputfile=str(pdf_path))

        return pdf_path
