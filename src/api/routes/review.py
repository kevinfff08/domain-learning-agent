"""Spaced repetition review API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from src.api.deps import get_orchestrator
from src.models.cards import CardDeck
from src.orchestrator import LearningOrchestrator

router = APIRouter()


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
    quality: int,
    concept_id: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Submit a review rating for a flashcard.

    quality: 0-5 (0-2 = wrong, 3 = hard, 4 = good, 5 = easy)
    """
    deck = orch.store.load_content(concept_id, "cards.json", CardDeck)
    if not deck:
        return {"error": f"No cards found for concept '{concept_id}'."}

    card = next((c for c in deck.cards if c.id == card_id), None)
    if not card:
        return {"error": f"Card '{card_id}' not found."}

    card = orch.spaced_rep.review_card(card, quality)

    # Save updated deck
    orch.store.save_content(concept_id, "cards.json", deck)

    return {
        "card_id": card.id,
        "next_review": str(card.sm2.next_review),
        "interval_days": card.sm2.interval,
        "easiness": card.sm2.easiness,
        "repetition": card.sm2.repetition,
    }


@router.post("/review/export/anki")
def export_anki(
    field: str,
    orch: LearningOrchestrator = Depends(get_orchestrator),
):
    """Export all flashcards as Anki .apkg file."""
    path = orch.spaced_rep.export_anki(field)
    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/octet-stream",
    )
