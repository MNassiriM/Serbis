"""Tenant service — CRUD and provisioning for tenants."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import create_tenant_schema
from app.core.security import create_access_token
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class TenantService:
    """Handles tenant creation, provisioning, and management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_tenant(
        self,
        name: str,
        industry: str,
        size: str,
        plan: str = "free",
    ) -> tuple[Tenant, str]:
        """
        Create a new tenant and provision its PostgreSQL schema.

        Returns (tenant, access_token).
        """
        slug = self._slugify(name)
        tenant_id = uuid.uuid4()
        schema_name = f"tenant_{str(tenant_id).replace('-', '_')}"

        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=await self._unique_slug(slug),
            plan=plan,
            industry=industry,
            size=size,
            schema_name=schema_name,
            is_active=True,
        )

        self._db.add(tenant)
        await self._db.flush()  # get ID before provisioning

        # Provision PostgreSQL schema
        await create_tenant_schema(str(tenant_id))
        logger.info("Provisioned schema '%s' for tenant '%s'", schema_name, name)

        await self._db.commit()
        await self._db.refresh(tenant)

        # Generate access token
        token = create_access_token(
            {"sub": str(tenant_id), "tenant_id": str(tenant_id), "plan": plan}
        )

        return tenant, token

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Retrieve a tenant by ID."""
        result = await self._db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        """Retrieve a tenant by slug."""
        result = await self._db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_tenants(self, limit: int = 50, offset: int = 0) -> list[Tenant]:
        """List all tenants (admin use only)."""
        result = await self._db.execute(
            select(Tenant).limit(limit).offset(offset).order_by(Tenant.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate_tenant(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Deactivate a tenant (soft delete)."""
        tenant = await self.get_tenant(tenant_id)
        if tenant:
            tenant.is_active = False
            await self._db.commit()
            await self._db.refresh(tenant)
        return tenant

    async def _unique_slug(self, base_slug: str) -> str:
        """Ensure slug uniqueness by appending a counter if needed."""
        slug = base_slug
        counter = 1
        while await self.get_tenant_by_slug(slug) is not None:
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @staticmethod
    def _slugify(name: str) -> str:
        """Convert a company name to a URL-safe slug."""
        slug = name.lower()
        slug = re.sub(r"[àáâãäå]", "a", slug)
        slug = re.sub(r"[èéêë]", "e", slug)
        slug = re.sub(r"[ìíîï]", "i", slug)
        slug = re.sub(r"[òóôõö]", "o", slug)
        slug = re.sub(r"[ùúûü]", "u", slug)
        slug = re.sub(r"[ç]", "c", slug)
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug).strip("-")
        return slug[:50] or "tenant"
