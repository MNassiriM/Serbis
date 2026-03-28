"""
HR module — Departments, Employees, Job Postings, Candidates, Leaves, Reviews.
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
router = APIRouter(prefix="/hr", tags=["hr"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DepartmentCreate(BaseModel):
    name: str
    manager_name: Optional[str] = None
    parent_id: Optional[str] = None
    budget: Optional[float] = None
    headcount: int = 0


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    manager_name: Optional[str] = None
    parent_id: Optional[str] = None
    budget: Optional[float] = None
    headcount: Optional[int] = None


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    department_id: Optional[str] = None
    manager_id: Optional[str] = None
    position: str
    hire_date: date
    contract_type: str = "cdi"
    salary: Optional[float] = None
    status: str = "active"
    emergency_contact: Optional[str] = None
    notes: Optional[str] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[str] = None
    manager_id: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[date] = None
    contract_type: Optional[str] = None
    salary: Optional[float] = None
    status: Optional[str] = None
    emergency_contact: Optional[str] = None
    notes: Optional[str] = None


class JobPostingCreate(BaseModel):
    title: str
    department_id: Optional[str] = None
    description: str
    requirements: Optional[str] = None
    contract_type: str = "cdi"
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    status: str = "draft"
    deadline: Optional[date] = None


class JobPostingUpdate(BaseModel):
    title: Optional[str] = None
    department_id: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    contract_type: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    status: Optional[str] = None
    deadline: Optional[date] = None


class CandidateCreate(BaseModel):
    job_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    score: Optional[int] = None
    notes: Optional[str] = None


class CandidateStageUpdate(BaseModel):
    stage: str


class LeaveRequestCreate(BaseModel):
    employee_id: str
    type: str  # paid/sick/unpaid/maternity/paternity/other
    start_date: date
    end_date: date
    days: float
    reason: Optional[str] = None


class LeaveApproval(BaseModel):
    approved_by: str


class PerformanceReviewCreate(BaseModel):
    employee_id: str
    reviewer_name: str
    period: str
    goals: list[Any] = []
    ratings: dict[str, Any] = {}
    overall_score: Optional[float] = None
    status: str = "draft"
    comments: Optional[str] = None


class PerformanceReviewUpdate(BaseModel):
    reviewer_name: Optional[str] = None
    period: Optional[str] = None
    goals: Optional[list[Any]] = None
    ratings: Optional[dict[str, Any]] = None
    overall_score: Optional[float] = None
    status: Optional[str] = None
    comments: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema(tenant_id: str) -> str:
    return f"tenant_{tenant_id.replace('-', '_')}"


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------


async def ensure_hr_tables(tenant_id: str) -> None:
    schema = _schema(tenant_id)
    engine = get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.departments (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL,
                manager_name TEXT,
                parent_id UUID REFERENCES {schema}.departments(id) ON DELETE SET NULL,
                budget NUMERIC(12,2),
                headcount INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.employees (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                department_id UUID REFERENCES {schema}.departments(id) ON DELETE SET NULL,
                manager_id UUID REFERENCES {schema}.employees(id) ON DELETE SET NULL,
                position TEXT NOT NULL,
                hire_date DATE NOT NULL,
                contract_type TEXT NOT NULL DEFAULT 'cdi',
                salary NUMERIC(10,2),
                status TEXT NOT NULL DEFAULT 'active',
                emergency_contact TEXT,
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.job_postings (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                title TEXT NOT NULL,
                department_id UUID REFERENCES {schema}.departments(id) ON DELETE SET NULL,
                description TEXT NOT NULL,
                requirements TEXT,
                contract_type TEXT NOT NULL DEFAULT 'cdi',
                location TEXT,
                salary_min NUMERIC(10,2),
                salary_max NUMERIC(10,2),
                status TEXT NOT NULL DEFAULT 'draft',
                deadline DATE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.candidates (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                job_id UUID NOT NULL REFERENCES {schema}.job_postings(id) ON DELETE CASCADE,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                resume_url TEXT,
                cover_letter TEXT,
                stage TEXT NOT NULL DEFAULT 'applied',
                score INTEGER,
                notes TEXT,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.leave_requests (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                employee_id UUID NOT NULL REFERENCES {schema}.employees(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                days NUMERIC(5,1) NOT NULL,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                approved_by TEXT,
                approved_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.performance_reviews (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                employee_id UUID NOT NULL REFERENCES {schema}.employees(id) ON DELETE CASCADE,
                reviewer_name TEXT NOT NULL,
                period TEXT NOT NULL,
                goals JSONB NOT NULL DEFAULT '[]',
                ratings JSONB NOT NULL DEFAULT '{{}}',
                overall_score NUMERIC(4,2),
                status TEXT NOT NULL DEFAULT 'draft',
                comments TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        # Indexes
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_employees_dept ON {schema}.employees (department_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_employees_status ON {schema}.employees (status)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_candidates_job ON {schema}.candidates (job_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_leaves_employee ON {schema}.leave_requests (employee_id)"))
    logger.info("HR tables ensured for tenant %s", tenant_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/setup")
async def setup_hr(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    await ensure_hr_tables(str(current_tenant.id))
    return {"status": "ready"}


# --- Departments ---


@router.get("/departments")
async def list_departments(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.departments ORDER BY name")
        )
        return [dict(r) for r in result.mappings().all()]


@router.post("/departments", status_code=201)
async def create_department(
    payload: DepartmentCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.departments (name, manager_name, parent_id, budget, headcount)
                VALUES (:name, :manager_name, :parent_id, :budget, :headcount)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/departments/org-chart")
async def get_org_chart(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.departments ORDER BY name")
        )
        all_depts = [dict(r) for r in result.mappings().all()]

    # Build tree
    dept_map: dict[str, dict[str, Any]] = {}
    for d in all_depts:
        d["children"] = []
        dept_map[str(d["id"])] = d

    roots: list[dict[str, Any]] = []
    for d in all_depts:
        parent_id = d.get("parent_id")
        if parent_id and str(parent_id) in dept_map:
            dept_map[str(parent_id)]["children"].append(d)
        else:
            roots.append(d)
    return roots


@router.get("/departments/{dept_id}")
async def get_department(
    dept_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.departments WHERE id = :id"),
            {"id": dept_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Department not found")
        return dict(row)


@router.put("/departments/{dept_id}")
async def update_department(
    dept_id: str,
    payload: DepartmentUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.departments WHERE id = :id"),
                {"id": dept_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Department not found")
            return dict(row)
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = dept_id
        result = await conn.execute(
            text(f"UPDATE {schema}.departments SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Department not found")
        return dict(row)


# --- Employees ---


@router.get("/employees")
async def list_employees(
    status: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.employees WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if department_id:
            query += " AND department_id = :department_id"
            params["department_id"] = department_id
        if search:
            query += " AND (first_name ILIKE :search OR last_name ILIKE :search OR email ILIKE :search)"
            params["search"] = f"%{search}%"
        query += " ORDER BY last_name, first_name"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/employees", status_code=201)
async def create_employee(
    payload: EmployeeCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.employees
                    (first_name, last_name, email, phone, department_id, manager_id,
                     position, hire_date, contract_type, salary, status, emergency_contact, notes)
                VALUES (:first_name, :last_name, :email, :phone, :department_id, :manager_id,
                        :position, :hire_date, :contract_type, :salary, :status, :emergency_contact, :notes)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/employees/{employee_id}")
async def get_employee(
    employee_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.employees WHERE id = :id"),
            {"id": employee_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        return dict(row)


@router.put("/employees/{employee_id}")
async def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.employees WHERE id = :id"),
                {"id": employee_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Employee not found")
            return dict(row)
        updates["updated_at"] = datetime.utcnow()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = employee_id
        result = await conn.execute(
            text(f"UPDATE {schema}.employees SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        return dict(row)


@router.delete("/employees/{employee_id}")
async def deactivate_employee(
    employee_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.employees SET status='inactive', updated_at=now()"
                " WHERE id = :id RETURNING id"
            ),
            {"id": employee_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Employee not found")
        return {"status": "inactive"}


@router.get("/employees/{employee_id}/leaves")
async def get_employee_leaves(
    employee_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"""
                SELECT * FROM {schema}.leave_requests
                WHERE employee_id = :employee_id
                ORDER BY start_date DESC
            """),
            {"employee_id": employee_id},
        )
        return [dict(r) for r in result.mappings().all()]


# --- Job Postings ---


@router.get("/job-postings")
async def list_job_postings(
    status: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.job_postings WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/job-postings", status_code=201)
async def create_job_posting(
    payload: JobPostingCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.job_postings
                    (title, department_id, description, requirements, contract_type,
                     location, salary_min, salary_max, status, deadline)
                VALUES (:title, :department_id, :description, :requirements, :contract_type,
                        :location, :salary_min, :salary_max, :status, :deadline)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/job-postings/{job_id}")
async def get_job_posting(
    job_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.job_postings WHERE id = :id"),
            {"id": job_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Job posting not found")
        return dict(row)


@router.put("/job-postings/{job_id}")
async def update_job_posting(
    job_id: str,
    payload: JobPostingUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.job_postings WHERE id = :id"),
                {"id": job_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Job posting not found")
            return dict(row)
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = job_id
        result = await conn.execute(
            text(f"UPDATE {schema}.job_postings SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Job posting not found")
        return dict(row)


@router.get("/job-postings/{job_id}/candidates")
async def get_job_candidates(
    job_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"""
                SELECT * FROM {schema}.candidates
                WHERE job_id = :job_id
                ORDER BY applied_at DESC
            """),
            {"job_id": job_id},
        )
        return [dict(r) for r in result.mappings().all()]


# --- Candidates ---


@router.post("/candidates", status_code=201)
async def create_candidate(
    payload: CandidateCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.candidates
                    (job_id, full_name, email, phone, resume_url, cover_letter, score, notes)
                VALUES (:job_id, :full_name, :email, :phone, :resume_url, :cover_letter, :score, :notes)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.candidates WHERE id = :id"),
            {"id": candidate_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return dict(row)


@router.put("/candidates/{candidate_id}/stage")
async def update_candidate_stage(
    candidate_id: str,
    payload: CandidateStageUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.candidates SET stage = :stage, updated_at = now()"
                " WHERE id = :id RETURNING *"
            ),
            {"id": candidate_id, "stage": payload.stage},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return dict(row)


# --- Leave Requests ---


@router.get("/leave-requests")
async def list_leave_requests(
    status: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.leave_requests WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if employee_id:
            query += " AND employee_id = :employee_id"
            params["employee_id"] = employee_id
        query += " ORDER BY start_date DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/leave-requests", status_code=201)
async def create_leave_request(
    payload: LeaveRequestCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.leave_requests
                    (employee_id, type, start_date, end_date, days, reason)
                VALUES (:employee_id, :type, :start_date, :end_date, :days, :reason)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/leave-requests/{leave_id}")
async def get_leave_request(
    leave_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.leave_requests WHERE id = :id"),
            {"id": leave_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Leave request not found")
        return dict(row)


@router.put("/leave-requests/{leave_id}/approve")
async def approve_leave(
    leave_id: str,
    payload: LeaveApproval,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                UPDATE {schema}.leave_requests
                SET status = 'approved', approved_by = :approved_by, approved_at = now()
                WHERE id = :id RETURNING *
            """),
            {"id": leave_id, "approved_by": payload.approved_by},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Leave request not found")
        return dict(row)


