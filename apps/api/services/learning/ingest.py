"""Turning raw study material into a concept graph.

This is the ingestion pipeline the README listed as missing. It reuses the
same `LLMClient.extract` call the tutor already goes through — no new
provider code, no new dependency. `extract` is deliberately routed to the
small/cheap model in the Bedrock client, since this is a structured, one-shot
call rather than a conversation.

Only plain text is handled here (pasted notes, a transcript). PDF extraction
is a separate, mechanical step — get bytes to text and this pipeline is
unchanged — deferred so this stays scoped to what was actually asked for.
"""

import json
import re

from services.learning.layout import acyclic_prereqs
from services.llm.base import LLMClient

SYSTEM_PROMPT = """You turn study material into a small knowledge graph.

Read the material and produce 5 to 15 concepts a learner would need to master
it, plus the prerequisite relationships between them. Order matters: a
concept should only depend on concepts that come genuinely before it.

Respond with ONLY a JSON object, no prose, no code fence, in this exact shape:

{
  "subject_title": "short title for this material",
  "concepts": [
    {"slug": "kebab-case-id", "title": "Human Title", "summary": "one sentence"}
  ],
  "edges": [
    {"source": "prerequisite-slug", "target": "unlocked-slug"}
  ]
}

Rules:
- Every slug in "edges" must appear in "concepts".
- Prefer more, smaller concepts over few broad ones.
- Do not invent material that is not in the text.
- Prerequisites must run one way only. Never make two concepts require each
  other, directly or through a chain, and never make a concept require itself.
- At least one concept must have no prerequisites at all — that is where the
  learner starts.
- Keep the concepts in one connected body of material: every concept should
  reach the rest through some chain of edges rather than floating alone."""


class IngestError(ValueError):
    """The model's output could not be parsed as the expected graph shape."""


def _extract_json(text: str) -> dict:
    # Models occasionally wrap JSON in a code fence despite instructions;
    # strip one if present rather than failing on it.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise IngestError("No JSON object found in the model's response.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise IngestError(f"Model output was not valid JSON: {exc}") from exc


async def extract_concept_graph(client: LLMClient, text: str) -> dict:
    """Call the LLM and return a validated {subject_title, concepts, edges} dict."""
    if len(text.strip()) < 40:
        raise IngestError("That's too little material to build a concept graph from.")

    content, _usage = await client.extract(SYSTEM_PROMPT, text[:12000])
    data = _extract_json(content)

    concepts = data.get("concepts")
    edges = data.get("edges", [])
    if not isinstance(concepts, list) or not concepts:
        raise IngestError("Model did not return any concepts.")

    slugs = set()
    for c in concepts:
        if not isinstance(c, dict) or "slug" not in c or "title" not in c:
            raise IngestError("A concept was missing a slug or title.")
        slugs.add(c["slug"])

    # Drop edges that reference a concept the model didn't actually list,
    # rather than failing the whole ingest over one bad reference.
    clean_edges = [
        e for e in edges
        if isinstance(e, dict) and e.get("source") in slugs and e.get("target") in slugs
    ]

    # Models do sometimes return mutually-dependent concepts despite the
    # prompt. Storing those would lock every concept in the cycle — and
    # anything downstream of it — with no way for the learner to start, so the
    # offending edges are dropped before the graph is persisted.
    kept, _ = acyclic_prereqs([(e["source"], e["target"]) for e in clean_edges])
    kept_set = set(kept)
    clean_edges = [e for e in clean_edges if (e["source"], e["target"]) in kept_set]

    return {
        "subject_title": data.get("subject_title", "Untitled subject"),
        "concepts": concepts,
        "edges": clean_edges,
    }
