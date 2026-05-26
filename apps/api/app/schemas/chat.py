from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None
    session_id: str = Field(default="local-session", max_length=128)
    provider: Literal["gemini", "openai"] = "gemini"
    model: str | None = None


class ChatMessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    provider: str | None = None
    model: str | None = None
    token_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: UUID
    session_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[ChatMessageOut]


class ChatResponse(BaseModel):
    conversation: ConversationOut
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
