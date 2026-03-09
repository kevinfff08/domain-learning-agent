"""Data models for spaced repetition flashcards."""

from __future__ import annotations

from enum import Enum
from datetime import datetime, timedelta

from pydantic import BaseModel, Field


class CardType(str, Enum):
    """Type of flashcard."""

    BASIC = "basic"
    CLOZE = "cloze"
    DERIVATION = "derivation"
    CODE_SNIPPET = "code_snippet"


class SM2State(BaseModel):
    """SuperMemo SM-2 algorithm state for a single card."""

    interval: float = Field(default=1.0, description="Days until next review")
    repetition: int = Field(default=0, description="Number of consecutive correct reviews")
    easiness: float = Field(default=2.5, ge=1.3, description="Easiness factor")
    next_review: datetime = Field(default_factory=datetime.now)
    last_reviewed: datetime | None = None

    def update(self, quality: int) -> None:
        """Update SM-2 state based on review quality (0-5).

        0-2: incorrect, restart
        3: correct with difficulty
        4: correct with some hesitation
        5: perfect recall
        """
        quality = max(0, min(5, quality))

        # Update easiness factor
        self.easiness = max(
            1.3,
            self.easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
        )

        if quality < 3:
            # Reset on failure
            self.repetition = 0
            self.interval = 1.0
        else:
            if self.repetition == 0:
                self.interval = 1.0
            elif self.repetition == 1:
                self.interval = 6.0
            else:
                self.interval = self.interval * self.easiness

            self.repetition += 1

        # Cap interval at 365 days
        self.interval = min(self.interval, 365.0)

        self.last_reviewed = datetime.now()
        self.next_review = datetime.now() + timedelta(days=self.interval)


class FlashCard(BaseModel):
    """A single flashcard."""

    id: str
    concept_id: str
    card_type: CardType
    front: str = Field(description="Question / prompt side")
    back: str = Field(description="Answer side")
    tags: list[str] = Field(default_factory=list)
    sm2: SM2State = Field(default_factory=SM2State)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_due(self) -> bool:
        """Whether this card is due for review."""
        return datetime.now() >= self.sm2.next_review


class CardDeck(BaseModel):
    """A collection of flashcards for a field or concept."""

    name: str
    description: str = ""
    cards: list[FlashCard] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def due_cards(self) -> list[FlashCard]:
        """Get all cards due for review."""
        return [c for c in self.cards if c.is_due]

    @property
    def total_cards(self) -> int:
        return len(self.cards)
