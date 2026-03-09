---
name: adaptive-controller
description: |
  4-level learning adaptation state machine based on quiz performance.
  Trigger: "adapt learning", "struggling with concept", "need different explanation",
    "adjust difficulty", "intervention needed", "learning stuck"
  DO NOT USE: for generating quizzes (use quiz-engine),
    for generating initial content (use deep-researcher),
    for tracking overall progress (use progress-tracker)
---

# Adaptive Controller

Implements a 4-level intervention state machine that responds to quiz results.
When a learner struggles with a concept, the controller escalates through
increasingly targeted interventions: alternative explanations, prerequisite
insertion, concept splitting, and Socratic dialogue.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 3 - Learning Delivery & Adaptation |
| CLI command | (automatically triggered by quiz results) |
| Python module | `src/skills/adaptive_controller.py` |
| Key class | `AdaptiveController` |
| Input | `QuizResult` + `KnowledgeGraph` + `AssessmentProfile` |
| Output | Modified graph, alternative content, or dialogue questions |
| Data models | `src/models/quiz.py` (QuizResult), `src/models/knowledge_graph.py` |

## Step-by-Step Instructions

### Determine Intervention Level

1. After Quiz Engine produces a `QuizResult`, call
   `AdaptiveController.determine_level(quiz_result, concept, history)`.
2. The controller evaluates the score and previous attempt history:

   | Level | Condition | Intervention |
   |---|---|---|
   | 0 (Normal) | Score >= 70% | No intervention. Proceed to next concept. |
   | 1 (Alternative) | Score 40-69%, first attempt | Generate alternative explanation. |
   | 2 (Prerequisite) | Score < 40% | Insert prerequisite nodes into graph. |
   | 3 (Split) | Persistent struggle (2+ failed attempts) | Split concept into sub-concepts. |
   | 4 (Socratic) | All above exhausted | Enter guided Socratic dialogue. |

3. Returns the intervention level and recommended action.

### Execute Intervention

1. Call `AdaptiveController.intervene(level, concept, profile, graph)`.
2. Actions per level:

   **Level 1 - Alternative Explanation**
   - Calls `DeepResearcher.generate_alternative_explanation(concept, profile, synthesis)`.
   - A different analogy, visual model, and mathematical framing is generated.
   - Learner studies the alternative, then retakes the quiz.

   **Level 2 - Prerequisite Review**
   - Analyzes the quiz result's `weak_areas` to identify missing prerequisites.
   - Calls `DomainMapper.add_prerequisite_node(graph, concept_id, prerequisite)`.
   - New prerequisite nodes are inserted into the knowledge graph.
   - Learner is redirected to study the prerequisites first.

   **Level 3 - Concept Splitting**
   - The concept is too broad or complex for the learner.
   - Calls `DomainMapper.split_concept(graph, concept_id, sub_concepts)`.
   - The original node is replaced with 2-4 smaller, more focused nodes.
   - Each sub-concept gets its own synthesis and quiz cycle.

   **Level 4 - Socratic Dialogue**
   - Generates a sequence of guiding questions that lead the learner to
     understanding through self-discovery.
   - LLM produces questions based on the specific weak areas identified.
   - Questions progress from concrete examples to abstract principles.
   - No quiz re-take; the dialogue itself is the learning activity.

### State Tracking

- The controller maintains an intervention history per concept to know
  which levels have been attempted.
- History stored in `data/content/{concept_id}/intervention_history.json`.

## Key Implementation Details

- Level determination uses both the current score and the full attempt history
  for the concept (number of prior attempts, scores over time).
- Cross-skill calls: Level 1 calls DeepResearcher, Levels 2-3 call DomainMapper.
- Level escalation is monotonic within a learning session: once at Level 2,
  the controller does not drop back to Level 1 for the same concept.
- Socratic dialogue questions are generated from the synthesis content and
  the quiz's identified weak areas.

## Anti-Patterns

- **Do not skip intervention levels.** The escalation sequence (1 -> 2 -> 3 -> 4)
  is designed so that simpler interventions are tried first. Jumping to
  concept splitting when an alternative explanation might suffice wastes
  effort and fragments the graph unnecessarily.

- **Do not trigger interventions manually without quiz data.** The controller
  relies on the quiz result's `weak_areas` and `bloom_level` breakdown to
  target its interventions. Without this data, interventions are unfocused.

- **Do not let concept splitting recurse indefinitely.** If a sub-concept
  itself triggers Level 3, the controller should escalate to Level 4
  (Socratic dialogue) rather than splitting further. Limit split depth to 1.
