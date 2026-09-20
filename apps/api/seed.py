"""Seed a demo tenant, learner and a handful of fully-connected subject
graphs, so the map isn't just a single Algebra demo.

Every concept and edge here is authored fresh for this project — none of it
is imported from the source projects in project_alpha, so there's no
licence question to track. Run with:  python seed.py
"""

import asyncio
import random

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base, SessionLocal, engine
from models import Concept, ConceptEdge, EdgeType, Mastery, Subject, Tenant, User

SUBJECTS = [
    {
        "subject": {
            "slug": "algebra",
            "title": "Algebra",
            "description": "From arithmetic laws through to quadratic behaviour.",
            "accent": "#0b6f7d",
        },
        "concepts": [
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
        ],
        "prereqs": [
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
        ],
        "related": [("inequalities", "slope"), ("fractions", "slope")],
        "confused": [("expressions", "linear-equations")],
        "progressed": ["number-line", "operations", "negatives", "fractions", "variables"],
        "in_progress": ["expressions", "like-terms"],
    },
    {
        "subject": {
            "slug": "cell-biology",
            "title": "Cell Biology",
            "description": "From cell theory to how a cell grows and divides.",
            "accent": "#2f7a3d",
        },
        "concepts": [
            ("cell-theory", "Cell Theory", "All living things are made of cells, the basic unit of life."),
            ("prokaryote-eukaryote", "Prokaryotes vs Eukaryotes", "Cells with and without a membrane-bound nucleus."),
            ("cell-membrane", "The Cell Membrane", "A selectively permeable boundary controlling what enters and leaves."),
            ("organelles", "Organelles", "Membrane-bound structures, each with a specialised job inside the cell."),
            ("nucleus", "The Nucleus", "Where DNA is stored and gene expression is controlled."),
            ("mitochondria", "Mitochondria", "Where cellular respiration converts glucose into usable energy."),
            ("chloroplasts", "Chloroplasts", "Where photosynthesis converts light into chemical energy, in plant cells."),
            ("cellular-respiration", "Cellular Respiration", "Breaking down glucose with oxygen to release ATP."),
            ("photosynthesis", "Photosynthesis", "Converting light, water and carbon dioxide into glucose and oxygen."),
            ("diffusion-osmosis", "Diffusion and Osmosis", "The passive movement of molecules and water across membranes."),
            ("active-transport", "Active Transport", "Moving molecules against their concentration gradient, using energy."),
            ("cell-cycle", "The Cell Cycle", "The sequence a cell follows to grow and divide."),
            ("mitosis", "Mitosis", "Division producing two genetically identical daughter cells."),
        ],
        "prereqs": [
            ("cell-theory", "prokaryote-eukaryote"),
            ("prokaryote-eukaryote", "cell-membrane"),
            ("prokaryote-eukaryote", "organelles"),
            ("organelles", "nucleus"),
            ("organelles", "mitochondria"),
            ("organelles", "chloroplasts"),
            ("mitochondria", "cellular-respiration"),
            ("chloroplasts", "photosynthesis"),
            ("cell-membrane", "diffusion-osmosis"),
            ("diffusion-osmosis", "active-transport"),
            ("nucleus", "cell-cycle"),
            ("cell-cycle", "mitosis"),
        ],
        "related": [("cellular-respiration", "photosynthesis")],
        "confused": [("diffusion-osmosis", "active-transport")],
        "progressed": ["cell-theory", "prokaryote-eukaryote", "cell-membrane"],
        "in_progress": ["organelles"],
    },
    {
        "subject": {
            "slug": "programming-fundamentals",
            "title": "Programming Fundamentals",
            "description": "From variables to why an algorithm's cost matters.",
            "accent": "#6f4fb0",
        },
        "concepts": [
            ("variables", "Variables", "Named storage for a value that can change."),
            ("data-types", "Data Types", "Categories of values — numbers, text, booleans and more."),
            ("operators", "Operators", "Symbols that combine or compare values."),
            ("conditionals", "Conditionals", "Branching code based on a true or false condition."),
            ("loops", "Loops", "Repeating a block of code while a condition holds."),
            ("functions", "Functions", "Reusable, named blocks of code that take inputs and return outputs."),
            ("arrays", "Arrays and Lists", "Ordered collections of values."),
            ("dictionaries", "Dictionaries", "Key-value lookups rather than position-based ones."),
            ("recursion", "Recursion", "A function that calls itself to solve a smaller version of the same problem."),
            ("algorithms", "Algorithms", "Step-by-step procedures for solving a problem."),
            ("big-o", "Big-O Notation", "Describing how an algorithm's cost grows with input size."),
            ("debugging", "Debugging", "Systematically finding and fixing incorrect behaviour."),
        ],
        "prereqs": [
            ("variables", "data-types"),
            ("data-types", "operators"),
            ("operators", "conditionals"),
            ("conditionals", "loops"),
            ("variables", "functions"),
            ("loops", "functions"),
            ("functions", "recursion"),
            ("data-types", "arrays"),
            ("arrays", "dictionaries"),
            ("loops", "algorithms"),
            ("arrays", "algorithms"),
            ("algorithms", "big-o"),
            ("conditionals", "debugging"),
            ("loops", "debugging"),
        ],
        "related": [("recursion", "loops")],
        "confused": [("arrays", "dictionaries")],
        "progressed": ["variables", "data-types", "operators", "conditionals"],
        "in_progress": ["loops"],
    },
]


