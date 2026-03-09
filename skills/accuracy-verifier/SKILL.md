---
name: accuracy-verifier
description: |
  Anti-hallucination content verification against source papers.
  Trigger: "verify content", "check accuracy", "validate citations",
    "hallucination check", "fact-check synthesis"
  DO NOT USE: for generating content (use deep-researcher),
    for quiz evaluation (use quiz-engine),
    for progress assessment (use progress-tracker)
---

# Accuracy Verifier

Runs automated verification checks on Deep Researcher output to detect
hallucinated citations, mathematical inconsistencies, and contradictions
between the intuition and mechanism layers. Produces a verification report
with a hallucination risk score; content scoring above 0.3 is flagged for
human review.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 2 - Knowledge Construction & Verification |
| CLI command | (auto-triggered after `newlearner learn`) |
| Python module | `src/skills/accuracy_verifier.py` |
| Key class | `AccuracyVerifier` |
| Input | `ResearchSynthesis` from Deep Researcher |
| Output | `data/content/{concept_id}/verification_report.json` |
| Data models | `src/models/verification.py` (VerificationReport, VerificationCheck, CheckType, VerificationStatus) |
| External APIs | SemanticScholarClient, CrossRefClient |

## Step-by-Step Instructions

### Full Verification (Default After Synthesis)

1. Receive a `ResearchSynthesis` object from Deep Researcher.
2. Call `AccuracyVerifier.verify(synthesis)`. This runs three checks in parallel:

   **a. Citation Existence (`_verify_citations`)**
   - For each `SourceAttribution` in key_equations and reference_implementations,
     queries Semantic Scholar API by title/DOI and CrossRef API by DOI.
   - Marks each citation as VERIFIED, UNVERIFIED, or SUSPICIOUS.
   - UNVERIFIED: paper not found in any database.
   - SUSPICIOUS: paper found but metadata mismatch (wrong authors, year).

   **b. Mathematical Consistency (`_verify_math_consistency`)**
   - LLM-based check: sends all key_equations to the LLM and asks it to
     verify dimensional consistency, correct use of notation, and whether
     equations match their stated source papers.
   - Flags equations where the LLM has low confidence in correctness.

   **c. Self-Consistency (`_verify_self_consistency`)**
   - LLM compares the intuition layer (analogy, key_insight) against the
     mechanism layer (mathematical_framework, key_equations).
   - Checks whether the analogy accurately represents the math.
   - Checks whether the key_insight is consistent with the equations.

3. Each check produces `VerificationCheck` objects with `CheckType`, status,
   message, and confidence score.
4. Aggregated into `VerificationReport` with `hallucination_risk_score` (0-1).
5. Report saved to `data/content/{concept_id}/verification_report.json`.

### Interpreting the Risk Score

| Risk Score | Action |
|---|---|
| 0.0 - 0.1 | Content is likely reliable. Proceed to learning delivery. |
| 0.1 - 0.3 | Minor concerns. Review flagged items but generally safe. |
| 0.3 - 0.6 | Moderate risk. Human review required before use. |
| 0.6 - 1.0 | High risk. Re-synthesize the concept or manually correct. |

### Manual Re-Verification

1. After editing a synthesis (e.g., correcting a citation), re-run
   `AccuracyVerifier.verify(updated_synthesis)` to refresh the report.

## Key Implementation Details

- Citation checks are async: Semantic Scholar and CrossRef queries run
  concurrently via `asyncio.gather`.
- `CheckType` enum: CITATION_EXISTENCE, MATH_CONSISTENCY, SELF_CONSISTENCY.
- `VerificationStatus` enum: PASSED, WARNING, FAILED.
- Risk score formula weights: citation issues (0.4), math issues (0.35),
  self-consistency issues (0.25).
- Rate limiting: Semantic Scholar free tier allows 100 req/5min; the verifier
  batches queries and respects backoff.

## Anti-Patterns

- **Do not disable verification to save API tokens.** Hallucinated citations
  and incorrect equations undermine the entire learning system. The cost of
  verification is small compared to learning wrong material.

- **Do not treat risk score 0.0 as guaranteed correctness.** The verifier
  catches many issues but cannot detect all mathematical errors. It
  supplements, not replaces, the learner's critical reading.

- **Do not re-verify unchanged content.** Verification results are
  deterministic for the citation check. Only re-run after edits or when
  API data may have updated (new papers published).
