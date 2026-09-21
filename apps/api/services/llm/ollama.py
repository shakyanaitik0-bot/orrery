"""Ollama provider — a fully offline, no-account option.

Ported from AI Tutor (MIT): that project's model discovery normalised three
different response shapes the `ollama` Python client has returned across
versions, which is exactly the kind of small compatibility work worth
reusing rather than re-deriving. Everything else here — the request/response
handling — follows bedrock.py and gemini.py's shape, since Ollama's REST API
(no API key, runs on the developer's own machine) needs the same three
methods and nothing from a vendor SDK.

Requires Ollama (https://ollama.com) running locally with at least one model
pulled — `ollama pull llama3` — which is the whole cost of this path: no AWS
account, no API key, no per-token bill, at the price of running on your own
hardware.
"""

import json
import logging
from typing import AsyncIterator

import httpx

from config import settings
from services.llm.base import LLMClient

logger = logging.getLogger("orrery.llm.ollama")


class OllamaClient(LLMClient):
    provider_name = "ollama"

    def __init__(self, model_id: str | None = None, small_model_id: str | None = None):
        super().__init__()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model_id = model_id or settings.ollama_model_id
        self.small_model_id = small_model_id or settings.ollama_small_model_id or self.model_id

    @staticmethod
    def _usage(payload: dict, model_id: str) -> dict:
        return {
            "provider": "ollama",
            "model": model_id,
            "input_tokens": payload.get("prompt_eval_count", 0),
            "output_tokens": payload.get("eval_count", 0),
        }

    async def chat(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
        self._last_usage = self._usage(payload, self.model_id)
        return payload.get("message", {}).get("content", ""), self._last_usage

    async def extract(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        """Routed to the small model when one is configured, same as the
        other providers — a local box benefits even more from a smaller
        model for high-volume, non-conversational calls."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.small_model_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
        self._last_usage = self._usage(payload, self.small_model_id)
        return payload.get("message", {}).get("content", ""), self._last_usage

    async def stream_chat(self, system_prompt: str, user_message: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    text = payload.get("message", {}).get("content", "")
                    if text:
                        yield text
                    if payload.get("done"):
                        self._last_usage = self._usage(payload, self.model_id)

    async def healthcheck(self) -> bool:
        """Confirms Ollama is reachable AND the configured model is actually
        pulled — a running server with the wrong model name is as unusable
        as no server at all, and should fall through to the next provider
        the same way."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                available = {m["name"] for m in response.json().get("models", [])}
        except httpx.HTTPError as exc:
            logger.warning("ollama unreachable: %s", exc)
            return False

        # Ollama tags carry a ":latest" suffix that a bare model name omits.
        def _matches(name: str) -> bool:
            return name in available or f"{name}:latest" in available

        if not _matches(self.model_id):
            logger.warning(
                "ollama is running but model '%s' is not pulled (pull it with "
                "`ollama pull %s`)",
                self.model_id,
                self.model_id,
            )
            return False
        return True
