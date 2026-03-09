"""CLI interface for NewLearner domain learning agent."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
import typer

load_dotenv()

from src.logging_config import setup_logging, get_logger

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

    return LearningOrchestrator(
        data_dir=kwargs.get("data_dir", "data"),
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        s2_api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
        github_token=os.environ.get("GITHUB_TOKEN"),
    )


@app.command()
def assess(
    field: str = typer.Argument(help="Target field to learn, e.g., 'Diffusion Models'"),
    quick: bool = typer.Option(True, help="Use quick self-assessment instead of diagnostic quiz"),
    math_level: int = typer.Option(3, min=0, max=5, help="Self-rated math level (0-5)"),
    programming_level: int = typer.Option(3, min=0, max=5, help="Self-rated programming level (0-5)"),
    domain_level: int = typer.Option(0, min=0, max=5, help="Self-rated domain knowledge (0-5)"),
    goal: str = typer.Option("understand_concepts", help="Learning goal: understand_concepts, reproduce_papers, improve_methods"),
    hours: float = typer.Option(10.0, help="Available hours per week"),
    style: str = typer.Option("intuition_first", help="Learning style: mathematical_first, code_first, intuition_first"),
):
    """Run background assessment and create user profile."""
    orch = _get_orchestrator()
    profile = asyncio.run(orch.run_assessment(
        field, quick, math_level, programming_level, domain_level, goal, hours, style,
    ))
    console.print(Panel(f"[green]Assessment complete for '{field}'[/green]"))
    console.print(f"  Math: {math_level}/5 | Programming: {programming_level}/5 | Domain: {domain_level}/5")
    console.print(f"  Goal: {goal} | Style: {style} | Hours/week: {hours}")


@app.command()
def map(
    field: str = typer.Argument(help="Target field (must match assessment)"),
):
    """Build knowledge graph from assessment profile."""
    from src.models.assessment import AssessmentProfile

    orch = _get_orchestrator()
    profile = orch.store.load_assessment(AssessmentProfile)
    if not profile:
        console.print("[red]No assessment found. Run 'assess' first.[/red]")
        raise typer.Exit(1)

    graph = asyncio.run(orch.build_knowledge_graph(profile))
    console.print(f"\n[green]Knowledge graph saved with {len(graph.nodes)} concepts.[/green]")


@app.command()
def learn(
    concept: str = typer.Argument(help="Concept ID to learn"),
    field: str = typer.Option("", help="Field name (auto-detected if omitted)"),
):
    """Learn a specific concept (generates content, quiz, exercises)."""
    from src.models.assessment import AssessmentProfile
    from src.models.knowledge_graph import KnowledgeGraph

    orch = _get_orchestrator()
    profile = orch.store.load_assessment(AssessmentProfile)
    if not profile:
        console.print("[red]No assessment found. Run 'assess' first.[/red]")
        raise typer.Exit(1)

    field_name = field or profile.target_field
    graph = orch.store.load_knowledge_graph(field_name, KnowledgeGraph)
    if not graph:
        console.print("[red]No knowledge graph found. Run 'map' first.[/red]")
        raise typer.Exit(1)

    result = asyncio.run(orch.learn_concept(concept, graph, profile))
    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
    else:
        console.print(f"\n[green]Content ready for '{concept}'. Take the quiz to proceed.[/green]")


@app.command()
def progress(
    field: str = typer.Argument(help="Field name"),
):
    """Show learning progress."""
    orch = _get_orchestrator()
    report = orch.get_weekly_report(field)
    console.print(report)


@app.command()
def export(
    field: str = typer.Argument(help="Field name"),
    formats: str = typer.Option("obsidian", help="Comma-separated: obsidian,anki,html,pdf"),
):
    """Export learning materials."""
    from src.models.knowledge_graph import KnowledgeGraph

    orch = _get_orchestrator()
    graph = orch.store.load_knowledge_graph(field, KnowledgeGraph)
    if not graph:
        console.print("[red]No knowledge graph found.[/red]")
        raise typer.Exit(1)

    fmt_list = [f.strip() for f in formats.split(",")]
    results = asyncio.run(orch.export_materials(graph, fmt_list))
    for fmt, path in results.items():
        console.print(f"[green]{fmt}: {path}[/green]")


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

    table.add_row("ANTHROPIC_API_KEY", "Set" if os.environ.get("ANTHROPIC_API_KEY") else "[red]Not set[/red]")
    table.add_row("SEMANTIC_SCHOLAR_API_KEY", "Set" if os.environ.get("SEMANTIC_SCHOLAR_API_KEY") else "Not set (optional)")
    table.add_row("GITHUB_TOKEN", "Set" if os.environ.get("GITHUB_TOKEN") else "Not set (optional)")
    table.add_row("Data directory", str(Path("data").resolve()))

    # Check for existing data
    store = _get_orchestrator().store
    from src.models.assessment import AssessmentProfile
    profile = store.load_assessment(AssessmentProfile)
    table.add_row("Assessment", "Found" if profile else "Not created")

    console.print(table)


if __name__ == "__main__":
    app()
