"""Minimal account creation.

This is deliberately not Clerk. The domain model (`User.external_id`) is the
seam for a real identity provider — TinkerSchool's pattern, from the merge
analysis — but standing up Clerk needs an account and API keys this session
doesn't have. What's here is a real, working substitute: a display name
creates a tenant and a user, and the returned id is the bearer of identity
client-side. No passwords are stored because none are collected.

Swapping to Clerk later means populating `external_id` from its JWT and
retiring `POST /start`. Nothing about the tenant/concept/mastery model changes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Tenant, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class StartIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    education_level: str = "high_school"


@router.post("/start")
async def start(body: StartIn, session: AsyncSession = Depends(get_session)):
    """Create a personal tenant and a user in it. Idempotent per browser:
    the frontend calls this once and keeps the returned id."""
    tenant = Tenant(name=f"{body.display_name}'s space", kind="solo")
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        display_name=body.display_name,
        education_level=body.education_level,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {
        "userId": str(user.id),
        "tenantId": str(tenant.id),
        "displayName": user.display_name,
    }


@router.get("/me/{user_id}")
async def me(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Restore a session from a stored id — called on page load."""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "No such user")
    return {
        "userId": str(user.id),
        "tenantId": str(user.tenant_id),
        "displayName": user.display_name,
        "educationLevel": user.education_level,
    }
