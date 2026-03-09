"""Skill 1: Pre-Assessor - Multi-dimensional diagnostic assessment."""

from __future__ import annotations

import json

from src.llm.client import LLMClient
from src.models.assessment import (
    AssessmentProfile,
    DiagnosticQuestion,
    DiagnosticResult,
    LearningGoal,
    LearningStyle,
    MathFoundations,
    ProgrammingSkills,
    SkillLevel,
)
from src.storage.local_store import LocalStore

SYSTEM_PROMPT = """You are an expert AI research educator assessing a PhD student's background.
Generate diagnostic questions to accurately assess their knowledge level.
Your questions should be precise, testing actual understanding rather than surface familiarity.
Return valid JSON only."""

QUESTION_GENERATION_PROMPT = """Generate diagnostic questions to assess a student who wants to learn "{field}".

Generate exactly {count} multiple-choice questions covering these dimensions:
- Math foundations: linear algebra, probability, calculus, optimization
- Programming: Python, PyTorch, JAX, distributed training
- Domain knowledge: related concepts to {field}

Each question should have 4 options with exactly one correct answer.

Return a JSON array of objects with this structure:
[
  {{
    "id": "q1",
    "dimension": "probability",
    "question": "What is the KL divergence between two distributions p and q?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": 0,
    "difficulty": 3,
    "explanation": "Brief explanation of why the answer is correct"
  }}
]

Focus on concepts that are prerequisites for understanding {field}.
Include questions at varying difficulty levels (1-5).
"""

ASSESSMENT_PROMPT = """Based on the following diagnostic results, assess the student's background profile.

Target field: {field}
Diagnostic results:
{results_text}

Analyze the results and return a JSON object with this structure:
{{
  "math_foundations": {{
    "linear_algebra": {{"level": 0-5, "gaps": ["list of identified gaps"]}},
    "probability": {{"level": 0-5, "gaps": []}},
    "calculus": {{"level": 0-5, "gaps": []}},
    "optimization": {{"level": 0-5, "gaps": []}}
  }},
  "programming": {{
    "python": {{"level": 0-5, "gaps": []}},
    "pytorch": {{"level": 0-5, "gaps": []}},
    "jax": {{"level": 0-5, "gaps": []}},
    "distributed_training": {{"level": 0-5, "gaps": []}}
  }},
  "domain_knowledge": {{
    "concept_name": 0-5
  }},
  "calibration_confidence": 0.0-1.0
}}

Base levels on: correct answers in that dimension, question difficulty, and patterns of errors.
Be conservative - it's better to slightly underestimate than overestimate.
"""


class PreAssessor:
    """Multi-dimensional diagnostic assessment skill."""

    def __init__(self, llm: LLMClient, store: LocalStore):
        self.llm = llm
        self.store = store

    def generate_diagnostic_questions(
        self, field: str, count: int = 12
    ) -> list[DiagnosticQuestion]:
        """Generate diagnostic questions for the target field."""
        prompt = QUESTION_GENERATION_PROMPT.format(field=field, count=count)
        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)

        try:
            questions_data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                questions_data = json.loads(response[start:end])
            else:
                raise ValueError(f"Failed to parse LLM response as JSON: {response[:200]}")

        return [DiagnosticQuestion.model_validate(q) for q in questions_data]

    def evaluate_results(
        self,
        field: str,
        questions: list[DiagnosticQuestion],
        results: list[DiagnosticResult],
        learning_goal: LearningGoal = LearningGoal.UNDERSTAND,
        available_hours: float = 10.0,
        learning_style: LearningStyle = LearningStyle.INTUITION_FIRST,
        seed_papers: list[str] | None = None,
    ) -> AssessmentProfile:
        """Evaluate diagnostic results and create assessment profile."""
        # Build results text for LLM
        results_text = []
        result_map = {r.question_id: r for r in results}
        for q in questions:
            r = result_map.get(q.id)
            if r:
                status = "CORRECT" if r.is_correct else "INCORRECT"
                results_text.append(
                    f"- [{q.dimension}] (difficulty {q.difficulty}) {q.question}\n"
                    f"  Answer: {status} (selected option {r.selected_answer}, "
                    f"correct was {q.correct_answer})"
                )

        prompt = ASSESSMENT_PROMPT.format(
            field=field,
            results_text="\n".join(results_text),
        )
        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)

        try:
            assessment_data = json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                assessment_data = json.loads(response[start:end])
            else:
                raise ValueError(f"Failed to parse assessment response: {response[:200]}")

        # Build profile
        math = assessment_data.get("math_foundations", {})
        prog = assessment_data.get("programming", {})

        profile = AssessmentProfile(
            target_field=field,
            math_foundations=MathFoundations(
                linear_algebra=SkillLevel(**math.get("linear_algebra", {"level": 0})),
                probability=SkillLevel(**math.get("probability", {"level": 0})),
                calculus=SkillLevel(**math.get("calculus", {"level": 0})),
                optimization=SkillLevel(**math.get("optimization", {"level": 0})),
            ),
            programming=ProgrammingSkills(
                python=SkillLevel(**prog.get("python", {"level": 0})),
                pytorch=SkillLevel(**prog.get("pytorch", {"level": 0})),
                jax=SkillLevel(**prog.get("jax", {"level": 0})),
                distributed_training=SkillLevel(**prog.get("distributed_training", {"level": 0})),
            ),
            domain_knowledge=assessment_data.get("domain_knowledge", {}),
            learning_goal=learning_goal,
            available_hours_per_week=available_hours,
            learning_style=learning_style,
            diagnostic_results=results,
            calibration_confidence=assessment_data.get("calibration_confidence", 0.5),
            seed_papers=seed_papers or [],
        )

        # Save profile
        self.store.save_assessment(profile)
        return profile

    def quick_assess(
        self,
        field: str,
        math_level: int = 3,
        programming_level: int = 3,
        domain_level: int = 0,
        learning_goal: LearningGoal = LearningGoal.UNDERSTAND,
        available_hours: float = 10.0,
        learning_style: LearningStyle = LearningStyle.INTUITION_FIRST,
    ) -> AssessmentProfile:
        """Quick assessment without diagnostic questions (for users who know their levels)."""
        profile = AssessmentProfile(
            target_field=field,
            math_foundations=MathFoundations(
                linear_algebra=SkillLevel(level=math_level),
                probability=SkillLevel(level=math_level),
                calculus=SkillLevel(level=math_level),
                optimization=SkillLevel(level=max(0, math_level - 1)),
            ),
            programming=ProgrammingSkills(
                python=SkillLevel(level=programming_level),
                pytorch=SkillLevel(level=max(0, programming_level - 1)),
                jax=SkillLevel(level=max(0, programming_level - 2)),
                distributed_training=SkillLevel(level=max(0, programming_level - 2)),
            ),
            domain_knowledge={field.lower().replace(" ", "_"): domain_level},
            learning_goal=learning_goal,
            available_hours_per_week=available_hours,
            learning_style=learning_style,
            calibration_confidence=0.4,  # Lower confidence for self-reported
        )

        self.store.save_assessment(profile)
        return profile
