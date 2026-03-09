"""Tests for assessment models."""

import pytest
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


class TestSkillLevel:
    def test_default_level(self):
        sl = SkillLevel(level=0)
        assert sl.level == 0
        assert sl.gaps == []

    def test_level_with_gaps(self):
        sl = SkillLevel(level=3, gaps=["eigendecomposition", "SVD"])
        assert sl.level == 3
        assert len(sl.gaps) == 2

    def test_level_validation(self):
        with pytest.raises(Exception):
            SkillLevel(level=-1)
        with pytest.raises(Exception):
            SkillLevel(level=6)


class TestMathFoundations:
    def test_default(self):
        mf = MathFoundations()
        assert mf.linear_algebra.level == 0
        assert mf.probability.level == 0
        assert mf.calculus.level == 0
        assert mf.optimization.level == 0


class TestAssessmentProfile:
    def test_basic_creation(self):
        profile = AssessmentProfile(target_field="Diffusion Models")
        assert profile.target_field == "Diffusion Models"
        assert profile.learning_goal == LearningGoal.UNDERSTAND
        assert profile.available_hours_per_week == 10.0

    def test_full_profile(self):
        profile = AssessmentProfile(
            target_field="Diffusion Models",
            math_foundations=MathFoundations(
                linear_algebra=SkillLevel(level=4),
                probability=SkillLevel(level=3, gaps=["measure theory"]),
            ),
            programming=ProgrammingSkills(
                python=SkillLevel(level=4),
                pytorch=SkillLevel(level=3),
            ),
            domain_knowledge={"generative_models": 2},
            learning_goal=LearningGoal.REPRODUCE,
            available_hours_per_week=15.0,
            learning_style=LearningStyle.MATH_FIRST,
            seed_papers=["2006.11239"],
        )
        assert profile.math_foundations.linear_algebra.level == 4
        assert profile.programming.pytorch.level == 3
        assert profile.learning_goal == LearningGoal.REPRODUCE
        assert len(profile.seed_papers) == 1


class TestDiagnosticQuestion:
    def test_creation(self):
        q = DiagnosticQuestion(
            id="q1",
            dimension="probability",
            question="What is KL divergence?",
            options=["A", "B", "C", "D"],
            correct_answer=1,
            difficulty=3,
        )
        assert q.id == "q1"
        assert q.correct_answer == 1


class TestDiagnosticResult:
    def test_creation(self):
        r = DiagnosticResult(
            question_id="q1",
            selected_answer=1,
            is_correct=True,
            time_spent_seconds=30.5,
        )
        assert r.is_correct is True
