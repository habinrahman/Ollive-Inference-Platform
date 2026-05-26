from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from llm_sdk.schemas import ChatMessage, InferenceResult


class BaseProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, *, messages: list[ChatMessage], model: str) -> InferenceResult:
        """Return a full completion response."""

    @abstractmethod
    async def stream(self, *, messages: list[ChatMessage], model: str) -> AsyncIterator[str]:
        """Yield completion chunks as they arrive from the provider."""
