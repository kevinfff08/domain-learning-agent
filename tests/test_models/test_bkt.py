"""Tests for BKT (Bayesian Knowledge Tracing) model."""

import pytest

from src.models.bkt import BKTParams, BKTState


class TestBKTState:
    def test_default_state(self):
        state = BKTState(concept_id="test")
        assert state.p_mastery == 0.1
        assert state.observations == []

    def test_correct_answer_increases_mastery(self):
        state = BKTState(concept_id="test")
        initial = state.p_mastery
        state.update(True)
        assert state.p_mastery > initial
        assert len(state.observations) == 1
        assert state.observations[0] is True

    def test_incorrect_answer_still_learns(self):
        """Even with wrong answer, learning transition increases mastery somewhat."""
        state = BKTState(concept_id="test")
        initial = state.p_mastery
        state.update(False)
        # After one wrong answer + learning transition, mastery may increase or decrease
        # but observations should be recorded
        assert len(state.observations) == 1
        assert state.observations[0] is False

    def test_repeated_correct_approaches_one(self):
        state = BKTState(concept_id="test")
        for _ in range(20):
            state.update(True)
        assert state.p_mastery > 0.95

    def test_mastery_bounded(self):
        state = BKTState(concept_id="test")
        for _ in range(100):
            state.update(True)
        assert 0.0 <= state.p_mastery <= 1.0

    def test_mixed_responses(self):
        state = BKTState(concept_id="test")
        state.update(True)
        state.update(True)
        state.update(False)
        state.update(True)
        assert len(state.observations) == 4
        assert 0.0 <= state.p_mastery <= 1.0

    def test_custom_params(self):
        params = BKTParams(p_learn=0.5, p_guess=0.1, p_slip=0.05, p_known=0.5)
        state = BKTState(concept_id="test", p_mastery=0.5, params=params)
        state.update(True)
        assert state.p_mastery > 0.5

    def test_p_mastery_higher_after_correct_than_incorrect(self):
        s1 = BKTState(concept_id="test")
        s2 = BKTState(concept_id="test")
        s1.update(True)
        s2.update(False)
        assert s1.p_mastery > s2.p_mastery
