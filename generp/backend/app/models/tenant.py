"""Tenant ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tenant(Base):
    """Represents a customer organisation (one schema in PostgreSQL per tenant)."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free"
    )  # "free" | "pro" | "enterprise"
    industry: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    size: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1-10"
    )  # "1-10" | "11-50" | "51-200" | "200+"
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    modules: Mapped[list[ERPModule]] = relationship(
        "ERPModule", back_populates="tenant", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r} plan={self.plan!r}>"


# Avoid circular imports by importing after class definition
from app.models.conversation import Conversation  # noqa: E402
from app.models.erp_module import ERPModule  # noqa: E402
