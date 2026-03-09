"""Data models for knowledge graphs."""

from __future__ import annotations

from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class ConceptStatus(str, Enum):
    """Learning status of a concept."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class EdgeType(str, Enum):
    """Type of relationship between concepts."""

    PREREQUISITE = "prerequisite"
    VARIANT = "variant"
    APPLICATION = "application"
    EXTENDS = "extends"


class PaperReference(BaseModel):
    """A reference to an academic paper."""

    arxiv_id: str = ""
    doi: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    venue: str = ""
    citation_count: int = 0
    role: str = Field(default="related", description="Role in concept: primary_source, builds_upon, related")


class ConceptNode(BaseModel):
    """A concept in the knowledge graph."""

    id: str = Field(description="Unique identifier, e.g., 'score_matching'")
    name: str = Field(description="Human-readable name, e.g., 'Score Matching'")
    description: str = ""
    difficulty: int = Field(default=3, ge=1, le=5)
    prerequisites: list[str] = Field(
        default_factory=list, description="IDs of prerequisite concept nodes"
    )
    estimated_hours: float = Field(default=2.0, ge=0.5)
    status: ConceptStatus = ConceptStatus.PENDING
    mastery: float = Field(default=0.0, ge=0.0, le=1.0)
    key_papers: list[PaperReference] = Field(default_factory=list)
    math_requirements: list[str] = Field(
        default_factory=list,
        description="Required math skills, e.g., ['calculus', 'probability']",
    )
    tags: list[str] = Field(default_factory=list)
    adaptive_level: int = Field(
        default=0, ge=0, le=4, description="Current adaptive intervention level"
    )


class GraphEdge(BaseModel):
    """An edge connecting two concepts."""

    source: str = Field(description="Source concept ID")
    target: str = Field(description="Target concept ID")
    edge_type: EdgeType = EdgeType.PREREQUISITE
    label: str = ""


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph for a learning domain."""

    field: str = Field(description="Target learning domain")
    version: int = Field(default=1)
    nodes: list[ConceptNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    learning_path: list[str] = Field(
        default_factory=list, description="Ordered list of concept IDs for recommended traversal"
    )
    estimated_total_hours: float = 0.0
    sources_searched: list[str] = Field(default_factory=list)
    survey_papers_used: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_node(self, concept_id: str) -> ConceptNode | None:
        """Get a concept node by ID."""
        for node in self.nodes:
            if node.id == concept_id:
                return node
        return None

    def get_prerequisites(self, concept_id: str) -> list[ConceptNode]:
        """Get all prerequisite nodes for a concept."""
        node = self.get_node(concept_id)
        if not node:
            return []
        return [n for n in self.nodes if n.id in node.prerequisites]

    def get_dependents(self, concept_id: str) -> list[ConceptNode]:
        """Get all nodes that depend on this concept."""
        return [n for n in self.nodes if concept_id in n.prerequisites]

    def completion_rate(self) -> float:
        """Calculate overall completion rate."""
        if not self.nodes:
            return 0.0
        completed = sum(1 for n in self.nodes if n.status == ConceptStatus.COMPLETED)
        return completed / len(self.nodes)
