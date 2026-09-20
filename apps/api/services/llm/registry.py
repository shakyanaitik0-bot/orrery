"""Provider selection.

Bedrock when it is reachable, the offline stub otherwise — unless
`LLM_REQUIRED` is set, in which case a missing provider is an error rather
than a silent downgrade. That distinction is the one thing OpenTutor got
right here and it is worth keeping: a production deployment should fail loudly
rather than quietly serve stub text to a student.
"""

import logging

from config import settings
from services.llm.base import LLMClient, LLMConfigurationError
from services.llm.stub import StubClient

logger = logging.getLogger("orrery.llm")

_client: LLMClient | None = None


async def get_client() -> LLMClient:
    global _client
    if _client is not None:
        return _client

    try:
        from services.llm.bedrock import BedrockClient

        candidate = BedrockClient()
        if await candidate.healthcheck():
            logger.info("using bedrock model %s", candidate.model_id)
            _client = candidate
            return _client
        raise RuntimeError("bedrock healthcheck failed")
    except Exception as exc:  # noqa: BLE001 - any failure means "not usable"
        if settings.llm_required:
            raise LLMConfigurationError(
                f"LLM_REQUIRED is set but Bedrock is not usable: {exc}"
            ) from exc
        logger.warning("bedrock unavailable (%s) — falling back to offline stub", exc)

    _client = StubClient()
    return _client


def reset() -> None:
    """Drop the cached client. Used by tests and after a config change."""
    global _client
    _client = None
