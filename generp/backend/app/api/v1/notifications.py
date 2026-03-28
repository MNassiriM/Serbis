"""
Notifications API — manage tenant notifications.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import CurrentTenant, DBSession
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(n: Any) -> dict[str, Any]:
    return {
        "id": str(n.id),
        "tenant_id": str(n.tenant_id),
        "user_id": str(n.user_id) if n.user_id else None,
        "type": n.type.value if hasattr(n.type, "value") else str(n.type),
        "title": n.title,
        "body": n.body,
        "read": n.read,
        "entity": n.entity,
        "record_id": n.record_id,
        "created_at": n.created_at,
    }


@router.get("")
async def list_notifications(
    current_tenant: CurrentTenant,
    db: DBSession,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    svc = NotificationService(db)
    notifications = await svc.list_for_tenant(
        tenant_id=current_tenant.id,
        unread_only=unread_only,
        limit=limit,
    )
    return [_serialize(n) for n in notifications]


@router.get("/count")
async def get_unread_count(
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, int]:
    svc = NotificationService(db)
    count = await svc.unread_count(tenant_id=current_tenant.id)
    return {"unread": count}


@router.post("/read-all")
async def mark_all_read(
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, int]:
    svc = NotificationService(db)
    count = await svc.mark_all_read(tenant_id=current_tenant.id)
    return {"updated": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, bool]:
    svc = NotificationService(db)
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")
    found = await svc.mark_read(notification_id=nid, tenant_id=current_tenant.id)
    if not found:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, bool]:
    svc = NotificationService(db)
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")
    deleted = await svc.delete(notification_id=nid, tenant_id=current_tenant.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"deleted": True}
