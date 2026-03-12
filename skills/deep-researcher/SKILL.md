---
name: deep-researcher
description: |
  PhD-level three-layer content synthesis for research concepts.
  Uses 3 specialized LLM calls (mechanism → intuition + practice in parallel).
  Trigger: "learn concept", "deep research", "synthesize content",
    "generate learning material", "explain concept", "newlearner learn"
  DO NOT USE: for verifying generated content (use accuracy-verifier),
    for finding external resources (use resource-curator),
    for generating quizzes (use quiz-engine)
---

# Deep Researcher

Generates PhD-level learning content for a single concept using a three-layer
synthesis structure with **3 specialized LLM calls**:

1. **Mechanism layer** (temp 0.2): Continuous mathematical narrative with
   definitions → assumptions → theorems → full derivations → remarks.
   Includes key equations with source attribution and academic-style
   algorithm blocks (Algorithm environment).
2. **Intuition layer** (temp 0.4, parallel): Deep analogies with explicit
   mappings and limitations, core non-obvious insights, historical context
   and downstream impact analysis.
3. **Practice layer** (temp 0.2, parallel): Concrete runnable code with
   line-by-line annotations and design decision explanations, hyperparameter
   guidance with reasoning, common pitfalls with fixes.

Calls 2 and 3 run in parallel after call 1 completes, using the mechanism
summary for cross-layer consistency. The Accuracy Verifier runs automatically
after synthesis.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 2 - Knowledge Construction & Verification |
| CLI command | `newlearner learn` |
| Python module | `src/skills/deep_researcher.py` |
| Key class | `DeepResearcher` |
| Input | `Chapter` from textbook + `AssessmentProfile` |
| Output | `data/courses/{course_id}/content/{chapter_id}/research_synthesis.json` |
| Data models | `src/models/content.py` (ResearchSynthesis, IntuitionLayer, MechanismLayer, PracticeLayer, Equation, AlgorithmBlock, CodeAnalysis, SourceAttribution) |

## Step-by-Step Instructions

### Synthesize Content for a Chapter

1. Load the textbook and identify the target `Chapter`.
2. Call `DeepResearcher.synthesize(chapter, textbook, profile, on_progress)`.
   - Fetches paper context via RAG (Semantic Scholar + arXiv).
   - **Call 1 — Mechanism** (runs first):
     - `theoretical_narrative`: 1000-2000 words of continuous mathematical
       exposition (definitions → theorems → full derivations → remarks).
     - `mathematical_framework`: High-level formulation overview.
     - `key_equations`: 5-8 equations with full derivation steps and source
       attribution.
     - `algorithms`: Academic paper-style pseudocode blocks (Algorithm
       environment with inputs, outputs, numbered steps).
   - **Call 2 — Intuition** (parallel with Call 3):
     - `analogy`: 500+ words with explicit mapping table and limitations.
     - `key_insight`: 200+ words on non-obvious breakthrough analysis.
     - `why_it_matters`: 300+ words covering history, impact, and open problems.
   - **Call 3 — Practice** (parallel with Call 2):
     - `code_analysis`: Complete runnable code (50-150 lines) with
       line-by-line annotations and design decision explanations.
     - `key_hyperparameters`: Values with reasoning (not just numbers).
     - `common_pitfalls`: Detailed descriptions with fixes.
     - `reproduction_checklist`: Step-by-step guide.
3. Content adapts to user's `LearningGoal` and math level.
4. Output saved to course content directory.
5. Accuracy Verifier is triggered automatically after synthesis.

### Generate Alternative Explanation

1. Called by Adaptive Controller when a learner scores 40-60% on a quiz
   (Level 1 intervention).
2. Call `DeepResearcher.generate_alternative_explanation(chapter, previous_synthesis)`.
   - LLM produces a different analogy and mathematical framing.
3. Useful when the original explanation does not resonate with the learner.

## Key Implementation Details

- Every `Equation` in `key_equations` must have a `SourceAttribution` with
  arXiv ID or DOI. This is verified by Accuracy Verifier.
- `AlgorithmBlock` follows academic paper Algorithm environment format with
  explicit inputs, outputs, and numbered steps supporting inline LaTeX.
- `CodeAnalysis` provides runnable code with `line_annotations` (e.g.,
  "Lines 7-15: Implements noise schedule from Eq. X") and
  `key_design_decisions` explaining engineering choices.
- `theoretical_narrative` is a continuous mathematical exposition — not a
  list of formulas but a connected narrative like a graduate textbook chapter.
- The mechanism summary is passed to intuition and practice generators for
  cross-layer consistency.
- `on_progress` callback sends SSE events for real-time progress display.

## Anti-Patterns

- **Do not skip the Accuracy Verifier step.** LLM-generated equations and
  citations are prone to hallucination. Always run verification.

- **Do not synthesize chapters out of order.** Prerequisites should be
  synthesized first for meaningful cross-concept connections.

- **Do not call generate_alternative_explanation without a quiz result.**
  Alternative explanations respond to demonstrated confusion, not as a
  substitute for primary synthesis.
