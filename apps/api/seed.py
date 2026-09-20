"""Seed a demo tenant, learner and one fully-connected subject graph.

The concept list and its prerequisite edges are authored here rather than
imported from any source project, so the demo carries no licence question.
Run with:  python seed.py
"""

import asyncio
import random

from sqlalchemy import delete, select

from database import Base, SessionLocal, engine
from models import Concept, ConceptEdge, EdgeType, Mastery, Subject, Tenant, User

SUBJECT = {
    "slug": "algebra",
    "title": "Algebra",
    "description": "From arithmetic laws through to quadratic behaviour.",
    "accent": "#0b6f7d",
}

# (slug, title, summary)
CONCEPTS = [
    ("number-line", "The Number Line", "Ordering, magnitude and sign as position."),
    ("operations", "The Four Operations", "How addition and multiplication behave and combine."),
    ("fractions", "Fractions", "Quantities as ratios of whole numbers."),
    ("negatives", "Negative Numbers", "Extending arithmetic below zero."),
    ("variables", "Variables", "A letter standing for an unknown or varying quantity."),
    ("expressions", "Expressions", "Combining variables and numbers without asserting equality."),
    ("like-terms", "Collecting Like Terms", "Simplifying by grouping the same variable powers."),
    ("distribution", "The Distributive Law", "Multiplying across a sum."),
    ("linear-equations", "Linear Equations", "Solving for one unknown of degree one."),
    ("inequalities", "Inequalities", "Solution sets rather than single values."),
    ("coordinates", "The Coordinate Plane", "Pairs of numbers as points."),
    ("slope", "Slope and Intercept", "Rate of change and where a line crosses."),
    ("systems", "Systems of Equations", "Two constraints, one shared solution."),
    ("factoring", "Factoring", "Writing an expression as a product."),
    ("quadratics", "Quadratic Equations", "Degree two, two roots, a parabola."),
]

# (prerequisite, unlocks)
PREREQS = [
    ("number-line", "operations"),
    ("number-line", "negatives"),
    ("operations", "fractions"),
    ("operations", "variables"),
    ("negatives", "variables"),
    ("variables", "expressions"),
    ("fractions", "expressions"),
    ("expressions", "like-terms"),
    ("expressions", "distribution"),
    ("like-terms", "linear-equations"),
    ("distribution", "linear-equations"),
    ("linear-equations", "inequalities"),
    ("linear-equations", "coordinates"),
    ("coordinates", "slope"),
    ("slope", "systems"),
    ("linear-equations", "systems"),
    ("distribution", "factoring"),
    ("factoring", "quadratics"),
    ("systems", "quadratics"),
]

RELATED = [("inequalities", "slope"), ("fractions", "slope")]
CONFUSED = [("expressions", "linear-equations")]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
        # Idempotent: wipe the demo subject and rebuild it.
        existing = (
            await s.execute(select(Subject).where(Subject.slug == SUBJECT["slug"]))
        ).scalar_one_or_none()
        if existing:
            ids = [
                c.id
                for c in (
                    await s.execute(select(Concept).where(Concept.subject_id == existing.id))
                ).scalars().all()
            ]
            if ids:
                await s.execute(delete(ConceptEdge).where(ConceptEdge.source_id.in_(ids)))
                await s.execute(delete(Mastery).where(Mastery.concept_id.in_(ids)))
                await s.execute(delete(Concept).where(Concept.id.in_(ids)))
            await s.execute(delete(Subject).where(Subject.id == existing.id))
            await s.commit()

        subject = Subject(**SUBJECT)
        s.add(subject)
        await s.flush()

        by_slug: dict[str, Concept] = {}
        for slug, title, summary in CONCEPTS:
            c = Concept(subject_id=subject.id, slug=slug, title=title, summary=summary)
            s.add(c)
            by_slug[slug] = c
        await s.flush()

        for src, dst in PREREQS:
            s.add(ConceptEdge(source_id=by_slug[src].id, target_id=by_slug[dst].id,
                              relation=EdgeType.prerequisite))
        for src, dst in RELATED:
            s.add(ConceptEdge(source_id=by_slug[src].id, target_id=by_slug[dst].id,
                              relation=EdgeType.related))
        for src, dst in CONFUSED:
            s.add(ConceptEdge(source_id=by_slug[src].id, target_id=by_slug[dst].id,
                              relation=EdgeType.confused_with))

        tenant = (
            await s.execute(select(Tenant).where(Tenant.name == "Demo"))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name="Demo", kind="solo")
            s.add(tenant)
            await s.flush()

        user = (
            await s.execute(select(User).where(User.display_name == "Demo Learner"))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant.id,
                display_name="Demo Learner",
                education_level="high_school",
            )
            s.add(user)
            await s.flush()

        # Partial progress, so the map opens in a realistic state rather than
        # entirely dark: the early layers are worked through, the rest is not.
        rng = random.Random(7)
        progressed = ["number-line", "operations", "negatives", "fractions", "variables"]
        for slug in progressed:
            s.add(
                Mastery(
                    user_id=user.id,
                    concept_id=by_slug[slug].id,
                    probability=rng.uniform(0.72, 0.95),
                    observations=rng.randint(4, 9),
                )
            )
        for slug in ["expressions", "like-terms"]:
            s.add(
                Mastery(
                    user_id=user.id,
                    concept_id=by_slug[slug].id,
                    probability=rng.uniform(0.35, 0.6),
                    observations=rng.randint(2, 4),
                )
            )

        await s.commit()

        print(f"subject   {subject.slug}")
        print(f"concepts  {len(CONCEPTS)}")
        print(f"edges     {len(PREREQS) + len(RELATED) + len(CONFUSED)}")
        print(f"user_id   {user.id}")


if __name__ == "__main__":
    asyncio.run(main())
