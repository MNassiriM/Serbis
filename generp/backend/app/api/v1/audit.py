"""
Audit Logs API — view tenant audit trail.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentTenant, DBSession
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit-logs", tags=["audit"])


def _serialize(log: Any) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "tenant_id": str(log.tenant_id),
        "entity": log.entity,
        "record_id": log.record_id,
        "action": log.action.value if hasattr(log.action, "value") else str(log.action),
        "old_data": log.old_data,
        "new_data": log.new_data,
        "performed_by": str(log.performed_by) if log.performed_by else None,
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }


@router.get("")
async def list_audit_logs(
    current_tenant: CurrentTenant,
    db: DBSession,
    entity: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    svc = AuditService(db)
    logs = await svc.get_tenant_logs(
        tenant_id=current_tenant.id,
        entity=entity,
        limit=limit,
        offset=offset,
    )
    return [_serialize(log) for log in logs]


@router.get("/{entity}/{record_id}")
async def get_record_history(
    entity: str,
    record_id: str,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> list[dict[str, Any]]:
    svc = AuditService(db)
    logs = await svc.get_record_history(
        tenant_id=current_tenant.id,
        entity=entity,
        record_id=record_id,
    )
    return [_serialize(log) for log in logs]
