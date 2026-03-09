"""Data models for content accuracy verification."""

from __future__ import annotations

from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Status of a verification check."""

    VERIFIED = "verified"
    WARNING = "warning"
    ERROR = "error"
    UNVERIFIABLE = "unverifiable"


class CheckType(str, Enum):
    """Type of verification check."""

    CITATION_EXISTENCE = "citation_existence"
    MATHEMATICAL_CORRECTNESS = "mathematical_correctness"
    PERFORMANCE_CLAIM = "performance_claim"
    ATTRIBUTION_ACCURACY = "attribution_accuracy"
    SELF_CONSISTENCY = "self_consistency"


class VerificationCheck(BaseModel):
    """A single verification check result."""

    check_type: CheckType
    claim: str = Field(description="The claim being verified")
    source_paper: str = Field(default="", description="arXiv ID or DOI referenced")
    result: VerificationStatus
    details: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class VerificationReport(BaseModel):
    """Complete verification report for a piece of content."""

    id: str
    concept_id: str
    checks: list[VerificationCheck] = Field(default_factory=list)
    hallucination_risk_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="0=fully verified, 1=high hallucination risk",
    )
    flagged_items: list[str] = Field(default_factory=list)
    overall_status: str = Field(
        default="pending",
        description="passed, passed_with_warnings, failed, pending",
    )
    verified_at: datetime = Field(default_factory=datetime.now)

    @property
    def needs_human_review(self) -> bool:
        """Whether this content should be flagged for human review."""
        return self.hallucination_risk_score > 0.3

    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.checks if c.result == VerificationStatus.VERIFIED)

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if c.result == VerificationStatus.ERROR)
