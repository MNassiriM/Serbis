"""Audit service — immutable audit trail for tenant operations."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Handles creation and querying of audit log entries."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        tenant_id: uuid.UUID,
        entity: str,
        record_id: str,
        action: AuditAction,
        old_data: Optional[dict[str, Any]] = None,
        new_data: Optional[dict[str, Any]] = None,
        performed_by: Optional[uuid.UUID] = None,
        ip: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            tenant_id=tenant_id,
            entity=entity,
            record_id=record_id,
            action=action,
            old_data=old_data,
            new_data=new_data,
            performed_by=performed_by,
            ip_address=ip,
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def get_record_history(
        self,
        tenant_id: uuid.UUID,
        entity: str,
        record_id: str,
    ) -> list[AuditLog]:
        """Return all audit entries for a specific record, ordered by time."""
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.entity == entity,
                AuditLog.record_id == record_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_tenant_logs(
        self,
        tenant_id: uuid.UUID,
        entity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit log entries for a tenant with optional entity filter."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if entity:
            stmt = stmt.where(AuditLog.entity == entity)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
