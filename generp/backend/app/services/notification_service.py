"""Notification service — CRUD for tenant notifications."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles creation and management of notifications."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        tenant_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        entity: Optional[str] = None,
        record_id: Optional[str] = None,
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            entity=entity,
            record_id=record_id,
        )
        self._db.add(notification)
        await self._db.commit()
        await self._db.refresh(notification)
        logger.info("Created notification %s for tenant %s", notification.id, tenant_id)
        return notification

    async def list_for_tenant(
        self,
        tenant_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """List notifications for a tenant."""
        stmt = (
            select(Notification)
            .where(Notification.tenant_id == tenant_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if unread_only:
            stmt = stmt.where(Notification.read.is_(False))
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def mark_read(self, notification_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Mark a single notification as read. Returns True if found."""
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
            )
            .values(read=True)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, tenant_id: uuid.UUID) -> int:
        """Mark all notifications for a tenant as read. Returns count updated."""
        stmt = (
            update(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.read.is_(False),
            )
            .values(read=True)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount

    async def unread_count(self, tenant_id: uuid.UUID) -> int:
        """Return the count of unread notifications for a tenant."""
        stmt = select(func.count(Notification.id)).where(
            Notification.tenant_id == tenant_id,
            Notification.read.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one() or 0

    async def delete(self, notification_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Delete a notification. Returns True if deleted."""
        result = await self._db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
            )
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            return False
        await self._db.delete(notification)
        await self._db.commit()
        return True
