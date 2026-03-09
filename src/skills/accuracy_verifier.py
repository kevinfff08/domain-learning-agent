"""Skill 5: Accuracy Verifier - Content verification against source papers."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

from src.apis.crossref import CrossRefClient
from src.apis.semantic_scholar import SemanticScholarClient
from src.llm.client import LLMClient
from src.models.content import ResearchSynthesis
from src.models.verification import (
    CheckType,
    VerificationCheck,
    VerificationReport,
    VerificationStatus,
)
from src.storage.local_store import LocalStore

SYSTEM_PROMPT = """You are a rigorous fact-checker for academic content.
Your job is to identify potential hallucinations, incorrect citations, and mathematical errors.
Be conservative: flag anything you're uncertain about.
Return valid JSON only."""

SELF_CONSISTENCY_PROMPT = """Analyze the following content for internal consistency.

Intuition layer analogy: {analogy}
Intuition key insight: {key_insight}

Mechanism layer math framework (excerpt): {math_excerpt}
Key equations: {equations}

Check:
1. Does the analogy accurately represent the mathematical mechanism?
2. Is the key insight consistent with the equations?
3. Are there any contradictions between layers?

Return JSON:
{{
  "is_consistent": true/false,
  "issues": ["list of consistency issues found"],
  "confidence": 0.0-1.0
}}
"""


class AccuracyVerifier:
    """Content accuracy verification skill."""

    def __init__(
        self,
        llm: LLMClient,
        store: LocalStore,
        semantic_scholar: SemanticScholarClient | None = None,
        crossref: CrossRefClient | None = None,
    ):
        self.llm = llm
        self.store = store
        self.s2 = semantic_scholar
        self.crossref = crossref

    async def verify(self, synthesis: ResearchSynthesis) -> VerificationReport:
        """Run all verification checks on a research synthesis."""
        checks: list[VerificationCheck] = []

        # 1. Citation existence checks
        citation_checks = await self._verify_citations(synthesis)
        checks.extend(citation_checks)

        # 2. Mathematical consistency checks
        math_checks = self._verify_math_consistency(synthesis)
        checks.extend(math_checks)

        # 3. Self-consistency check
        consistency_check = self._verify_self_consistency(synthesis)
        checks.append(consistency_check)

        # Calculate hallucination risk score
        if checks:
            non_verified = sum(
                1 for c in checks
                if c.result in (VerificationStatus.ERROR, VerificationStatus.UNVERIFIABLE)
            )
            warnings = sum(1 for c in checks if c.result == VerificationStatus.WARNING)
            risk = (non_verified * 0.3 + warnings * 0.1) / max(len(checks), 1)
            risk = min(1.0, risk)
        else:
            risk = 0.5  # No checks = uncertain

        flagged = [c.claim for c in checks if c.result in (VerificationStatus.ERROR, VerificationStatus.WARNING)]

        # Determine overall status
        if any(c.result == VerificationStatus.ERROR for c in checks):
            overall = "failed"
        elif any(c.result == VerificationStatus.WARNING for c in checks):
            overall = "passed_with_warnings"
        else:
            overall = "passed"

        report = VerificationReport(
            id=str(uuid.uuid4())[:8],
            concept_id=synthesis.concept_id,
            checks=checks,
            hallucination_risk_score=risk,
            flagged_items=flagged,
            overall_status=overall,
        )

        # Save report
        self.store.save_content(
            synthesis.concept_id,
            "verification_report.json",
            report,
        )

        # Update synthesis verification status
        synthesis.verified = overall in ("passed", "passed_with_warnings")
        synthesis.verification_report_id = report.id

        return report

    async def _verify_citations(self, synthesis: ResearchSynthesis) -> list[VerificationCheck]:
        """Verify that cited papers exist and metadata is correct."""
        checks = []

        for source in synthesis.sources:
            if source.arxiv_id and self.s2:
                try:
                    paper = await self.s2.get_paper(f"ARXIV:{source.arxiv_id}")
                    if paper and paper.get("title"):
                        checks.append(VerificationCheck(
                            check_type=CheckType.CITATION_EXISTENCE,
                            claim=f"{source.title} (arXiv:{source.arxiv_id})",
                            source_paper=source.arxiv_id,
                            result=VerificationStatus.VERIFIED,
                            details=f"Paper exists: {paper.get('title', '')}",
                            confidence=0.95,
                        ))
                    else:
                        checks.append(VerificationCheck(
                            check_type=CheckType.CITATION_EXISTENCE,
                            claim=f"{source.title} (arXiv:{source.arxiv_id})",
                            source_paper=source.arxiv_id,
                            result=VerificationStatus.WARNING,
                            details="Paper not found in Semantic Scholar",
                            confidence=0.6,
                        ))
                except Exception as e:
                    checks.append(VerificationCheck(
                        check_type=CheckType.CITATION_EXISTENCE,
                        claim=f"{source.title} (arXiv:{source.arxiv_id})",
                        source_paper=source.arxiv_id,
                        result=VerificationStatus.UNVERIFIABLE,
                        details=f"API error: {str(e)[:100]}",
                        confidence=0.3,
                    ))

            elif source.doi and self.crossref:
                try:
                    result = await self.crossref.verify_citation(source.doi)
                    if result.get("exists"):
                        checks.append(VerificationCheck(
                            check_type=CheckType.CITATION_EXISTENCE,
                            claim=f"{source.title} (DOI:{source.doi})",
                            source_paper=source.doi,
                            result=VerificationStatus.VERIFIED,
                            details=f"DOI verified: {result.get('title', '')}",
                            confidence=0.95,
                        ))
                    else:
                        checks.append(VerificationCheck(
                            check_type=CheckType.CITATION_EXISTENCE,
                            claim=f"{source.title} (DOI:{source.doi})",
                            source_paper=source.doi,
                            result=VerificationStatus.ERROR,
                            details="DOI not found in CrossRef",
                            confidence=0.9,
                        ))
                except Exception as e:
                    checks.append(VerificationCheck(
                        check_type=CheckType.CITATION_EXISTENCE,
                        claim=f"{source.title}",
                        result=VerificationStatus.UNVERIFIABLE,
                        details=f"CrossRef API error: {str(e)[:100]}",
                        confidence=0.3,
                    ))

        return checks

    def _verify_math_consistency(self, synthesis: ResearchSynthesis) -> list[VerificationCheck]:
        """Use LLM to check mathematical consistency of equations."""
        checks = []

        for eq in synthesis.mechanism.key_equations:
            if eq.source_paper:
                # Ask LLM to verify equation against stated source
                prompt = f"""Verify this equation:
