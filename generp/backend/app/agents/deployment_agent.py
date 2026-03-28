"""
Deployment Agent — orchestrates schema creation and route registration.

Coordinates schema_service (DDL execution) and apisix_service (route registration)
after the user has confirmed the generated schema.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.validation_agent import validate_schema
from app.services.apisix_service import APISIXService
from app.services.schema_service import SchemaService

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DeploymentAgent:
    """
    Deploys a validated schema by:
    1. Creating the tenant PostgreSQL schema
    2. Executing DDL for each entity
    3. Registering CRUD routes in APISIX
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session
        self._schema_service = SchemaService(db_session)
        self._apisix_service = APISIXService()

    async def deploy(
        self, tenant_id: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Full deployment pipeline for a validated schema.

        Returns a summary dict with tables_created and routes_registered.
        """
        # 1. Security validation before any DDL
        validation = validate_schema(schema)
        if not validation.is_valid:
            raise ValueError(
                f"Schema validation failed: {'; '.join(validation.errors)}"
            )

        # 2. Create tenant schema + execute DDL
        ddl_result = await self._schema_service.generate_and_execute_ddl(
            tenant_id=tenant_id,
            schema_definition=schema,
        )

        # 3. Register routes in APISIX for each entity
        route_results: list[dict[str, Any]] = []
        for entity in schema.get("entities", []):
            try:
                route_result = await self._apisix_service.register_module_routes(
                    tenant_id=tenant_id,
                    module_name=entity["name"],
                    entity_fields=entity.get("fields", []),
                )
                route_results.append(route_result)
            except Exception as exc:
                # Non-fatal: log and continue (routes can be re-registered)
                logger.warning(
                    "Failed to register APISIX routes for entity '%s': %s",
                    entity["name"],
                    exc,
                )

        return {
            "tables_created": ddl_result.get("tables_created", []),
            "routes_registered": route_results,
            "warnings": validation.warnings,
        }
