"""ERPModule ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ERPModule(Base):
    """
    Represents a generated ERP module (e.g. Clients, Factures, Opportunités)
    scoped to a tenant.
    """

    __tablename__ = "erp_modules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "clients", "factures"
    display_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g. "Clients", "Factures"
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "finance" | "crm" | "hr" | "supply_chain"

    # JSON definitions stored as JSONB
    schema_definition: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    ui_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    api_routes: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="modules")

    def __repr__(self) -> str:
        return (
            f"<ERPModule id={self.id} name={self.name!r} category={self.category!r}>"
        )


# Avoid circular import
from app.models.tenant import Tenant  # noqa: E402
