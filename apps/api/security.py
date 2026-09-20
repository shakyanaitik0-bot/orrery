"""Bearer-token sessions — the stand-in for Clerk until there's a Clerk
account to swap in.

Every endpoint that acts on a specific learner's data depends on
`get_current_user` instead of trusting a client-supplied user id, so one
account can no longer read or write another's mastery, chat history, or
review cards just by knowing its id.
"""

import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Session as SessionRow
from models import User


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(401, "Missing bearer token")

    row = (
        await session.execute(
            select(SessionRow).where(SessionRow.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(401, "Invalid or expired session")

    user = await session.get(User, row.user_id)
    if user is None:
        raise HTTPException(401, "Invalid session")
    return user
