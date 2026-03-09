"""Skill 11: Progress Tracker - Learning metrics and visualization."""

from __future__ import annotations

from datetime import datetime

from src.models.knowledge_graph import ConceptStatus, KnowledgeGraph
from src.models.progress import ConceptProgress, LearnerProgress, WeeklyStats
from src.models.quiz import QuizResult
from src.storage.local_store import LocalStore


class ProgressTracker:
    """Learning progress tracking skill."""

    def __init__(self, store: LocalStore):
        self.store = store

    def get_or_create_progress(self, field: str) -> LearnerProgress:
        """Load existing progress or create new."""
        progress = self.store.load_progress(LearnerProgress)
        if progress is None:
            progress = LearnerProgress(field=field)
            self.store.save_progress(progress)
        return progress

    def initialize_from_graph(self, graph: KnowledgeGraph) -> LearnerProgress:
        """Initialize progress tracking from a knowledge graph."""
        progress = self.get_or_create_progress(graph.field)

        for node in graph.nodes:
            if node.id not in progress.concepts:
                progress.concepts[node.id] = ConceptProgress(
                    concept_id=node.id,
                    status=node.status.value,
                    mastery_level=node.mastery,
                )

        progress.updated_at = datetime.now()
        self.store.save_progress(progress)
        return progress

    def start_concept(self, progress: LearnerProgress, concept_id: str) -> LearnerProgress:
        """Mark a concept as started."""
        cp = progress.get_or_create_concept(concept_id)
        cp.status = "in_progress"
        cp.started_at = datetime.now()
        cp.last_accessed = datetime.now()
        progress.last_active = datetime.now()
        progress.updated_at = datetime.now()
        self.store.save_progress(progress)
        return progress

    def record_quiz_result(
        self,
        progress: LearnerProgress,
        quiz_result: QuizResult,
    ) -> LearnerProgress:
        """Record a quiz result for a concept."""
        cp = progress.get_or_create_concept(quiz_result.concept_id)
        cp.quiz_scores.append(quiz_result.overall_score)
        cp.mastery_level = max(cp.mastery_level, quiz_result.overall_score)
        cp.last_accessed = datetime.now()

        if quiz_result.passed:
            cp.status = "completed"
            cp.completed_at = datetime.now()

        progress.last_active = datetime.now()
        progress.updated_at = datetime.now()
        self.store.save_progress(progress)
        return progress

    def record_time(
        self,
        progress: LearnerProgress,
        concept_id: str,
        hours: float,
    ) -> LearnerProgress:
        """Record time spent on a concept."""
        cp = progress.get_or_create_concept(concept_id)
        cp.time_spent_hours += hours
        progress.total_hours_spent += hours
        progress.last_active = datetime.now()
        progress.updated_at = datetime.now()
        self.store.save_progress(progress)
        return progress

    def generate_weekly_report(self, progress: LearnerProgress) -> str:
        """Generate a markdown weekly progress report."""
        report = f"""# Weekly Progress Report
**Field:** {progress.field}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Overview
- **Concepts completed:** {progress.concepts_completed}/{progress.concepts_total}
- **Completion rate:** {progress.completion_rate:.0%}
- **Total time spent:** {progress.total_hours_spent:.1f} hours
- **Average quiz score:** {progress.average_quiz_score:.0%}
- **Streak:** {progress.streak_days} days

## Concept Status
| Concept | Status | Mastery | Quiz Scores | Time |
|---------|--------|---------|-------------|------|
"""
        for cid, cp in sorted(progress.concepts.items()):
            scores = ", ".join(f"{s:.0%}" for s in cp.quiz_scores[-3:]) if cp.quiz_scores else "-"
            report += f"| {cid} | {cp.status} | {cp.mastery_level:.0%} | {scores} | {cp.time_spent_hours:.1f}h |\n"

        # Recommendations
        report += "\n## Recommendations\n"
        in_progress = [c for c in progress.concepts.values() if c.status == "in_progress"]
        if in_progress:
            report += f"- Continue working on: {', '.join(c.concept_id for c in in_progress)}\n"

        struggling = [
            c for c in progress.concepts.values()
            if c.quiz_scores and c.quiz_scores[-1] < 0.5
        ]
        if struggling:
            report += f"- Consider reviewing: {', '.join(c.concept_id for c in struggling)}\n"

        # Save report
        report_path = f"user/weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
        self.store.save_json(report_path, {"content": report})

        return report

    def sync_with_graph(
        self,
        progress: LearnerProgress,
        graph: KnowledgeGraph,
    ) -> None:
        """Sync progress back to the knowledge graph."""
        for node in graph.nodes:
            cp = progress.concepts.get(node.id)
            if cp:
                node.mastery = cp.mastery_level
                if cp.status == "completed":
                    node.status = ConceptStatus.COMPLETED
                elif cp.status == "in_progress":
                    node.status = ConceptStatus.IN_PROGRESS

        self.store.save_knowledge_graph(graph.field, graph)
