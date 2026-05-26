from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from llm_sdk.providers.base import BaseProvider
from llm_sdk.schemas import ChatMessage, InferenceResult, Usage


class GeminiProvider(BaseProvider):
    name = "gemini"

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

        payload = self._payload(messages)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self._url(model, action="generateContent"),
                headers=self._headers(),
                json=payload,
            )
            self._raise_for_status(response)
            body = response.json()

        content = self._extract_text(body)
        usage_body = body.get("usageMetadata") or {}
        usage = Usage(
            prompt_tokens=usage_body.get("promptTokenCount", 0),
            completion_tokens=usage_body.get("candidatesTokenCount", 0),
            total_tokens=usage_body.get("totalTokenCount", 0),
        )
        return InferenceResult(
            content=content,
            provider=self.name,
            model=model,
            usage=usage,
            raw_response={
                "finish_reason": (body.get("candidates") or [{}])[0].get("finishReason"),
                "usage_metadata": usage_body,
            },
        )

    async def stream(self, *, messages: list[ChatMessage], model: str) -> AsyncIterator[str]:
        if self.allow_mock or not self.api_key:
            result = self._mock_response(messages=messages, model=model)
            for token in result.content.split(" "):
                yield f"{token} "
            return

        payload = self._payload(messages)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream(
                "POST",
                self._url(model, action="streamGenerateContent", stream=True),
                headers=self._headers(),
                json=payload,
            ) as response:
                if not response.is_success:
                    await response.aread()
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if not data:
                        continue
                    chunk = json.loads(data)
                    text = self._extract_text(chunk)
                    if text:
                        yield text

    def _url(self, model: str, *, action: str, stream: bool = False) -> str:
        suffix = "?alt=sse" if stream else ""
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{action}{suffix}"

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key or ""}

    def _payload(self, messages: list[ChatMessage]) -> dict:
        system_parts = [
            {"text": message.content}
            for message in messages
            if message.role == "system" and message.content
        ]
        contents = [
            {
                "role": "model" if message.role == "assistant" else "user",
                "parts": [{"text": message.content}],
            }
            for message in messages
            if message.role != "system" and message.content
        ]
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        return payload

    @staticmethod
    def _extract_text(body: dict) -> str:
        candidates = body.get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts") or []
        return "".join(part.get("text", "") for part in parts)

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
        raise RuntimeError(f"Gemini request failed with HTTP {response.status_code}: {detail}")

    def _mock_response(self, *, messages: list[ChatMessage], model: str) -> InferenceResult:
        if not self.allow_mock:
            raise RuntimeError("GEMINI_API_KEY is required when ALLOW_MOCK_PROVIDER is false")

        last_user_message = next((message.content for message in reversed(messages) if message.role == "user"), "")
        content = (
            "Mock Gemini response: this provider adapter is wired through the same "
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
