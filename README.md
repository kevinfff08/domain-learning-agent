# Domain Learning Agent

A PhD-level AI research domain learning system with 12 agent skills. Designed for researchers entering new frontier AI fields (e.g., Diffusion Models, Flow Matching, Neural ODEs), this system provides structured, adaptive, and verified learning paths.

## Features

- **Multi-dimensional assessment** - Goes beyond 0-5 self-rating with diagnostic questions covering math, programming, and domain knowledge
- **Dynamic knowledge graph** - Builds and updates a concept dependency graph from academic sources (Semantic Scholar, arXiv, OpenAlex)
- **PhD-level content synthesis** - Three-layer architecture: Intuition (analogies), Mechanism (math derivations with source attribution), Practice (implementation guides)
- **Accuracy verification** - Anti-hallucination pipeline checking citation existence, math consistency, performance claims, and attribution
- **Adaptive learning** - 4-level intervention when concepts aren't understood (alternative explanation -> prerequisite review -> concept splitting -> Socratic dialogue)
- **Spaced repetition** - SM-2 algorithm with Anki deck export
- **Interactive practice** - Jupyter notebooks, coding challenges, paper reproduction guides
- **Progress tracking** - Mastery metrics, weekly reports, knowledge graph visualization
- **Multi-format export** - Obsidian vault, Anki `.apkg`, D3.js interactive HTML, PDF

## Architecture

```
12 Skills across 4 Layers:

Layer 1: Assessment & Planning
  [1] Pre-Assessor      - Multi-dimensional diagnostic assessment
  [2] Domain Mapper      - Multi-source knowledge graph construction
  [3] Path Visualizer    - Learning path visualization (D3.js + ASCII)

Layer 2: Knowledge Construction & Verification
  [4] Deep Researcher    - PhD-level three-layer content synthesis
  [5] Accuracy Verifier  - Citation/math/claims verification
  [6] Resource Curator   - Papers, blogs, videos, code, courses

Layer 3: Learning Delivery & Adaptation
  [7] Quiz Engine        - Multi-type questions with Bloom's taxonomy
  [8] Adaptive Controller - 4-level "can't understand" intervention
  [9] Spaced Repetition  - SM-2 algorithm + Anki export
  [10] Practice Generator - Notebooks, challenges, reproduction guides

Layer 4: Output & Tracking
  [11] Progress Tracker  - Metrics, weekly reports, dashboard
  [12] Material Integrator - Obsidian/PDF/HTML export
```

## Prerequisites

- Python 3.14+
- Node.js 18+ (for web frontend)
- Conda (recommended)
- Anthropic API key **or** Claude subscription + [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI)

## Installation