async def seed_subject(s: AsyncSession, spec: dict, user: User, rng: random.Random) -> None:
    slug = spec["subject"]["slug"]
    existing = (await s.execute(select(Subject).where(Subject.slug == slug))).scalar_one_or_none()
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

    subject = Subject(**spec["subject"])
    s.add(subject)
    await s.flush()

    by_slug: dict[str, Concept] = {}
    for slug_, title, summary in spec["concepts"]:
        c = Concept(subject_id=subject.id, slug=slug_, title=title, summary=summary)
        s.add(c)
        by_slug[slug_] = c
    await s.flush()

    for src, dst in spec["prereqs"]:
        s.add(ConceptEdge(source_id=by_slug[src].id, target_id=by_slug[dst].id,
                          relation=EdgeType.prerequisite))
    for src, dst in spec.get("related", []):
        s.add(ConceptEdge(source_id=by_slug[src].id, target_id=by_slug[dst].id,
                          relation=EdgeType.related))
    for src, dst in spec.get("confused", []):
        s.add(ConceptEdge(source_id=by_slug[src].id, target_id=by_slug[dst].id,
                          relation=EdgeType.confused_with))

    # Partial progress, so each map opens in a realistic state rather than
    # entirely dark: the early layers are worked through, the rest is not.
    for slug_ in spec.get("progressed", []):
        s.add(
            Mastery(
                user_id=user.id,
                concept_id=by_slug[slug_].id,
                probability=rng.uniform(0.72, 0.95),
                observations=rng.randint(4, 9),
            )
        )
    for slug_ in spec.get("in_progress", []):
        s.add(
            Mastery(
                user_id=user.id,
                concept_id=by_slug[slug_].id,
                probability=rng.uniform(0.35, 0.6),
                observations=rng.randint(2, 4),
            )
        )

    await s.commit()
    print(f"subject   {subject.slug}")
    print(f"concepts  {len(spec['concepts'])}")
    edge_count = len(spec["prereqs"]) + len(spec.get("related", [])) + len(spec.get("confused", []))
    print(f"edges     {edge_count}")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
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
        await s.commit()

        rng = random.Random(7)
        for spec in SUBJECTS:
            await seed_subject(s, spec, user, rng)

        print(f"user_id   {user.id}")


if __name__ == "__main__":
    asyncio.run(main())
