"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1 import chat, health, modules, tenants

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(tenants.router)
api_router.include_router(modules.router)
api_router.include_router(chat.router)
