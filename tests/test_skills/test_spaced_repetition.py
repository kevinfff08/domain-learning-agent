"""Tests for Spaced Repetition Manager skill."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.models.cards import CardDeck, CardType, FlashCard, FSRSState
from src.models.content import IntuitionLayer, MechanismLayer, PracticeLayer, ResearchSynthesis, Equation
from src.skills.spaced_repetition import SpacedRepetitionManager
from src.storage.local_store import LocalStore


@pytest.fixture
def manager():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStore(tmp)
        llm = MagicMock()
        llm.generate_json.return_value = '[{"card_type": "basic", "front": "Q1", "back": "A1", "tags": ["test"]}]'
        yield SpacedRepetitionManager(llm, store), store


class TestSpacedRepetitionManager:
    def test_generate_cards(self, manager):
        mgr, store = manager
        synthesis = ResearchSynthesis(
            concept_id="ddpm",
            title="DDPM",
            intuition=IntuitionLayer(key_insight="Reverse denoising"),
            mechanism=MechanismLayer(
                key_equations=[Equation(name="Forward", latex="q(x_t|x_{t-1})=...")],
                algorithm_steps=["Step 1", "Step 2"],
            ),
            practice=PracticeLayer(common_pitfalls=["Pitfall 1"]),
        )
        cards = mgr.generate_cards(synthesis)
        assert len(cards) >= 1
        assert cards[0].concept_id == "ddpm"

    def test_review_card_fsrs(self, manager):
        mgr, store = manager
        # Create a deck with the card first (for persistence)
        card = FlashCard(
            id="c1", concept_id="test", card_type=CardType.BASIC,
            front="Q", back="A",
        )
        deck = CardDeck(name="Test", cards=[card])
        store.save_content("test", "cards.json", deck)

        # Review
        assert card.fsrs_state.state == 1  # Learning
        card = mgr.review_card(card, 4)  # Good
        # FSRS should update the state
        assert card.fsrs_state.last_review is not None

    def test_review_card_persists(self, manager):
        """#5: Verify that review_card persists the updated deck."""
        mgr, store = manager
        card = FlashCard(
            id="c1", concept_id="test", card_type=CardType.BASIC,
            front="Q", back="A",
        )
        deck = CardDeck(name="Test", cards=[card])
        store.save_content("test", "cards.json", deck)

        mgr.review_card(card, 5)

        # Reload from store and verify persistence
        reloaded = store.load_content("test", "cards.json", CardDeck)
        assert reloaded is not None
        assert reloaded.cards[0].fsrs_state.last_review is not None

    def test_get_due_cards_empty(self, manager):
        mgr, _ = manager
        due = mgr.get_due_cards("nonexistent")
        assert due == []

    def test_get_due_cards_with_data(self, manager):
        mgr, store = manager
        deck = CardDeck(name="Test", cards=[
            FlashCard(id="c1", concept_id="test", card_type=CardType.BASIC, front="Q1", back="A1"),
        ])
        store.save_content("test", "cards.json", deck)
        due = mgr.get_due_cards("test")
        assert len(due) == 1

    def test_export_anki(self, manager):
        mgr, store = manager
        # Create some cards
        deck = CardDeck(name="Test", cards=[
            FlashCard(id="c1", concept_id="test", card_type=CardType.BASIC, front="Q1", back="A1"),
            FlashCard(id="c2", concept_id="test", card_type=CardType.CLOZE, front="Q2", back="A2"),
        ])
        store.save_content("test", "cards.json", deck)

        with tempfile.TemporaryDirectory() as out:
            path = mgr.export_anki("Test Field", output_dir=out)
            assert path.exists()
            assert path.suffix == ".apkg"
