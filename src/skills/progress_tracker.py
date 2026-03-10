"""Skill 11: Progress Tracker - Learning metrics and visualization."""

from __future__ import annotations

from datetime import datetime, timedelta

from src.models.bkt import BKTState
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
        # Initialize BKT state if not present
        if cp.bkt_state is None:
            cp.bkt_state = BKTState(concept_id=concept_id)
        self._update_streak(progress)
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

        # Weighted mastery update (replaces naive max())
        cp.mastery_level = 0.7 * quiz_result.overall_score + 0.3 * cp.mastery_level
        cp.last_accessed = datetime.now()

        # Update BKT state
        if cp.bkt_state is None:
            cp.bkt_state = BKTState(concept_id=quiz_result.concept_id)
        for r in quiz_result.results:
            cp.bkt_state.update(r.is_correct)

        if quiz_result.passed:
            cp.status = "completed"
            cp.completed_at = datetime.now()

        self._update_streak(progress)
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

    @staticmethod
    def apply_decay(progress: LearnerProgress) -> None:
        """Apply FSRS-style retrievability decay to mastery levels."""
        now = datetime.now()
        for cp in progress.concepts.values():
            if cp.last_accessed and cp.mastery_level > 0:
                days_since = (now - cp.last_accessed).total_seconds() / 86400
                if days_since > 0:
                    # FSRS retrievability: R = (1 + t/(9*S))^(-1)
                    stability = 30.0  # default stability in days
                    retrievability = (1 + days_since / (9 * stability)) ** (-1)
                    cp.mastery_level = cp.mastery_level * retrievability

    def _update_streak(self, progress: LearnerProgress) -> None:
        """Update consecutive learning days streak."""
        today = datetime.now().date()
        if progress.last_active:
            last_date = progress.last_active.date()
            if last_date == today:
                pass  # already counted today
            elif last_date == today - timedelta(days=1):
                progress.streak_days += 1
            else:
                progress.streak_days = 1
        else:
            progress.streak_days = 1
        progress.last_active = datetime.now()

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
