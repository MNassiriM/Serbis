"""
Notifications API — manage tenant notifications.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.dependencies import DBSession, get_current_tenant
from app.models.notification import NotificationType
from app.models.tenant import Tenant
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str]
    type: str
    title: str
    body: Optional[str]
    read: bool
    entity: Optional[str]
    record_id: Optional[str]
    created_at: Any

    @classmethod
    def from_model(cls, n: Any) -> "NotificationResponse":
        return cls(
            id=str(n.id),
            tenant_id=str(n.tenant_id),
            user_id=str(n.user_id) if n.user_id else None,
            type=n.type.value if hasattr(n.type, "value") else str(n.type),
            title=n.title,
            body=n.body,
            read=n.read,
            entity=n.entity,
            record_id=n.record_id,
            created_at=n.created_at,
        )


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50),
    db: DBSession = DBSession,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    svc = NotificationService(db)
    notifications = await svc.list_for_tenant(
        tenant_id=current_tenant.id,
        unread_only=unread_only,
        limit=limit,
    )
    return [NotificationResponse.from_model(n).model_dump() for n in notifications]


@router.get("/count")
async def get_unread_count(
    db: DBSession = DBSession,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, int]:
    svc = NotificationService(db)
    count = await svc.unread_count(tenant_id=current_tenant.id)
    return {"unread": count}


@router.post("/read-all")
async def mark_all_read(
    db: DBSession = DBSession,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, int]:
    svc = NotificationService(db)
    count = await svc.mark_all_read(tenant_id=current_tenant.id)
    return {"updated": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: DBSession = DBSession,
    current_tenant: Tenant = Depends(get_current_tenant),
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
    db: DBSession = DBSession,
    current_tenant: Tenant = Depends(get_current_tenant),
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
