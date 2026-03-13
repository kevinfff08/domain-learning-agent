"""Skill 7: Quiz Engine - Multi-type assessment with Bloom's taxonomy."""

from __future__ import annotations

import json
import uuid

from src.llm.client import LLMClient
from src.utils.json_repair import repair_json, repair_json_array
from src.models.assessment import AssessmentProfile, LearningGoal
from src.models.content import ResearchSynthesis
from src.models.quiz import (
    BloomLevel,
    Question,
    QuestionResult,
    QuestionType,
    Quiz,
    QuizResult,
)
from src.storage.local_store import LocalStore

SYSTEM_PROMPT = """You are an expert AI educator creating assessment questions.
Questions must test genuine understanding, not surface-level recall.
For PhD-level students, include derivation and code completion questions.
Return valid JSON only."""

QUIZ_GENERATION_PROMPT = """Create assessment questions for the concept: "{concept_name}"

Content summary:
- Key insight: {key_insight}
- Key equations: {equations}
- Algorithm steps: {algorithm_steps}

Student's learning goal: {learning_goal}
Previous quiz scores for this concept: {prev_scores}

Generate {count} questions with a mix of types and Bloom levels:
- Multiple choice (2-3 questions, testing recall/comprehension)
- Derivation (1 question if goal is reproduce_papers, testing application)
- Code completion (1 question if goal is reproduce_papers, testing application)
- Concept comparison (1 question, testing analysis)

Return JSON:
[
  {{
    "id": "q1",
    "question_type": "multiple_choice|derivation|code_completion|concept_comparison",
    "bloom_level": "remember|understand|apply|analyze|evaluate|create",
    "question": "Question text",
    "difficulty": 1-5,
    "concept_id": "{concept_id}",
    "options": ["A", "B", "C", "D"],
    "correct_answer": 0,
    "solution_steps": [],
    "code_template": "",
    "expected_solution": "",
    "concepts_to_compare": [],
    "explanation": "Why this is the correct answer",
    "source_paper": "arXiv ID if applicable"
  }}
]

Adapt difficulty based on previous scores: {difficulty_guidance}
"""