@router.put("/leave-requests/{leave_id}/reject")
async def reject_leave(
    leave_id: str,
    payload: LeaveApproval,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                UPDATE {schema}.leave_requests
                SET status = 'rejected', approved_by = :approved_by, approved_at = now()
                WHERE id = :id RETURNING *
            """),
            {"id": leave_id, "approved_by": payload.approved_by},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Leave request not found")
        return dict(row)


@router.get("/leave-calendar")
async def get_leave_calendar(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT
                e.first_name || ' ' || e.last_name AS employee_name,
                lr.type,
                lr.start_date,
                lr.end_date,
                lr.status
            FROM {schema}.leave_requests lr
            JOIN {schema}.employees e ON e.id = lr.employee_id
            WHERE lr.start_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '3 months'
            ORDER BY lr.start_date
        """))
        return [dict(r) for r in result.mappings().all()]


# --- Performance Reviews ---


@router.get("/performance-reviews")
async def list_performance_reviews(
    employee_id: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.performance_reviews WHERE 1=1"
        params: dict[str, Any] = {}
        if employee_id:
            query += " AND employee_id = :employee_id"
            params["employee_id"] = employee_id
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/performance-reviews", status_code=201)
async def create_performance_review(
    payload: PerformanceReviewCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.performance_reviews
                    (employee_id, reviewer_name, period, goals, ratings, overall_score, status, comments)
                VALUES (:employee_id, :reviewer_name, :period, :goals, :ratings, :overall_score, :status, :comments)
                RETURNING *
            """),
            {
                "employee_id": payload.employee_id,
                "reviewer_name": payload.reviewer_name,
                "period": payload.period,
                "goals": json.dumps(payload.goals),
                "ratings": json.dumps(payload.ratings),
                "overall_score": payload.overall_score,
                "status": payload.status,
                "comments": payload.comments,
            },
        )
        return dict(result.mappings().one())


@router.get("/performance-reviews/{review_id}")
async def get_performance_review(
    review_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.performance_reviews WHERE id = :id"),
            {"id": review_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Performance review not found")
        return dict(row)


@router.put("/performance-reviews/{review_id}")
async def update_performance_review(
    review_id: str,
    payload: PerformanceReviewUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates: dict[str, Any] = {}
        if payload.reviewer_name is not None:
            updates["reviewer_name"] = payload.reviewer_name
        if payload.period is not None:
            updates["period"] = payload.period
        if payload.goals is not None:
            updates["goals"] = json.dumps(payload.goals)
        if payload.ratings is not None:
            updates["ratings"] = json.dumps(payload.ratings)
        if payload.overall_score is not None:
            updates["overall_score"] = payload.overall_score
        if payload.status is not None:
            updates["status"] = payload.status
        if payload.comments is not None:
            updates["comments"] = payload.comments
        updates["updated_at"] = datetime.utcnow()

        if len(updates) == 1:  # only updated_at
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.performance_reviews WHERE id = :id"),
                {"id": review_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Performance review not found")
            return dict(row)

        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = review_id
        result = await conn.execute(
            text(f"UPDATE {schema}.performance_reviews SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Performance review not found")
        return dict(row)


# --- Dashboard ---


@router.get("/dashboard")
async def hr_dashboard(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        # Total active employees
        te = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.employees WHERE status = 'active'
        """))
        total_employees = int(te.scalar() or 0)

        # By department
        bd = await conn.execute(text(f"""
            SELECT d.name, COUNT(e.id) AS count
            FROM {schema}.departments d
            LEFT JOIN {schema}.employees e ON e.department_id = d.id AND e.status = 'active'
            GROUP BY d.id, d.name
            ORDER BY count DESC
        """))
        by_department = [dict(r) for r in bd.mappings().all()]

        # Pending leaves
        pl = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.leave_requests WHERE status = 'pending'
        """))
        pending_leaves = int(pl.scalar() or 0)

        # Open positions
        op = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.job_postings WHERE status = 'published'
        """))
        open_positions = int(op.scalar() or 0)

        # Hires this month
        hm = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.employees
            WHERE DATE_TRUNC('month', hire_date) = DATE_TRUNC('month', CURRENT_DATE)
        """))
        hires_this_month = int(hm.scalar() or 0)

        # Leave calendar preview
        lc = await conn.execute(text(f"""
            SELECT e.first_name || ' ' || e.last_name AS employee_name,
                   lr.type, lr.start_date, lr.end_date, lr.status
            FROM {schema}.leave_requests lr
            JOIN {schema}.employees e ON e.id = lr.employee_id
            WHERE lr.status = 'approved'
              AND lr.start_date >= CURRENT_DATE
            ORDER BY lr.start_date
            LIMIT 5
        """))
        leave_calendar_preview = [dict(r) for r in lc.mappings().all()]

    return {
        "total_employees": total_employees,
        "by_department": by_department,
        "pending_leaves": pending_leaves,
        "open_positions": open_positions,
        "hires_this_month": hires_this_month,
        "leave_calendar_preview": leave_calendar_preview,
    }
