"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter, Depends

from app.api.v1 import (
    audit,
    chat,
    crm,
    finance,
    health,
    hr,
    modules,
    notifications,
    projects,
    search,
    supply,
    tenants,
    workflows,
)
from app.core.dependencies import get_current_tenant

api_router = APIRouter(prefix="/api/v1")

# Public / lightly-authenticated routes
api_router.include_router(health.router)
api_router.include_router(tenants.router)
api_router.include_router(modules.router)
api_router.include_router(chat.router)

# ERP modules — all require tenant auth
api_router.include_router(
    finance.router, dependencies=[Depends(get_current_tenant)]
)
api_router.include_router(
    crm.router, dependencies=[Depends(get_current_tenant)]
)
api_router.include_router(
    hr.router, dependencies=[Depends(get_current_tenant)]
)
api_router.include_router(
    supply.router, dependencies=[Depends(get_current_tenant)]
)
api_router.include_router(
    projects.router, dependencies=[Depends(get_current_tenant)]
)

# Platform services — all require tenant auth
api_router.include_router(
    notifications.router, dependencies=[Depends(get_current_tenant)]
)
api_router.include_router(
    audit.router, dependencies=[Depends(get_current_tenant)]
)
api_router.include_router(
    workflows.router, dependencies=[Depends(get_current_tenant)]
)
api_router.include_router(
    search.router, dependencies=[Depends(get_current_tenant)]
)
