"""Tests for Adaptive Controller skill."""

import pytest
from unittest.mock import MagicMock

from src.models.content import IntuitionLayer, MechanismLayer, ResearchSynthesis
from src.models.knowledge_graph import ConceptNode, KnowledgeGraph
from src.models.quiz import QuestionResult, QuizResult
from src.skills.adaptive_controller import AdaptiveController, AdaptiveLevel


@pytest.fixture
def controller():
    llm = MagicMock()
    store = MagicMock()
    researcher = MagicMock()
    mapper = MagicMock()
    return AdaptiveController(llm, store, researcher, mapper)


@pytest.fixture
def sample_concept():
    return ConceptNode(id="ddpm", name="DDPM", difficulty=4)


class TestAdaptiveLevel:
    def test_normal_on_pass(self, controller, sample_concept):
        result = QuizResult(quiz_id="q", concept_id="ddpm", overall_score=0.8, results=[])
        level = controller.determine_level(result, sample_concept)
        assert level == AdaptiveLevel.NORMAL

    def test_level1_on_moderate_fail(self, controller, sample_concept):
        result = QuizResult(quiz_id="q", concept_id="ddpm", overall_score=0.55, results=[])
        level = controller.determine_level(result, sample_concept)
        assert level == AdaptiveLevel.ALTERNATIVE_EXPLANATION

    def test_level2_on_bad_fail(self, controller, sample_concept):
        result = QuizResult(quiz_id="q", concept_id="ddpm", overall_score=0.3, results=[])
        level = controller.determine_level(result, sample_concept)
        assert level == AdaptiveLevel.PREREQUISITE_REVIEW

    def test_level3_escalation(self, controller, sample_concept):
        sample_concept.adaptive_level = AdaptiveLevel.PREREQUISITE_REVIEW
        result = QuizResult(quiz_id="q", concept_id="ddpm", overall_score=0.5, results=[])
        level = controller.determine_level(result, sample_concept)
        assert level == AdaptiveLevel.CONCEPT_SPLIT

    def test_level4_escalation(self, controller, sample_concept):
        sample_concept.adaptive_level = AdaptiveLevel.CONCEPT_SPLIT
        result = QuizResult(quiz_id="q", concept_id="ddpm", overall_score=0.3, results=[])
        level = controller.determine_level(result, sample_concept)
        assert level == AdaptiveLevel.SOCRATIC_DIALOGUE

    def test_level1_intervention_calls_researcher(self, controller, sample_concept):
        synthesis = ResearchSynthesis(
            concept_id="ddpm", title="DDPM",
            intuition=IntuitionLayer(analogy="test analogy", key_insight="test insight"),
        )
        result = QuizResult(
            quiz_id="q", concept_id="ddpm", overall_score=0.5,
            results=[QuestionResult(question_id="q1", user_answer="0", is_correct=False, score=0.0, feedback="Wrong")],
        )
        response = controller.intervene(
            AdaptiveLevel.ALTERNATIVE_EXPLANATION,
            sample_concept, KnowledgeGraph(field="Test"), result, synthesis,
        )
        assert response["action"] == "alternative_explanation"
        controller.researcher.generate_alternative_explanation.assert_called_once()
