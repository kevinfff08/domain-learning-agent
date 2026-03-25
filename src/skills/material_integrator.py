"""Skill 12: Material Integrator - Assemble content into multiple output formats."""

from __future__ import annotations

from html import escape
from pathlib import Path

from src.models.content import ResearchSynthesis
from src.models.progress import LearnerProgress
from src.models.quiz import Quiz
from src.models.resources import ResourceCollection
from src.models.textbook import Chapter, Textbook
from src.storage.local_store import LocalStore


class MaterialIntegrator:
    """Assembles all generated content into cohesive output formats."""

    def __init__(self, store: LocalStore):
        self.store = store

    @staticmethod
    def _slugify(value: str) -> str:
        """Create a filesystem-safe lowercase file stem."""
        sanitized = value.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
        return sanitized.lower() or "export"

    def _load_chapter_artifacts(
        self,
        textbook: Textbook,
        chapter: Chapter,
    ) -> tuple[ResearchSynthesis | None, ResourceCollection | None, Quiz | None]:
        """Load export assets with course-scoped storage first and legacy fallback second."""
        course_id = textbook.course_id

        synthesis = self.store.load_course_content(
            course_id, chapter.id, "research_synthesis.json", ResearchSynthesis
        )
        if not synthesis:
            synthesis = self.store.load_content(
                chapter.id, "research_synthesis.json", ResearchSynthesis
            )

        resources = self.store.load_course_content(
            course_id, chapter.id, "resources.json", ResourceCollection
        )
        if not resources:
            resources = self.store.load_content(
                chapter.id, "resources.json", ResourceCollection
            )

        quiz = self.store.load_course_content(course_id, chapter.id, "quiz.json", Quiz)
        if not quiz:
            quiz = self.store.load_content(chapter.id, "quiz.json", Quiz)

        return synthesis, resources, quiz

    def _iter_export_rows(
        self,
        textbook: Textbook,
    ) -> list[tuple[Chapter, ResearchSynthesis | None, ResourceCollection | None, Quiz | None]]:
        """Collect chapter export data once so all output formats stay consistent."""
        return [
            (chapter, *self._load_chapter_artifacts(textbook, chapter))
            for chapter in textbook.chapters
        ]

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
        for chapter, synthesis, resources, _quiz in self._iter_export_rows(textbook):
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

        return vault.resolve()

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

    def export_html(
        self,
        textbook: Textbook,
        output_dir: Path | str = "output/html",
    ) -> Path:
        """Export as a standalone HTML study guide."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        html_path = output_path / f"{self._slugify(textbook.field)}_guide.html"
        html_path.write_text(self._build_html_document(textbook), encoding="utf-8")

        return html_path.resolve()

    def export_pdf(
        self,
        textbook: Textbook,
        output_dir: Path | str = "output/pdf",
    ) -> Path:
        """Export as a PDF study guide."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        pdf_path = output_path / f"{self._slugify(textbook.field)}_guide.pdf"

        try:
            self._build_pdf_with_reportlab(textbook, pdf_path)
        except ImportError as exc:
            try:
                import pypandoc
            except ImportError as pandoc_exc:
                raise RuntimeError(
                    "PDF export requires `reportlab` or `pypandoc`. "
                    "Install one of them in the `research_tools` environment."
                ) from pandoc_exc

            try:
                pypandoc.convert_text(
                    self._build_markdown_document(textbook),
                    "pdf",
                    format="md",
                    outputfile=str(pdf_path),
                )
            except Exception as conversion_exc:
                raise RuntimeError(f"PDF export failed: {conversion_exc}") from conversion_exc
        except Exception as exc:
            raise RuntimeError(f"PDF export failed: {exc}") from exc

        return pdf_path.resolve()

    def _build_markdown_document(self, textbook: Textbook) -> str:
        """Build combined markdown for fallback PDF conversion."""
        md_content = f"# {textbook.title}\n\n"
        md_content += f"Field: {textbook.field}\n\n"
        md_content += f"Generated: {textbook.created_at}\n\n"
        md_content += "---\n\n"

        for chapter, synthesis, resources, quiz in self._iter_export_rows(textbook):
            md_content += f"## {chapter.chapter_number}. {chapter.title}\n\n"

            if chapter.description:
                md_content += f"{chapter.description}\n\n"

            if synthesis:
                if synthesis.intuition.analogy:
                    md_content += f"### Intuition\n\n**Analogy:** {synthesis.intuition.analogy}\n\n"
                if synthesis.intuition.key_insight:
                    md_content += f"**Key Insight:** {synthesis.intuition.key_insight}\n\n"
                if synthesis.intuition.why_it_matters:
                    md_content += f"{synthesis.intuition.why_it_matters}\n\n"

                if synthesis.mechanism.mathematical_framework:
                    md_content += (
                        "### Mathematical Framework\n\n"
                        f"{synthesis.mechanism.mathematical_framework}\n\n"
                    )
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
                    for index, step in enumerate(synthesis.mechanism.algorithm_steps, 1):
                        md_content += f"{index}. {step}\n"
                    md_content += "\n"

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
                    for index, step in enumerate(synthesis.practice.reproduction_checklist, 1):
                        md_content += f"{index}. {step}\n"
                    md_content += "\n"

            if resources and resources.total_resources > 0:
                md_content += "### Resources\n\n"
                for paper in resources.papers[:5]:
                    md_content += f"- [{paper.title}]({paper.url})\n"
                for blog in resources.blogs[:3]:
                    md_content += f"- [{blog.title}]({blog.url})\n"
                for video in resources.videos[:2]:
                    md_content += f"- [{video.title}]({video.url})\n"
                md_content += "\n"

            if quiz and quiz.questions:
                md_content += "### Self-Assessment\n\n"
                for index, question in enumerate(quiz.questions[:3], 1):
                    md_content += f"**Q{index}:** {question.question}\n\n"
                    if question.options:
                        for option_index, option in enumerate(question.options):
                            md_content += f"  {chr(65 + option_index)}. {option}\n"
                        md_content += "\n"

            md_content += "---\n\n"

        return md_content

    def _build_html_document(self, textbook: Textbook) -> str:
        """Build a standalone HTML export."""
        chapter_sections: list[str] = []

        for chapter, synthesis, resources, quiz in self._iter_export_rows(textbook):
            parts = [
                '<section class="chapter">',
                f"<h2>{chapter.chapter_number}. {escape(chapter.title)}</h2>",
            ]

            if chapter.description:
                parts.append(f"<p>{escape(chapter.description)}</p>")

            if synthesis:
                parts.append("<h3>Intuition</h3>")
                if synthesis.intuition.analogy:
                    parts.append(f"<p><strong>Analogy:</strong> {escape(synthesis.intuition.analogy)}</p>")
                if synthesis.intuition.key_insight:
                    parts.append(f"<p><strong>Key insight:</strong> {escape(synthesis.intuition.key_insight)}</p>")
                if synthesis.intuition.why_it_matters:
                    parts.append(f"<p>{escape(synthesis.intuition.why_it_matters)}</p>")

                parts.append("<h3>Mechanism</h3>")
                if synthesis.mechanism.mathematical_framework:
                    parts.append(
                        "<pre>"
                        f"{escape(synthesis.mechanism.mathematical_framework)}"
                        "</pre>"
                    )
                if synthesis.mechanism.key_equations:
                    equation_items = "".join(
                        (
                            f"<li><strong>{escape(eq.name)}</strong>: {escape(eq.latex)}"
                            + (
                                f"<br><span class=\"muted\">{escape(eq.explanation)}</span>"
                                if eq.explanation else ""
                            )
                            + "</li>"
                        )
                        for eq in synthesis.mechanism.key_equations
                    )
                    parts.append(f"<h4>Key Equations</h4><ul>{equation_items}</ul>")
                if synthesis.mechanism.algorithm_steps:
                    step_items = "".join(
                        f"<li>{escape(step)}</li>"
                        for step in synthesis.mechanism.algorithm_steps
                    )
                    parts.append(f"<h4>Steps</h4><ol>{step_items}</ol>")
                elif synthesis.mechanism.pseudocode:
                    parts.append(f"<pre>{escape(synthesis.mechanism.pseudocode)}</pre>")

                parts.append("<h3>Practice</h3>")
                if synthesis.practice.reference_implementations:
                    impl_items = "".join(
                        f"<li>{escape(item)}</li>"
                        for item in synthesis.practice.reference_implementations
                    )
                    parts.append(f"<h4>Reference Implementations</h4><ul>{impl_items}</ul>")
                if synthesis.practice.common_pitfalls:
                    pitfall_items = "".join(
                        f"<li>{escape(item)}</li>"
                        for item in synthesis.practice.common_pitfalls
                    )
                    parts.append(f"<h4>Common Pitfalls</h4><ul>{pitfall_items}</ul>")
                if synthesis.practice.reproduction_checklist:
                    checklist_items = "".join(
                        f"<li>{escape(item)}</li>"
                        for item in synthesis.practice.reproduction_checklist
                    )
                    parts.append(f"<h4>Reproduction Checklist</h4><ol>{checklist_items}</ol>")

            if resources and resources.total_resources > 0:
                resource_items = []
                for resource in [*resources.papers[:5], *resources.blogs[:3], *resources.videos[:2]]:
                    resource_items.append(
                        f'<li><a href="{escape(resource.url)}">{escape(resource.title)}</a></li>'
                    )
                parts.append(f"<h3>Resources</h3><ul>{''.join(resource_items)}</ul>")

            if quiz and quiz.questions:
                question_items = []
                for question in quiz.questions[:3]:
                    options = ""
                    if question.options:
                        options = (
                            "<ol>"
                            + "".join(f"<li>{escape(option)}</li>" for option in question.options)
                            + "</ol>"
                        )
                    question_items.append(f"<li><p>{escape(question.question)}</p>{options}</li>")
                parts.append(f"<h3>Self-Assessment</h3><ol>{''.join(question_items)}</ol>")

            parts.append("</section>")
            chapter_sections.append("\n".join(parts))

        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8">',
                '  <meta name="viewport" content="width=device-width, initial-scale=1">',
                f"  <title>{escape(textbook.title)}</title>",
                "  <style>",
                "    :root { color-scheme: light; }",
                "    body { font-family: Georgia, 'Times New Roman', serif; margin: 0; background: #f5f7fb; color: #132238; }",
                "    main { max-width: 960px; margin: 0 auto; padding: 48px 24px 72px; }",
                "    header { margin-bottom: 32px; }",
                "    .meta { color: #526277; font-size: 14px; }",
                "    .chapter { background: #ffffff; border: 1px solid #d7e0ea; border-radius: 18px; padding: 28px; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(19, 34, 56, 0.06); }",
                "    h1, h2, h3, h4 { color: #0f2650; }",
                "    h1 { margin-bottom: 8px; }",
                "    h2 { margin-top: 0; }",
                "    p, li { line-height: 1.65; }",
                "    ul, ol { padding-left: 22px; }",
                "    pre { background: #f3f6fb; border-radius: 12px; padding: 16px; overflow-x: auto; white-space: pre-wrap; }",
                "    a { color: #0b63ce; }",
                "    .muted { color: #5e6f82; }",
                "  </style>",
                "</head>",
                "<body>",
                "  <main>",
                "    <header>",
                f"      <h1>{escape(textbook.title)}</h1>",
                f"      <p class=\"meta\">Field: {escape(textbook.field)} | Chapters: {len(textbook.chapters)} | Generated: {escape(str(textbook.created_at))}</p>",
                "    </header>",
                *chapter_sections,
                "  </main>",
                "</body>",
                "</html>",
            ]
        )

    def _build_pdf_with_reportlab(self, textbook: Textbook, pdf_path: Path) -> None:
        """Create a PDF using reportlab when available."""
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=textbook.title,
        )
        styles = getSampleStyleSheet()
        base_font_name = self._resolve_reportlab_cjk_font()
        title_style = ParagraphStyle(
            "GuideTitle",
            parent=styles["Title"],
            fontName=base_font_name,
            textColor=HexColor("#0f2650"),
            spaceAfter=12,
        )
        heading_style = ParagraphStyle(
            "GuideHeading",
            parent=styles["Heading2"],
            fontName=base_font_name,
            textColor=HexColor("#163d73"),
            spaceBefore=12,
            spaceAfter=8,
        )
        subheading_style = ParagraphStyle(
            "GuideSubheading",
            parent=styles["Heading3"],
            fontName=base_font_name,
            textColor=HexColor("#285589"),
            spaceBefore=8,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "GuideBody",
            parent=styles["BodyText"],
            fontName=base_font_name,
            leading=15,
            spaceAfter=6,
        )
        code_style = ParagraphStyle(
            "GuideCode",
            parent=styles["Code"],
            fontName=base_font_name,
            fontSize=8.5,
            leading=11,
        )

        story = [
            Paragraph(escape(textbook.title), title_style),
            Paragraph(
                escape(
                    f"Field: {textbook.field} | Chapters: {len(textbook.chapters)} | Generated: {textbook.created_at}"
                ),
                body_style,
            ),
            Spacer(1, 8),
        ]

        for chapter_index, (chapter, synthesis, resources, quiz) in enumerate(self._iter_export_rows(textbook), start=1):
            if chapter_index > 1:
                story.append(PageBreak())

            story.append(
                Paragraph(
                    escape(f"{chapter.chapter_number}. {chapter.title}"),
                    heading_style,
                )
            )

            if chapter.description:
                story.append(Paragraph(self._paragraph_text(chapter.description), body_style))

            if synthesis:
                story.append(Paragraph("Intuition", subheading_style))
                if synthesis.intuition.analogy:
                    story.append(Paragraph(self._paragraph_text(f"Analogy: {synthesis.intuition.analogy}"), body_style))
                if synthesis.intuition.key_insight:
                    story.append(Paragraph(self._paragraph_text(f"Key insight: {synthesis.intuition.key_insight}"), body_style))
                if synthesis.intuition.why_it_matters:
                    story.append(Paragraph(self._paragraph_text(synthesis.intuition.why_it_matters), body_style))

                story.append(Paragraph("Mechanism", subheading_style))
                if synthesis.mechanism.mathematical_framework:
                    story.append(Preformatted(synthesis.mechanism.mathematical_framework, code_style))
                if synthesis.mechanism.key_equations:
                    story.append(
                        ListFlowable(
                            [
                                ListItem(
                                    Paragraph(
                                        self._paragraph_text(
                                            f"{equation.name}: {equation.latex}"
                                            + (f" - {equation.explanation}" if equation.explanation else "")
                                        ),
                                        body_style,
                                    )
                                )
                                for equation in synthesis.mechanism.key_equations
                            ],
                            bulletType="bullet",
                        )
                    )
                if synthesis.mechanism.algorithm_steps:
                    story.append(Paragraph("Steps", subheading_style))
                    story.append(
                        ListFlowable(
                            [
                                ListItem(Paragraph(self._paragraph_text(step), body_style))
                                for step in synthesis.mechanism.algorithm_steps
                            ],
                            bulletType="1",
                        )
                    )
                elif synthesis.mechanism.pseudocode:
                    story.append(Paragraph("Algorithm", subheading_style))
                    story.append(Preformatted(synthesis.mechanism.pseudocode, code_style))

                story.append(Paragraph("Practice", subheading_style))
                if synthesis.practice.reference_implementations:
                    story.append(Paragraph("Reference Implementations", subheading_style))
                    story.append(
                        ListFlowable(
                            [
                                ListItem(Paragraph(self._paragraph_text(item), body_style))
                                for item in synthesis.practice.reference_implementations
                            ],
                            bulletType="bullet",
                        )
                    )
                if synthesis.practice.common_pitfalls:
                    story.append(Paragraph("Common Pitfalls", subheading_style))
                    story.append(
                        ListFlowable(
                            [
                                ListItem(Paragraph(self._paragraph_text(item), body_style))
                                for item in synthesis.practice.common_pitfalls
                            ],
                            bulletType="bullet",
                        )
                    )
                if synthesis.practice.reproduction_checklist:
                    story.append(Paragraph("Reproduction Checklist", subheading_style))
                    story.append(
                        ListFlowable(
                            [
                                ListItem(Paragraph(self._paragraph_text(item), body_style))
                                for item in synthesis.practice.reproduction_checklist
                            ],
                            bulletType="1",
                        )
                    )

            if resources and resources.total_resources > 0:
                story.append(Paragraph("Resources", subheading_style))
                resource_entries = [
                    f"{resource.title}: {resource.url}"
                    for resource in [*resources.papers[:5], *resources.blogs[:3], *resources.videos[:2]]
                ]
                story.append(
                    ListFlowable(
                        [ListItem(Paragraph(self._paragraph_text(item), body_style)) for item in resource_entries],
                        bulletType="bullet",
                    )
                )

            if quiz and quiz.questions:
                story.append(Paragraph("Self-Assessment", subheading_style))
                for index, question in enumerate(quiz.questions[:3], start=1):
                    story.append(Paragraph(self._paragraph_text(f"Q{index}: {question.question}"), body_style))
                    if question.options:
                        story.append(
                            ListFlowable(
                                [
                                    ListItem(Paragraph(self._paragraph_text(option), body_style))
                                    for option in question.options
                                ],
                                bulletType="A",
                            )
                        )
                    story.append(Spacer(1, 4))

        doc.build(story)

    @staticmethod
    def _resolve_reportlab_cjk_font() -> str:
        """Register and return a font name that can render Chinese text in PDFs."""
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfbase.ttfonts import TTFont

        font_candidates = [
            ("NotoSansSC", Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")),
            ("MicrosoftYaHei", Path("C:/Windows/Fonts/msyh.ttc")),
            ("SimHei", Path("C:/Windows/Fonts/simhei.ttf")),
            ("SimSun", Path("C:/Windows/Fonts/simsun.ttc")),
            ("KaiTi", Path("C:/Windows/Fonts/simkai.ttf")),
        ]

        registered_fonts = set(pdfmetrics.getRegisteredFontNames())
        for font_name, font_path in font_candidates:
            if not font_path.exists():
                continue

            if font_name in registered_fonts:
                return font_name

            try:
                if font_path.suffix.lower() == ".ttc":
                    pdfmetrics.registerFont(TTFont(font_name, str(font_path), subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                return font_name
            except Exception:
                continue

        fallback_font = "STSong-Light"
        if fallback_font not in registered_fonts:
            pdfmetrics.registerFont(UnicodeCIDFont(fallback_font))
        return fallback_font

    @staticmethod
    def _paragraph_text(value: str) -> str:
        """Escape plain text for reportlab Paragraph usage."""
        return escape(value).replace("\n", "<br/>")
