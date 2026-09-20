"""The LLM interface every provider implements.

Kept deliberately identical in shape to OpenTutor's `LLMClient` — three
methods, `chat`, `stream_chat` and `extract`, each returning usage alongside
content. That interface is why adding Bedrock is a single new file rather than
a refactor: the rest of the application only ever sees this abstract class.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMClient(ABC):
    """Base class for all providers."""

    provider_name: str = "base"

    def __init__(self) -> None:
        self._last_usage: dict = {}

    def get_last_usage(self) -> dict:
        """Usage from the most recent call. Populated after streaming too."""
        return self._last_usage

    @abstractmethod
    async def chat(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        """One complete response. Returns (content, usage)."""

    @abstractmethod
    async def stream_chat(self, system_prompt: str, user_message: str) -> AsyncIterator[str]:
        """Response streamed in chunks. Usage lands in `_last_usage`."""
        raise NotImplementedError
        yield ""  # pragma: no cover - makes this an async generator

    @abstractmethod
    async def extract(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        """A short, cheap, non-conversational call — classification, tagging,
        pulling concepts out of a document. Routed to a smaller model."""


class LLMConfigurationError(RuntimeError):
    """No usable provider is configured."""
