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
    """First layer: intuitive understanding (deep, PhD-level)."""

    analogy: str = Field(default="", description="500+ words: detailed analogy with mappings and limitations")
    why_it_matters: str = Field(default="", description="300+ words: historical context, downstream impact, open problems")
    key_insight: str = Field(default="", description="200+ words: core breakthrough and non-obvious analysis")
    estimated_reading_minutes: int = 10


class AlgorithmBlock(BaseModel):
    """Academic paper-style pseudocode block (Algorithm environment)."""

    name: str = Field(description="e.g., 'Algorithm 1: DDPM Training'")
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list, description="Numbered steps, may contain inline LaTeX")
    source_paper: str = Field(default="", description="arXiv ID or DOI")


class MechanismLayer(BaseModel):
    """Second layer: mathematical and algorithmic details (PhD level)."""

    theoretical_narrative: str = Field(
        default="",
        description="1000-2000 words continuous mathematical narrative: definitions → assumptions → theorems → full derivations → remarks",
    )
    mathematical_framework: str = Field(default="", description="LaTeX-formatted framework overview (legacy)")
    key_equations: list[Equation] = Field(default_factory=list)
    algorithms: list[AlgorithmBlock] = Field(default_factory=list, description="Academic-style pseudocode blocks")
    pseudocode: str = Field(default="", description="Deprecated, kept for backward compatibility")
    algorithm_steps: list[str] = Field(default_factory=list)
    connections: list[CrossConceptConnection] = Field(default_factory=list)
    estimated_reading_minutes: int = 45


class CodeAnalysis(BaseModel):
    """Concrete code example with line-by-line analysis."""

    title: str = Field(description="e.g., 'DDPM Training Loop (PyTorch)'")
    language: str = "python"
    source_url: str = Field(default="", description="GitHub URL or reference")
    code: str = Field(default="", description="50-150 lines of complete, runnable code")
    line_annotations: list[str] = Field(
        default_factory=list, description="'Lines X-Y: explanation' entries"
    )
    key_design_decisions: list[str] = Field(default_factory=list)


class PracticeLayer(BaseModel):
    """Third layer: implementation and reproduction."""

    code_analysis: list[CodeAnalysis] = Field(default_factory=list, description="Concrete code examples with analysis")
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
