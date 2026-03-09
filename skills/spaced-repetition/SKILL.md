---
name: spaced-repetition
description: |
  SM-2 spaced repetition scheduling with Anki export.
  Trigger: "review cards", "spaced repetition", "create flashcards",
    "export to anki", "review schedule", "newlearner review"
  DO NOT USE: for generating quizzes (use quiz-engine),
    for tracking concept progress (use progress-tracker),
    for generating practice exercises (use practice-generator)
---

# Spaced Repetition

Generates flashcards from research synthesis content, manages review scheduling
using the SM-2 algorithm, and exports card decks to Anki (.apkg format). Cards
cover key definitions, equations, code patterns, and conceptual relationships
at multiple levels of recall difficulty.

## Quick Reference

| Item | Value |
|---|---|
| Layer | 3 - Learning Delivery & Adaptation |
| CLI command | `newlearner review` |
| Python module | `src/skills/spaced_repetition.py` |
| Key class | `SpacedRepetitionManager` |
| Input | `ResearchSynthesis` or manual card definitions |
| Output | `data/user/cards.json` (card database), `output/deck.apkg` (Anki export) |
| Data models | `src/models/cards.py` (card-related types) |
| Dependencies | `genanki` for .apkg export |

## Step-by-Step Instructions

### Generate Cards from Synthesis

1. After Deep Researcher produces a `ResearchSynthesis`, call
   `SpacedRepetitionManager.generate_cards(synthesis)`.
2. LLM generates cards in four types:

   | Card Type | Front | Back |
   |---|---|---|
   | basic | Question about a concept or definition | Answer with explanation |
   | cloze | Sentence with `{{c1::hidden}}` key term | Full sentence revealed |
   | derivation | "Derive X starting from Y" | Step-by-step derivation |
   | code_snippet | "Implement X" or "What does this code do?" | Code with explanation |

3. Cards are tagged with concept_id and difficulty level.
4. Cards added to the card database at `data/user/cards.json`.

### Review Due Cards

1. Call `SpacedRepetitionManager.get_due_cards(limit=20)`.
   - Returns cards whose `next_review` date is today or earlier.
   - Ordered by urgency (most overdue first).
2. Present each card to the learner.
3. After the learner responds, call
   `SpacedRepetitionManager.review_card(card_id, quality)`.
   - `quality`: integer 0-5 (SM-2 scale).
     - 0: complete blackout.
     - 1: wrong, but recognized answer.
     - 2: wrong, but answer seemed easy to recall.
     - 3: correct with serious difficulty.
     - 4: correct after hesitation.
     - 5: perfect recall.
4. SM-2 algorithm updates the card's scheduling parameters.

### SM-2 Algorithm Parameters

| Parameter | Default | Description |
|---|---|---|
| Initial easiness factor | 2.5 | Starting EF for new cards |
| Minimum interval | 1 day | Shortest gap between reviews |
| Maximum interval | 365 days | Longest gap between reviews |
| EF minimum | 1.3 | Floor for easiness factor |

- Interval calculation: `interval = previous_interval * easiness_factor`
- EF adjustment: `EF = EF + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))`
- Quality < 3 resets the interval to 1 day (re-learning).

### Export to Anki

1. Call `SpacedRepetitionManager.export_anki(output_path="output/deck.apkg")`.
   - Uses `genanki` library to create an Anki package.
   - Maps card types to Anki note types (Basic, Cloze).
   - Preserves tags, deck structure (one sub-deck per concept).
   - LaTeX equations rendered in Anki's MathJax format.
2. Import the `.apkg` file into Anki desktop or AnkiWeb.

## Key Implementation Details

- Card database is a JSON file with all cards, their SM-2 state, and
  review history.
- Each card tracks: id, concept_id, card_type, front, back, easiness_factor,
  interval_days, repetitions, next_review, last_review, quality_history.
- `genanki` requires model IDs and deck IDs; these are deterministically
  generated from the field name to allow re-exports without duplication.
- Cloze cards use Anki's `{{c1::...}}` syntax for compatibility.

## Anti-Patterns

- **Do not generate cards for concepts the learner has not studied yet.**
  Cards should reinforce learned material, not introduce new concepts.
  Generate cards only after the learner has completed the synthesis and quiz.

- **Do not export to Anki as the sole review method.** The built-in
  `newlearner review` command tracks review data within the system. Anki
  export is a convenience copy; changes in Anki are not synced back.

- **Do not set quality=5 for every review.** Honest self-assessment is
  critical for SM-2 accuracy. Inflated quality ratings lead to intervals
  that are too long, causing forgotten material.
