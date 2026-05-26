from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from llm_sdk.providers.base import BaseProvider
from llm_sdk.schemas import ChatMessage, InferenceResult, Usage


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None,
        allow_mock: bool = False,
        timeout_seconds: float = 30,
    ) -> None:
        self.api_key = api_key
        self.allow_mock = allow_mock
        self.timeout_seconds = timeout_seconds

    async def complete(self, *, messages: list[ChatMessage], model: str) -> InferenceResult:
        if self.allow_mock or not self.api_key:
            return self._mock_response(messages=messages, model=model)

        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "temperature": 0.3,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            self._raise_for_status(response)
            body = response.json()

        content = body["choices"][0]["message"]["content"]
        usage_body = body.get("usage") or {}
        usage = Usage(
            prompt_tokens=usage_body.get("prompt_tokens", 0),
            completion_tokens=usage_body.get("completion_tokens", 0),
            total_tokens=usage_body.get("total_tokens", 0),
        )
        return InferenceResult(
            content=content,
            provider=self.name,
            model=model,
            usage=usage,
            raw_response={"id": body.get("id"), "finish_reason": body["choices"][0].get("finish_reason")},
        )

    async def stream(self, *, messages: list[ChatMessage], model: str) -> AsyncIterator[str]:
        if self.allow_mock or not self.api_key:
            result = self._mock_response(messages=messages, model=model)
            for token in result.content.split(" "):
                yield f"{token} "
            return

        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "temperature": 0.3,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            ) as response:
                if not response.is_success:
                    await response.aread()
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    content = chunk["choices"][0].get("delta", {}).get("content")
                    if content:
                        yield content

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return

        detail = response.text[:500]
        try:
            body = response.json()
            detail = body.get("error", {}).get("message") or detail
        except ValueError:
            pass
        raise RuntimeError(f"OpenAI request failed with HTTP {response.status_code}: {detail}")

    def _mock_response(self, *, messages: list[ChatMessage], model: str) -> InferenceResult:
        if not self.allow_mock:
            raise RuntimeError("OPENAI_API_KEY is required when ALLOW_MOCK_PROVIDER is false")

        last_user_message = next((message.content for message in reversed(messages) if message.role == "user"), "")
        content = (
            "Mock OpenAI response: this provider adapter is wired through the same "
            f"inference and telemetry interfaces. User prompt: {last_user_message[:160]}"
        )
        prompt_tokens = sum(len(message.content.split()) for message in messages)
        completion_tokens = len(content.split())
        return InferenceResult(
            content=content,
            provider=self.name,
            model=model,
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            raw_response={"mock": True},
        )
