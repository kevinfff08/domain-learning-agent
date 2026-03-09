"""Tests for local storage layer."""

import pytest
import tempfile
from pathlib import Path

from src.models.assessment import AssessmentProfile, LearningGoal
from src.models.knowledge_graph import ConceptNode, KnowledgeGraph
from src.models.progress import LearnerProgress
from src.storage.local_store import LocalStore


@pytest.fixture
def temp_store():
    """Create a temporary store for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        yield LocalStore(tmp)


class TestLocalStore:
    def test_save_and_load_json(self, temp_store):
        data = {"key": "value", "number": 42}
        temp_store.save_json("test/data.json", data)
        loaded = temp_store.load_json("test/data.json")
        assert loaded == data

    def test_load_nonexistent(self, temp_store):
        assert temp_store.load_json("nonexistent.json") is None

    def test_save_and_load_model(self, temp_store):
        profile = AssessmentProfile(
            target_field="Diffusion Models",
            learning_goal=LearningGoal.REPRODUCE,
        )
        temp_store.save_model("test/profile.json", profile)
        loaded = temp_store.load_model("test/profile.json", AssessmentProfile)
        assert loaded is not None
        assert loaded.target_field == "Diffusion Models"
        assert loaded.learning_goal == LearningGoal.REPRODUCE

    def test_save_and_load_assessment(self, temp_store):
        profile = AssessmentProfile(target_field="RL")
        temp_store.save_assessment(profile)
        loaded = temp_store.load_assessment(AssessmentProfile)
        assert loaded is not None
        assert loaded.target_field == "RL"

    def test_save_and_load_knowledge_graph(self, temp_store):
        graph = KnowledgeGraph(
            field="Test Field",
            nodes=[ConceptNode(id="c1", name="Concept 1")],
            learning_path=["c1"],
        )
        temp_store.save_knowledge_graph("Test Field", graph)
        loaded = temp_store.load_knowledge_graph("Test Field", KnowledgeGraph)
        assert loaded is not None
        assert loaded.field == "Test Field"
        assert len(loaded.nodes) == 1

    def test_save_and_load_progress(self, temp_store):
        progress = LearnerProgress(field="DM")
        temp_store.save_progress(progress)
        loaded = temp_store.load_progress(LearnerProgress)
        assert loaded is not None
        assert loaded.field == "DM"

    def test_exists(self, temp_store):
        assert temp_store.exists("nonexistent.json") is False
        temp_store.save_json("exists.json", {})
        assert temp_store.exists("exists.json") is True

    def test_list_files(self, temp_store):
        temp_store.save_json("test/a.json", {})
        temp_store.save_json("test/b.json", {})
        files = temp_store.list_files("test")
        assert len(files) == 2

    def test_save_content(self, temp_store):
        from src.models.content import ResearchSynthesis
        synthesis = ResearchSynthesis(concept_id="ddpm", title="DDPM")
        temp_store.save_content("ddpm", "synthesis.json", synthesis)
        loaded = temp_store.load_content("ddpm", "synthesis.json", ResearchSynthesis)
        assert loaded is not None
        assert loaded.concept_id == "ddpm"
