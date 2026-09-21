"""Flashcard generation and review, tying SM-2 scheduling to BKT mastery.

Cards are generated deterministically from a concept's own title and summary
— "What is X?" / the summary — rather than through another LLM call. This
stays fast, free, and available offline; the ingestion pipeline already used
the model once to produce the concept in the first place.

Grading a card also updates that concept's mastery: a quality of 3+ (SM-2's
own pass/fail line) counts as a correct answer to the same Rust BKT update
the tutor's "got it right" button uses. One review, one signal, not two
disagreeing trackers.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import Concept, ReviewCard
from services.learning.mastery import record_answer
from services.learning.mastery import grade_review as _sm2_grade


async def ensure_cards(session: AsyncSession, user_id, subject_id) -> int:
    """Create a review card for every concept in a subject this learner
    doesn't already have one for. Idempotent — safe to call every time the
    learner opens a subject."""
    concepts = (
        await session.execute(select(Concept).where(Concept.subject_id == subject_id))
    ).scalars().all()
    if not concepts:
        return 0

    existing_ids = {
        row[0]
        for row in (
            await session.execute(
                select(ReviewCard.concept_id).where(
                    ReviewCard.user_id == user_id,
                    ReviewCard.concept_id.in_([c.id for c in concepts]),
                )
            )
        ).all()
    }

    created = 0
    now = datetime.now(timezone.utc)
    for c in concepts:
        if c.id in existing_ids:
            continue
        session.add(
            ReviewCard(
                user_id=user_id,
                concept_id=c.id,
                front=f"What is {c.title.lower() if not c.title.isupper() else c.title}?",
                back=c.summary or c.title,
                due_at=now,  # due immediately — a fresh concept starts in the queue
            )
        )
        created += 1

    if created:
        try:
            await session.commit()
        except IntegrityError:
            # A concurrent request (a second tab, a double-fired effect)
            # created the same cards first — its rows now stand instead.
            await session.rollback()
            return 0
    return created


async def due_cards(session: AsyncSession, user_id, subject_id) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows = (
        await session.execute(
            select(ReviewCard, Concept.title)
            .join(Concept, Concept.id == ReviewCard.concept_id)
            .where(
                ReviewCard.user_id == user_id,
                Concept.subject_id == subject_id,
                ReviewCard.due_at <= now,
            )
            .order_by(ReviewCard.due_at)
        )
    ).all()
    return [
        {
            "id": str(card.id),
            "conceptId": str(card.concept_id),
            "conceptTitle": title,
            "front": card.front,
            "back": card.back,
        }
        for card, title in rows
    ]


async def all_cards(session: AsyncSession, user_id, subject_id) -> list[dict]:
    """Every card in a subject's deck, due or not — for export, not review."""
    rows = (
        await session.execute(
            select(ReviewCard, Concept.title)
            .join(Concept, Concept.id == ReviewCard.concept_id)
            .where(ReviewCard.user_id == user_id, Concept.subject_id == subject_id)
            .order_by(Concept.title)
        )
    ).all()
    return [
        {"conceptTitle": title, "front": card.front, "back": card.back}
        for card, title in rows
    ]


async def grade_card(session: AsyncSession, card: ReviewCard, quality: int) -> dict:
    """Reschedule via SM-2 and fold the same result into BKT mastery."""
    card = await _sm2_grade(session, card, quality)
    mastery_row = await record_answer(session, card.user_id, card.concept_id, quality >= 3)
    return {
        "cardId": str(card.id),
        "nextDueAt": card.due_at.isoformat() if card.due_at else None,
        "intervalDays": card.interval_days,
        "mastery": round(mastery_row.probability, 4),
    }
