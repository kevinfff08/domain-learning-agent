"""Data models for research content synthesis."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Equation(BaseModel):
    """A mathematical equation with source attribution."""

    name: str = Field(description="Descriptive name, e.g., 'Forward process'")
    latex: str = Field(description="LaTeX representation")
    explanation: str = ""
    derivation_steps: list[str] = Field(default_factory=list)
    source_paper: str = Field(default="", description="arXiv ID or DOI of source")
    source_equation_ref: str = Field(default="", description="e.g., 'Eq. 2'")


class CrossConceptConnection(BaseModel):
    """An explicit connection between this concept and another."""

    target_concept_id: str
    relationship: str = Field(description="e.g., 'DDPM can be viewed as a hierarchical VAE with...'")


class IntuitionLayer(BaseModel):
    """First layer: intuitive understanding."""

    analogy: str = ""
    visual_description: str = ""
    why_it_matters: str = ""
    key_insight: str = ""
    estimated_reading_minutes: int = 10


class MechanismLayer(BaseModel):
    """Second layer: mathematical and algorithmic details (PhD level)."""

    mathematical_framework: str = Field(default="", description="LaTeX-formatted framework overview")
    key_equations: list[Equation] = Field(default_factory=list)
    pseudocode: str = ""
    algorithm_steps: list[str] = Field(default_factory=list)
    connections: list[CrossConceptConnection] = Field(default_factory=list)
    estimated_reading_minutes: int = 45


class PracticeLayer(BaseModel):
    """Third layer: implementation and reproduction."""

    reference_implementations: list[str] = Field(
        default_factory=list, description="GitHub repository URLs"
    )
    key_hyperparameters: dict[str, str] = Field(default_factory=dict)
    common_pitfalls: list[str] = Field(default_factory=list)
    reproduction_checklist: list[str] = Field(default_factory=list)
    estimated_reading_minutes: int = 120


class SourceAttribution(BaseModel):
    """Source for a piece of generated content."""

    arxiv_id: str = ""
    doi: str = ""
    title: str = ""
    url: str = ""
    source_type: str = Field(default="paper", description="paper, blog, code, course")
    role: str = Field(default="reference", description="primary_source, builds_upon, reference")


class ResearchSynthesis(BaseModel):
    """Complete research synthesis for a single concept, produced by Deep Researcher."""

    concept_id: str
    title: str
    intuition: IntuitionLayer = Field(default_factory=IntuitionLayer)
    mechanism: MechanismLayer = Field(default_factory=MechanismLayer)
    practice: PracticeLayer = Field(default_factory=PracticeLayer)
    sources: list[SourceAttribution] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
    verified: bool = False
    verification_report_id: str = ""
