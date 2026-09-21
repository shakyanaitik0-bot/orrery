"""Provider selection.

`LLM_PROVIDER=auto` (the default) tries Bedrock, then Gemini, then falls
back to the offline stub — whichever is reachable. Set it to "bedrock",
"gemini", or "stub" to force one explicitly. Unless `LLM_REQUIRED` is set,
in which case a missing provider is an error rather than a silent
downgrade — a production deployment should fail loudly rather than quietly
serve stub text to a student.
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


_PROVIDERS = {"bedrock": _try_bedrock, "gemini": _try_gemini}


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
        for try_provider in (_try_bedrock, _try_gemini):
            candidate = await try_provider()
            if candidate is not None:
                _client = candidate
                return _client
        if settings.llm_required:
            raise LLMConfigurationError(
                "LLM_REQUIRED is set but no provider (Bedrock, Gemini) is usable"
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
