"""Offline stand-in used when Bedrock has no credentials.

Keeps the app demoable on a laptop with no AWS account. It is selected only
when `LLM_REQUIRED` is false, and it says plainly in its own output that it is
not a real model, so a stub response can never be mistaken for tutoring.
"""

import asyncio
from typing import AsyncIterator

from services.llm.base import LLMClient


class StubClient(LLMClient):
    provider_name = "stub"

    def _compose(self, user_message: str) -> str:
        return (
            f"[offline stub — no Bedrock credentials configured]\n\n"
            f"A tutor response to “{user_message.strip()[:120]}” would appear here. "
            f"Set AWS credentials and BEDROCK_MODEL_ID to route this through "
            f"Bedrock; the request path is otherwise identical."
        )

    async def chat(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        usage = {"provider": "stub", "model": "stub", "input_tokens": 0, "output_tokens": 0}
        self._last_usage = usage
        return self._compose(user_message), usage

    async def extract(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        return await self.chat(system_prompt, user_message)

    async def stream_chat(self, system_prompt: str, user_message: str) -> AsyncIterator[str]:
        for word in self._compose(user_message).split(" "):
            await asyncio.sleep(0.015)
            yield word + " "
        self._last_usage = {"provider": "stub", "model": "stub", "output_tokens": 0}