class QuizEngine:
    """Multi-type assessment skill with Bloom's taxonomy."""

    def __init__(self, llm: LLMClient, store: LocalStore):
        self.llm = llm
        self.store = store

    def generate_quiz(
        self,
        synthesis: ResearchSynthesis,
        profile: AssessmentProfile,
        previous_scores: list[float] | None = None,
    ) -> Quiz:
        """Generate a quiz for a concept."""
        # Determine question count and difficulty guidance
        goal = profile.learning_goal
        count = 5 if goal == LearningGoal.REPRODUCE else 4

        if previous_scores:
            avg = sum(previous_scores) / len(previous_scores)
            if avg > 0.8:
                difficulty_guidance = "Student is doing well - increase difficulty, focus on analysis/evaluation"
            elif avg > 0.5:
                difficulty_guidance = "Student has moderate understanding - mix comprehension and application"
            else:
                difficulty_guidance = "Student is struggling - focus on comprehension questions with worked examples"
        else:
            difficulty_guidance = "First attempt - start with comprehension, include 1-2 application questions"

        equations_text = "\n".join(
            f"- {eq.name}: {eq.latex[:80]}" for eq in synthesis.mechanism.key_equations[:5]
        )

        prompt = QUIZ_GENERATION_PROMPT.format(
            concept_name=synthesis.title,
            concept_id=synthesis.concept_id,
            key_insight=synthesis.intuition.key_insight,
            equations=equations_text or "No specific equations",
            algorithm_steps="\n".join(synthesis.mechanism.algorithm_steps[:5]) or "No algorithm steps",
            learning_goal=goal.value,
            prev_scores=str(previous_scores) if previous_scores else "None (first attempt)",
            count=count,
            difficulty_guidance=difficulty_guidance,
        )

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)
        questions_data = repair_json_array(response)

        questions = []
        for q in questions_data:
            # Coerce correct_answer to int (LLM may return "" for non-MC questions)
            raw_answer = q.get("correct_answer", 0)
            try:
                correct_answer = int(raw_answer) if raw_answer != "" else 0
            except (ValueError, TypeError):
                correct_answer = 0

            # Clamp difficulty to valid range
            try:
                difficulty = max(1, min(5, int(q.get("difficulty", 3))))
            except (ValueError, TypeError):
                difficulty = 3

            questions.append(Question(
                id=q.get("id", f"q{len(questions) + 1}"),
                question_type=QuestionType(q.get("question_type", "multiple_choice")),
                bloom_level=BloomLevel(q.get("bloom_level", "understand")),
                question=q.get("question", ""),
                difficulty=difficulty,
                concept_id=q.get("concept_id", synthesis.concept_id),
                options=q.get("options", []),
                correct_answer=correct_answer,
                solution_steps=q.get("solution_steps", []),
                code_template=q.get("code_template", ""),
                expected_solution=q.get("expected_solution", ""),
                concepts_to_compare=q.get("concepts_to_compare", []),
                explanation=q.get("explanation", ""),
                source_paper=q.get("source_paper", ""),
            ))

        quiz = Quiz(
            id=str(uuid.uuid4())[:8],
            concept_id=synthesis.concept_id,
            questions=questions,
        )

        self.store.save_content(synthesis.concept_id, "quiz.json", quiz)
        return quiz

    def evaluate_answers(
        self,
        quiz: Quiz,
        answers: dict[str, str | int],
    ) -> QuizResult:
        """Evaluate user's answers and produce results."""
        results = []
        bloom_scores: dict[str, list[float]] = {}

        for question in quiz.questions:
            user_answer = answers.get(question.id, "")
            is_correct = False
            score = 0.0

            if question.question_type == QuestionType.MULTIPLE_CHOICE:
                try:
                    answer_idx = int(user_answer)
                    is_correct = answer_idx == question.correct_answer
                    score = 1.0 if is_correct else 0.0
                except (ValueError, TypeError):
                    score = 0.0

            elif question.question_type in (QuestionType.DERIVATION, QuestionType.CODE_COMPLETION):
                # Use LLM to grade open-ended answers
                graded = self._grade_open_answer(question, str(user_answer))
                score = graded if graded is not None else 0.0
                is_correct = score >= 0.7

            elif question.question_type == QuestionType.CONCEPT_COMPARISON:
                graded = self._grade_open_answer(question, str(user_answer))
                score = graded if graded is not None else 0.0
                is_correct = score >= 0.7

            results.append(QuestionResult(
                question_id=question.id,
                user_answer=str(user_answer),
                is_correct=is_correct,
                score=score,
                feedback=question.explanation if not is_correct else "Correct!",
            ))

            # Track Bloom level scores
            bloom = question.bloom_level.value
            if bloom not in bloom_scores:
                bloom_scores[bloom] = []
            bloom_scores[bloom].append(score)

        overall = sum(r.score for r in results) / len(results) if results else 0.0

        quiz_result = QuizResult(
            quiz_id=quiz.id,
            concept_id=quiz.concept_id,
            results=results,
            overall_score=overall,
            bloom_scores={k: sum(v) / len(v) for k, v in bloom_scores.items()},
        )

        self.store.save_content(quiz.concept_id, "quiz_result.json", quiz_result)
        return quiz_result

    def _grade_open_answer(self, question: Question, answer: str) -> float | None:
        """Use LLM to grade an open-ended answer with multi-sample consistency.

        Calls LLM 3 times with different temperatures and takes the mean.
        If standard deviation > 0.3, adds a 4th call and takes median.
        Returns None if all LLM calls fail (caller should handle retry).
        """
        prompt = f"""Grade this student answer on a scale of 0.0 to 1.0.

Question: {question.question}
Expected answer/solution: {question.expected_solution or question.explanation}
Solution steps: {json.dumps(question.solution_steps) if question.solution_steps else 'N/A'}

Student's answer: {answer}

Return JSON: {{"score": 0.0-1.0, "feedback": "brief feedback"}}"""

        temperatures = [0.2, 0.3, 0.4]
        scores: list[float] = []

        for temp in temperatures:
            try:
                response = self.llm.generate_json(prompt, temperature=temp)
                result = json.loads(response)
                scores.append(float(result.get("score", 0.0)))
            except Exception:
                continue

        if not scores:
            return None

        # Check consistency
        mean_score = sum(scores) / len(scores)
        if len(scores) >= 2:
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            std_dev = variance ** 0.5
            if std_dev > 0.3:
                # High disagreement - add a 4th "arbiter" call
                try:
                    response = self.llm.generate_json(prompt, temperature=0.1)
                    result = json.loads(response)
                    scores.append(float(result.get("score", 0.0)))
                except Exception:
                    pass
                # Use median for robustness
                scores.sort()
                mid = len(scores) // 2
                return scores[mid] if len(scores) % 2 else (scores[mid - 1] + scores[mid]) / 2

        return mean_score
