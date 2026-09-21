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
- **Signing in** creates a real account (name + level, no password) and a
  personal tenant, and issues a bearer session token — every request that
  touches a learner's data is authenticated by that token, not by a
  client-supplied id, so one account cannot read or write another's mastery,
  chat history, or review cards. See "Real identity" below for what this is
  still a stand-in for.
- **Pasting notes, uploading a PDF, or pasting a YouTube link** ("+ New
  subject") all build a new concept graph through the same LLM interface the
  tutor uses, and drop you straight into the resulting map. A PDF needs a
  real text layer; a YouTube video needs captions — both are rejected with a
  clear error otherwise, no OCR or audio transcription attempted.
- **Reviewing flashcards** ("Review") runs a per-concept SM-2 deck, generated
  automatically the first time you open a subject. Grading a card feeds the
  same BKT mastery update as the tutor, so the map and the deck agree. An
  "Export to Anki" button in that panel downloads the deck as a CSV that
  Anki's importer accepts directly.
- **"Quiz me"** on any concept generates a short mixed multiple-choice /
  short-answer quiz, grades it server-side (answers never reach the browser
  before submission), and feeds every question into the same mastery engine
  as a flashcard grade or a tutor "got it right."
- **Three built-in subjects** — Algebra, Cell Biology, and Programming
  Fundamentals — each with real prerequisite structure, plus whatever you
  ingest yourself.

## Quick start

Two terminals. Python 3.11+, Node 20+, and a Rust toolchain.

```bash
# 1. Build the Rust engine into the Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install maturin -r apps/api/requirements.txt
(cd packages/engine-py && maturin develop --release)

# 2. (optional) Start Postgres — see "Postgres" below. Skipping this runs
#    on a local SQLite file instead, which is fine for a quick look.
docker compose up -d

# 3. Apply migrations, seed, and run the API
cd apps/api
alembic upgrade head
python seed.py && uvicorn main:app --port 8000
```

```bash
# 4. Run the web app (second terminal)
cd apps/web && npm install && npm run dev
```

Open <http://localhost:3000> and sign in with any name — that creates a real
account. `seed.py` seeds a separate "Demo Learner" account with pre-filled
progress, for reference; there's no login-as-that-user flow, since the app
has no password-based login yet (see "Real identity" below).

Without any provider credentials the tutor runs on an offline stub that says
so in its own output — the map, the graph and all mastery scoring are fully
live either way.

## Connecting a real model: Bedrock, Gemini, or Ollama

Three real providers are supported, all behind the same `LLMClient`
interface (`apps/api/services/llm/base.py`) — the app never talks to any
vendor's SDK directly outside its own provider file. `LLM_PROVIDER=auto`
(the default) tries Bedrock, then Gemini, then Ollama, then falls back to
the stub; set it to `bedrock`, `gemini`, `ollama`, or `stub` to force one.

**AWS Bedrock** — the whole integration is `apps/api/services/llm/bedrock.py`:

```bash
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-5-20260115-v1:0
BEDROCK_SMALL_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Credentials resolve through the normal boto3 chain, so in deployment the task
or instance role is enough and no keys go in the environment. It uses the
Bedrock **Converse** API rather than per-model `invoke_model` payloads, so
switching to Llama or Mistral on Bedrock is a model-id change.

**Google Gemini** — a free-tier alternative with no AWS account needed, in
`apps/api/services/llm/gemini.py`. Get a free key at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) (no billing
account required for the free tier's rate limits) and set:

```bash
LLM_PROVIDER=gemini            # or leave as "auto" and just set the key below
GEMINI_API_KEY=your-key-here   # never commit this — set it as an env var only
GEMINI_MODEL_ID=gemini-2.5-flash              # optional, this is the default
GEMINI_SMALL_MODEL_ID=gemini-2.5-flash-lite   # optional, this is the default
```

**Ollama** — a fully offline, no-account option in
`apps/api/services/llm/ollama.py`. Install [Ollama](https://ollama.com), pull
a model, and there's nothing to set unless you want a non-default one:

```bash
ollama pull llama3               # any model works; llama3 is the default
LLM_PROVIDER=ollama              # or leave as "auto" and it's tried last
OLLAMA_MODEL_ID=llama3           # optional, this is the default
OLLAMA_BASE_URL=http://localhost:11434   # optional, this is the default
```

No API key, no AWS account, no per-token cost — the tradeoff is running the
model on your own machine, and answer quality depends on what you've pulled.

Either way: `GET /api/tutor/provider` reports which provider is actually
serving requests, and `LLM_REQUIRED=true` fails loudly instead of falling
back to the stub if the configured provider turns out not to be reachable —
useful in production, where silently serving stub text would be worse than
an error.

**Never put a real API key or AWS secret in the repository or in chat.**
Both settings above are read from environment variables (a local `.env` file
is fine — it's already listed in `.gitignore`), never from a config file
that gets committed.

## Postgres

SQLite is the default only so a fresh clone runs. Point it at Postgres and the
same models work unchanged — `apps/api/database.py` resolves UUID and JSON
columns per dialect. `docker-compose.yml` at the repo root starts a local one:

```bash
docker compose up -d     # postgres:16, user/pass/db all "orrery", port 5432
export DATABASE_URL=postgresql+asyncpg://orrery:orrery@localhost/orrery
cd apps/api && alembic upgrade head && python seed.py
```

This is the deliberate inverse of OpenTutor, which raises unless the URL is
SQLite. See [docs/MERGE-DECISIONS.md](docs/MERGE-DECISIONS.md). Verified
against a real Postgres 16 instance, not just SQLite — schema, auth, and
mastery scoring all checked out.

### Migrations

Alembic lives in `apps/api/migrations/`, wired to the app's own `Settings`
(`migrations/env.py` reads `DATABASE_URL`, so it always targets whatever
database the API itself is configured for) and to `Base.metadata`, so
`alembic revision --autogenerate` picks up model changes automatically.

```bash
cd apps/api
alembic upgrade head                          # apply
alembic revision --autogenerate -m "message"  # after changing models/
```

One thing autogenerate can't see: the app's custom `GUID`/`JSONDict` column
types aren't part of SQLAlchemy's own vocabulary, so every migration file
needs `import database` — `migrations/script.py.mako` adds it automatically
for new ones.

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

- **Real identity.** `POST /api/auth/start` is a working stand-in for Clerk:
  a name creates a real account with no password, because none are
  collected, and a bearer session token (`apps/api/security.py`) is what
  actually gates access to a learner's data — not the account name or id.
  What this stand-in is still missing is anything Clerk would add: password
  or social login, email verification, multi-device session management,
  revoking a stolen token before it expires on its own. `User.external_id`
  is still the seam for swapping in real Clerk later; see
  `apps/api/routers/auth.py`. **This needs a Clerk account and API keys to
  finish — ask if you want to set that up.**
- **Curriculum.** Three seeded subjects (Algebra, Cell Biology, Programming
  Fundamentals) plus whatever you ingest. TinkerSchool's 81 migrations and
  Open Alpha's subject JSON are not imported.
- **Subjects are shared, not tenant-scoped.** A subject anyone ingests is
  visible to every account — mastery, review cards, and chat are private per
  learner (enforced by the session-token auth above), but the concept graphs
  themselves are a shared catalog, closer to a public wiki than private
  files. Scoping subjects to a tenant, if that's wanted, is a schema change
  (a `tenant_id` on `Subject`), not just an API check.
