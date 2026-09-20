"""Tutor chat — streamed from Bedrock."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import SessionLocal, get_session
from models import ChatTurn, Concept, Mastery, User
from services.learning.tutor import system_prompt
from services.llm.registry import get_client

router = APIRouter(prefix="/api/tutor", tags=["tutor"])


class AskIn(BaseModel):
    user_id: uuid.UUID
    concept_id: uuid.UUID
    message: str
    learning_style: str = "reading"


async def _context(session: AsyncSession, body: AskIn):
    concept = await session.get(Concept, body.concept_id)
    if concept is None:
        raise HTTPException(404, "Unknown concept")
    user = await session.get(User, body.user_id)
    if user is None:
        raise HTTPException(404, "Unknown user")
    row = (
        await session.execute(
            select(Mastery).where(
                Mastery.user_id == body.user_id, Mastery.concept_id == body.concept_id
            )
        )
    ).scalar_one_or_none()
    return concept, user, (row.probability if row else 0.0)


@router.post("/ask")
async def ask(body: AskIn, session: AsyncSession = Depends(get_session)):
    """Stream a tutor reply, then persist the exchange."""
    concept, user, mastery = await _context(session, body)
    prompt = system_prompt(
        concept_title=concept.title,
        concept_summary=concept.summary,
        education_level=user.education_level,
        learning_style=body.learning_style,
        mastery=mastery,
    )
    client = await get_client()

    async def stream():
        collected: list[str] = []
        async for chunk in client.stream_chat(prompt, body.message):
            collected.append(chunk)
            yield chunk
        # Persist on a fresh session: the request-scoped one is closed by the
        # time the response body finishes streaming.
        async with SessionLocal() as write:
            write.add(
                ChatTurn(user_id=user.id, concept_id=concept.id,
                         role="user", content=body.message)
            )
            write.add(
                ChatTurn(
                    user_id=user.id,
                    concept_id=concept.id,
                    role="tutor",
                    content="".join(collected),
                    usage=client.get_last_usage(),
                )
            )
            await write.commit()

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")


@router.get("/history/{user_id}/{concept_id}")
async def history(
    user_id: uuid.UUID, concept_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    rows = (
        await session.execute(
            select(ChatTurn)
            .where(ChatTurn.user_id == user_id, ChatTurn.concept_id == concept_id)
            .order_by(ChatTurn.created_at)
        )
    ).scalars().all()
    return [{"role": r.role, "content": r.content} for r in rows]


@router.get("/provider")
async def provider():
    """Which LLM is actually serving requests — surfaced so a stub response is
    never mistaken for a real one."""
    client = await get_client()
    return {
        "provider": client.provider_name,
        "model": getattr(client, "model_id", None),
    }