```bash
# Create conda environment
conda create -n research_tools python=3.14
conda activate research_tools

# Clone and install Python backend
git clone https://github.com/kevinfff08/domain-learning-agent.git
cd domain-learning-agent
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

## Configuration

Copy the example environment file and choose your LLM connection mode:

```bash
cp .env.example .env
```

### Mode A: API Key (default)

Set `LLM_MODE=api-key` in `.env` and fill in your Anthropic API key:

```env
LLM_MODE=api-key
ANTHROPIC_API_KEY=sk-ant-api03-...
```

> **Note**: The Anthropic API requires a separate key from [console.anthropic.com](https://console.anthropic.com). A Claude Pro/Max subscription does **not** include API access.

### Mode B: Setup Token (Claude subscription)

If you have a Claude Pro/Max subscription and don't want to pay for separate API credits, you can route requests through [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI):

```env
LLM_MODE=setup-token
LLM_PROXY_URL=http://localhost:8317
```

Setup:
1. Install CLIProxyAPI: `brew install cliproxyapi` (macOS) or see the project README
2. Authenticate: `cliproxyapi --claude-login`
3. The startup script (`start.bat` / `start.sh`) will automatically launch the proxy

### All `.env` fields

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_MODE` | No | `api-key` (default) or `setup-token` |
| `ANTHROPIC_API_KEY` | api-key mode | Get from [console.anthropic.com](https://console.anthropic.com) |
| `LLM_PROXY_URL` | No | Proxy URL for setup-token mode (default: `http://localhost:8317`) |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Higher rate limits for paper search |
| `GITHUB_TOKEN` | No | Repository quality metrics |
| `LLM_MODEL` | No | Override default model (default: `claude-sonnet-4-20250514`) |
| `API_HOST` | No | Backend host (default: `127.0.0.1`) |
| `API_PORT` | No | Backend port (default: `8000`) |

## Usage

### Web Interface (Recommended)

The web frontend provides an interactive learning experience with real-time content streaming.

**One-click startup:**

```bash
# Windows
start.bat

# Linux / macOS / WSL
./start.sh
```

This automatically starts the backend API, frontend dev server, and CLIProxyAPI proxy (if using setup-token mode).

**Or start manually:**

```bash
# Terminal 1: backend
conda activate research_tools
uvicorn src.api.app:app --reload --port 8000

# Terminal 2: frontend
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser.

**Web UI features:**
- Real-time progress tracking during content generation (SSE streaming)
- Three-layer content rendering with LaTeX math (KaTeX) and syntax-highlighted code
- Interactive knowledge graph visualization (D3.js force-directed)
- Interactive quiz with immediate feedback + downloadable quiz files (with answers)
- Flashcard review with 3D flip animation and SM-2 scheduling
- Progress dashboard with charts
- Multi-format export (Obsidian, Anki, PDF, HTML)

### CLI Commands

```bash
# 1. Run assessment for a target field
newlearner assess "Diffusion Models" --math-level 4 --programming-level 3 --goal reproduce_papers

# 2. Build knowledge graph
newlearner map "Diffusion Models"

# 3. Learn a specific concept
newlearner learn ddpm

# 4. View progress
newlearner progress "Diffusion Models"

# 5. Export materials
newlearner export "Diffusion Models" --formats "obsidian,anki,html"

# 6. Review flashcards
newlearner review

# 7. Check system status
newlearner status
```

### Complete Workflow

```
User: "I want to learn Diffusion Models"
        |
        v
[1. Pre-Assessor] --> assessment_profile.json
        |
        v
[2. Domain Mapper] --> knowledge_graph.json (30+ concepts)
        |
        v
[3. Path Visualizer] --> Interactive D3.js map + ASCII overview
        |
        v
=== Concept Loop (for each concept in learning_path) ===
        |
        v
[4. Deep Researcher] --> Three-layer PhD content
        |
        v
[5. Accuracy Verifier] --> Hallucination risk score
        |                   (risk > 0.3 = human review)
        |
[6. Resource Curator] --> Papers, blogs, code repos
        |
        v
[7. Quiz Engine] --> Multi-type assessment
        |
        |-- score >= 70% --> [9] Anki cards + [10] Practice --> Next concept
        |-- score 40-60% --> [8 L1] Alternative explanation --> Re-quiz
        |-- score < 40%  --> [8 L2] Prerequisite review --> Update graph
        |-- persistent   --> [8 L3/4] Concept split / Socratic dialogue
=== End Loop ===
        |
        v
[11. Progress Tracker] --> Weekly reports + dashboard
[12. Material Integrator] --> Obsidian vault / PDF / HTML
[9. Spaced Repetition] --> Daily review reminders
```

## Project Structure

```
NewLearner/
├── pyproject.toml             # Project config & dependencies
├── .env.example               # Environment variable template
├── start.bat                  # One-click startup (Windows)
├── start.sh                   # One-click startup (Linux/macOS)
├── CLAUDE.md                  # Claude Code project instructions
│
├── frontend/                  # React web frontend
│   ├── package.json
│   ├── vite.config.ts         # Vite config (proxy /api → backend)
│   └── src/
│       ├── App.tsx            # Routes
│       ├── api/client.ts      # REST + SSE API client
│       ├── pages/             # 8 page components
│       │   ├── HomePage.tsx
│       │   ├── AssessmentPage.tsx
│       │   ├── KnowledgeGraphPage.tsx
│       │   ├── LearningPage.tsx       # Core: SSE streaming content
│       │   ├── QuizPage.tsx
│       │   ├── ReviewPage.tsx
│       │   ├── ProgressPage.tsx
│       │   └── ExportPage.tsx
│       └── components/        # Reusable UI components
│           ├── KnowledgeGraph.tsx     # D3.js force-directed graph
│           ├── ContentRenderer.tsx    # Three-layer content + KaTeX
│           ├── FlashCard.tsx          # 3D flip card
│           └── ...
│
├── skills/                    # SKILL.md files for Claude Code integration
│   ├── pre-assessor/
│   ├── domain-mapper/
│   ├── ...
│   └── material-integrator/
│
├── src/
│   ├── cli.py                 # Typer CLI entry point
│   ├── orchestrator.py        # Workflow engine (wires 12 skills)
│   ├── api/                   # FastAPI backend
│   │   ├── app.py             # App config, CORS, routers
│   │   ├── deps.py            # Dependency injection
│   │   └── routes/            # API endpoints
│   │       ├── assessment.py  # POST/GET /api/assessment
│   │       ├── graph.py       # Graph build (SSE) + query
│   │       ├── learning.py    # Content stream (SSE) + retrieval
│   │       ├── quiz.py        # Quiz interaction + export
│   │       ├── review.py      # Spaced repetition + Anki export
│   │       ├── progress.py    # Progress metrics
│   │       └── export.py      # Multi-format export
│   ├── models/                # Pydantic v2 data models
│   │   ├── assessment.py      # AssessmentProfile, DiagnosticQuestion
│   │   ├── knowledge_graph.py # KnowledgeGraph, ConceptNode, GraphEdge
│   │   ├── content.py         # ResearchSynthesis (3-layer architecture)
│   │   ├── quiz.py            # Quiz, QuizResult (Bloom's taxonomy)
│   │   ├── cards.py           # FlashCard, SM2State
│   │   ├── progress.py        # LearnerProgress, ConceptProgress
│   │   ├── resources.py       # ResourceCollection
│   │   └── verification.py    # VerificationReport, VerificationCheck
│   ├── skills/                # 12 skill implementations
│   ├── apis/                  # Academic API clients
│   │   ├── base.py            # RateLimiter, ResponseCache, BaseAPIClient
│   │   ├── semantic_scholar.py
│   │   ├── arxiv_client.py
│   │   ├── crossref.py
│   │   ├── open_alex.py
│   │   ├── papers_with_code.py
│   │   └── github_client.py
│   ├── llm/                   # Anthropic API wrapper
│   │   └── client.py
│   ├── storage/               # JSON file persistence
│   │   └── local_store.py
│   └── export/                # Output format generators
│
├── templates/                 # Jinja2 templates
├── data/                      # Runtime data (gitignored)
├── output/                    # Generated materials (gitignored)
└── tests/                     # Test suite (76 tests)
```

## Data Models

All skills communicate through Pydantic v2 models that serve as data contracts:

| Model | File | Purpose |
|-------|------|---------|
| `AssessmentProfile` | `assessment.py` | Multi-dimensional learner profile |
| `KnowledgeGraph` | `knowledge_graph.py` | Concept dependency graph with mastery tracking |
| `ResearchSynthesis` | `content.py` | Three-layer content (intuition/mechanism/practice) |
| `Quiz` / `QuizResult` | `quiz.py` | Bloom's taxonomy questions with scoring |
| `FlashCard` / `SM2State` | `cards.py` | Spaced repetition with SM-2 algorithm |
| `LearnerProgress` | `progress.py` | Per-concept and aggregate progress metrics |
| `ResourceCollection` | `resources.py` | Curated papers, blogs, videos, code, courses |
| `VerificationReport` | `verification.py` | Accuracy checks with hallucination risk score |

## API Integrations

| API | Usage | Skills |
|-----|-------|--------|
| Semantic Scholar | Paper search, citations, metadata | 2, 5, 6 |
| arXiv | Paper search, PDF access | 2, 4 |
| CrossRef | DOI verification, citation validation | 5 |
| OpenAlex | Subject classification, trends | 2 |
| Papers With Code | Paper-to-code mapping | 6, 10 |
| GitHub | Repository quality metrics | 6 |
| Anthropic Claude | All LLM reasoning and generation | All skills |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test module
pytest tests/test_models/test_cards.py

# Run only unit tests (skip integration)
pytest -m "not integration"
```

Test coverage includes:
- Data model validation and computed properties
- SM-2 spaced repetition algorithm correctness
- Adaptive controller state machine transitions
- Storage layer round-trip serialization
- Path visualization output generation
- Progress tracking with graph synchronization

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Project conventions
# - Pydantic v2 models as inter-skill contracts
# - httpx for async HTTP (with rate limiting and caching)
# - All file paths use pathlib.Path
# - JSON for persistence (via LocalStore)
# - Rich for CLI output formatting
```

## License

MIT
