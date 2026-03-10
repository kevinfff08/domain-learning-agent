"""Spaced repetition review API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.deps import get_orchestrator
from src.models.cards import CardDeck
from src.orchestrator import LearningOrchestrator

router = APIRouter()


class ReviewRequest(BaseModel):
    """Review submission body."""
    rating: int
    concept_id: str


class AnkiExportRequest(BaseModel):
    """Anki export body."""
    field: str


@router.get("/review/due")
def get_due_cards(
    concept_id: str | None = None,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Get all flashcards due for review."""
    due = orch.spaced_rep.get_due_cards(concept_id)
    return {
        "count": len(due),
        "cards": [json.loads(card.model_dump_json()) for card in due],
    }


@router.post("/review/{card_id}")
def review_card(
    card_id: str,
    req: ReviewRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Submit a review rating for a flashcard.

    rating: 0-5 (0-2 = wrong, 3 = hard, 4 = good, 5 = easy)
    """
    deck = orch.store.load_content(req.concept_id, "cards.json", CardDeck)
    if not deck:
        return {"error": f"No cards found for concept '{req.concept_id}'."}

    card = next((c for c in deck.cards if c.id == card_id), None)
    if not card:
        return {"error": f"Card '{card_id}' not found."}

    card = orch.spaced_rep.review_card(card, req.rating)

    # review_card already persists the deck internally

    return {
        "card_id": card.id,
        "next_review": str(card.fsrs_state.due),
        "stability": card.fsrs_state.stability,
        "difficulty": card.fsrs_state.difficulty,
        "state": card.fsrs_state.state,
    }


@router.post("/review/export/anki")
def export_anki(
    req: AnkiExportRequest,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Export all flashcards as Anki .apkg file."""
    path = orch.spaced_rep.export_anki(req.field)
    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/octet-stream",
    )
