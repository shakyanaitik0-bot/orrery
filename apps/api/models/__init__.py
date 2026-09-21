"""The merged domain model.

Two lineages meet here, as the merge analysis recommended:

* **Tenancy and identity** follow TinkerSchool — an organization is the family
  or classroom, and every learner-owned row is scoped to it. This is what
  OpenTutor has no concept of.
* **Learning structure** follows OpenTutor — concepts as graph nodes with
  typed edges (`prerequisite`, `related`, `confused_with`) rather than a flat
  list of lessons. That graph is also what the 3D interface renders.

Mastery and review state are stored here but *computed* by the vendored Rust
engine (`packages/engine`), not by any Python reimplementation.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import GUID, JSONDict, Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Role(str, enum.Enum):
    learner = "learner"
    guardian = "guardian"
    educator = "educator"


class EdgeType(str, enum.Enum):
    """Typed concept relationships, carried over from OpenTutor's graph."""

    prerequisite = "prerequisite"
    related = "related"
    confused_with = "confused_with"


class Tenant(Base):
    """A family, classroom or individual account. TinkerSchool's org model."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(160))
    # "family" keeps the guardian/child flow; "solo" is the self-directed adult
    # learner that OpenTutor and SkillCoco were built for.
    kind: Mapped[str] = mapped_column(String(32), default="solo")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    # Identity is delegated to the auth provider (Clerk, per the analysis).
    # No password column: this service never handles credentials.
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.learner)
    # AI Tutor's education ladder, which framed grade-adaptation better than
    # the larger projects did.
    education_level: Mapped[str] = mapped_column(String(32), default="high_school")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class Session(Base):
    """A bearer-token session for a user.

    This is the stand-in for Clerk's JWT while there's no Clerk account yet:
    `/api/auth/start` issues a token here, and every request that needs to
    know who's asking presents it as `Authorization: Bearer <token>` rather
    than a client-supplied user id. Only `token_hash` is stored, so a
    database read alone can't be replayed as a session.
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GuardianLink(Base):
    """Guardian-to-learner link, taken from Open Alpha's invite-code flow.

    Reimplemented rather than copied: Open Alpha ships without a licence.
    """

    __tablename__ = "guardian_links"
    __table_args__ = (UniqueConstraint("guardian_id", "learner_id", name="uq_guardian_learner"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    guardian_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"))
    learner_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"))
    invite_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hex accent used to colour this subject's region of the 3D map.
    accent: Mapped[str] = mapped_column(String(7), default="#0b6f7d")


class Concept(Base):
    """One idea a learner can master. A node in the knowledge graph."""

    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("subject_id", "slug", name="uq_concept_subject_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(96))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bloom level, source, difficulty — kept open like OpenTutor's metadata blob.
    attributes: Mapped[dict | None] = mapped_column(JSONDict, nullable=True)


class ConceptEdge(Base):
    __tablename__ = "concept_edges"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation", name="uq_concept_edge"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("concepts.id", ondelete="CASCADE"))
    target_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("concepts.id", ondelete="CASCADE"))
    relation: Mapped[EdgeType] = mapped_column(Enum(EdgeType), default=EdgeType.prerequisite)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class Mastery(Base):
    """Per-learner, per-concept BKT state.

    `probability` is written only by the Rust engine — see
    `services/learning/mastery.py`.
    """

    __tablename__ = "mastery"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_mastery_user_concept"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("concepts.id", ondelete="CASCADE"), index=True
    )
    probability: Mapped[float] = mapped_column(Float, default=0.3)
    observations: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReviewCard(Base):
    """SM-2 scheduling state for one learner and one concept."""

    __tablename__ = "review_cards"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_card_user_concept"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"))
    concept_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("concepts.id", ondelete="CASCADE"))
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Quiz(Base):
    """A generated quiz for one learner on one concept.

    The correct answers live here and are never sent to the browser — the
    client receives questions only, and grading happens server-side when the
    attempt comes back. Otherwise a learner could read the answers out of the
    network tab and the mastery score it feeds would mean nothing.
    """

    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("concepts.id", ondelete="CASCADE"), index=True
    )
    # [{id, type: "mcq"|"short", prompt, options?, answer, explanation}]
    questions: Mapped[dict] = mapped_column(JSONDict)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChatTurn(Base):
    """Tutor conversation, scoped to a concept so it can be replayed in context."""

    __tablename__ = "chat_turns"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(16))  # "user" | "tutor"
    content: Mapped[str] = mapped_column(Text)
    # Token counts and model id, so cost is attributable per tenant.
    usage: Mapped[dict | None] = mapped_column(JSONDict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
