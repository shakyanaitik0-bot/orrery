"""Provider selection.

`LLM_PROVIDER=auto` (the default) tries Bedrock, then Gemini, then Ollama,
then falls back to the offline stub — whichever is reachable. Set it to
"bedrock", "gemini", "ollama", or "stub" to force one explicitly. Unless
`LLM_REQUIRED` is set, in which case a missing provider is an error rather
than a silent downgrade — a production deployment should fail loudly rather
than quietly serve stub text to a student.

Ollama is tried last in "auto" because it depends on something running on
the same machine as the API, which is the common case for local development
but not for a real deployment — Bedrock and Gemini are both remote services
reachable from anywhere, so they get first refusal.
"""

import logging

from config import settings
from services.llm.base import LLMClient, LLMConfigurationError
from services.llm.stub import StubClient

logger = logging.getLogger("orrery.llm")

_client: LLMClient | None = None


async def _try_bedrock() -> LLMClient | None:
    try:
        from services.llm.bedrock import BedrockClient

        candidate = BedrockClient()
        if await candidate.healthcheck():
            logger.info("using bedrock model %s", candidate.model_id)
            return candidate
    except Exception as exc:  # noqa: BLE001 - any failure means "not usable"
        logger.warning("bedrock unavailable: %s", exc)
    return None


async def _try_gemini() -> LLMClient | None:
    try:
        from services.llm.gemini import GeminiClient

        candidate = GeminiClient()
        if await candidate.healthcheck():
            logger.info("using gemini model %s", candidate.model_id)
            return candidate
    except Exception as exc:  # noqa: BLE001 - any failure means "not usable"
        logger.warning("gemini unavailable: %s", exc)
    return None


async def _try_ollama() -> LLMClient | None:
    try:
        from services.llm.ollama import OllamaClient

        candidate = OllamaClient()
        if await candidate.healthcheck():
            logger.info("using ollama model %s", candidate.model_id)
            return candidate
    except Exception as exc:  # noqa: BLE001 - any failure means "not usable"
        logger.warning("ollama unavailable: %s", exc)
    return None


_PROVIDERS = {"bedrock": _try_bedrock, "gemini": _try_gemini, "ollama": _try_ollama}


async def get_client() -> LLMClient:
    global _client
    if _client is not None:
        return _client

    provider = settings.llm_provider.lower()

    if provider == "stub":
        _client = StubClient()
        return _client

    if provider in _PROVIDERS:
        candidate = await _PROVIDERS[provider]()
        if candidate is not None:
            _client = candidate
            return _client
        if settings.llm_required:
            raise LLMConfigurationError(
                f"LLM_REQUIRED is set but the configured provider '{provider}' is not usable"
            )
    elif provider == "auto":
        for try_provider in (_try_bedrock, _try_gemini, _try_ollama):
            candidate = await try_provider()
            if candidate is not None:
                _client = candidate
                return _client
        if settings.llm_required:
            raise LLMConfigurationError(
                "LLM_REQUIRED is set but no provider (Bedrock, Gemini, Ollama) is usable"
            )
    else:
        raise LLMConfigurationError(f"Unknown LLM_PROVIDER '{provider}'")

    logger.warning("no LLM provider reachable — falling back to offline stub")
    _client = StubClient()
    return _client


def reset() -> None:
    """Drop the cached client. Used by tests and after a config change."""
    global _client
    _client = None
