"""Data models for spaced repetition flashcards."""

from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CardType(str, Enum):
    """Type of flashcard."""

    BASIC = "basic"
    CLOZE = "cloze"
    DERIVATION = "derivation"
    CODE_SNIPPET = "code_snippet"


class SM2State(BaseModel):
    """SuperMemo SM-2 algorithm state (deprecated, kept for backward compatibility)."""

    interval: float = Field(default=1.0, description="Days until next review")
    repetition: int = Field(default=0, description="Number of consecutive correct reviews")
    easiness: float = Field(default=2.5, ge=1.3, description="Easiness factor")
    next_review: datetime = Field(default_factory=datetime.now)
    last_reviewed: datetime | None = None


class FSRSState(BaseModel):
    """FSRS-6 algorithm state for a single card."""

    card_id: int = Field(default=0)
    state: int = Field(default=1, description="1=Learning, 2=Review, 3=Relearning")
    step: int | None = Field(default=0)
    stability: float | None = Field(default=None)
    difficulty: float | None = Field(default=None)
    due: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_review: datetime | None = None


class FlashCard(BaseModel):
    """A single flashcard."""

    id: str
    concept_id: str
    card_type: CardType
    front: str = Field(description="Question / prompt side")
    back: str = Field(description="Answer side")
    tags: list[str] = Field(default_factory=list)
    fsrs_state: FSRSState = Field(default_factory=FSRSState)
    created_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="before")
    @classmethod
    def migrate_sm2_to_fsrs(cls, data: Any) -> Any:
        """Backward compatibility: migrate old SM2 data to FSRS."""
        if isinstance(data, dict) and "sm2" in data and "fsrs_state" not in data:
            data["fsrs_state"] = FSRSState().model_dump()
            data.pop("sm2", None)
        return data

    @property
    def is_due(self) -> bool:
        """Whether this card is due for review."""
        now = datetime.now(timezone.utc)
        due = self.fsrs_state.due
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        return now >= due


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
