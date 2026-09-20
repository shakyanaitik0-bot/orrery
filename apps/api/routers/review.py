"""Flashcard review — SM-2 scheduling, driven from the map."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import ReviewCard, Subject, User
from security import get_current_user
from services.learning import flashcards

router = APIRouter(prefix="/api/review", tags=["review"])


class GradeIn(BaseModel):
    card_id: uuid.UUID
    quality: int = Field(ge=0, le=5)


@router.get("/due/{subject_slug}")
async def due(
    subject_slug: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Cards due now for this learner in this subject, generating any that
    don't exist yet — the deck fills in the first time a subject is opened."""
    subject = (
        await session.execute(select(Subject).where(Subject.slug == subject_slug))
    ).scalar_one_or_none()
    if subject is None:
        raise HTTPException(404, f"No subject '{subject_slug}'")
    # Read both ids before ensure_cards, which may roll back the session on
    # a concurrent-create race and expire every ORM object's attributes.
    subject_id = subject.id
    user_id = user.id

    await flashcards.ensure_cards(session, user_id, subject_id)
    cards = await flashcards.due_cards(session, user_id, subject_id)
    return {"cards": cards, "count": len(cards)}


@router.post("/grade")
async def grade(
    body: GradeIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    card = await session.get(ReviewCard, body.card_id)
    if card is None or card.user_id != user.id:
        raise HTTPException(404, "No such card for this learner")
    return await flashcards.grade_card(session, card, body.quality)
