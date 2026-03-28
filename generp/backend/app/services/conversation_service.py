"""Conversation service — manages conversation history per tenant."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message


class ConversationService:
    """Handles conversation and message persistence."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create_conversation(
        self,
        tenant_id: uuid.UUID,
        conversation_id: str | None,
        title: str = "New conversation",
    ) -> Conversation:
        """Return existing conversation or create a new one."""
        if conversation_id:
            result = await self._db.execute(
                select(Conversation).where(
                    Conversation.id == uuid.UUID(conversation_id),
                    Conversation.tenant_id == tenant_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        conversation = Conversation(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title=title,
        )
        self._db.add(conversation)
        await self._db.flush()
        return conversation

    async def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Append a message to a conversation."""
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self._db.add(message)
        await self._db.flush()
        return message

    async def get_conversation_history(
        self, conversation_id: uuid.UUID, limit: int = 50
    ) -> list[dict[str, str]]:
        """
        Return the last N messages in LangChain-compatible format.
        [{"role": "user"|"assistant", "content": "..."}]
        """
        result = await self._db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in messages]

    async def get_pending_schema(
        self, conversation_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """
        Retrieve the most recent pending schema stored in message metadata.
        Used to persist schema between the generation and confirmation steps.
        """
        result = await self._db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
            )
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        messages = result.scalars().all()

        for message in messages:
            meta = message.metadata or {}
            if "pending_schema" in meta:
                return meta["pending_schema"]  # type: ignore[return-value]

        return None

    async def list_conversations(
        self, tenant_id: uuid.UUID, limit: int = 20
    ) -> list[Conversation]:
        """List conversations for a tenant, newest first."""
        result = await self._db.execute(
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def commit(self) -> None:
        """Commit pending changes."""
        await self._db.commit()
