from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from llm_sdk import InferenceClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_inference_client
from app.core.request_context import get_request_id, get_trace_id
from app.db.session import get_session
from app.schemas.chat import ChatRequest, ChatResponse, ConversationDetail, ConversationOut
from app.services.chat_service import ChatService

router = APIRouter(prefix="/v1", tags=["chat"])


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    session_id: str | None = None,
    db: AsyncSession = Depends(get_session),
    inference_client: InferenceClient = Depends(get_inference_client),
) -> list[ConversationOut]:
    service = ChatService(session=db, inference_client=inference_client)
    conversations = await service.list_conversations(session_id=session_id)
    return [ConversationOut.model_validate(conversation) for conversation in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session),
    inference_client: InferenceClient = Depends(get_inference_client),
) -> ConversationDetail:
    service = ChatService(session=db, inference_client=inference_client)
    conversation = await service.get_conversation(conversation_id)
    return ConversationDetail.model_validate(conversation)


@router.post("/conversations/{conversation_id}/cancel", response_model=ConversationOut)
async def cancel_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session),
    inference_client: InferenceClient = Depends(get_inference_client),
) -> ConversationOut:
    service = ChatService(session=db, inference_client=inference_client)
    conversation = await service.cancel_conversation(conversation_id)
    return ConversationOut.model_validate(conversation)


@router.post("/chat", response_model=ChatResponse)
async def create_chat_completion(
    request: ChatRequest,
    db: AsyncSession = Depends(get_session),
    inference_client: InferenceClient = Depends(get_inference_client),
) -> ChatResponse:
    service = ChatService(session=db, inference_client=inference_client)
    return await service.complete(request)


@router.post("/chat/stream")
async def stream_chat_completion(
    request: ChatRequest,
    db: AsyncSession = Depends(get_session),
    inference_client: InferenceClient = Depends(get_inference_client),
) -> StreamingResponse:
    service = ChatService(session=db, inference_client=inference_client)
    return StreamingResponse(
        service.stream(request, request_id=get_request_id(), trace_id=get_trace_id()),
        media_type="text/event-stream",
    )
