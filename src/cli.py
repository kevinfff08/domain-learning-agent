"""CLI interface for NewLearner domain learning agent."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
import typer

load_dotenv()

from src.logging_config import setup_logging, get_logger
from src.llm.client import resolve_llm_api_key

setup_logging()
logger = get_logger("cli")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="newlearner",
    help="PhD-level AI research domain learning system",
    no_args_is_help=True,
)
console = Console()


def _get_orchestrator(**kwargs):
    """Create orchestrator with environment config."""
    from src.orchestrator import LearningOrchestrator

    llm_model = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
    return LearningOrchestrator(
        data_dir=kwargs.get("data_dir", "data"),
        api_key=resolve_llm_api_key(model=llm_model),
        s2_api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
        github_token=os.environ.get("GITHUB_TOKEN"),
        llm_model=llm_model,
    )


@app.command()
def create(
    field: str = typer.Argument(help="Target field to learn, e.g., 'Diffusion Models'"),
    math_level: int = typer.Option(3, min=0, max=5, help="Self-rated math level (0-5)"),
    programming_level: int = typer.Option(3, min=0, max=5, help="Self-rated programming level (0-5)"),
    domain_level: int = typer.Option(0, min=0, max=5, help="Self-rated domain knowledge (0-5)"),
    goal: str = typer.Option("understand_concepts", help="Learning goal: understand_concepts, reproduce_papers, improve_methods"),
    hours: float = typer.Option(10.0, help="Available hours per week"),
    style: str = typer.Option("intuition_first", help="Learning style: mathematical_first, code_first, intuition_first"),
):
    """Create a new course with assessment."""
    orch = _get_orchestrator()
    course, profile = orch.create_course(
        field=field,
        assessment_data={
            "math_level": math_level,
            "programming_level": programming_level,
            "domain_level": domain_level,
            "learning_goal": goal,
            "available_hours": hours,
            "learning_style": style,
        },
    )
    console.print(Panel(f"[green]Course '{course.id}' created for '{field}'[/green]"))
    console.print(f"  Math: {math_level}/5 | Programming: {programming_level}/5 | Domain: {domain_level}/5")
    console.print(f"  Goal: {goal} | Style: {style} | Hours/week: {hours}")


@app.command()
def outline(
    course_id: str = typer.Argument(help="Course ID"),
):
    """Build textbook outline for a course."""
    orch = _get_orchestrator()
    textbook = asyncio.run(orch.build_outline(course_id))
    console.print(f"\n[green]Textbook outline saved: {len(textbook.chapters)} chapters, "
                  f"{textbook.total_estimated_hours:.0f} hours[/green]")


@app.command()
def generate(
    course_id: str = typer.Argument(help="Course ID"),
    chapter: str = typer.Option("", help="Specific chapter ID (all if omitted)"),
):
    """Generate content for chapters."""
    orch = _get_orchestrator()
    if chapter:
        result = asyncio.run(orch.generate_chapter(course_id, chapter))
        console.print(f"\n[green]Chapter '{chapter}' generated.[/green]")
    else:
        asyncio.run(orch.generate_all_chapters(course_id))
        console.print(f"\n[green]All chapters generated for '{course_id}'.[/green]")


@app.command()
def courses():
    """List all courses."""
    orch = _get_orchestrator()
    course_list = orch.list_courses()
    if not course_list:
        console.print("[yellow]No courses found. Create one with 'create'.[/yellow]")
        return

    table = Table(title="Courses")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Status", style="green")
    table.add_column("Chapters")
    for c in course_list:
        table.add_row(
            c.get("id", ""),
            c.get("title", ""),
            c.get("status", ""),
            f"{c.get('completed_chapters', 0)}/{c.get('total_chapters', 0)}",
        )
    console.print(table)


@app.command()
def progress(
    course_id: str = typer.Argument(help="Course ID"),
):
    """Show learning progress."""
    from src.models.textbook import Textbook
    orch = _get_orchestrator()
    textbook = orch.store.load_course_model(course_id, "textbook.json", Textbook)
    if not textbook:
        console.print("[red]No textbook found for this course.[/red]")
        raise typer.Exit(1)
    report = orch.get_weekly_report(textbook.field)
    console.print(report)


@app.command()
def export(
    course_id: str = typer.Argument(help="Course ID"),
    formats: str = typer.Option("obsidian", help="Comma-separated: obsidian,anki,html,pdf"),
):
    """Export learning materials."""
    orch = _get_orchestrator()
    fmt_list = [f.strip() for f in formats.split(",")]
    results = asyncio.run(orch.export_materials(course_id, fmt_list))
    for fmt, path in results["items"].items():
        console.print(f"[green]{fmt}: {path}[/green]")
    for fmt, message in results["errors"].items():
        console.print(f"[yellow]{fmt}: {message}[/yellow]")


@app.command()
def review():
    """Show flashcards due for review."""
    orch = _get_orchestrator()
    due = orch.get_due_reviews()
    if not due:
        console.print("[green]No cards due for review![/green]")
        return

    console.print(f"[yellow]{len(due)} cards due for review[/yellow]\n")
    for card in due[:10]:
        console.print(Panel(card.front, title=f"[{card.concept_id}]"))
        console.print(f"  Answer: {card.back}\n")


@app.command()
def status():
    """Show system status and configuration."""
    table = Table(title="NewLearner System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    table.add_row("LLM_PROVIDER", os.environ.get("LLM_PROVIDER", "auto"))
    table.add_row("ANTHROPIC_API_KEY", "Set" if os.environ.get("ANTHROPIC_API_KEY") else "Not set")
    table.add_row("OPENAI_API_KEY", "Set" if os.environ.get("OPENAI_API_KEY") else "Not set")
    table.add_row("SEMANTIC_SCHOLAR_API_KEY", "Set" if os.environ.get("SEMANTIC_SCHOLAR_API_KEY") else "Not set (optional)")
    table.add_row("GITHUB_TOKEN", "Set" if os.environ.get("GITHUB_TOKEN") else "Not set (optional)")
    table.add_row("Data directory", str(Path("data").resolve()))

    orch = _get_orchestrator()
    course_list = orch.list_courses()
    table.add_row("Courses", str(len(course_list)))

    console.print(table)


if __name__ == "__main__":
    app()
