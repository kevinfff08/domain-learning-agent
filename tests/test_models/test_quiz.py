"""Tests for quiz models."""

import pytest
from src.models.quiz import (
    BloomLevel,
    Question,
    QuestionResult,
    QuestionType,
    Quiz,
    QuizResult,
)


class TestQuestion:
    def test_multiple_choice(self):
        q = Question(
            id="q1",
            question_type=QuestionType.MULTIPLE_CHOICE,
            bloom_level=BloomLevel.UNDERSTAND,
            question="What is X?",
            difficulty=3,
            concept_id="ddpm",
            options=["A", "B", "C", "D"],
            correct_answer=1,
        )
        assert q.question_type == QuestionType.MULTIPLE_CHOICE
        assert q.correct_answer == 1

    def test_derivation(self):
        q = Question(
            id="q2",
            question_type=QuestionType.DERIVATION,
            bloom_level=BloomLevel.APPLY,
            question="Derive the ELBO",
            difficulty=5,
            concept_id="ddpm",
            solution_steps=["Step 1", "Step 2"],
        )
        assert len(q.solution_steps) == 2


class TestQuizResult:
    def test_passed(self):
        result = QuizResult(
            quiz_id="quiz1",
            concept_id="ddpm",
            results=[
                QuestionResult(question_id="q1", user_answer="1", is_correct=True, score=1.0),
                QuestionResult(question_id="q2", user_answer="0", is_correct=True, score=1.0),
            ],
            overall_score=0.8,
        )
        assert result.passed is True
        assert result.needs_level1_intervention is False
        assert result.needs_level2_intervention is False

    def test_level1_intervention(self):
        result = QuizResult(
            quiz_id="quiz1", concept_id="ddpm",
            overall_score=0.55,
            results=[],
        )
        assert result.passed is False
        assert result.needs_level1_intervention is True
        assert result.needs_level2_intervention is False

    def test_level2_intervention(self):
        result = QuizResult(
            quiz_id="quiz1", concept_id="ddpm",
            overall_score=0.3,
            results=[],
        )
        assert result.passed is False
        assert result.needs_level1_intervention is False
        assert result.needs_level2_intervention is True
