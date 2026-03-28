"""ERP Module CRUD endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.dependencies import CurrentTenant, DBSession
from app.models.erp_module import ERPModule
from sqlalchemy import select

router = APIRouter(tags=["modules"])


class ModuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    category: str
    schema_definition: dict[str, Any]
    ui_config: dict[str, Any]
    api_routes: dict[str, Any]
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/modules", response_model=list[ModuleResponse])
async def list_modules(
    tenant: CurrentTenant,
    db: DBSession,
) -> list[ModuleResponse]:
    """List all active ERP modules for the current tenant."""
    result = await db.execute(
        select(ERPModule)
        .where(ERPModule.tenant_id == tenant.id, ERPModule.is_active.is_(True))
        .order_by(ERPModule.created_at.asc())
    )
    modules = result.scalars().all()
    return [ModuleResponse.model_validate(m) for m in modules]


@router.get("/modules/{module_id}", response_model=ModuleResponse)
async def get_module(
    module_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DBSession,
) -> ModuleResponse:
    """Get a specific ERP module."""
    result = await db.execute(
        select(ERPModule).where(
            ERPModule.id == module_id,
            ERPModule.tenant_id == tenant.id,
        )
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return ModuleResponse.model_validate(module)


@router.delete("/modules/{module_id}", status_code=204)
async def deactivate_module(
    module_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DBSession,
) -> None:
    """Deactivate (soft-delete) an ERP module."""
    result = await db.execute(
        select(ERPModule).where(
            ERPModule.id == module_id,
            ERPModule.tenant_id == tenant.id,
        )
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.is_active = False
    await db.commit()
