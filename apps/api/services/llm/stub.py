"""Offline stand-in used when no real provider is configured.

Keeps the app demoable with no AWS account and no Gemini key. It is
selected only when `LLM_REQUIRED` is false, and it says plainly in its own
output that it is not a real model, so a stub response can never be
mistaken for tutoring.

`extract` gets a second mode: when the caller is clearly asking for the
ingestion pipeline's concept-graph JSON (see `services/learning/ingest.py`),
it returns a real, valid graph built by a naive sentence split rather than
placeholder prose — a real LLM does better, but the ingestion pipeline stays
exercisable end-to-end without AWS credentials, matching the rest of the app.
"""

import asyncio
import json
import re
from typing import AsyncIterator

from services.llm.base import LLMClient


class StubClient(LLMClient):
    provider_name = "stub"

    def _compose(self, user_message: str) -> str:
        return (
            f"[offline stub — no LLM provider configured]\n\n"
            f"A tutor response to “{user_message.strip()[:120]}” would appear here. "
            f"Set AWS credentials for Bedrock, GEMINI_API_KEY for the free "
            f"Gemini option, or run Ollama locally with no account at all, "
            f"to route this through a real model; the request path is "
            f"otherwise identical."
        )

    def _fake_concept_graph(self, text: str) -> str:
        # Split on sentence boundaries, drop fragments too short to be a
        # concept on their own, cap it so the graph stays readable.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]
        sentences = sentences[:8] or [text[:120] or "This subject"]

        concepts = []
        for i, sentence in enumerate(sentences):
            words = re.findall(r"[A-Za-z][A-Za-z\-]*", sentence)
            title = " ".join(words[:4]).title() or f"Concept {i + 1}"
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or f"concept-{i}"
            concepts.append({"slug": slug, "title": title, "summary": sentence[:160]})

        # Naive but valid: chain each sentence's idea after the previous one.
        edges = [
            {"source": concepts[i]["slug"], "target": concepts[i + 1]["slug"]}
            for i in range(len(concepts) - 1)
        ]

        return json.dumps(
            {
                "subject_title": "Untitled subject (offline stub)",
                "concepts": concepts,
                "edges": edges,
            }
        )

    async def chat(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        usage = {"provider": "stub", "model": "stub", "input_tokens": 0, "output_tokens": 0}
        self._last_usage = usage
        return self._compose(user_message), usage

    def _fake_quiz(self, material: str) -> str:
        subject = material.split("\n", 1)[0].removeprefix("Concept:").strip() or "this concept"
        return json.dumps(
            {
                "questions": [
                    {
                        "type": "mcq",
                        "prompt": f"[offline stub] Which of these names the concept you are studying?",
                        "options": [subject, "An unrelated idea", "None of these"],
                        "answer": subject,
                        "explanation": "A real model would ask something worth answering here.",
                    },
                    {
                        "type": "short",
                        "prompt": f"[offline stub] Name the concept you are studying.",
                        "answer": subject,
                        "accept": [],
                        "explanation": "Configure a provider to get real questions.",
                    },
                ]
            }
        )

    async def extract(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        usage = {"provider": "stub", "model": "stub", "input_tokens": 0, "output_tokens": 0}
        self._last_usage = usage
        if "concepts" in system_prompt and "edges" in system_prompt:
            return self._fake_concept_graph(user_message), usage
        if "quizzes" in system_prompt and "questions" in system_prompt:
            return self._fake_quiz(user_message), usage
        return self._compose(user_message), usage

    async def stream_chat(self, system_prompt: str, user_message: str) -> AsyncIterator[str]:
        for word in self._compose(user_message).split(" "):
            await asyncio.sleep(0.015)
            yield word + " "
        self._last_usage = {"provider": "stub", "model": "stub", "output_tokens": 0}
