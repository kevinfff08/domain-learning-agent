---
name: progress-tracker
description: |
  Learning progress metrics tracking and reporting.
  Trigger: "show progress", "track progress", "learning stats",
    "weekly report", "completion rate", "newlearner progress"
  DO NOT USE: for quiz generation or evaluation (use quiz-engine),
    for adapting learning based on scores (use adaptive-controller),
    for visualizing the knowledge graph (use path-visualizer)
---

# Progress Tracker

Tracks quantitative learning progress across all concepts: completion rates,
quiz scores, time spent, mastery levels, and streak days. Generates weekly
reports and keeps the knowledge graph's node statuses synchronized with
actual learner progress.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 4 - Output & Tracking |
| CLI command | `newlearner progress` |
| Python module | `src/skills/progress_tracker.py` |
| Key class | `ProgressTracker` |
| Input | Quiz results, time logs, graph state |
| Output | `data/user/progress.json` |
| Data models | `src/models/progress.py` (progress-related types) |

## Step-by-Step Instructions

### Initialize Progress from Knowledge Graph

1. After Domain Mapper builds the knowledge graph, call
   `ProgressTracker.initialize_from_graph(graph)`.
2. Creates a progress entry for each concept node with:
   - status: NOT_STARTED
   - mastery_level: 0.0
   - quiz_scores: []
   - time_spent_hours: 0.0
3. Initializes aggregate metrics: concepts_total, completion_rate (0%),
   total_hours_spent (0), average_quiz_score (0), streak_days (0).
4. Saves to `data/user/progress.json`.

### Record Learning Activity

**Start a concept:**
1. Call `ProgressTracker.start_concept(concept_id)`.
   - Sets concept status to IN_PROGRESS.
   - Records start timestamp.
   - Syncs status to knowledge graph via `DomainMapper.update_node_status`.

**Record quiz result:**
1. Call `ProgressTracker.record_quiz_result(concept_id, quiz_result)`.
   - Appends score to the concept's quiz_scores list.
   - Updates mastery_level based on latest and average scores.
   - If score >= 70%: marks concept as LEARNED.
   - If average of last 3 scores >= 85%: marks concept as MASTERED.
   - Updates aggregate average_quiz_score.

**Record time spent:**
1. Call `ProgressTracker.record_time(concept_id, hours)`.
   - Adds hours to concept's time_spent_hours.
   - Updates aggregate total_hours_spent.

### Generate Weekly Report

1. Call `ProgressTracker.generate_weekly_report()`.
2. Report includes:
   - Concepts completed this week (count and names).
   - Total time spent this week.
   - Average quiz score this week vs. overall.
   - Current streak (consecutive days with learning activity).
   - Concepts in progress and estimated time to completion.
   - Weak areas identified from recent quiz results.
3. Report printed to terminal via Rich and optionally saved to
   `output/reports/weekly_{date}.md`.

### Sync with Graph

1. Call `ProgressTracker.sync_with_graph(graph)`.
   - If the graph has been modified (nodes added/split by Adaptive Controller),
     progress entries are created for new nodes.
   - Removed nodes have their progress entries archived.
   - Ensures progress.json and knowledge_graph.json are consistent.

## Aggregate Metrics

| Metric | Type | Description |
|---|---|---|
| concepts_total | int | Total concept nodes in the graph |
| concepts_completed | int | Nodes with LEARNED or MASTERED status |
| completion_rate | float | concepts_completed / concepts_total |
| total_hours_spent | float | Cumulative study time |
| average_quiz_score | float | Mean of all quiz scores (0-100) |
| streak_days | int | Consecutive days with at least one activity |

## Per-Concept Metrics

| Metric | Type | Description |
|---|---|---|
| status | ConceptStatus | NOT_STARTED, IN_PROGRESS, LEARNED, MASTERED, SKIPPED |
| mastery_level | float | 0.0 to 1.0 composite score |
| quiz_scores | list[float] | History of all quiz scores |
| time_spent_hours | float | Total study time for this concept |
| started_at | datetime | When the learner started this concept |
| completed_at | datetime | When the learner achieved LEARNED/MASTERED |

## Anti-Patterns

- **Do not update progress manually in the JSON file.** Use the class
  methods to maintain consistency between progress.json and the
  knowledge graph. Manual edits can desynchronize the two.

- **Do not call sync_with_graph before every operation.** Sync is needed
  only after the graph structure changes (node addition or splitting).
  Calling it on every quiz result is wasteful.

- **Do not conflate streak_days with quality.** A long streak of brief,
  low-score sessions is worse than focused study. The weekly report
  combines streak with quiz scores to give a balanced picture.
