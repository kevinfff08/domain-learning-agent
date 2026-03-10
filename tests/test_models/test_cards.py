"""Tests for flashcard and FSRS models."""

import pytest
from datetime import datetime, timedelta, timezone
from src.models.cards import CardDeck, CardType, FlashCard, FSRSState, SM2State


class TestFSRSState:
    def test_default_state(self):
        state = FSRSState()
        assert state.state == 1  # Learning
        assert state.stability is None
        assert state.difficulty is None

    def test_due_is_timezone_aware(self):
        state = FSRSState()
        assert state.due.tzinfo is not None


class TestSM2StateBackwardCompat:
    def test_sm2_still_loads(self):
        """SM2State class exists for backward compatibility."""
        sm2 = SM2State()
        assert sm2.interval == 1.0
        assert sm2.easiness == 2.5


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
        assert card.fsrs_state is not None

    def test_is_due_new_card(self):
        card = FlashCard(
            id="card_1", concept_id="test", card_type=CardType.BASIC,
            front="Q", back="A",
        )
        assert card.is_due is True

    def test_is_due_future(self):
        future = datetime.now(timezone.utc) + timedelta(days=7)
        card = FlashCard(
            id="card_1", concept_id="test", card_type=CardType.BASIC,
            front="Q", back="A",
            fsrs_state=FSRSState(due=future),
        )
        assert card.is_due is False

    def test_sm2_migration(self):
        """Old SM2 data should be migrated to FSRSState."""
        data = {
            "id": "c1",
            "concept_id": "test",
            "card_type": "basic",
            "front": "Q",
            "back": "A",
            "sm2": {"interval": 6.0, "repetition": 2, "easiness": 2.5},
        }
        card = FlashCard.model_validate(data)
        assert card.fsrs_state is not None
        assert not hasattr(card, "sm2") or "sm2" not in card.model_fields

    def test_fsrs_state_preserved(self):
        """Explicit FSRSState should not be overwritten."""
        future = datetime.now(timezone.utc) + timedelta(days=3)
        card = FlashCard(
            id="c1", concept_id="test", card_type=CardType.BASIC,
            front="Q", back="A",
            fsrs_state=FSRSState(stability=5.0, difficulty=3.0, due=future),
        )
        assert card.fsrs_state.stability == 5.0
        assert card.fsrs_state.difficulty == 3.0


class TestCardDeck:
    def test_due_cards(self):
        deck = CardDeck(name="Test Deck", cards=[
            FlashCard(id="c1", concept_id="t", card_type=CardType.BASIC, front="Q1", back="A1"),
            FlashCard(id="c2", concept_id="t", card_type=CardType.BASIC, front="Q2", back="A2"),
        ])
        # New cards should all be due
        assert len(deck.due_cards) == 2
        assert deck.total_cards == 2

    def test_future_card_not_due(self):
        future = datetime.now(timezone.utc) + timedelta(days=7)
        deck = CardDeck(name="Test Deck", cards=[
            FlashCard(id="c1", concept_id="t", card_type=CardType.BASIC, front="Q1", back="A1"),
            FlashCard(id="c2", concept_id="t", card_type=CardType.BASIC, front="Q2", back="A2",
                      fsrs_state=FSRSState(due=future)),
        ])
        assert len(deck.due_cards) == 1
