"""Google Gemini provider — a free-tier alternative to Bedrock.

Same shape as bedrock.py: this is the whole integration, talking to
`LLMClient` and nothing else calling into a vendor SDK directly. Gemini's
REST API is used directly over HTTPS (via httpx, natively async — no worker
thread needed, unlike boto3) rather than pulling in Google's SDK for three
endpoints.

Get a free API key at https://aistudio.google.com/apikey — no billing
account required for the free tier's rate limits.
"""

import json
import logging
from typing import AsyncIterator

import httpx

from config import settings
from services.llm.base import LLMClient

logger = logging.getLogger("orrery.llm.gemini")

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient(LLMClient):
    provider_name = "gemini"

    def __init__(self, model_id: str | None = None, small_model_id: str | None = None):
        super().__init__()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self.api_key = settings.gemini_api_key
        self.model_id = model_id or settings.gemini_model_id
        self.small_model_id = small_model_id or settings.gemini_small_model_id

    @staticmethod
    def _usage(payload: dict, model_id: str) -> dict:
        u = payload.get("usageMetadata", {}) or {}
        return {
            "provider": "gemini",
            "model": model_id,
            "input_tokens": u.get("promptTokenCount", 0),
            "output_tokens": u.get("candidatesTokenCount", 0),
            "total_tokens": u.get("totalTokenCount", 0),
        }

    def _body(self, system_prompt: str, user_message: str, max_tokens: int) -> dict:
        return {
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.6},
        }

    @staticmethod
    def _text(payload: dict) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)

    async def _generate(self, model_id: str, system_prompt: str, user_message: str, max_tokens: int) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{_BASE_URL}/{model_id}:generateContent",
                params={"key": self.api_key},
                json=self._body(system_prompt, user_message, max_tokens),
            )
            response.raise_for_status()
            return response.json()

    async def chat(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        payload = await self._generate(self.model_id, system_prompt, user_message, 2048)
        self._last_usage = self._usage(payload, self.model_id)
        return self._text(payload), self._last_usage

    async def extract(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        """Routed to the small model — extraction is high-volume and cheap."""
        payload = await self._generate(self.small_model_id, system_prompt, user_message, 1024)
        self._last_usage = self._usage(payload, self.small_model_id)
        return self._text(payload), self._last_usage

    async def stream_chat(self, system_prompt: str, user_message: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{_BASE_URL}/{self.model_id}:streamGenerateContent",
                params={"key": self.api_key, "alt": "sse"},
                json=self._body(system_prompt, user_message, 2048),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = json.loads(line[len("data: "):])
                    text = self._text(payload)
                    if text:
                        yield text
                    if "usageMetadata" in payload:
                        self._last_usage = self._usage(payload, self.model_id)

    async def healthcheck(self) -> bool:
        try:
            await self.extract("Reply with OK.", "ping")
            return True
        except httpx.HTTPError as exc:
            logger.warning("gemini unreachable: %s", exc)
            return False
