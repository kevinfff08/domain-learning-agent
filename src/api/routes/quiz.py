"""Quiz API routes (legacy — prefer /courses/{id}/chapters/{id}/quiz/submit)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.api.deps import get_orchestrator
from src.models.quiz import Quiz, QuizResult
from src.orchestrator import LearningOrchestrator

router = APIRouter()


@router.get("/quiz/{concept_id}")
def get_quiz(
    concept_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get quiz for a concept/chapter (legacy path)."""
    quiz = orch.store.load_content(concept_id, "quiz.json", Quiz)
    if not quiz:
        return {"error": f"No quiz found for '{concept_id}'."}
    return json.loads(quiz.model_dump_json())


@router.get("/quiz/{concept_id}/result")
def get_quiz_result(
    concept_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get previous quiz result."""
    result = orch.store.load_content(concept_id, "quiz_result.json", QuizResult)
    if not result:
        return {"error": f"No quiz result found for '{concept_id}'."}
    return json.loads(result.model_dump_json())


@router.get("/quiz/{concept_id}/export")
def export_quiz(
    concept_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Export quiz as Markdown file."""
    quiz = orch.store.load_content(concept_id, "quiz.json", Quiz)
    if not quiz:
        return {"error": f"No quiz found for '{concept_id}'."}

    result = orch.store.load_content(concept_id, "quiz_result.json", QuizResult)

    lines = [f"# Quiz: {concept_id}\n"]
    lines.append(f"Total questions: {len(quiz.questions)}\n")
    if result:
        lines.append(f"Score: {result.overall_score:.0%} ({'PASSED' if result.passed else 'FAILED'})\n")
    lines.append("---\n")

    for i, q in enumerate(quiz.questions, 1):
        lines.append(f"## Question {i} [{q.question_type.value}] (Bloom: {q.bloom_level.value})\n")
        lines.append(f"{q.question}\n")

        if q.options:
            for j, opt in enumerate(q.options):
                marker = "-> " if j == q.correct_answer else "   "
                lines.append(f"{marker}{chr(65 + j)}. {opt}")
            lines.append("")

        if q.code_template:
            lines.append(f"```python\n{q.code_template}\n```\n")

        lines.append(f"**Answer:** {q.explanation}\n")

        if q.solution_steps:
            lines.append("**Solution steps:**")
            for step in q.solution_steps:
                lines.append(f"- {step}")
            lines.append("")

        if result:
            r = next((r for r in result.results if r.question_id == q.id), None)
            if r:
                status = "Correct" if r.is_correct else "Incorrect"
                lines.append(f"**Your answer:** {r.user_answer} ({status}, score: {r.score:.0%})")
                if r.feedback:
                    lines.append(f"**Feedback:** {r.feedback}")
            lines.append("")

        lines.append("---\n")

    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="quiz_{concept_id}.md"'},
    )
