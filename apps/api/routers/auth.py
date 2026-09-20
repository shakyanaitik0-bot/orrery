"""Minimal account creation.

This is deliberately not Clerk. The domain model (`User.external_id`) is the
seam for a real identity provider — TinkerSchool's pattern, from the merge
analysis — but standing up Clerk needs an account and API keys this session
doesn't have. What's here is a real, working substitute: a display name
creates a tenant and a user, and a bearer session token (see `security.py`)
is what proves identity on every later request — not the user id itself,
which is not a secret and appears in URLs and logs.

Swapping to Clerk later means populating `external_id` from its JWT and
retiring `POST /start` and the session table here. Nothing about the
tenant/concept/mastery model changes.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Session as SessionRow
from models import Tenant, User
from security import generate_token, get_current_user, hash_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class StartIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    education_level: str = "high_school"


async def _issue_session(session: AsyncSession, user: User) -> str:
    token = generate_token()
    session.add(SessionRow(user_id=user.id, token_hash=hash_token(token)))
    await session.commit()
    return token


@router.post("/start")
async def start(body: StartIn, session: AsyncSession = Depends(get_session)):
    """Create a personal tenant and a user in it, and issue a session token.
    The frontend calls this once and keeps the returned token — not the
    user id — as its proof of identity."""
    tenant = Tenant(name=f"{body.display_name}'s space", kind="solo")
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        display_name=body.display_name,
        education_level=body.education_level,
    )
    session.add(user)
    await session.flush()
    token = await _issue_session(session, user)

    return {
        "userId": str(user.id),
        "tenantId": str(tenant.id),
        "displayName": user.display_name,
        "sessionToken": token,
    }


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """Restore a session from its bearer token — called on page load."""
    return {
        "userId": str(user.id),
        "tenantId": str(user.tenant_id),
        "displayName": user.display_name,
        "educationLevel": user.education_level,
    }
