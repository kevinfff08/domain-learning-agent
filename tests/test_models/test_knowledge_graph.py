"""Tests for knowledge graph models."""

import pytest
from src.models.knowledge_graph import (
    ConceptNode,
    ConceptStatus,
    EdgeType,
    GraphEdge,
    KnowledgeGraph,
    PaperReference,
)


class TestConceptNode:
    def test_basic_creation(self):
        node = ConceptNode(id="score_matching", name="Score Matching")
        assert node.id == "score_matching"
        assert node.difficulty == 3
        assert node.status == ConceptStatus.PENDING
        assert node.mastery == 0.0

    def test_with_prerequisites(self):
        node = ConceptNode(
            id="ddpm",
            name="DDPM",
            prerequisites=["score_matching", "vae"],
            difficulty=4,
            estimated_hours=5.0,
        )
        assert len(node.prerequisites) == 2
        assert node.estimated_hours == 5.0


class TestKnowledgeGraph:
    @pytest.fixture
    def sample_graph(self):
        return KnowledgeGraph(
            field="Diffusion Models",
            nodes=[
                ConceptNode(id="prob_review", name="Probability Review", difficulty=1),
                ConceptNode(id="score_matching", name="Score Matching", prerequisites=["prob_review"], difficulty=3),
                ConceptNode(id="ddpm", name="DDPM", prerequisites=["score_matching"], difficulty=4),
            ],
            edges=[
                GraphEdge(source="prob_review", target="score_matching", edge_type=EdgeType.PREREQUISITE),
                GraphEdge(source="score_matching", target="ddpm", edge_type=EdgeType.PREREQUISITE),
            ],
            learning_path=["prob_review", "score_matching", "ddpm"],
        )

    def test_get_node(self, sample_graph):
        node = sample_graph.get_node("ddpm")
        assert node is not None
        assert node.name == "DDPM"

    def test_get_node_not_found(self, sample_graph):
        assert sample_graph.get_node("nonexistent") is None

    def test_get_prerequisites(self, sample_graph):
        prereqs = sample_graph.get_prerequisites("ddpm")
        assert len(prereqs) == 1
        assert prereqs[0].id == "score_matching"

    def test_get_dependents(self, sample_graph):
        deps = sample_graph.get_dependents("score_matching")
        assert len(deps) == 1
        assert deps[0].id == "ddpm"

    def test_completion_rate_empty(self):
        graph = KnowledgeGraph(field="Test")
        assert graph.completion_rate() == 0.0

    def test_completion_rate(self, sample_graph):
        assert sample_graph.completion_rate() == 0.0

        sample_graph.nodes[0].status = ConceptStatus.COMPLETED
        assert abs(sample_graph.completion_rate() - 1/3) < 0.01

        sample_graph.nodes[1].status = ConceptStatus.COMPLETED
        sample_graph.nodes[2].status = ConceptStatus.COMPLETED
        assert sample_graph.completion_rate() == 1.0


class TestPaperReference:
    def test_creation(self):
        ref = PaperReference(
            arxiv_id="2006.11239",
            title="Denoising Diffusion Probabilistic Models",
            authors=["Jonathan Ho", "Ajay Jain", "Pieter Abbeel"],
            year=2020,
            citation_count=5200,
            role="primary_source",
        )
        assert ref.arxiv_id == "2006.11239"
        assert ref.year == 2020
