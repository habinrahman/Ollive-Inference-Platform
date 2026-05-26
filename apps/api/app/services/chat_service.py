from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import HTTPException
from llm_sdk import ChatMessage as SDKMessage
from llm_sdk import InferenceClient
from llm_sdk import redact_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_context import get_request_id, get_trace_id
from app.models.chat import Conversation
from app.repositories.conversations import ConversationRepository
from app.schemas.chat import ChatMessageOut, ChatRequest, ChatResponse, ConversationOut

SYSTEM_PROMPT = (
    "You are a concise assistant running inside Ollive's inference observability demo. "
    "Answer the user normally; platform telemetry is captured outside the prompt."
)

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, *, session: AsyncSession, inference_client: InferenceClient) -> None:
        self.session = session
        self.conversations = ConversationRepository(session)
        self.inference_client = inference_client

    async def list_conversations(self, *, session_id: str | None = None) -> list[Conversation]:
        return await self.conversations.list(session_id=session_id)

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = await self.conversations.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    async def cancel_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = await self.get_conversation(conversation_id)
        await self.conversations.cancel(conversation)
        await self.session.commit()
        return conversation

    async def complete(self, request: ChatRequest) -> ChatResponse:
        conversation = await self._get_or_create_conversation(request)
        user_message = await self.conversations.add_message(
            conversation=conversation,
            role="user",
            content=request.message,
            token_count=len(request.message.split()),
        )
        await self.session.commit()
        messages = await self._build_context(conversation.id)
        selected_provider, selected_model = self.inference_client.resolve(
            provider_name=request.provider,
            model=request.model,
        )
        logger.info(
            "inference_started",
            extra={
                "request_id": get_request_id(),
                "trace_id": get_trace_id(),
                "conversation_id": str(conversation.id),
                "provider": selected_provider,
                "model": selected_model,
                "transport": "json",
            },
        )
        try:
            result = await self.inference_client.complete(
                messages=messages,
                provider_name=request.provider,
                model=request.model,
                conversation_id=str(conversation.id),
                session_id=conversation.session_id,
                trace_id=get_trace_id(),
                request_id=get_request_id(),
                correlation_id=str(conversation.id),
                metadata={"transport": "json"},
            )
        except Exception as exc:
            logger.exception(
                "inference_failed",
                extra={
                    "request_id": get_request_id(),
                    "trace_id": get_trace_id(),
                    "conversation_id": str(conversation.id),
                    "provider": selected_provider,
                    "model": selected_model,
                    "transport": "json",
                },
            )
            raise HTTPException(status_code=502, detail="Inference provider request failed") from exc
        assistant_message = await self.conversations.add_message(
            conversation=conversation,
            role="assistant",
            content=result.content,
            provider=result.provider,
            model=result.model,
            token_count=result.usage.completion_tokens,
        )
        await self.session.commit()
        logger.info(
            "inference_completed",
            extra={
                "request_id": get_request_id(),
                "trace_id": get_trace_id(),
                "conversation_id": str(conversation.id),
                "provider": result.provider,
                "model": result.model,
                "tokens": result.usage.total_tokens,
                "transport": "json",
            },
        )
        return ChatResponse(
            conversation=ConversationOut.model_validate(conversation),
            user_message=ChatMessageOut.model_validate(user_message),
            assistant_message=ChatMessageOut.model_validate(assistant_message),
        )

    async def stream(
        self,
        request: ChatRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> AsyncIterator[str]:
        conversation = await self._get_or_create_conversation(request)
        user_message = await self.conversations.add_message(
            conversation=conversation,
            role="user",
            content=request.message,
            token_count=len(request.message.split()),
        )
        await self.session.commit()
        conversation_id = str(conversation.id)
        session_id = conversation.session_id
        yield self._sse(
            "conversation",
            {
                "conversation": ConversationOut.model_validate(conversation).model_dump(mode="json"),
                "user_message": ChatMessageOut.model_validate(user_message).model_dump(mode="json"),
            },
        )

        messages = await self._build_context(conversation.id)
        chunks: list[str] = []
        provider, model = self.inference_client.resolve(provider_name=request.provider, model=request.model)
        logger.info(
            "inference_started",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "provider": provider,
                "model": model,
                "transport": "sse",
            },
        )
        try:
            async for chunk in self.inference_client.stream(
                messages=messages,
                provider_name=provider,
                model=model,
                conversation_id=conversation_id,
                session_id=session_id,
                trace_id=trace_id,
                request_id=request_id,
                correlation_id=conversation_id,
                metadata={"transport": "sse"},
            ):
                chunks.append(chunk)
                yield self._sse("token", {"token": chunk})

            content = "".join(chunks)
            assistant_message = await self.conversations.add_message(
                conversation=conversation,
                role="assistant",
                content=content,
                provider=provider,
                model=model,
                token_count=len(content.split()),
            )
            await self.session.commit()
            logger.info(
                "inference_completed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "provider": provider,
                    "model": model,
                    "tokens": len(content.split()),
                    "transport": "sse",
                },
            )
            yield self._sse(
                "done",
                {"assistant_message": ChatMessageOut.model_validate(assistant_message).model_dump(mode="json")},
            )
        except Exception as exc:
            await self.session.rollback()
            logger.exception(
                "inference_failed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "provider": provider,
                    "model": model,
                },
            )
            yield self._sse("error", {"message": "Inference provider request failed", "detail": str(exc)})

    async def _get_or_create_conversation(self, request: ChatRequest) -> Conversation:
        if request.conversation_id:
            conversation = await self.conversations.get(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if conversation.status == "cancelled":
                raise HTTPException(status_code=409, detail="Conversation is cancelled")
            return conversation

        title = redact_text(request.message.strip().replace("\n", " ")[:80]) or "Untitled conversation"
        return await self.conversations.create(session_id=request.session_id, title=title)

    async def _build_context(self, conversation_id: UUID) -> list[SDKMessage]:
        recent_messages = await self.conversations.recent_messages(conversation_id=conversation_id, limit=10)
        messages = [SDKMessage(role="system", content=SYSTEM_PROMPT)]
        messages.extend(SDKMessage(role=message.role, content=message.content) for message in recent_messages)
        return messages

    @staticmethod
    def _sse(event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
