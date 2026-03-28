"""
Workflows API — CRUD and simulation of tenant workflows.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import CurrentTenant, DBSession
from app.models.workflow import WorkflowTrigger
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger: WorkflowTrigger
    conditions: list[Any] = []
    actions: list[Any] = []
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger: Optional[WorkflowTrigger] = None
    conditions: Optional[list[Any]] = None
    actions: Optional[list[Any]] = None
    is_active: Optional[bool] = None


class WorkflowTestRequest(BaseModel):
    entity: str
    record_data: dict[str, Any]


def _serialize(wf: Any) -> dict[str, Any]:
    return {
        "id": str(wf.id),
        "tenant_id": str(wf.tenant_id),
        "name": wf.name,
        "description": wf.description,
        "trigger": wf.trigger.value if hasattr(wf.trigger, "value") else str(wf.trigger),
        "conditions": wf.conditions,
        "actions": wf.actions,
        "is_active": wf.is_active,
        "created_at": wf.created_at,
        "updated_at": wf.updated_at,
    }


@router.get("")
async def list_workflows(
    current_tenant: CurrentTenant,
    db: DBSession,
) -> list[dict[str, Any]]:
    svc = WorkflowService(db)
    workflows = await svc.list_for_tenant(tenant_id=current_tenant.id)
    return [_serialize(wf) for wf in workflows]


@router.post("", status_code=201)
async def create_workflow(
    payload: WorkflowCreate,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, Any]:
    svc = WorkflowService(db)
    wf = await svc.create(
        tenant_id=current_tenant.id,
        name=payload.name,
        trigger=payload.trigger,
        conditions=payload.conditions,
        actions=payload.actions,
        description=payload.description,
    )
    return _serialize(wf)


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, Any]:
    svc = WorkflowService(db)
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
    wf = await svc.get(workflow_id=wid, tenant_id=current_tenant.id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _serialize(wf)


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, Any]:
    svc = WorkflowService(db)
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
    try:
        wf = await svc.update(
            workflow_id=wid,
            tenant_id=current_tenant.id,
            **{k: v for k, v in payload.model_dump().items() if v is not None},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize(wf)


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, bool]:
    svc = WorkflowService(db)
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
    deleted = await svc.delete(workflow_id=wid, tenant_id=current_tenant.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"deleted": True}


@router.post("/{workflow_id}/test")
async def test_workflow(
    workflow_id: str,
    payload: WorkflowTestRequest,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> dict[str, Any]:
    """Simulate a workflow trigger and return which actions would fire."""
    svc = WorkflowService(db)
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    wf = await svc.get(workflow_id=wid, tenant_id=current_tenant.id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    conditions_pass = WorkflowService._evaluate_conditions(
        wf.conditions, payload.record_data, payload.entity
    )
    return {
        "workflow_id": str(wf.id),
        "workflow_name": wf.name,
        "trigger": wf.trigger.value if hasattr(wf.trigger, "value") else str(wf.trigger),
        "conditions_pass": conditions_pass,
        "actions_that_would_fire": wf.actions if conditions_pass else [],
        "test_entity": payload.entity,
        "test_record_data": payload.record_data,
    }
