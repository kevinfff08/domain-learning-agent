"""Tests for mastery decay and streak in progress tracker."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.models.progress import ConceptProgress, LearnerProgress
from src.skills.progress_tracker import ProgressTracker


@pytest.fixture
def tracker():
    store = MagicMock()
    return ProgressTracker(store)


class TestMasteryDecay:
    def test_decay_reduces_mastery(self):
        progress = LearnerProgress(field="test")
        cp = progress.get_or_create_concept("c1")
        cp.mastery_level = 0.9
        cp.last_accessed = datetime.now() - timedelta(days=30)

        ProgressTracker.apply_decay(progress)
        assert cp.mastery_level < 0.9

    def test_no_decay_recent(self):
        progress = LearnerProgress(field="test")
        cp = progress.get_or_create_concept("c1")
        cp.mastery_level = 0.9
        cp.last_accessed = datetime.now()

        ProgressTracker.apply_decay(progress)
        # Very recent access - minimal decay
        assert cp.mastery_level > 0.85

    def test_zero_mastery_unchanged(self):
        progress = LearnerProgress(field="test")
        cp = progress.get_or_create_concept("c1")
        cp.mastery_level = 0.0
        cp.last_accessed = datetime.now() - timedelta(days=60)

        ProgressTracker.apply_decay(progress)
        assert cp.mastery_level == 0.0


class TestStreak:
    def test_first_activity_sets_streak(self, tracker):
        progress = LearnerProgress(field="test")
        tracker._update_streak(progress)
        assert progress.streak_days == 1

    def test_consecutive_day_increments(self, tracker):
        progress = LearnerProgress(field="test")
        progress.last_active = datetime.now() - timedelta(days=1)
        progress.streak_days = 3
        tracker._update_streak(progress)
        assert progress.streak_days == 4

    def test_gap_resets_streak(self, tracker):
        progress = LearnerProgress(field="test")
        progress.last_active = datetime.now() - timedelta(days=3)
        progress.streak_days = 10
        tracker._update_streak(progress)
        assert progress.streak_days == 1

    def test_same_day_no_change(self, tracker):
        progress = LearnerProgress(field="test")
        progress.last_active = datetime.now()
        progress.streak_days = 5
        tracker._update_streak(progress)
        assert progress.streak_days == 5
