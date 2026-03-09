"""Tests for Path Visualizer skill."""

import pytest
import tempfile
from pathlib import Path

from src.models.knowledge_graph import ConceptNode, ConceptStatus, KnowledgeGraph, GraphEdge, EdgeType
from src.models.progress import ConceptProgress, LearnerProgress
from src.skills.path_visualizer import PathVisualizer
from src.storage.local_store import LocalStore


@pytest.fixture
def visualizer():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStore(tmp)
        yield PathVisualizer(store), tmp


@pytest.fixture
def sample_graph():
    return KnowledgeGraph(
        field="Diffusion Models",
        nodes=[
            ConceptNode(id="prob", name="Probability", difficulty=1, status=ConceptStatus.COMPLETED, mastery=0.9),
            ConceptNode(id="sm", name="Score Matching", difficulty=3, prerequisites=["prob"], status=ConceptStatus.IN_PROGRESS),
            ConceptNode(id="ddpm", name="DDPM", difficulty=4, prerequisites=["sm"]),
        ],
        edges=[
            GraphEdge(source="prob", target="sm", edge_type=EdgeType.PREREQUISITE),
            GraphEdge(source="sm", target="ddpm", edge_type=EdgeType.PREREQUISITE),
        ],
        learning_path=["prob", "sm", "ddpm"],
        estimated_total_hours=20.0,
    )


class TestPathVisualizer:
    def test_generate_html(self, visualizer, sample_graph):
        viz, tmp = visualizer
        with tempfile.TemporaryDirectory() as out:
            path = viz.generate_html(sample_graph, output_dir=out)
            assert path.exists()
            content = path.read_text()
            assert "Diffusion Models" in content
            assert "d3.js" in content.lower() or "d3.v7" in content

    def test_generate_markdown(self, visualizer, sample_graph):
        viz, _ = visualizer
        md = viz.generate_markdown(sample_graph)
        assert "Diffusion Models" in md
        assert "Probability" in md
        assert "Score Matching" in md
        assert "DDPM" in md

    def test_markdown_with_progress(self, visualizer, sample_graph):
        viz, _ = visualizer
        progress = LearnerProgress(
            field="Diffusion Models",
            concepts={
                "prob": ConceptProgress(concept_id="prob", status="completed", mastery_level=0.9),
                "sm": ConceptProgress(concept_id="sm", status="in_progress", mastery_level=0.3),
            },
        )
        md = viz.generate_markdown(sample_graph, progress)
        assert "[x]" in md  # completed
        assert "[~]" in md  # in progress
        assert "YOU ARE HERE" in md

    def test_ascii_tree(self, visualizer, sample_graph):
        viz, _ = visualizer
        tree = viz.print_ascii_tree(sample_graph)
        assert "Probability" in tree
        assert "Score Matching" in tree
        assert "DDPM" in tree
