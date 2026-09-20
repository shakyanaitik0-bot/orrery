"""AWS Bedrock provider.

This is the whole Bedrock integration. It exists as one file because the
application talks to `LLMClient` and never to a vendor SDK directly — the
point the merge analysis made about OpenTutor's provider registry being a
clean seam.

Uses the Bedrock **Converse** API rather than per-model `invoke_model` payload
shapes, so switching between Claude, Llama or Mistral on Bedrock is a model-id
change and nothing else. boto3 is synchronous, so calls are pushed to a worker
thread to keep the event loop free.
"""

import asyncio
import logging
from typing import AsyncIterator

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import settings
from services.llm.base import LLMClient

logger = logging.getLogger("orrery.llm.bedrock")


class BedrockClient(LLMClient):
    provider_name = "bedrock"

    def __init__(self, model_id: str | None = None, small_model_id: str | None = None):
        super().__init__()
        self.model_id = model_id or settings.bedrock_model_id
        self.small_model_id = small_model_id or settings.bedrock_small_model_id

        client_kwargs: dict = {
            "region_name": settings.bedrock_region,
            "config": Config(retries={"max_attempts": 3, "mode": "adaptive"}),
        }
        # Omitted in deployment so boto3 picks up the task/instance role.
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        self._client = boto3.client("bedrock-runtime", **client_kwargs)

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _usage(response: dict, model_id: str) -> dict:
        u = response.get("usage", {}) or {}
        return {
            "provider": "bedrock",
            "model": model_id,
            "input_tokens": u.get("inputTokens", 0),
            "output_tokens": u.get("outputTokens", 0),
            "total_tokens": u.get("totalTokens", 0),
        }

    def _converse(self, model_id: str, system_prompt: str, user_message: str, max_tokens: int):
        return self._client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.6},
        )

    # -- interface -------------------------------------------------------

    async def chat(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        response = await asyncio.to_thread(
            self._converse, self.model_id, system_prompt, user_message, 2048
        )
        content = response["output"]["message"]["content"][0]["text"]
        self._last_usage = self._usage(response, self.model_id)
        return content, self._last_usage

    async def extract(self, system_prompt: str, user_message: str) -> tuple[str, dict]:
        """Routed to the small model — extraction is high-volume and cheap."""
        response = await asyncio.to_thread(
            self._converse, self.small_model_id, system_prompt, user_message, 1024
        )
        content = response["output"]["message"]["content"][0]["text"]
        self._last_usage = self._usage(response, self.small_model_id)
        return content, self._last_usage

    async def stream_chat(self, system_prompt: str, user_message: str) -> AsyncIterator[str]:
        def _open_stream():
            return self._client.converse_stream(
                modelId=self.model_id,
                system=[{"text": system_prompt}],
                messages=[{"role": "user", "content": [{"text": user_message}]}],
                inferenceConfig={"maxTokens": 2048, "temperature": 0.6},
            )

        response = await asyncio.to_thread(_open_stream)
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _pump():
            # botocore's event stream is a blocking iterator; drain it on a
            # worker thread and hand chunks back through the queue.
            try:
                for event in response["stream"]:
                    if "contentBlockDelta" in event:
                        text = event["contentBlockDelta"]["delta"].get("text", "")
                        if text:
                            loop.call_soon_threadsafe(queue.put_nowait, text)
                    elif "metadata" in event:
                        self._last_usage = self._usage(event["metadata"], self.model_id)
            except (BotoCoreError, ClientError) as exc:  # pragma: no cover
                logger.error("bedrock stream failed: %s", exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.get_running_loop().run_in_executor(None, _pump)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    async def healthcheck(self) -> bool:
        try:
            await self.extract("Reply with OK.", "ping")
            return True
        except (BotoCoreError, ClientError) as exc:
            logger.warning("bedrock unreachable: %s", exc)
            return False
