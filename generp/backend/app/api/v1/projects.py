"""
Projects module — Projects, Milestones, Tasks, Time Entries.
All tables reside in the tenant schema (tenant_{id}).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.core.database import get_tenant_engine
from app.core.dependencies import get_current_tenant
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "planning"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    manager_name: Optional[str] = None
    client_name: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    spent_budget: Optional[float] = None
    manager_name: Optional[str] = None
    client_name: Optional[str] = None
    progress: Optional[int] = None


class MilestoneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    due_date: date
    status: str = "pending"


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None


class TaskCreate(BaseModel):
    project_id: str
    milestone_id: Optional[str] = None
    parent_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    tags: list[str] = []


class TaskUpdate(BaseModel):
    milestone_id: Optional[str] = None
    parent_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    tags: Optional[list[str]] = None


class TimeEntryCreate(BaseModel):
    task_id: str
    project_id: str
    user_name: str
    hours: float
    description: Optional[str] = None
    date: date
    approved: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema(tenant_id: str) -> str:
    return f"tenant_{tenant_id.replace('-', '_')}"


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------


async def ensure_project_tables(tenant_id: str) -> None:
    schema = _schema(tenant_id)
    engine = get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.projects (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'planning',
                start_date DATE,
                end_date DATE,
                budget NUMERIC(12,2),
                spent_budget NUMERIC(12,2) NOT NULL DEFAULT 0,
                manager_name TEXT,
                client_name TEXT,
                progress INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.milestones (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                project_id UUID NOT NULL REFERENCES {schema}.projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                due_date DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.tasks (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                project_id UUID NOT NULL REFERENCES {schema}.projects(id) ON DELETE CASCADE,
                milestone_id UUID REFERENCES {schema}.milestones(id) ON DELETE SET NULL,
                parent_id UUID REFERENCES {schema}.tasks(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                description TEXT,
                assignee_name TEXT,
                status TEXT NOT NULL DEFAULT 'todo',
                priority TEXT NOT NULL DEFAULT 'medium',
                due_date DATE,
                estimated_hours NUMERIC(6,2),
                actual_hours NUMERIC(6,2) NOT NULL DEFAULT 0,
                tags JSONB NOT NULL DEFAULT '[]',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.time_entries (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                task_id UUID NOT NULL REFERENCES {schema}.tasks(id) ON DELETE CASCADE,
                project_id UUID NOT NULL REFERENCES {schema}.projects(id) ON DELETE CASCADE,
                user_name TEXT NOT NULL,
                hours NUMERIC(6,2) NOT NULL,
                description TEXT,
                date DATE NOT NULL,
                approved BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        # Indexes
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_milestones_project ON {schema}.milestones (project_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_tasks_project ON {schema}.tasks (project_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_tasks_milestone ON {schema}.tasks (milestone_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_time_entries_task ON {schema}.time_entries (task_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_time_entries_project ON {schema}.time_entries (project_id)"))
    logger.info("Project tables ensured for tenant %s", tenant_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/setup")
async def setup_projects(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    await ensure_project_tables(str(current_tenant.id))
    return {"status": "ready"}


# --- Projects ---


@router.get("/projects")
async def list_projects(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.projects WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if search:
            query += " AND name ILIKE :search"
            params["search"] = f"%{search}%"
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/projects", status_code=201)
async def create_project(
    payload: ProjectCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.projects
                    (name, description, status, start_date, end_date, budget, manager_name, client_name)
                VALUES (:name, :description, :status, :start_date, :end_date, :budget, :manager_name, :client_name)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.projects WHERE id = :id"),
            {"id": project_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return dict(row)


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.projects WHERE id = :id"),
                {"id": project_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Project not found")
            return dict(row)
        updates["updated_at"] = datetime.utcnow()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = project_id
        result = await conn.execute(
            text(f"UPDATE {schema}.projects SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return dict(row)


@router.delete("/projects/{project_id}")
async def cancel_project(
    project_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.projects SET status='cancelled', updated_at=now()"
                " WHERE id = :id RETURNING id"
            ),
            {"id": project_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"status": "cancelled"}


@router.get("/projects/{project_id}/gantt")
async def get_project_gantt(
    project_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        proj_result = await conn.execute(
            text(f"SELECT id::text, name, start_date, end_date FROM {schema}.projects WHERE id = :id"),
            {"id": project_id},
        )
        project = proj_result.mappings().one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        milestones_result = await conn.execute(
            text(f"""
                SELECT id::text, name, due_date, status
                FROM {schema}.milestones WHERE project_id = :project_id ORDER BY due_date
            """),
            {"project_id": project_id},
        )
        milestones = [dict(r) for r in milestones_result.mappings().all()]

        tasks_result = await conn.execute(
            text(f"""
                SELECT id::text, title, due_date, status, milestone_id::text, assignee_name, created_at AS start_date
                FROM {schema}.tasks WHERE project_id = :project_id ORDER BY created_at
            """),
            {"project_id": project_id},
        )
        tasks = [dict(r) for r in tasks_result.mappings().all()]

    return {"project": dict(project), "milestones": milestones, "tasks": tasks}


# --- Milestones ---


@router.get("/projects/{project_id}/milestones")
async def list_milestones(
    project_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"""
                SELECT * FROM {schema}.milestones
                WHERE project_id = :project_id ORDER BY due_date
            """),
            {"project_id": project_id},
        )
        return [dict(r) for r in result.mappings().all()]


@router.post("/projects/{project_id}/milestones", status_code=201)
async def create_milestone(
    project_id: str,
    payload: MilestoneCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.milestones (project_id, name, description, due_date, status)
                VALUES (:project_id, :name, :description, :due_date, :status)
                RETURNING *
            """),
            {"project_id": project_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())


