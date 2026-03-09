---
name: quiz-engine
description: |
  Multi-type assessment with Bloom's taxonomy alignment.
  Trigger: "generate quiz", "test knowledge", "create questions",
    "assessment questions", "evaluate understanding", "quiz me"
  DO NOT USE: for diagnostic pre-assessment (use pre-assessor),
    for adapting after poor scores (use adaptive-controller),
    for spaced repetition review (use spaced-repetition)
---

# Quiz Engine

Generates concept-specific assessments using four question types aligned to
Bloom's taxonomy levels. Adapts difficulty based on the learner's previous
scores and learning goal. Evaluates answers and produces scored results that
feed into the Adaptive Controller and Progress Tracker.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 3 - Learning Delivery & Adaptation |
| CLI command | (invoked as part of `newlearner learn` workflow) |
| Python module | `src/skills/quiz_engine.py` |
| Key class | `QuizEngine` |
| Input | `ResearchSynthesis` + `AssessmentProfile` + previous quiz scores |
| Output | `data/content/{concept_id}/quiz.json` + `quiz_result.json` |
| Data models | `src/models/quiz.py` (Quiz, QuizQuestion, QuizResult, QuestionType, BloomLevel) |

## Step-by-Step Instructions

### Generate a Quiz

1. Load the `ResearchSynthesis` for the target concept.
2. Call `QuizEngine.generate_quiz(synthesis, profile, previous_scores)`.
3. LLM generates questions across four types:

   | Question Type | Description | Bloom Levels |
   |---|---|---|
   | MULTIPLE_CHOICE | Conceptual understanding, 4 options | REMEMBER, UNDERSTAND |
   | DERIVATION | Derive or prove a mathematical result | APPLY, ANALYZE |
   | CODE_COMPLETION | Complete a function given a stub and docstring | APPLY, CREATE |
   | CONCEPT_COMPARISON | Compare/contrast two related concepts | ANALYZE, EVALUATE |

4. Question mix adapts to `LearningGoal`:
   - REPRODUCE_PAPERS: more DERIVATION and CODE_COMPLETION.
   - UNDERSTAND_CONCEPTS: more MULTIPLE_CHOICE and CONCEPT_COMPARISON.
   - IMPLEMENT_METHODS: more CODE_COMPLETION.
5. Difficulty scales with previous scores: higher scores yield harder questions.
6. Quiz saved to `data/content/{concept_id}/quiz.json`.

### Evaluate Answers

1. Collect learner answers for each question.
2. Call `QuizEngine.evaluate_answers(quiz, answers)`.
   - MULTIPLE_CHOICE: exact match scoring.
   - DERIVATION: LLM evaluates mathematical correctness and completeness
     (partial credit 0.0-1.0).
   - CODE_COMPLETION: LLM evaluates functional correctness, style, and
     edge case handling (partial credit 0.0-1.0).
   - CONCEPT_COMPARISON: LLM evaluates depth, accuracy, and coverage of
     key differences (partial credit 0.0-1.0).
3. Result includes: total_score (0-100%), per_question scores, bloom_level
   breakdown, time_taken, and identified weak_areas.
4. Result saved to `data/content/{concept_id}/quiz_result.json`.
5. Result forwarded to Adaptive Controller and Progress Tracker.

### Score Interpretation

| Score | Meaning | Next Action |
|---|---|---|
| >= 70% | Concept mastered at current level | Proceed to next concept |
| 40-69% | Partial understanding | Adaptive Controller Level 1: alternative explanation |
| < 40% | Significant gaps | Adaptive Controller Level 2+: prerequisite review |

## Key Implementation Details

- `BloomLevel` enum: REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE, CREATE.
- Each `QuizQuestion` has: id, type, bloom_level, question_text, options
  (for MC), expected_answer, rubric, max_score, difficulty (1-5).
- Partial credit evaluation uses a rubric string that guides LLM scoring.
- Previous scores from `quiz_result.json` files inform difficulty calibration.

## Anti-Patterns

- **Do not generate quizzes before synthesizing content.** The quiz draws
  directly from the ResearchSynthesis; without it, questions lack grounding
  in the actual learning material and may test irrelevant details.

- **Do not rely solely on MULTIPLE_CHOICE for advanced learners.** Higher
  Bloom levels (ANALYZE, CREATE) require open-ended question types.
  Multiple-choice only tests recognition, not deep understanding.

- **Do not ignore the bloom_level breakdown in results.** A learner scoring
  high on REMEMBER but low on APPLY has surface knowledge without
  operational understanding. The Adaptive Controller uses this breakdown.
