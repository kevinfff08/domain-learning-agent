---
name: deep-researcher
description: |
  PhD-level three-layer content synthesis for research concepts.
  Trigger: "learn concept", "deep research", "synthesize content",
    "generate learning material", "explain concept", "newlearner learn"
  DO NOT USE: for verifying generated content (use accuracy-verifier),
    for finding external resources (use resource-curator),
    for generating quizzes (use quiz-engine)
---

# Deep Researcher

Generates PhD-level learning content for a single concept using a three-layer
synthesis structure: Intuition (analogies, visual descriptions, key insights),
Mechanism (mathematical framework, key equations with source attribution,
pseudocode, algorithm steps), and Practice (reference implementations,
hyperparameters, common pitfalls, reproduction checklists). The Accuracy
Verifier runs automatically after synthesis.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 2 - Knowledge Construction & Verification |
| CLI command | `newlearner learn` |
| Python module | `src/skills/deep_researcher.py` |
| Key class | `DeepResearcher` |
| Input | `ConceptNode` from knowledge graph + `AssessmentProfile` |
| Output | `data/content/{concept_id}/research_synthesis.json` |
| Data models | `src/models/content.py` (ResearchSynthesis, IntuitionLayer, MechanismLayer, PracticeLayer, Equation, SourceAttribution) |

## Step-by-Step Instructions

### Synthesize Content for a Concept

1. Load the knowledge graph and identify the target `ConceptNode`.
2. Call `DeepResearcher.synthesize(concept, profile, graph)`.
   - LLM generates all three layers in a single structured response:
   - **Intuition layer**: `analogy`, `visual_description`, `why_it_matters`,
     `key_insight`.
   - **Mechanism layer**: `mathematical_framework` (LaTeX), `key_equations`
     (each with `name`, `latex`, `source_paper`, `explanation`),
     `pseudocode`, `algorithm_steps`, `connections` to related concepts.
   - **Practice layer**: `reference_implementations` (GitHub links),
     `key_hyperparameters`, `common_pitfalls`, `reproduction_checklist`.
3. Content adapts to user's `LearningStyle` and `SkillLevel`:
   - CODE_FIRST style: more pseudocode and implementation detail.
   - MATHEMATICAL style: deeper equation derivations.
   - VISUAL style: richer visual_description and analogy.
4. Output saved to `data/content/{concept_id}/research_synthesis.json`.
5. Accuracy Verifier is triggered automatically after synthesis.

### Generate Alternative Explanation

1. Called by Adaptive Controller when a learner scores 40-60% on a quiz
   (Level 1 intervention).
2. Call `DeepResearcher.generate_alternative_explanation(concept, profile, previous_synthesis)`.
   - LLM produces a different analogy, visual description, and
     mathematical framing while covering the same core content.
   - The alternative is appended to the existing synthesis, not replacing it.
3. Useful when the original explanation does not resonate with the learner.

## Key Implementation Details

- Every `Equation` in `key_equations` must have a `SourceAttribution` with
  paper title, authors, year, and DOI/arXiv ID. This is verified by
  Accuracy Verifier.
- `CrossConceptConnection` links the current concept to related nodes in
  the knowledge graph, explaining how they relate.
- Content length scales with concept `difficulty_level`: higher difficulty
  gets more detailed mechanism and practice layers.
- LLM prompt includes `related_concepts` from the graph for contextual
  cross-referencing.

## Anti-Patterns

- **Do not skip the Accuracy Verifier step.** LLM-generated equations and
  citations are prone to hallucination. Always run verification before
  presenting content to the learner.

- **Do not synthesize concepts out of topological order.** Prerequisites
  should be synthesized first so that cross-concept connections reference
  existing content. The knowledge graph's topological sort defines the order.

- **Do not call generate_alternative_explanation without a quiz result.**
  Alternative explanations are a response to demonstrated confusion, not
  a substitute for the primary synthesis. Generating alternatives
  preemptively wastes API tokens.
