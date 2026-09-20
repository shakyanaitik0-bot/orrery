"""Knowledge-graph endpoints — the data behind the 3D map."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Concept, ConceptEdge, Mastery, Subject
from services.learning import mastery as mastery_service
from services.learning.layout import build_scene

router = APIRouter(prefix="/api/graph", tags=["graph"])


class AnswerIn(BaseModel):
    user_id: uuid.UUID
    concept_id: uuid.UUID
    correct: bool


@router.get("/subjects")
async def list_subjects(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Subject).order_by(Subject.title))).scalars().all()
    return [
        {"id": str(s.id), "slug": s.slug, "title": s.title,
         "description": s.description, "accent": s.accent}
        for s in rows
    ]


@router.get("/scene/{subject_slug}")
async def scene(
    subject_slug: str,
    user_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
):
    """The positioned graph for one subject, with this learner's mastery."""
    subject = (
        await session.execute(select(Subject).where(Subject.slug == subject_slug))
    ).scalar_one_or_none()
    if subject is None:
        raise HTTPException(404, f"No subject '{subject_slug}'")

    concepts = (
        await session.execute(select(Concept).where(Concept.subject_id == subject.id))
    ).scalars().all()
    concept_ids = {c.id for c in concepts}

    edges = (await session.execute(select(ConceptEdge))).scalars().all()
    edges = [e for e in edges if e.source_id in concept_ids and e.target_id in concept_ids]

    mastery_map: dict[str, float] = {}
    if user_id is not None:
        rows = (
            await session.execute(select(Mastery).where(Mastery.user_id == user_id))
        ).scalars().all()
        mastery_map = {str(m.concept_id): m.probability for m in rows}

    payload = build_scene(
        concepts=[
            {
                "id": str(c.id),
                "slug": c.slug,
                "title": c.title,
                "summary": c.summary,
                "subject": subject.slug,
            }
            for c in concepts
        ],
        edges=[
            {
                "source": str(e.source_id),
                "target": str(e.target_id),
                "relation": e.relation.value,
                "weight": e.weight,
            }
            for e in edges
        ],
        mastery=mastery_map,
    )
    payload["subject"] = {"slug": subject.slug, "title": subject.title, "accent": subject.accent}
    return payload


@router.post("/answer")
async def submit_answer(body: AnswerIn, session: AsyncSession = Depends(get_session)):
    """Record one answer. Mastery is recomputed by the Rust engine."""
    row = await mastery_service.record_answer(
        session, body.user_id, body.concept_id, body.correct
    )
    return {
        "conceptId": str(row.concept_id),
        "mastery": round(row.probability, 4),
        "observations": row.observations,
        "mastered": mastery_service.is_mastered(row.probability),
        "threshold": mastery_service.MASTERY_THRESHOLD,
    }
