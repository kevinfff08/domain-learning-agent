---
name: practice-generator
description: |
  Interactive exercise generation: coding challenges, notebooks, and paper reproduction guides.
  Trigger: "generate exercises", "create coding challenge", "practice problems",
    "generate notebook", "reproduction guide", "hands-on practice"
  DO NOT USE: for flashcard-style review (use spaced-repetition),
    for quiz assessment (use quiz-engine),
    for content synthesis (use deep-researcher)
---

# Practice Generator

Creates three types of interactive exercises for hands-on learning: coding
challenges with function stubs, test suites, and solutions; guided Jupyter
notebooks mixing explanation with code TODOs; and paper reproduction guides
with environment setup, hyperparameters, and checkpoint validation.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 3 - Learning Delivery & Adaptation |
| CLI command | (invoked as part of `newlearner learn` workflow) |
| Python module | `src/skills/practice_generator.py` |
| Key class | `PracticeGenerator` |
| Input | `ResearchSynthesis` + `AssessmentProfile` |
| Output | `data/exercises/{concept_id}/` directory |
| Data models | `src/models/content.py` (exercise-related types) |
| Dependencies | `nbformat` for notebook generation |

## Step-by-Step Instructions

### Generate Coding Challenge

1. Call `PracticeGenerator.generate_coding_challenge(synthesis, profile)`.
2. Creates a self-contained exercise directory:
   ```
   data/exercises/{concept_id}/coding/
     challenge.py     # Function stubs with docstrings and type hints
     test_challenge.py # pytest test suite (5-10 tests)
     hints.md         # Progressive hints (3 levels)
     solution.py      # Reference solution with comments
   ```
3. Challenge difficulty matches the learner's programming `SkillLevel`:
   - BEGINNER: fill in a single function body.
   - INTERMEDIATE: implement a class with 2-3 methods.
   - ADVANCED: implement an algorithm end-to-end with edge cases.
4. Tests cover correctness, edge cases, and numerical precision.

### Generate Guided Notebook

1. Call `PracticeGenerator.generate_notebook(synthesis, profile)`.
2. Creates a Jupyter notebook at `data/exercises/{concept_id}/notebook.ipynb`:
   - Markdown cells: concept overview, mathematical background, key equations.
   - Code cells marked `# TODO: implement ...` for the learner to complete.
   - Pre-written visualization cells (matplotlib plots) that run after
     the learner completes the TODOs.
   - Solution cells hidden in a collapsed section at the end.
3. Uses `nbformat` to construct the notebook programmatically.
4. Notebook includes pip install commands for any extra dependencies.

### Generate Paper Reproduction Guide

1. Call `PracticeGenerator.generate_reproduction_guide(synthesis, profile)`.
2. Creates a structured guide at `data/exercises/{concept_id}/reproduction/`:
   ```
   data/exercises/{concept_id}/reproduction/
     README.md          # Full guide document
     environment.yml    # Conda environment specification
     config.yaml        # Key hyperparameters with explanations
     checkpoints.md     # Expected intermediate results at each stage
   ```
3. Guide sections:
   - **Environment Setup**: conda env, GPU requirements, library versions.
   - **Hyperparameters**: each hyperparameter with its value, source paper
     reference, and sensitivity notes.
   - **Common Pitfalls**: known failure modes with symptoms and fixes.
   - **Checkpoints**: expected loss/metric values at training steps 100,
     1000, 10000 etc. for validation.
4. Only generated when `LearningGoal` is REPRODUCE_PAPERS or EXTEND_RESEARCH.

## Key Implementation Details

- Coding challenges use Python type hints and Google-style docstrings.
- Test suites use `pytest` with parametrized test cases and `numpy.testing`
  for numerical comparisons.
- Notebooks use `nbformat.v4` API; cell metadata includes difficulty tags.
- Reproduction guides pull hyperparameters from the synthesis's PracticeLayer.
- Exercise directory structure is standardized for Material Integrator to
  discover and package exercises.

## Anti-Patterns

- **Do not generate reproduction guides for theoretical concepts.** Only
  concepts with concrete implementations (models, algorithms, training
  procedures) benefit from reproduction guides. Theoretical concepts
  should use coding challenges or notebooks instead.

- **Do not generate exercises without a completed synthesis.** The exercises
  draw directly from the synthesis content (equations, pseudocode,
  hyperparameters). Without it, exercises lack grounding and may test
  unrelated skills.

- **Do not generate all three exercise types for every concept.** Choose
  based on the concept's nature and learner's goal. A pure math concept
  benefits from a derivation notebook, not a reproduction guide.
