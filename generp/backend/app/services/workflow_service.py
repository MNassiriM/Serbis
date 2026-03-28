"""Workflow service — CRUD and evaluation of tenant workflows."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowTrigger

logger = logging.getLogger(__name__)


class WorkflowService:
    """Handles creation, management, and evaluation of workflows."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        tenant_id: uuid.UUID,
        name: str,
        trigger: WorkflowTrigger,
        conditions: list[Any],
        actions: list[Any],
        description: Optional[str] = None,
    ) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(
            tenant_id=tenant_id,
            name=name,
            description=description,
            trigger=trigger,
            conditions=conditions,
            actions=actions,
        )
        self._db.add(workflow)
        await self._db.commit()
        await self._db.refresh(workflow)
        logger.info("Created workflow %s for tenant %s", workflow.id, tenant_id)
        return workflow

    async def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Workflow]:
        """List all workflows for a tenant."""
        result = await self._db.execute(
            select(Workflow)
            .where(Workflow.tenant_id == tenant_id)
            .order_by(Workflow.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, workflow_id: uuid.UUID, tenant_id: uuid.UUID) -> Workflow | None:
        """Get a workflow by ID, scoped to the tenant."""
        result = await self._db.execute(
            select(Workflow).where(
                Workflow.id == workflow_id,
                Workflow.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self, workflow_id: uuid.UUID, tenant_id: uuid.UUID, **kwargs: Any
    ) -> Workflow:
        """Update a workflow. Raises ValueError if not found."""
        workflow = await self.get(workflow_id, tenant_id)
        if workflow is None:
            raise ValueError(f"Workflow {workflow_id} not found")
        for key, value in kwargs.items():
            if hasattr(workflow, key) and value is not None:
                setattr(workflow, key, value)
        await self._db.commit()
        await self._db.refresh(workflow)
        return workflow

    async def delete(self, workflow_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Delete a workflow. Returns True if deleted."""
        workflow = await self.get(workflow_id, tenant_id)
        if workflow is None:
            return False
        await self._db.delete(workflow)
        await self._db.commit()
        return True

    async def evaluate(
        self,
        tenant_id: uuid.UUID,
        trigger_type: WorkflowTrigger,
        entity: str,
        record_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Find active workflows matching the trigger type, evaluate conditions
        against record_data, and return the triggered actions.
        """
        result = await self._db.execute(
            select(Workflow).where(
                Workflow.tenant_id == tenant_id,
                Workflow.trigger == trigger_type,
                Workflow.is_active.is_(True),
            )
        )
        workflows = list(result.scalars().all())

        triggered: list[dict[str, Any]] = []
        for wf in workflows:
            if self._evaluate_conditions(wf.conditions, record_data, entity):
                triggered.append(
                    {
                        "workflow_id": str(wf.id),
                        "workflow_name": wf.name,
                        "actions": wf.actions,
                    }
                )
        return triggered

    @staticmethod
    def _evaluate_conditions(
        conditions: list[Any],
        record_data: dict[str, Any],
        entity: str,
    ) -> bool:
        """
        Evaluate a list of conditions against record data.

        Each condition is a dict with keys: field, operator, value.
        All conditions must pass (AND logic).
        If no conditions, the workflow always triggers.
        """
        if not conditions:
            return True

        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            field = condition.get("field", "")
            operator = condition.get("operator", "eq")
            expected = condition.get("value")
            actual = record_data.get(field)

            if operator == "eq" and actual != expected:
                return False
            elif operator == "neq" and actual == expected:
                return False
            elif operator == "gt":
                try:
                    if not (float(actual) > float(expected)):
                        return False
                except (TypeError, ValueError):
                    return False
            elif operator == "lt":
                try:
                    if not (float(actual) < float(expected)):
                        return False
                except (TypeError, ValueError):
                    return False
            elif operator == "contains":
                if expected not in str(actual or ""):
                    return False
            elif operator == "entity_is" and entity != expected:
                return False

        return True
