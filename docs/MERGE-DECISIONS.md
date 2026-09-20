# Merge decisions

The inventory analysis found ten projects, three of them substantial, with
overlapping features and incompatible foundations. These are the calls made
while building this skeleton, and why. Each one is reversible; none was
guessed at without a reason.

## 1. Two foundations, split along one boundary

OpenTutor has the strongest domain model and no multi-tenancy. TinkerSchool has
real multi-tenancy and a thinner learning model. Rather than pick one whole,
the boundary runs between them:

| Layer | Follows | Why |
|---|---|---|
| Tenancy, identity, families, billing | TinkerSchool | The only shipped multi-tenant auth in the collection |
| Concepts, graph, mastery, tutoring | OpenTutor | 26 models and a typed knowledge graph no other project has |
| Adaptive algorithms | SkillCoco | The only audited, separately-tested implementation |

`models/__init__.py` is where the two meet: `Tenant` and `User` are
TinkerSchool's shape, everything below `Concept` is OpenTutor's.

## 2. Postgres is the default, SQLite is the convenience

OpenTutor's config raises unless `DATABASE_URL` is SQLite, and its type layer
had been narrowed to match — UUIDs as 36-char strings, JSON as text, vectors as
serialized JSON with no index. That is the single biggest obstacle to a
multi-user deployment.

`apps/api/database.py` inverts it. `GUID` and `JSONDict` resolve to native
`UUID` and `JSONB` on Postgres and to string/JSON fallbacks elsewhere, chosen
per dialect at runtime. Model code is written once. Neither dialect is refused.

**Still to do:** vector storage for RAG needs `pgvector`; there is no embedding
column yet because there is no ingestion pipeline yet.

## 3. One spaced-repetition algorithm, one mastery model

The collection contained FSRS *and* SM-2, plus three mastery models — BKT in
Python, BKT in Rust, and an 80% quiz gate. Shipping two of anything here means
"mastered" means different things on different screens.

Resolved: **SkillCoco's Rust implementations, for both.** It is the only one
written as a standalone, separately-tested library, with an enforced rule that
no database, UI or async dependency may leak into it. Its 126 tests pass
unmodified in this repo.

It is reached through PyO3 rather than WASM. WASM remains the better target for
running the same code in the browser, and the crate already compiles to
`wasm32-unknown-unknown` — but mastery scoring should not be client-side
anyway, so the server binding came first.

There is deliberately **no Python implementation of BKT or SM-2** in this
codebase. `services/learning/mastery.py` only stores what the engine returns.

## 4. Nothing unlicensed was copied

Five of the ten projects carry no licence file, which by default means all
rights reserved. Their good ideas are used; their code is not. What was
reimplemented from scratch is listed in [PROVENANCE.md](PROVENANCE.md).

This is the one decision that should be revisited first — if those projects
are yours, or you have the authors' permission, several of them have code
worth taking directly rather than rewriting.

## 5. The 3D view renders real structure

No source project had any 3D. The temptation with a brief like "3D UI" is
decoration over a list. Instead every visual property is bound to data the
system already had:

- **Height** — prerequisite depth, by longest path, so a concept sits above
  everything it requires.
- **Size and glow** — that learner's mastery probability.
- **Wireframe** — locked, with blockers named on selection.
- **Bright edges** — the prerequisite chain through the selected concept.

Layout is computed server-side in `services/learning/layout.py`, because the
gating rule belongs with the data, not the renderer. The client draws what it
is given.

## Open questions

1. **Primary audience.** Built for the self-directed learner, since two of the
   three heavyweights target that. TinkerSchool's K-6 flow, COPPA consent and
   parent billing would land as a mode on top. If K-6 is actually primary, the
   onboarding and tone decisions invert.
2. **FSRS vs SM-2.** SM-2 was chosen because SkillCoco's implementation is
   solid. FSRS is the better algorithm on the merits; if it matters, port it
   into the same crate rather than reintroducing a second scheduler.
3. **Hardware and labs.** TinkerSchool's Web Serial device features and
   SkillCoco's terminal labs are both desktop-bound. They fit as optional
   modules, not core.
