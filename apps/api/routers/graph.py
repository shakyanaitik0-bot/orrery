"""Knowledge-graph endpoints — the data behind the 3D map."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Concept, ConceptEdge, Mastery, Subject, User
from security import get_current_user
from services.learning import mastery as mastery_service
from services.learning.layout import build_scene
from services.learning.mastery import MASTERY_THRESHOLD

router = APIRouter(prefix="/api/graph", tags=["graph"])


class AnswerIn(BaseModel):
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


@router.get("/dashboard")
async def dashboard(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Per-subject progress summary for this learner — the home screen.

    Reuses `build_scene`'s own locking rule rather than recomputing it, so a
    subject's mastered/open/locked counts here can never drift from what the
    map itself would show for the same subject.
    """
    subjects = (await session.execute(select(Subject).order_by(Subject.title))).scalars().all()
    all_edges = (await session.execute(select(ConceptEdge))).scalars().all()
    mastery_rows = (
        await session.execute(select(Mastery).where(Mastery.user_id == user.id))
    ).scalars().all()
    mastery_map = {str(m.concept_id): m.probability for m in mastery_rows}

    summaries = []
    for subject in subjects:
        concepts = (
            await session.execute(select(Concept).where(Concept.subject_id == subject.id))
        ).scalars().all()
        concept_ids = {c.id for c in concepts}
        edges = [e for e in all_edges if e.source_id in concept_ids and e.target_id in concept_ids]

        scene_data = build_scene(
            concepts=[
                {"id": str(c.id), "slug": c.slug, "title": c.title,
                 "summary": c.summary, "subject": subject.slug}
                for c in concepts
            ],
            edges=[
                {"source": str(e.source_id), "target": str(e.target_id),
                 "relation": e.relation.value, "weight": e.weight}
                for e in edges
            ],
            mastery=mastery_map,
        )
        nodes = scene_data["nodes"]
        mastered = sum(1 for n in nodes if n["mastered"])
        locked = sum(1 for n in nodes if n["locked"])
        avg_mastery = sum(n["mastery"] for n in nodes) / len(nodes) if nodes else 0.0

        summaries.append(
            {
                "slug": subject.slug,
                "title": subject.title,
                "description": subject.description,
                "accent": subject.accent,
                "conceptCount": len(nodes),
                "mastered": mastered,
                "open": len(nodes) - mastered - locked,
                "locked": locked,
                "averageMastery": round(avg_mastery, 4),
            }
        )
    return {"subjects": summaries, "masteryThreshold": MASTERY_THRESHOLD}


@router.get("/scene/{subject_slug}")
async def scene(
    subject_slug: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
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

    rows = (
        await session.execute(select(Mastery).where(Mastery.user_id == user.id))
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
async def submit_answer(
    body: AnswerIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Record one answer. Mastery is recomputed by the Rust engine."""
    row = await mastery_service.record_answer(
        session, user.id, body.concept_id, body.correct
    )
    return {
        "conceptId": str(row.concept_id),
        "mastery": round(row.probability, 4),
        "observations": row.observations,
        "mastered": mastery_service.is_mastered(row.probability),
        "threshold": mastery_service.MASTERY_THRESHOLD,
    }
