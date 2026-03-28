"""
APISIX Service — registers and manages API routes via the APISIX Admin API.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# HTTP verbs per CRUD operation
_CRUD_METHODS: dict[str, list[str]] = {
    "list": ["GET"],
    "create": ["POST"],
    "get": ["GET"],
    "update": ["PUT", "PATCH"],
    "delete": ["DELETE"],
}

_BACKEND_BASE = "http://backend:8000"


class APISIXService:
    """Interacts with the APISIX Admin API to register/update/delete routes."""

    def __init__(self) -> None:
        self._admin_url = settings.apisix_admin_url.rstrip("/")
        self._headers = {
            "X-API-KEY": settings.apisix_admin_key,
            "Content-Type": "application/json",
        }

    async def register_module_routes(
        self,
        tenant_id: str,
        module_name: str,
        entity_fields: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Register CRUD routes for an ERP module entity in APISIX.

        Routes created:
          GET    /api/v1/data/{tenant_id}/{module_name}         → list
          POST   /api/v1/data/{tenant_id}/{module_name}         → create
          GET    /api/v1/data/{tenant_id}/{module_name}/{id}    → get
          PUT    /api/v1/data/{tenant_id}/{module_name}/{id}    → update
          DELETE /api/v1/data/{tenant_id}/{module_name}/{id}    → delete

        Returns dict with route_ids created.
        """
        safe_tenant = tenant_id.replace("-", "_")
        base_path = f"/api/v1/data/{tenant_id}/{module_name}"
        item_path = f"{base_path}/{{id}}"

        route_configs = [
            {
                "route_id": f"{safe_tenant}_{module_name}_list",
                "uri": base_path,
                "methods": ["GET"],
                "upstream_url": f"{_BACKEND_BASE}{base_path}",
            },
            {
                "route_id": f"{safe_tenant}_{module_name}_create",
                "uri": base_path,
                "methods": ["POST"],
                "upstream_url": f"{_BACKEND_BASE}{base_path}",
            },
            {
                "route_id": f"{safe_tenant}_{module_name}_get",
                "uri": item_path,
                "methods": ["GET"],
                "upstream_url": f"{_BACKEND_BASE}{item_path}",
            },
            {
                "route_id": f"{safe_tenant}_{module_name}_update",
                "uri": item_path,
                "methods": ["PUT", "PATCH"],
                "upstream_url": f"{_BACKEND_BASE}{item_path}",
            },
            {
                "route_id": f"{safe_tenant}_{module_name}_delete",
                "uri": item_path,
                "methods": ["DELETE"],
                "upstream_url": f"{_BACKEND_BASE}{item_path}",
            },
        ]

        created_ids: list[str] = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for config in route_configs:
                route_id = config["route_id"]
                payload = self._build_route_payload(
                    uri=config["uri"],
                    methods=config["methods"],
                    upstream_url=config["upstream_url"],
                    tenant_id=tenant_id,
                )

                try:
                    response = await client.put(
                        f"{self._admin_url}/apisix/admin/routes/{route_id}",
                        json=payload,
                        headers=self._headers,
                    )
                    response.raise_for_status()
                    created_ids.append(route_id)
                    logger.info("Registered APISIX route '%s'", route_id)
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        "APISIX registration failed for route '%s': %s — %s",
                        route_id,
                        exc.response.status_code,
                        exc.response.text,
                    )
                    raise
                except httpx.RequestError as exc:
                    logger.error("APISIX connection error: %s", exc)
                    raise

        return {
            "module": module_name,
            "tenant_id": tenant_id,
            "route_ids": created_ids,
            "base_path": base_path,
        }

    async def delete_module_routes(
        self, tenant_id: str, module_name: str
    ) -> dict[str, Any]:
        """Remove all CRUD routes for a module from APISIX."""
        safe_tenant = tenant_id.replace("-", "_")
        operations = ["list", "create", "get", "update", "delete"]
        deleted_ids: list[str] = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for op in operations:
                route_id = f"{safe_tenant}_{module_name}_{op}"
                try:
                    response = await client.delete(
                        f"{self._admin_url}/apisix/admin/routes/{route_id}",
                        headers=self._headers,
                    )
                    if response.status_code in (200, 204, 404):
                        deleted_ids.append(route_id)
                except httpx.RequestError as exc:
                    logger.warning("Could not delete route '%s': %s", route_id, exc)

        return {"deleted_route_ids": deleted_ids}

    async def health_check(self) -> bool:
        """Check if APISIX admin API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self._admin_url}/apisix/admin/routes",
                    headers=self._headers,
                )
                return response.status_code == 200
        except httpx.RequestError:
            return False

    @staticmethod
    def _build_route_payload(
        uri: str,
        methods: list[str],
        upstream_url: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Build the APISIX route registration payload."""
        return {
            "uri": uri,
            "methods": methods,
            "plugins": {
                "proxy-rewrite": {
                    "uri": uri,
                    "headers": {
                        "X-Tenant-ID": tenant_id,
                    },
                },
                "cors": {
                    "allow_origins": "*",
                    "allow_methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
                    "allow_headers": "Authorization,Content-Type,X-Tenant-ID",
                },
            },
            "upstream": {
                "type": "roundrobin",
                "nodes": {
                    # Extract host:port from upstream_url
                    "backend:8000": 1,
                },
            },
            "status": 1,
        }
