# NewLearner - Domain Learning Agent

## Project Overview
A PhD-level AI research domain learning system built around a **textbook/course** architecture.
The system searches academic papers, generates structured textbook outlines via LLM, then
produces deep three-layer content (Intuition → Mechanism → Practice) for each chapter.

### Skill Layers (11 skills)
- Layer 1: Assessment & Planning — Pre-Assessor, **Textbook Planner**
- Layer 2: Knowledge Construction & Verification — Deep Researcher, Accuracy Verifier, Resource Curator
- Layer 3: Learning Delivery & Adaptation — Quiz Engine, Adaptive Controller, Spaced Repetition (FSRS), Practice Generator
- Layer 4: Output & Tracking — Progress Tracker, Material Integrator

### Core Data Flow
```
Assessment → Textbook Outline (paper search + LLM) → Chapter Content Generation → Quiz & Review
```

## Environment
- Python 3.14, conda environment `research_tools`
- Activate: `conda activate research_tools`
- Install: `pip install -e ".[dev]"`
- Run tests: `pytest`
- CLI: `newlearner` or `python -m src.cli`
- Backend: `uvicorn src.api.app:app --reload`
- Frontend: `cd frontend && npm run dev`

## Project Structure
```
src/
  models/          Pydantic data models (Course, Textbook, Chapter, etc.)
  skills/          Python skill implementations (11 skills)
  apis/            External API clients (OpenAlex, arXiv, Semantic Scholar)
  api/             FastAPI backend (routes/, deps.py, app.py)
  llm/             LLM interaction layer (Anthropic API)
  storage/         Persistence (JSON file store, course-scoped)
  logging_config.py
  orchestrator.py  Central workflow coordinator
  cli.py           Typer CLI
frontend/          React + TypeScript + Vite + Tailwind CSS
  src/
    api/client.ts  API client with SSE streaming
    pages/         CoursesPage, NewCoursePage, TextbookPage, ChapterPage, etc.
    components/    Layout, Sidebar, CourseLayout, ContentRenderer, etc.
    contexts/      CourseContext (React Context)
    types/         TypeScript type definitions
templates/         Jinja2 templates for export
tests/             pytest test suite
```

## Data Storage (in data/, gitignored)
```
data/
  courses.json                              Course registry
  courses/{course_id}/
    course.json                             Course metadata
    assessment_profile.json                 Learner profile
    textbook.json                           Textbook outline (chapters)
    progress.json                           Learning progress
    content/{chapter_id}/
      research_synthesis.json               Three-layer chapter content
      resources.json                        Curated resources
      verification_report.json              Accuracy verification
    cards/{chapter_id}/cards.json           Flashcards (FSRS)
    quizzes/{chapter_id}/quiz.json          Chapter quiz
  cache/                                    Shared API cache
```

## API Routes
```
GET/POST        /api/courses                    Course CRUD
GET/DELETE      /api/courses/{id}
GET             /api/courses/{id}/textbook      Textbook outline
GET (SSE)       /api/courses/{id}/textbook/build      Build outline
GET (SSE)       /api/courses/{id}/textbook/generate   Batch generate chapters
GET             /api/courses/{id}/chapters/{ch}        Chapter content
GET (SSE)       /api/courses/{id}/chapters/{ch}/stream Generate single chapter
POST            /api/courses/{id}/chapters/{ch}/quiz/submit
GET             /api/courses/{id}/review/due
POST            /api/courses/{id}/review/{card}
GET             /api/courses/{id}/progress
POST            /api/courses/{id}/export
```

## CLI Commands
```
newlearner create <field>     Create course with assessment
newlearner outline <course>   Build textbook outline
newlearner generate <course>  Generate chapter content
newlearner courses            List all courses
newlearner progress <course>  Show learning progress
newlearner review             Show due flashcards
newlearner export <course>    Export materials
newlearner status             System status
```

## API Keys
Store in `.env` file (gitignored):
- `ANTHROPIC_API_KEY` - Required for LLM operations
- `TAVILY_API_KEY` - Optional, web search for outline generation (tutorials + papers)
- `SEMANTIC_SCHOLAR_API_KEY` - Optional, increases rate limit
- `GITHUB_TOKEN` - Optional, increases rate limit

## Coding Conventions
- Use Pydantic v2 models for all data structures
- Use httpx for HTTP requests (async where beneficial)
- Use rich for CLI output formatting
- Use typer for CLI commands
- All skills follow the same pattern: input model → process → output model
- SSE (Server-Sent Events) for long-running operations
- Tests use pytest with respx for HTTP mocking
- Frontend uses React Router for course-scoped navigation
