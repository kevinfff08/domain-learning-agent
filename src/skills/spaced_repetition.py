"""Skill 9: Spaced Repetition Manager - SM-2 algorithm + Anki export."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from src.llm.client import LLMClient
from src.models.cards import CardDeck, CardType, FlashCard, SM2State
from src.models.content import ResearchSynthesis
from src.storage.local_store import LocalStore

SYSTEM_PROMPT = """You are creating spaced repetition flashcards for a PhD student.
Cards should test key concepts, equations, and algorithmic steps.
Make cards atomic - each card tests exactly one piece of knowledge.
Return valid JSON only."""

CARD_GENERATION_PROMPT = """Create flashcards for the concept: "{concept_name}"

Key insight: {key_insight}
Key equations: {equations}
Algorithm steps: {algorithm_steps}
Common pitfalls: {pitfalls}

Generate 8-12 flashcards covering:
- Key definitions and concepts (Basic type)
- Important equations with blanked-out parts (Cloze type)
- Step-by-step derivation questions (Derivation type)
- Code-related knowledge (Code_snippet type)

Return JSON:
[
  {{
    "card_type": "basic|cloze|derivation|code_snippet",
    "front": "Question or prompt (for cloze: use {{{{c1::answer}}}} syntax)",
    "back": "Answer or explanation",
    "tags": ["tag1", "tag2"]
  }}
]

Rules:
- Each card should be self-contained
- For cloze cards, the blanked content should be the key term/formula
- For derivation cards, the front is the starting point, back is the next step
- Keep cards concise - no card should have more than 3 sentences on either side
"""


class SpacedRepetitionManager:
    """SM-2 spaced repetition with Anki export."""

    def __init__(self, llm: LLMClient, store: LocalStore):
        self.llm = llm
        self.store = store

    def generate_cards(self, synthesis: ResearchSynthesis) -> list[FlashCard]:
        """Generate flashcards from a research synthesis."""
        equations_text = "\n".join(
            f"- {eq.name}: {eq.latex[:80]}" for eq in synthesis.mechanism.key_equations[:5]
        )
        steps_text = "\n".join(synthesis.mechanism.algorithm_steps[:5])
        pitfalls_text = "\n".join(synthesis.practice.common_pitfalls[:3])

        prompt = CARD_GENERATION_PROMPT.format(
            concept_name=synthesis.title,
            key_insight=synthesis.intuition.key_insight,
            equations=equations_text or "None",
            algorithm_steps=steps_text or "None",
            pitfalls=pitfalls_text or "None",
        )

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)

        try:
            cards_data = json.loads(response)
        except json.JSONDecodeError:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                cards_data = json.loads(response[start:end])
            else:
                cards_data = []

        cards = []
        for i, c in enumerate(cards_data):
            card = FlashCard(
                id=f"{synthesis.concept_id}_card_{i + 1}",
                concept_id=synthesis.concept_id,
                card_type=CardType(c.get("card_type", "basic")),
                front=c.get("front", ""),
                back=c.get("back", ""),
                tags=c.get("tags", [synthesis.concept_id]),
            )
            cards.append(card)

        # Save cards
        deck = CardDeck(
            name=synthesis.title,
            description=f"Flashcards for {synthesis.title}",
            cards=cards,
        )
        self.store.save_content(synthesis.concept_id, "cards.json", deck)

        return cards

    def review_card(self, card: FlashCard, quality: int) -> FlashCard:
        """Process a card review with SM-2 algorithm.

        quality: 0-5 (0-2 = wrong, 3 = hard, 4 = good, 5 = easy)
        """
        card.sm2.update(quality)
        return card

    def get_due_cards(self, concept_id: str | None = None) -> list[FlashCard]:
        """Get all cards due for review."""
        if concept_id:
            deck = self.store.load_content(concept_id, "cards.json", CardDeck)
            if deck:
                return deck.due_cards
            return []

        # Search all concept directories for cards
        all_due = []
        content_dir = self.store.data_dir / "content"
        if content_dir.exists():
            for concept_dir in content_dir.iterdir():
                if concept_dir.is_dir():
                    deck = self.store.load_content(concept_dir.name, "cards.json", CardDeck)
                    if deck:
                        all_due.extend(deck.due_cards)
        return all_due

    def export_anki(self, field_name: str, output_dir: Path | str = "output") -> Path:
        """Export all cards as an Anki .apkg file."""
        import genanki

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create Anki model
        model_id = abs(hash(field_name)) % (10**9)
        model = genanki.Model(
            model_id,
            f"NewLearner - {field_name}",
            fields=[
                {"name": "Front"},
                {"name": "Back"},
                {"name": "Tags"},
            ],
            templates=[{
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
            }],
        )

        # Create deck
        deck_id = abs(hash(f"newlearner_{field_name}")) % (10**9)
        deck = genanki.Deck(deck_id, f"NewLearner: {field_name}")

        # Collect all cards
        content_dir = self.store.data_dir / "content"
        if content_dir.exists():
            for concept_dir in content_dir.iterdir():
                if concept_dir.is_dir():
                    card_deck = self.store.load_content(concept_dir.name, "cards.json", CardDeck)
                    if card_deck:
                        for card in card_deck.cards:
                            note = genanki.Note(
                                model=model,
                                fields=[card.front, card.back, " ".join(card.tags)],
                                tags=card.tags,
                            )
                            deck.add_note(note)

        # Write .apkg file
        apkg_path = output_path / f"{field_name.replace(' ', '_').lower()}_cards.apkg"
        genanki.Package(deck).write_to_file(str(apkg_path))

        return apkg_path
