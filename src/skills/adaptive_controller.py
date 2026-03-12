"""Skill 8: Adaptive Controller - 4-level learning adaptation."""

from __future__ import annotations

from src.llm.client import LLMClient
from src.utils.json_repair import repair_json, repair_json_array
from src.models.bkt import BKTState
from src.models.content import ResearchSynthesis
from src.models.textbook import Chapter, Textbook
from src.models.quiz import QuizResult
from src.skills.deep_researcher import DeepResearcher
from src.storage.local_store import LocalStore


class AdaptiveLevel:
    """Constants for adaptive intervention levels."""

    NORMAL = 0
    ALTERNATIVE_EXPLANATION = 1
    PREREQUISITE_REVIEW = 2
    SOCRATIC_DIALOGUE = 3


class AdaptiveController:
    """Adaptive learning controller.

    Level 0: Normal flow
    Level 1: Alternative explanation (score 40-85%)
    Level 2: Prerequisite review hint (score < 40%)
    Level 3: Socratic dialogue (persistent struggle)
    """

    def __init__(
        self,
        llm: LLMClient,
        store: LocalStore,
        deep_researcher: DeepResearcher,
    ):
        self.llm = llm
        self.store = store
        self.researcher = deep_researcher

    def determine_level(
        self,
        quiz_result: QuizResult,
        chapter: Chapter,
        bkt_state: BKTState | None = None,
    ) -> int:
        """Determine the appropriate adaptive intervention level."""
        mastery = bkt_state.p_mastery if bkt_state else quiz_result.overall_score

        if mastery >= 0.85:
            return AdaptiveLevel.NORMAL

        if mastery < 0.3:
            return AdaptiveLevel.PREREQUISITE_REVIEW

        return AdaptiveLevel.ALTERNATIVE_EXPLANATION

    def intervene(
        self,
        level: int,
        chapter: Chapter,
        textbook: Textbook,
        quiz_result: QuizResult,
        synthesis: ResearchSynthesis,
        profile=None,
    ) -> dict:
        """Execute the appropriate intervention based on level."""
        if level == AdaptiveLevel.ALTERNATIVE_EXPLANATION:
            return self._level1_alternative(chapter, synthesis, quiz_result)
        elif level == AdaptiveLevel.PREREQUISITE_REVIEW:
            return self._level2_review_hint(chapter, textbook, quiz_result)
        elif level == AdaptiveLevel.SOCRATIC_DIALOGUE:
            return self._level4_socratic(chapter, synthesis, quiz_result)
        else:
            return {"action": "continue", "message": "Quiz passed, proceed to next chapter"}

    def _level1_alternative(
        self,
        chapter: Chapter,
        synthesis: ResearchSynthesis,
        quiz_result: QuizResult,
    ) -> dict:
        """Level 1: Generate alternative explanation."""
        struggle_areas = [r.feedback for r in quiz_result.results if not r.is_correct]

        alt_synthesis = self.researcher.generate_alternative_explanation(
            chapter, synthesis, struggle_areas
        )

        return {
            "action": "alternative_explanation",
            "message": f"Generating alternative explanation for '{chapter.title}'",
            "alternative_synthesis": alt_synthesis,
            "next_step": "Re-take quiz after reviewing alternative explanation",
        }

    def _level2_review_hint(
        self,
        chapter: Chapter,
        textbook: Textbook,
        quiz_result: QuizResult,
    ) -> dict:
        """Level 2: Suggest reviewing earlier chapters."""
        # Find earlier chapters that might help
        earlier = [
            ch for ch in textbook.chapters
            if ch.chapter_number < chapter.chapter_number
        ]
        review_suggestions = [ch.title for ch in earlier[-3:]] if earlier else []

        return {
            "action": "prerequisite_review",
            "message": f"Score too low on '{chapter.title}'. Consider reviewing earlier chapters.",
            "review_chapters": review_suggestions,
            "next_step": "Review suggested chapters, then retry this chapter",
        }

    def _level4_socratic(
        self,
        chapter: Chapter,
        synthesis: ResearchSynthesis,
        quiz_result: QuizResult,
    ) -> dict:
        """Level 3/4: Generate Socratic dialogue questions."""
        prompt = f"""Create a Socratic dialogue to help a student understand "{chapter.title}".

Key concept insight: {synthesis.intuition.key_insight}
Areas of confusion (from quiz results):
{chr(10).join(f"- {r.feedback}" for r in quiz_result.results if not r.is_correct)}

Generate 5-7 guiding questions that lead the student step-by-step to understanding.

Return JSON:
[
  {{
    "question": "What do you think would happen if...",
    "expected_insight": "The student should realize that...",
    "hint": "Think about..."
  }}
]"""

        try:
            response = self.llm.generate_json(prompt)
            dialogue = repair_json_array(response)
        except (ValueError, Exception):
            dialogue = [{"question": "Let's start from the basics. What do you already know about this topic?"}]

        return {
            "action": "socratic_dialogue",
            "message": f"Starting Socratic dialogue for '{chapter.title}'",
            "dialogue_questions": dialogue,
            "current_step": 0,
            "next_step": "answer_first_question",
        }

    def advance_socratic(
        self,
        chapter_id: str,
        student_answer: str,
        current_step: int,
        dialogue: list[dict],
    ) -> dict:
        """Advance Socratic dialogue by evaluating student's answer."""
        if current_step >= len(dialogue):
            return {"action": "complete", "summary": "All dialogue questions completed."}

        current_q = dialogue[current_step]
        prompt = f"""Evaluate this student's answer in a Socratic dialogue.

Question: {current_q.get('question', '')}
Expected insight: {current_q.get('expected_insight', '')}
Student's answer: {student_answer}

Return JSON:
{{
  "understood": true/false,
  "feedback": "Brief feedback on their answer",
  "follow_up": "Optional follow-up question or encouragement"
}}"""

        try:
            response = self.llm.generate_json(prompt)
            result = repair_json(response)
        except (ValueError, Exception):
            result = {"understood": True, "feedback": "Good attempt. Let's continue."}

        if result.get("understood", False):
            next_step = current_step + 1
            if next_step >= len(dialogue):
                return {
                    "action": "complete",
                    "step": next_step,
                    "feedback": result.get("feedback", ""),
                    "summary": "Socratic dialogue completed successfully.",
                }
            return {
                "action": "next_question",
                "step": next_step,
                "feedback": result.get("feedback", ""),
                "next_question": dialogue[next_step],
            }
        else:
            hint = current_q.get("hint", "Think about it from a different angle.")
            return {
                "action": "hint",
                "step": current_step,
                "feedback": result.get("feedback", ""),
                "hint": hint,
            }
