"""Tenant CRUD endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import CurrentTenant, DBSession
from app.models.tenant import Tenant
from app.services.tenant_service import TenantService

router = APIRouter(tags=["tenants"])


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    industry: str = Field(..., min_length=2, max_length=100)
    size: str = Field(..., pattern=r"^(1-10|11-50|51-200|200\+)$")
    plan: str = Field(default="free", pattern=r"^(free|pro|enterprise)$")


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    industry: str
    size: str
    schema_name: str
    is_active: bool

    model_config = {"from_attributes": True}


class CreateTenantResponse(BaseModel):
    tenant: TenantResponse
    access_token: str
    token_type: str = "bearer"


@router.post("/tenants", response_model=CreateTenantResponse, status_code=201)
async def create_tenant(
    request: CreateTenantRequest,
    db: DBSession,
) -> CreateTenantResponse:
    """Register a new tenant and provision its database schema."""
    service = TenantService(db)
    tenant, token = await service.create_tenant(
        name=request.name,
        industry=request.industry,
        size=request.size,
        plan=request.plan,
    )
    return CreateTenantResponse(
        tenant=TenantResponse.model_validate(tenant),
        access_token=token,
    )


@router.get("/tenants/me", response_model=TenantResponse)
async def get_current_tenant_info(
    tenant: CurrentTenant,
) -> TenantResponse:
    """Return the authenticated tenant's information."""
    return TenantResponse.model_validate(tenant)


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    current_tenant: CurrentTenant,
    db: DBSession,
) -> TenantResponse:
    """Get a tenant by ID (restricted to same tenant)."""
    if current_tenant.id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)
