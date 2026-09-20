"""Build a subject and its concept graph from pasted text or an uploaded PDF."""

import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Concept, ConceptEdge, EdgeType, Subject
from services.learning.ingest import IngestError, extract_concept_graph
from services.learning.pdf import PdfExtractionError, extract_text
from services.llm.registry import get_client

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

MAX_PDF_BYTES = 15 * 1024 * 1024  # 15 MB


class NotesIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    # Optional: force the subject title/slug rather than letting the model pick.
    title: str | None = None


def _slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or f"subject-{uuid.uuid4().hex[:8]}"


async def _build_subject(session: AsyncSession, text: str, title: str | None) -> dict:
    """Shared by the text and PDF entry points: text in, a persisted subject out."""
    client = await get_client()
    try:
        graph = await extract_concept_graph(client, text)
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc

    subject_title = title or graph["subject_title"]
    slug = _slugify(subject_title)

    existing = (await session.execute(select(Subject).where(Subject.slug == slug))).scalar_one_or_none()
    if existing is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    subject = Subject(slug=slug, title=subject_title)
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


@router.post("/notes")
async def ingest_notes(body: NotesIn, session: AsyncSession = Depends(get_session)):
    """Paste notes, a transcript, or pasted document text; get back a subject.

    Covers the "paste notes" path from the source projects' ingestion flows.
    A PDF becomes text upstream of this same builder — see `/pdf` below.
    """
    return await _build_subject(session, body.text, body.title)


@router.post("/pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Upload a PDF; get back a subject built from its text.

    Text extraction only — a scanned, image-only PDF has no text layer for
    pypdf to read, and is rejected with a clear reason rather than silently
    producing an empty graph. OCR is a separate concern this doesn't take on.
    """
    data = await file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, f"PDF is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB.")

    try:
        text = extract_text(data)
    except PdfExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc

    # Let the model choose the title from the content; no forced override.
    return await _build_subject(session, text, title=None)