@router.put("/milestones/{milestone_id}")
async def update_milestone(
    milestone_id: str,
    payload: MilestoneUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.milestones WHERE id = :id"),
                {"id": milestone_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Milestone not found")
            return dict(row)
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = milestone_id
        result = await conn.execute(
            text(f"UPDATE {schema}.milestones SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Milestone not found")
        return dict(row)


# --- Tasks ---


@router.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = Query(None),
    assignee_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.tasks WHERE 1=1"
        params: dict[str, Any] = {}
        if project_id:
            query += " AND project_id = :project_id"
            params["project_id"] = project_id
        if assignee_name:
            query += " AND assignee_name ILIKE :assignee_name"
            params["assignee_name"] = f"%{assignee_name}%"
        if status:
            query += " AND status = :status"
            params["status"] = status
        if priority:
            query += " AND priority = :priority"
            params["priority"] = priority
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/tasks", status_code=201)
async def create_task(
    payload: TaskCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.tasks
                    (project_id, milestone_id, parent_id, title, description,
                     assignee_name, status, priority, due_date, estimated_hours, tags)
                VALUES (:project_id, :milestone_id, :parent_id, :title, :description,
                        :assignee_name, :status, :priority, :due_date, :estimated_hours, :tags)
                RETURNING *
            """),
            {
                "project_id": payload.project_id,
                "milestone_id": payload.milestone_id,
                "parent_id": payload.parent_id,
                "title": payload.title,
                "description": payload.description,
                "assignee_name": payload.assignee_name,
                "status": payload.status,
                "priority": payload.priority,
                "due_date": payload.due_date,
                "estimated_hours": payload.estimated_hours,
                "tags": json.dumps(payload.tags),
            },
        )
        return dict(result.mappings().one())


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.tasks WHERE id = :id"),
            {"id": task_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return dict(row)


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates: dict[str, Any] = {}
        for field in ["milestone_id", "parent_id", "title", "description",
                      "assignee_name", "status", "priority", "due_date",
                      "estimated_hours", "actual_hours"]:
            val = getattr(payload, field, None)
            if val is not None:
                updates[field] = val
        if payload.tags is not None:
            updates["tags"] = json.dumps(payload.tags)
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.tasks WHERE id = :id"),
                {"id": task_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Task not found")
            return dict(row)
        updates["updated_at"] = datetime.utcnow()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = task_id
        result = await conn.execute(
            text(f"UPDATE {schema}.tasks SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return dict(row)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"DELETE FROM {schema}.tasks WHERE id = :id RETURNING id"),
            {"id": task_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "deleted"}


# --- Time Entries ---


@router.get("/time-entries")
async def list_time_entries(
    project_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    user_name: Optional[str] = Query(None),
    approved: Optional[bool] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.time_entries WHERE 1=1"
        params: dict[str, Any] = {}
        if project_id:
            query += " AND project_id = :project_id"
            params["project_id"] = project_id
        if task_id:
            query += " AND task_id = :task_id"
            params["task_id"] = task_id
        if user_name:
            query += " AND user_name ILIKE :user_name"
            params["user_name"] = f"%{user_name}%"
        if approved is not None:
            query += " AND approved = :approved"
            params["approved"] = approved
        query += " ORDER BY date DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/time-entries", status_code=201)
async def create_time_entry(
    payload: TimeEntryCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.time_entries
                    (task_id, project_id, user_name, hours, description, date, approved)
                VALUES (:task_id, :project_id, :user_name, :hours, :description, :date, :approved)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.put("/time-entries/{entry_id}/approve")
async def approve_time_entry(
    entry_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.time_entries SET approved = true WHERE id = :id RETURNING *"
            ),
            {"id": entry_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Time entry not found")
        return dict(row)


# --- Dashboard ---


@router.get("/dashboard")
async def projects_dashboard(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        # Active projects
        ap = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.projects WHERE status = 'active'
        """))
        active_projects = int(ap.scalar() or 0)

        # Completed this month
        cm = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.projects
            WHERE status = 'completed'
              AND DATE_TRUNC('month', updated_at) = DATE_TRUNC('month', NOW())
        """))
        completed_this_month = int(cm.scalar() or 0)

        # Overdue tasks
        ot = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.tasks
            WHERE due_date < CURRENT_DATE
              AND status NOT IN ('done', 'cancelled')
        """))
        overdue_tasks = int(ot.scalar() or 0)

        # Hours logged this week
        hlw = await conn.execute(text(f"""
            SELECT COALESCE(SUM(hours), 0) FROM {schema}.time_entries
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        """))
        hours_logged_this_week = float(hlw.scalar() or 0)

        # Projects by status
        pbs = await conn.execute(text(f"""
            SELECT status, COUNT(*) AS count FROM {schema}.projects GROUP BY status
        """))
        projects_by_status = [dict(r) for r in pbs.mappings().all()]

        # Top tasks by priority
        mt = await conn.execute(text(f"""
            SELECT id::text, title, priority, status, due_date, assignee_name, project_id::text
            FROM {schema}.tasks
            WHERE status NOT IN ('done', 'cancelled')
            ORDER BY
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END, due_date ASC NULLS LAST
            LIMIT 5
        """))
        my_tasks = [dict(r) for r in mt.mappings().all()]

    return {
        "active_projects": active_projects,
        "completed_this_month": completed_this_month,
        "overdue_tasks": overdue_tasks,
        "hours_logged_this_week": hours_logged_this_week,
        "projects_by_status": projects_by_status,
        "my_tasks": my_tasks,
    }
