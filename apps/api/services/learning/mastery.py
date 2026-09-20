"""Mastery and review scheduling.

Every number here comes out of the vendored Rust engine. There is deliberately
no Python implementation of BKT or SM-2 in this codebase: the merge analysis
found three competing mastery models across the source projects, and the
resolution was to keep exactly one — SkillCoco's, which is the audited and
unit-tested implementation.
"""

from datetime import datetime, timedelta, timezone

import orrery_engine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Mastery, ReviewCard

MASTERY_THRESHOLD: float = orrery_engine.mastery_threshold()


async def record_answer(
    session: AsyncSession, user_id, concept_id, correct: bool
) -> Mastery:
    """Fold one answer into a learner's mastery estimate for a concept."""
    row = (
        await session.execute(
            select(Mastery).where(
                Mastery.user_id == user_id, Mastery.concept_id == concept_id
            )
        )
    ).scalar_one_or_none()

    if row is None:
        row = Mastery(user_id=user_id, concept_id=concept_id, probability=0.3, observations=0)
        session.add(row)

    row.probability = orrery_engine.bkt_update(row.probability, correct)
    row.observations += 1
    await session.commit()
    await session.refresh(row)
    return row


async def grade_review(
    session: AsyncSession, card: ReviewCard, quality: int
) -> ReviewCard:
    """Reschedule a flashcard after a review. `quality` is 0-5."""
    interval, ease, reps = orrery_engine.sm2_schedule(
        quality, card.repetitions, card.ease_factor, card.interval_days
    )
    card.interval_days = interval
    card.ease_factor = ease
    card.repetitions = reps
    card.due_at = datetime.now(timezone.utc) + timedelta(days=interval)
    await session.commit()
    await session.refresh(card)
    return card


def is_mastered(probability: float) -> bool:
    return probability >= MASTERY_THRESHOLD
