---
name: pre-assessor
description: |
  Multi-dimensional diagnostic assessment of learner background.
  Trigger: "assess learner", "diagnostic assessment", "evaluate background",
    "check prerequisites", "skill assessment", "newlearner assess"
  DO NOT USE: for quiz generation (use quiz-engine), for progress tracking
    (use progress-tracker), for adapting difficulty (use adaptive-controller)
---

# Pre-Assessor

Assesses a learner's math foundations, programming skills, and domain knowledge
through diagnostic questions or quick self-assessment. Produces a structured
assessment profile that downstream skills (Domain Mapper, Deep Researcher) use
to calibrate content difficulty and prerequisite selection.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 1 - Assessment & Planning |
| CLI command | `newlearner assess` |
| Python module | `src/skills/pre_assessor.py` |
| Key class | `PreAssessor` |
| Input | Target field name + optional background description |
| Output | `data/user/assessment_profile.json` |
| Data models | `src/models/assessment.py` (AssessmentProfile, DiagnosticQuestion, SkillLevel, LearningGoal) |

## Step-by-Step Instructions

### Full Diagnostic Assessment

1. Call `PreAssessor.generate_diagnostic_questions(field, count=15)`.
   - LLM generates multiple-choice questions across three dimensions:
     math (linear algebra, probability, calculus, optimization),
     programming (Python, PyTorch, JAX, distributed training),
     and domain knowledge specific to the target field.
   - Each question has difficulty 1-5, four options, one correct answer.
2. Present questions to the learner and collect answers.
3. Call `PreAssessor.evaluate_results(questions, answers)`.
   - Scores each dimension, assigns `SkillLevel` (NOVICE through EXPERT).
   - Determines recommended `LearningGoal` and `LearningStyle`.
4. Result: `AssessmentProfile` saved to `data/user/assessment_profile.json`.

### Quick Self-Assessment

1. Call `PreAssessor.quick_assess(field, background_description)`.
   - LLM infers skill levels from a free-text background description
     (e.g., "I have a CS masters, comfortable with PyTorch, weak in measure theory").
   - No diagnostic questions generated.
2. Result: `AssessmentProfile` with `is_self_reported=True`.

### Re-Assessment After Learning

1. Load existing profile from `data/user/assessment_profile.json`.
2. Run `generate_diagnostic_questions()` targeting weak dimensions only.
3. Merge new scores into the existing profile.

## Key Implementation Details

- `SkillLevel` enum: NOVICE (1), BEGINNER (2), INTERMEDIATE (3), ADVANCED (4), EXPERT (5).
- `LearningGoal` enum: UNDERSTAND_CONCEPTS, IMPLEMENT_METHODS, REPRODUCE_PAPERS, EXTEND_RESEARCH.
- `LearningStyle` enum: VISUAL, MATHEMATICAL, CODE_FIRST, EXAMPLE_DRIVEN.
- The `MathFoundations` model tracks: linear_algebra, probability, calculus, optimization.
- The `ProgrammingSkills` model tracks: python, pytorch, jax, distributed.
- Questions use difficulty 1-5 scale; scoring maps to `SkillLevel` thresholds.

## Anti-Patterns

- **Do not skip assessment before mapping.** Domain Mapper relies on the
  assessment profile to calibrate graph depth and prerequisite inclusion.
  Running `newlearner map` without a profile produces a generic graph.

- **Do not use quick_assess for high-stakes decisions.** Self-reported levels
  are often inaccurate. Use full diagnostic when the learner's actual level
  critically affects content generation (e.g., whether to include measure
  theory prerequisites for diffusion models).

- **Do not regenerate the full profile repeatedly.** If the learner has
  progressed, run a targeted re-assessment on weak dimensions rather than
  starting from scratch, which discards historical data.