Name: {eq.name}
LaTeX: {eq.latex}
Explanation: {eq.explanation}
Claimed source: {eq.source_paper} ({eq.source_equation_ref})

Check:
1. Is the LaTeX syntactically valid?
2. Is the equation dimensionally consistent?
3. Does the explanation match the equation?

Return JSON: {{"valid": true/false, "issues": ["list"], "confidence": 0.0-1.0}}"""

                try:
                    response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)
                    result = json.loads(response)

                    status = VerificationStatus.VERIFIED if result.get("valid", False) else VerificationStatus.WARNING
                    checks.append(VerificationCheck(
                        check_type=CheckType.MATHEMATICAL_CORRECTNESS,
                        claim=f"Equation '{eq.name}': {eq.latex[:80]}",
                        source_paper=eq.source_paper,
                        result=status,
                        details="; ".join(result.get("issues", [])) or "No issues found",
                        confidence=result.get("confidence", 0.5),
                    ))
                except Exception:
                    checks.append(VerificationCheck(
                        check_type=CheckType.MATHEMATICAL_CORRECTNESS,
                        claim=f"Equation '{eq.name}'",
                        source_paper=eq.source_paper,
                        result=VerificationStatus.UNVERIFIABLE,
                        details="Failed to verify",
                        confidence=0.3,
                    ))

        return checks

    def _verify_self_consistency(self, synthesis: ResearchSynthesis) -> VerificationCheck:
        """Check that intuition and mechanism layers are consistent."""
        equations_text = "\n".join(
            f"- {eq.name}: {eq.latex[:100]}"
            for eq in synthesis.mechanism.key_equations[:5]
        )

        prompt = SELF_CONSISTENCY_PROMPT.format(
            analogy=synthesis.intuition.analogy[:300],
            key_insight=synthesis.intuition.key_insight,
            math_excerpt=synthesis.mechanism.mathematical_framework[:500],
            equations=equations_text,
        )

        try:
            response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)
            result = json.loads(response)

            is_consistent = result.get("is_consistent", True)
            issues = result.get("issues", [])

            return VerificationCheck(
                check_type=CheckType.SELF_CONSISTENCY,
                claim="Intuition-Mechanism layer consistency",
                result=VerificationStatus.VERIFIED if is_consistent else VerificationStatus.WARNING,
                details="; ".join(issues) if issues else "Layers are consistent",
                confidence=result.get("confidence", 0.5),
            )
        except Exception:
            return VerificationCheck(
                check_type=CheckType.SELF_CONSISTENCY,
                claim="Intuition-Mechanism layer consistency",
                result=VerificationStatus.UNVERIFIABLE,
                details="Failed to check consistency",
                confidence=0.3,
            )
