# Provenance

What in this repository came from which source project, and under what terms.
Keep this current — it is the record that makes the licence position auditable.

## Code vendored directly

| Path | Source | Licence | Notes |
|---|---|---|---|
| `packages/engine/` | [skillcoco/skillcoco](https://github.com/skillcoco/skillcoco) `skillcoco-core` | MIT | Licence retained at `packages/engine/LICENSE`. Contains Apache-2.0 DeepTutor-derived portions with file-level attribution — do not strip those headers. Only change made: workspace dependency declarations replaced with the versions the upstream lockfile pinned, so the crate builds standalone. All 126 upstream tests pass unmodified. |

## Approaches ported from two more MIT sources (AI-Tutor, TutorBot)

Two further MIT-licensed source projects were not used in the initial merge.
Their licences (© Hariom Kumar; © TutorBot Team) permit copying; what
follows is either logic reimplemented in Python from their approach, or a
UI/data shape carried over — no source file was copied verbatim.

| What | Source project | Where it lives now |
|---|---|---|
| Quiz mode: mixed MCQ/short-answer generation, server-side grading, wired into the same BKT mastery update flashcards and the tutor use | TutorBot (`backend/utils/ai.ts`, `components/QuizComponent.tsx`) | `services/learning/quiz.py`, `routers/quiz.py`, `components/QuizPanel.tsx` |
| Defensive JSON-response parsing for LLM output | TutorBot (`backend/utils/ai.ts` `cleanAIResponse`) | `services/learning/quiz.py` `_extract_json` (same pattern already existed in `services/learning/ingest.py`, kept consistent) |
| Anki-importable CSV deck export | TutorBot (`hooks/flashcardExport.hook.ts`) | `services/learning/export.py`, `GET /api/review/export/{subject}.csv` — streamed to the response rather than written to a web-served directory, which was a real flaw in the original |
| Ollama (local model) provider: model discovery quirks across `ollama` client response shapes | AI-Tutor (`app.py`) | `services/llm/ollama.py` |

Nothing else is copied.

## Ideas reimplemented, code written fresh

These come from projects that ship **without a licence file**, which by default
means all rights reserved. The approach is used; none of their source is
present here.

| What | Source project | Where it lives now |
|---|---|---|
| Guardian account linked to a learner by invite code | Open Alpha | `models.GuardianLink` |
| Learning-style adaptation (visual / auditory / reading / kinaesthetic) | Multi-Agent Study Assistant | `services/learning/tutor.py` — prompt text written from scratch |
| Education-level ladder driving explanation complexity | AI Tutor *(MIT, so this could have been copied — it was not)* | `services/learning/tutor.py` |
| Naming the provider in the response so a stub is never mistaken for a model | Smart Study Agent's security posture | `routers/tutor.py` `/provider` |

## Patterns followed, no code taken

| Pattern | Source project | Where |
|---|---|---|
| `LLMClient` interface — `chat` / `stream_chat` / `extract`, each returning usage | OpenTutor (MIT) | `services/llm/base.py` |
| Provider registry with explicit fallback and a loud failure mode in production | OpenTutor (MIT) | `services/llm/registry.py` |
| Concept graph with typed edges (`prerequisite`, `related`, `confused_with`) and per-user mastery | OpenTutor (MIT) | `models.Concept`, `models.ConceptEdge` |
| Organization-as-family tenancy; identity delegated to the auth provider | TinkerSchool (MIT) | `models.Tenant`, `models.User` |
| Socratic tutor that never hands over the answer | TinkerSchool (MIT) | `services/learning/tutor.py` |

## Content

The Algebra concept list, its prerequisite edges and all summaries in
`apps/api/seed.py` were authored for this repository. No curriculum content
was imported from any source project.

## If the licence position changes

If the five unlicensed projects turn out to be yours, or their authors give
permission, these are worth taking as code rather than rewriting:

- **Smart Study Agent** — the MCP server exposing PDF tools, and the input
  sanitising / rate limiting / file validation layer.
- **Multi-Agent Study Assistant** — `prompts.yaml` in full.
- **Open Alpha** — the ten curriculum subject JSON files and their
  contribution schema.
- **MyTutor** — the YouTube transcript ingestion path.
