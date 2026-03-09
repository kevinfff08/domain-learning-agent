"""Tests for Progress Tracker skill."""

import pytest
import tempfile

from src.models.knowledge_graph import ConceptNode, ConceptStatus, KnowledgeGraph
from src.models.progress import LearnerProgress
from src.models.quiz import QuizResult
from src.skills.progress_tracker import ProgressTracker
from src.storage.local_store import LocalStore


@pytest.fixture
def tracker():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStore(tmp)
        yield ProgressTracker(store)


@pytest.fixture
def sample_graph():
    return KnowledgeGraph(
        field="Test",
        nodes=[
            ConceptNode(id="c1", name="Concept 1"),
            ConceptNode(id="c2", name="Concept 2"),
            ConceptNode(id="c3", name="Concept 3"),
        ],
        learning_path=["c1", "c2", "c3"],
    )


class TestProgressTracker:
    def test_initialize_from_graph(self, tracker, sample_graph):
        progress = tracker.initialize_from_graph(sample_graph)
        assert progress.concepts_total == 3
        assert all(cid in progress.concepts for cid in ["c1", "c2", "c3"])

    def test_start_concept(self, tracker, sample_graph):
        progress = tracker.initialize_from_graph(sample_graph)
        progress = tracker.start_concept(progress, "c1")
        assert progress.concepts["c1"].status == "in_progress"
        assert progress.concepts["c1"].started_at is not None

    def test_record_quiz_result_pass(self, tracker, sample_graph):
        progress = tracker.initialize_from_graph(sample_graph)
        result = QuizResult(
            quiz_id="q1", concept_id="c1",
            overall_score=0.85, results=[],
        )
        progress = tracker.record_quiz_result(progress, result)
        assert progress.concepts["c1"].status == "completed"
        assert progress.concepts["c1"].quiz_scores == [0.85]

    def test_record_quiz_result_fail(self, tracker, sample_graph):
        progress = tracker.initialize_from_graph(sample_graph)
        result = QuizResult(
            quiz_id="q1", concept_id="c1",
            overall_score=0.4, results=[],
        )
        progress = tracker.record_quiz_result(progress, result)
        assert progress.concepts["c1"].status != "completed"

    def test_record_time(self, tracker, sample_graph):
        progress = tracker.initialize_from_graph(sample_graph)
        progress = tracker.record_time(progress, "c1", 2.5)
        assert progress.concepts["c1"].time_spent_hours == 2.5
        assert progress.total_hours_spent == 2.5

    def test_generate_weekly_report(self, tracker, sample_graph):
        progress = tracker.initialize_from_graph(sample_graph)
        report = tracker.generate_weekly_report(progress)
        assert "Weekly Progress Report" in report
        assert "Test" in report

    def test_sync_with_graph(self, tracker, sample_graph):
        progress = tracker.initialize_from_graph(sample_graph)
        progress.concepts["c1"].status = "completed"
        progress.concepts["c1"].mastery_level = 0.9
        tracker.sync_with_graph(progress, sample_graph)
        assert sample_graph.nodes[0].status == ConceptStatus.COMPLETED
        assert sample_graph.nodes[0].mastery == 0.9
