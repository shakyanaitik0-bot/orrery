# Orrery

A single study platform merged from the projects in `project_alpha`, navigated
as a 3D knowledge map. The name is a placeholder — rename freely.

This is a **working vertical slice**, not a finished product. It exists to prove
the three merge decisions that the [inventory analysis](docs/MERGE-DECISIONS.md)
said were the hard ones, and to give the rest of the work somewhere to land.

```
┌── apps/web        Next.js 14 + React Three Fiber — the 3D knowledge map
├── apps/api        FastAPI — graph, mastery, tutoring
├── packages/engine     skillcoco-core (MIT, vendored) — BKT, SM-2, path DAG
└── packages/engine-py  PyO3 bindings so the API calls that Rust directly
```

## What actually works

Run it and you get a navigable 3D map of an Algebra concept graph where a
learner's real mastery drives what you see:

- **Height is prerequisite depth**, computed server-side by longest path, so
  "up" means "further in".
- **Size and glow are mastery**, per concept, per learner.
- **Locked concepts** are drawn as wireframes with their blockers named — a
  concept unlocks when every prerequisite crosses the mastery threshold.
- **Clicking a concept** opens a tutor that adapts its prompt to how much of
  that concept the learner has already mastered.
- **Recording an answer** runs Bayesian Knowledge Tracing in Rust, writes the
  new probability, and re-evaluates what is unlocked.

## Quick start

Two terminals. Python 3.11+, Node 20+, and a Rust toolchain.

```bash
# 1. Build the Rust engine into the Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install maturin fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" \
            aiosqlite asyncpg pydantic-settings boto3
(cd packages/engine-py && maturin develop --release)

# 2. Seed and run the API
cd apps/api && python seed.py && uvicorn main:app --port 8000
```

```bash
# 3. Run the web app (second terminal)
cd apps/web && npm install && npm run dev
```

Open <http://localhost:3000>. `seed.py` prints the demo learner's id.

Without AWS credentials the tutor runs on an offline stub that says so in its
own output — the map, the graph and all mastery scoring are fully live either
way.

## Connecting AWS Bedrock

The entire integration is `apps/api/services/llm/bedrock.py`. Set:

```bash
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-5-20260115-v1:0
BEDROCK_SMALL_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
LLM_REQUIRED=true      # fail loudly instead of falling back to the stub
```

Credentials resolve through the normal boto3 chain, so in deployment the task
or instance role is enough and no keys go in the environment.

It uses the Bedrock **Converse** API rather than per-model `invoke_model`
payloads, so switching to Llama or Mistral on Bedrock is a model-id change.
`GET /api/tutor/provider` reports which provider is actually serving requests.

## Postgres

SQLite is the default only so a fresh clone runs. Point it at Postgres and the
same models work unchanged — `apps/api/database.py` resolves UUID and JSON
columns per dialect:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/orrery
```

This is the deliberate inverse of OpenTutor, which raises unless the URL is
SQLite. See [docs/MERGE-DECISIONS.md](docs/MERGE-DECISIONS.md).

## Licensing

`packages/engine` is vendored from [SkillCoco](https://github.com/skillcoco/skillcoco)
(MIT) with its licence retained at `packages/engine/LICENSE`. Parts of it derive
from DeepTutor (Apache-2.0) and carry file-level attribution — keep those notices.

Nothing here is copied from the five unlicensed projects in `project_alpha`.
Where their ideas are used — the guardian invite-code link, the learning-style
prompts, the education ladder — the code is written fresh. See
[docs/PROVENANCE.md](docs/PROVENANCE.md) for what came from where.

## What is not built yet

Named plainly so nothing here looks more finished than it is:

- **Auth.** `User.external_id` is the seam for Clerk; there is no sign-in flow.
- **Ingestion.** No PDF, notes or YouTube pipeline yet.
- **Flashcard review UI.** SM-2 runs and is wired, but nothing drives it.
- **Migrations.** Tables are created from the models; Alembic is not set up.
- **Curriculum.** One seeded subject. TinkerSchool's 81 migrations and Open
  Alpha's subject JSON are not imported.
- **Multi-subject map.** The API serves any subject; the client requests one.
