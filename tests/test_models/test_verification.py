"""Tests for verification models."""

import pytest
from src.models.verification import (
    CheckType,
    VerificationCheck,
    VerificationReport,
    VerificationStatus,
)


class TestVerificationCheck:
    def test_verified(self):
        check = VerificationCheck(
            check_type=CheckType.CITATION_EXISTENCE,
            claim="Paper X exists",
            source_paper="2006.11239",
            result=VerificationStatus.VERIFIED,
            confidence=0.95,
        )
        assert check.result == VerificationStatus.VERIFIED

    def test_error(self):
        check = VerificationCheck(
            check_type=CheckType.MATHEMATICAL_CORRECTNESS,
            claim="Equation is wrong",
            result=VerificationStatus.ERROR,
            details="Dimension mismatch",
        )
        assert check.result == VerificationStatus.ERROR


class TestVerificationReport:
    def test_needs_human_review(self):
        report = VerificationReport(
            id="test",
            concept_id="ddpm",
            hallucination_risk_score=0.5,
        )
        assert report.needs_human_review is True

    def test_no_human_review_needed(self):
        report = VerificationReport(
            id="test",
            concept_id="ddpm",
            hallucination_risk_score=0.1,
        )
        assert report.needs_human_review is False

    def test_counts(self):
        report = VerificationReport(
            id="test",
            concept_id="ddpm",
            checks=[
                VerificationCheck(check_type=CheckType.CITATION_EXISTENCE, claim="c1", result=VerificationStatus.VERIFIED),
                VerificationCheck(check_type=CheckType.CITATION_EXISTENCE, claim="c2", result=VerificationStatus.ERROR),
                VerificationCheck(check_type=CheckType.SELF_CONSISTENCY, claim="c3", result=VerificationStatus.VERIFIED),
            ],
        )
        assert report.verified_count == 2
        assert report.error_count == 1
