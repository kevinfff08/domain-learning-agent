"""Skill 8: Adaptive Controller - 4-level learning adaptation."""

from __future__ import annotations

import json

from src.llm.client import LLMClient
from src.models.content import ResearchSynthesis
from src.models.knowledge_graph import ConceptNode, ConceptStatus, KnowledgeGraph
from src.models.quiz import QuizResult
from src.skills.deep_researcher import DeepResearcher
from src.skills.domain_mapper import DomainMapper
from src.storage.local_store import LocalStore


class AdaptiveLevel:
    """Constants for adaptive intervention levels."""

    NORMAL = 0
    ALTERNATIVE_EXPLANATION = 1
    PREREQUISITE_REVIEW = 2
    CONCEPT_SPLIT = 3
    SOCRATIC_DIALOGUE = 4


class AdaptiveController:
    """4-level adaptive learning controller.

    Level 0: Normal flow
    Level 1: Alternative explanation (score 40-60%)
    Level 2: Prerequisite gap filling (score < 40%)
    Level 3: Concept splitting (specific blocker identified)
    Level 4: Socratic dialogue (persistent struggle)
    """

    def __init__(
        self,
        llm: LLMClient,
        store: LocalStore,
        deep_researcher: DeepResearcher,
        domain_mapper: DomainMapper,
    ):
        self.llm = llm
        self.store = store
        self.researcher = deep_researcher
        self.mapper = domain_mapper

    def determine_level(
        self,
        quiz_result: QuizResult,
        concept: ConceptNode,
    ) -> int:
        """Determine the appropriate adaptive intervention level."""
        score = quiz_result.overall_score

        if score >= 0.7:
            return AdaptiveLevel.NORMAL

        if concept.adaptive_level >= AdaptiveLevel.CONCEPT_SPLIT:
            return AdaptiveLevel.SOCRATIC_DIALOGUE

        if concept.adaptive_level >= AdaptiveLevel.ALTERNATIVE_EXPLANATION and score < 0.4:
            return AdaptiveLevel.PREREQUISITE_REVIEW

        if concept.adaptive_level >= AdaptiveLevel.PREREQUISITE_REVIEW:
            return AdaptiveLevel.CONCEPT_SPLIT

        if score < 0.4:
            return AdaptiveLevel.PREREQUISITE_REVIEW

        return AdaptiveLevel.ALTERNATIVE_EXPLANATION

    def intervene(
        self,
        level: int,
        concept: ConceptNode,
        graph: KnowledgeGraph,
        quiz_result: QuizResult,
        synthesis: ResearchSynthesis,
        profile=None,
    ) -> dict:
        """Execute the appropriate intervention based on level.

        Returns a dict describing the action taken and next steps.
        """
        concept.adaptive_level = level

        if level == AdaptiveLevel.ALTERNATIVE_EXPLANATION:
            return self._level1_alternative(concept, synthesis, quiz_result)
        elif level == AdaptiveLevel.PREREQUISITE_REVIEW:
            return self._level2_prerequisites(concept, graph, quiz_result)
        elif level == AdaptiveLevel.CONCEPT_SPLIT:
            return self._level3_split(concept, graph)
        elif level == AdaptiveLevel.SOCRATIC_DIALOGUE:
            return self._level4_socratic(concept, synthesis, quiz_result)
        else:
            return {"action": "continue", "message": "Quiz passed, proceed to next concept"}

    def _level1_alternative(
        self,
        concept: ConceptNode,
        synthesis: ResearchSynthesis,
        quiz_result: QuizResult,
    ) -> dict:
        """Level 1: Generate alternative explanation."""
        # Identify struggle areas from wrong answers
        struggle_areas = []
        for r in quiz_result.results:
            if not r.is_correct:
                struggle_areas.append(r.feedback)

        alt_synthesis = self.researcher.generate_alternative_explanation(
            concept, synthesis, struggle_areas
        )

        return {
            "action": "alternative_explanation",
            "message": f"Generating alternative explanation for '{concept.name}'",
            "alternative_synthesis": alt_synthesis,
            "next_step": "Re-take quiz after reviewing alternative explanation",
        }

    def _level2_prerequisites(
        self,
        concept: ConceptNode,
        graph: KnowledgeGraph,
        quiz_result: QuizResult,
    ) -> dict:
        """Level 2: Identify and fill prerequisite gaps."""
        # Analyze wrong answers to identify prerequisite gaps
        prompt = f"""A student scored {quiz_result.overall_score:.0%} on a quiz about "{concept.name}".

Wrong answers:
{chr(10).join(f"- {r.feedback}" for r in quiz_result.results if not r.is_correct)}

The concept has these math requirements: {concept.math_requirements}

Identify 1-3 prerequisite concepts that the student likely needs to review.
Return JSON:
[
  {{
    "id": "prereq_id_snake_case",
    "name": "Prerequisite Name",
    "description": "Why this prerequisite is needed",
    "difficulty": 1-3,
    "estimated_hours": 1.0-3.0,
    "tags": ["prerequisite", "math"|"programming"|"domain"]
  }}
]"""

        try:
            response = self.llm.generate_json(prompt)
            prereqs_data = json.loads(response)
        except Exception:
            prereqs_data = [{
                "id": f"prereq_{concept.id}",
                "name": f"Prerequisites for {concept.name}",
                "description": "Review foundational concepts",
                "difficulty": 2,
                "estimated_hours": 2.0,
                "tags": ["prerequisite"],
            }]

        new_nodes = []
        for p in prereqs_data:
            new_node = ConceptNode(
                id=p["id"],
                name=p.get("name", p["id"]),
                description=p.get("description", ""),
                difficulty=p.get("difficulty", 2),
                estimated_hours=p.get("estimated_hours", 2.0),
                tags=p.get("tags", ["prerequisite"]),
            )
            # Only add if not already in graph
            if not graph.get_node(new_node.id):
                self.mapper.add_prerequisite_node(graph, new_node, concept.id)
                new_nodes.append(new_node)

        return {
            "action": "prerequisite_review",
            "message": f"Added {len(new_nodes)} prerequisite nodes before '{concept.name}'",
            "new_prerequisites": [n.id for n in new_nodes],
            "next_step": "Learn the prerequisite concepts first, then return to this concept",
        }

    def _level3_split(
        self,
        concept: ConceptNode,
        graph: KnowledgeGraph,
    ) -> dict:
        """Level 3: Split concept into finer-grained sub-concepts."""
        prompt = f"""The student is persistently struggling with "{concept.name}": {concept.description}

Split this concept into 2-4 smaller, more manageable sub-concepts that can be learned sequentially.
Each sub-concept should build on the previous one.

Return JSON:
[
  {{
    "id": "{concept.id}_part1",
    "name": "Sub-concept name",
    "description": "What this covers",
    "difficulty": 1-5,
    "estimated_hours": 0.5-2.0,
    "math_requirements": [],
    "tags": ["sub_concept"]
  }}
]"""

        try:
            response = self.llm.generate_json(prompt)
            subs_data = json.loads(response)
        except Exception:
            subs_data = [
                {"id": f"{concept.id}_basics", "name": f"{concept.name} - Basics", "difficulty": concept.difficulty - 1, "estimated_hours": 1.0},
                {"id": f"{concept.id}_details", "name": f"{concept.name} - Details", "difficulty": concept.difficulty, "estimated_hours": 1.5},
            ]

        sub_concepts = [
            ConceptNode(
                id=s["id"],
                name=s.get("name", s["id"]),
                description=s.get("description", ""),
                difficulty=s.get("difficulty", concept.difficulty),
                estimated_hours=s.get("estimated_hours", 1.0),
                math_requirements=s.get("math_requirements", concept.math_requirements),
                tags=s.get("tags", ["sub_concept"]),
            )
            for s in subs_data
        ]

        self.mapper.split_concept(graph, concept.id, sub_concepts)

        return {
            "action": "concept_split",
            "message": f"Split '{concept.name}' into {len(sub_concepts)} sub-concepts",
            "sub_concepts": [s.id for s in sub_concepts],
            "next_step": "Learn the sub-concepts in order",
        }

    def _level4_socratic(
        self,
        concept: ConceptNode,
        synthesis: ResearchSynthesis,
        quiz_result: QuizResult,
    ) -> dict:
        """Level 4: Generate Socratic dialogue questions."""
        prompt = f"""Create a Socratic dialogue to help a student understand "{concept.name}".

The student has tried alternative explanations and prerequisite review but still struggles.

Key concept insight: {synthesis.intuition.key_insight}
Areas of confusion (from quiz results):
{chr(10).join(f"- {r.feedback}" for r in quiz_result.results if not r.is_correct)}

Generate 5-7 guiding questions that lead the student step-by-step to understanding.
Each question should build on the expected answer to the previous one.

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
            dialogue = json.loads(response)
        except Exception:
            dialogue = [{"question": "Let's start from the basics. What do you already know about this topic?"}]

        return {
            "action": "socratic_dialogue",
            "message": f"Starting Socratic dialogue for '{concept.name}'",
            "dialogue_questions": dialogue,
            "next_step": "Work through the guiding questions one at a time",
        }
