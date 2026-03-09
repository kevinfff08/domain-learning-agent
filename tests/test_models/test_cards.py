"""Tests for flashcard and SM-2 models."""

import pytest
from datetime import datetime, timedelta
from src.models.cards import CardDeck, CardType, FlashCard, SM2State


class TestSM2State:
    def test_default_state(self):
        sm2 = SM2State()
        assert sm2.interval == 1.0
        assert sm2.repetition == 0
        assert sm2.easiness == 2.5

    def test_correct_answer_quality_5(self):
        sm2 = SM2State()
        sm2.update(5)  # Perfect recall
        assert sm2.repetition == 1
        assert sm2.interval == 1.0  # First correct: 1 day
        assert sm2.easiness > 2.5  # Easiness increases

    def test_correct_answer_sequence(self):
        sm2 = SM2State()
        sm2.update(4)  # Correct
        assert sm2.repetition == 1
        assert sm2.interval == 1.0

        sm2.update(4)  # Correct again
        assert sm2.repetition == 2
        assert sm2.interval == 6.0  # Second correct: 6 days

        sm2.update(4)  # Third correct
        assert sm2.repetition == 3
        assert sm2.interval > 6.0  # Interval grows

    def test_incorrect_answer_resets(self):
        sm2 = SM2State()
        sm2.update(4)
        sm2.update(4)
        assert sm2.repetition == 2

        sm2.update(1)  # Incorrect
        assert sm2.repetition == 0
        assert sm2.interval == 1.0

    def test_easiness_decreases_on_hard(self):
        sm2 = SM2State()
        initial_easiness = sm2.easiness
        sm2.update(3)  # Correct but hard
        assert sm2.easiness < initial_easiness

    def test_easiness_minimum(self):
        sm2 = SM2State()
        for _ in range(20):
            sm2.update(3)  # Repeatedly hard
        assert sm2.easiness >= 1.3

    def test_interval_capped_at_365(self):
        sm2 = SM2State()
        for _ in range(50):
            sm2.update(5)  # Perfect recalls
        assert sm2.interval <= 365.0

    def test_next_review_set(self):
        sm2 = SM2State()
        before = datetime.now()
        sm2.update(4)
        assert sm2.next_review >= before
        assert sm2.last_reviewed is not None


class TestFlashCard:
    def test_creation(self):
        card = FlashCard(
            id="card_1",
            concept_id="ddpm",
            card_type=CardType.BASIC,
            front="What is the forward process?",
            back="Gradually adding Gaussian noise.",
        )
        assert card.id == "card_1"
        assert card.card_type == CardType.BASIC

    def test_is_due_new_card(self):
        card = FlashCard(
            id="card_1", concept_id="test", card_type=CardType.BASIC,
            front="Q", back="A",
        )
        assert card.is_due is True

    def test_is_due_after_review(self):
        card = FlashCard(
            id="card_1", concept_id="test", card_type=CardType.BASIC,
            front="Q", back="A",
        )
        card.sm2.update(5)  # Review correctly
        # Next review should be in the future
        assert card.is_due is False


class TestCardDeck:
    def test_due_cards(self):
        deck = CardDeck(name="Test Deck", cards=[
            FlashCard(id="c1", concept_id="t", card_type=CardType.BASIC, front="Q1", back="A1"),
            FlashCard(id="c2", concept_id="t", card_type=CardType.BASIC, front="Q2", back="A2"),
        ])
        # New cards should all be due
        assert len(deck.due_cards) == 2
        assert deck.total_cards == 2

        # Review one
        deck.cards[0].sm2.update(5)
        assert len(deck.due_cards) == 1
