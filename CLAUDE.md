# NewLearner - Domain Learning Agent

## Project Overview
A PhD-level AI research domain learning system with 12 agent skills organized in 4 layers:
- Layer 1: Assessment & Planning (Pre-Assessor, Domain Mapper, Path Visualizer)
- Layer 2: Knowledge Construction & Verification (Deep Researcher, Accuracy Verifier, Resource Curator)
- Layer 3: Learning Delivery & Adaptation (Quiz Engine, Adaptive Controller, Spaced Repetition, Practice Generator)
- Layer 4: Output & Tracking (Progress Tracker, Material Integrator)

## Environment
- Python 3.14, conda environment `research_tools`
- Activate: `conda activate research_tools`
- Install: `pip install -e ".[dev]"`
- Run tests: `pytest`
- CLI: `newlearner` or `python -m src.cli`

## Project Structure
- `src/models/` - Pydantic data models (data contracts between skills)
- `src/skills/` - Python implementations of each skill
- `src/apis/` - External API client wrappers (Semantic Scholar, arXiv, etc.)
- `src/llm/` - LLM interaction layer (Anthropic API)
- `src/storage/` - Persistence (SQLite + JSON)
- `src/export/` - Output format generators (Obsidian, PDF, Anki)
- `skills/` - Claude Code SKILL.md files
- `templates/` - Jinja2 templates for output generation
- `data/` - Runtime data (gitignored)
- `output/` - Generated learning materials (gitignored)
- `tests/` - Test suite

## Key Data Files (in data/, gitignored)
- `data/user/assessment_profile.json` - User diagnostic profile
- `data/graphs/{field}_knowledge_graph.json` - Knowledge graph
- `data/user/progress.json` - Learning progress
- `data/content/{concept_id}/` - Generated content per concept

## API Keys
Store in `.env` file (gitignored):
- `ANTHROPIC_API_KEY` - Required for LLM operations
- `SEMANTIC_SCHOLAR_API_KEY` - Optional, increases rate limit
- `GITHUB_TOKEN` - Optional, increases rate limit

## Coding Conventions
- Use Pydantic v2 models for all data structures
- Use httpx for HTTP requests (async where beneficial)
- Use rich for CLI output formatting
- Use typer for CLI commands
- All skills follow the same pattern: input model -> process -> output model
- Tests use pytest with respx for HTTP mocking
