from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, *, session_id: str | None = None, limit: int = 50) -> list[Conversation]:
        stmt = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
        if session_id:
            stmt = stmt.where(Conversation.session_id == session_id)
        return list((await self.session.scalars(stmt)).all())

    async def get(self, conversation_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return await self.session.scalar(stmt)

    async def create(self, *, session_id: str, title: str) -> Conversation:
        conversation = Conversation(session_id=session_id, title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def cancel(self, conversation: Conversation) -> Conversation:
        conversation.status = "cancelled"
        conversation.updated_at = datetime.now(UTC)
        await self.session.flush()
        return conversation

    async def add_message(
        self,
        *,
        conversation: Conversation,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        token_count: int | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
            provider=provider,
            model=model,
            token_count=token_count,
        )
        conversation.updated_at = datetime.now(UTC)
        self.session.add(message)
        await self.session.flush()
        return message

    async def recent_messages(self, *, conversation_id: UUID, limit: int = 10) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = list((await self.session.scalars(stmt)).all())
        return list(reversed(messages))
