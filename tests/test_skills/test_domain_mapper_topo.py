"""Tests for domain mapper topological sort validation."""

import pytest

from src.models.knowledge_graph import ConceptNode, EdgeType, GraphEdge
from src.skills.domain_mapper import DomainMapper


class TestValidateAndFixLearningPath:
    def test_valid_path_unchanged(self):
        nodes = [
            ConceptNode(id="a", name="A", difficulty=1),
            ConceptNode(id="b", name="B", difficulty=2),
            ConceptNode(id="c", name="C", difficulty=3),
        ]
        edges = [
            GraphEdge(source="a", target="b", edge_type=EdgeType.PREREQUISITE),
            GraphEdge(source="b", target="c", edge_type=EdgeType.PREREQUISITE),
        ]
        path = ["a", "b", "c"]
        result = DomainMapper._validate_and_fix_learning_path(nodes, edges, path)
        assert result == ["a", "b", "c"]

    def test_invalid_path_fixed(self):
        nodes = [
            ConceptNode(id="a", name="A", difficulty=1),
            ConceptNode(id="b", name="B", difficulty=2),
            ConceptNode(id="c", name="C", difficulty=3),
        ]
        edges = [
            GraphEdge(source="a", target="b", edge_type=EdgeType.PREREQUISITE),
            GraphEdge(source="b", target="c", edge_type=EdgeType.PREREQUISITE),
        ]
        # Invalid: c before a
        path = ["c", "b", "a"]
        result = DomainMapper._validate_and_fix_learning_path(nodes, edges, path)
        # a must appear before b, b before c
        assert result.index("a") < result.index("b")
        assert result.index("b") < result.index("c")

    def test_missing_nodes_in_path(self):
        nodes = [
            ConceptNode(id="a", name="A", difficulty=1),
            ConceptNode(id="b", name="B", difficulty=2),
            ConceptNode(id="c", name="C", difficulty=3),
        ]
        edges = [
            GraphEdge(source="a", target="b", edge_type=EdgeType.PREREQUISITE),
        ]
        # Path missing "c"
        path = ["a", "b"]
        result = DomainMapper._validate_and_fix_learning_path(nodes, edges, path)
        # All nodes should be present
        assert set(result) == {"a", "b", "c"}
        assert result.index("a") < result.index("b")

    def test_no_edges(self):
        nodes = [
            ConceptNode(id="a", name="A", difficulty=1),
            ConceptNode(id="b", name="B", difficulty=2),
        ]
        edges = []
        path = ["b", "a"]
        result = DomainMapper._validate_and_fix_learning_path(nodes, edges, path)
        assert set(result) == {"a", "b"}

    def test_non_prerequisite_edges_ignored(self):
        nodes = [
            ConceptNode(id="a", name="A", difficulty=1),
            ConceptNode(id="b", name="B", difficulty=2),
        ]
        edges = [
            GraphEdge(source="a", target="b", edge_type=EdgeType.VARIANT),
        ]
        path = ["b", "a"]
        result = DomainMapper._validate_and_fix_learning_path(nodes, edges, path)
        # Variant edges don't enforce ordering
        assert set(result) == {"a", "b"}
