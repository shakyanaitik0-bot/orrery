"""Build a subject and its concept graph from pasted text."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Concept, ConceptEdge, EdgeType, Subject
from services.learning.ingest import IngestError, extract_concept_graph
from services.llm.registry import get_client

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class NotesIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    # Optional: force the subject title/slug rather than letting the model pick.
    title: str | None = None


def _slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or f"subject-{uuid.uuid4().hex[:8]}"


@router.post("/notes")
async def ingest_notes(body: NotesIn, session: AsyncSession = Depends(get_session)):
    """Paste notes, a transcript, or pasted document text; get back a subject.

    Covers the "paste notes" path from the source projects' ingestion flows.
    A PDF or YouTube transcript becomes text upstream of this call — the
    graph-building step is the same either way.
    """
    client = await get_client()
    try:
        graph = await extract_concept_graph(client, body.text)
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc

    title = body.title or graph["subject_title"]
    slug = _slugify(title)

    existing = (await session.execute(select(Subject).where(Subject.slug == slug))).scalar_one_or_none()
    if existing is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    subject = Subject(slug=slug, title=title)
    session.add(subject)
    await session.flush()

    by_slug: dict[str, Concept] = {}
    for c in graph["concepts"]:
        concept = Concept(
            subject_id=subject.id,
            slug=c["slug"],
            title=c["title"],
            summary=c.get("summary"),
        )
        session.add(concept)
        by_slug[c["slug"]] = concept
    await session.flush()

    for e in graph["edges"]:
        session.add(
            ConceptEdge(
                source_id=by_slug[e["source"]].id,
                target_id=by_slug[e["target"]].id,
                relation=EdgeType.prerequisite,
            )
        )

    await session.commit()

    return {
        "subject": {"slug": subject.slug, "title": subject.title},
        "conceptCount": len(graph["concepts"]),
        "edgeCount": len(graph["edges"]),
        "provider": client.provider_name,
    }
