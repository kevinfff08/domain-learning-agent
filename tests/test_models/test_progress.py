"""Tests for progress tracking models."""

import pytest
from src.models.progress import ConceptProgress, LearnerProgress, WeeklyStats


class TestConceptProgress:
    def test_default(self):
        cp = ConceptProgress(concept_id="ddpm")
        assert cp.status == "pending"
        assert cp.mastery_level == 0.0
        assert cp.quiz_scores == []


class TestLearnerProgress:
    def test_default(self):
        lp = LearnerProgress()
        assert lp.concepts_total == 0
        assert lp.completion_rate == 0.0

    def test_completion_rate(self):
        lp = LearnerProgress(concepts={
            "a": ConceptProgress(concept_id="a", status="completed"),
            "b": ConceptProgress(concept_id="b", status="in_progress"),
            "c": ConceptProgress(concept_id="c", status="pending"),
        })
        assert lp.concepts_total == 3
        assert lp.concepts_completed == 1
        assert abs(lp.completion_rate - 1/3) < 0.01

    def test_average_quiz_score(self):
        lp = LearnerProgress(concepts={
            "a": ConceptProgress(concept_id="a", quiz_scores=[0.8, 0.9]),
            "b": ConceptProgress(concept_id="b", quiz_scores=[0.6]),
        })
        expected = (0.8 + 0.9 + 0.6) / 3
        assert abs(lp.average_quiz_score - expected) < 0.01

    def test_average_quiz_score_empty(self):
        lp = LearnerProgress()
        assert lp.average_quiz_score == 0.0

    def test_get_or_create_concept(self):
        lp = LearnerProgress()
        cp = lp.get_or_create_concept("new_concept")
        assert cp.concept_id == "new_concept"
        assert "new_concept" in lp.concepts

        # Should return same object on second call
        cp2 = lp.get_or_create_concept("new_concept")
        assert cp is cp2
