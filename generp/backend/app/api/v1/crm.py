"""
CRM module — Companies, Contacts, Deals, Pipeline, Activities.
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
router = APIRouter(prefix="/crm", tags=["crm"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company_id: Optional[str] = None
    is_primary: bool = False
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company_id: Optional[str] = None
    is_primary: Optional[bool] = None
    notes: Optional[str] = None


class DealCreate(BaseModel):
    title: str
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    stage_id: str
    value: float = 0.0
    currency: str = "EUR"
    probability: int = 0
    expected_close: Optional[date] = None
    owner_name: Optional[str] = None
    notes: Optional[str] = None


class DealUpdate(BaseModel):
    title: Optional[str] = None
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    stage_id: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    probability: Optional[int] = None
    expected_close: Optional[date] = None
    owner_name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class DealStageUpdate(BaseModel):
    stage_id: str


class ActivityCreate(BaseModel):
    type: str  # call/email/meeting/note/task
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema(tenant_id: str) -> str:
    return f"tenant_{tenant_id.replace('-', '_')}"


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------

_DEFAULT_STAGES = [
    ("Prospect", 0, 0, "#94a3b8"),
    ("Qualifié", 25, 1, "#60a5fa"),
    ("Proposition", 50, 2, "#a78bfa"),
    ("Négociation", 75, 3, "#fb923c"),
    ("Gagné", 100, 4, "#4ade80"),
    ("Perdu", 0, 5, "#f87171"),
]


async def ensure_crm_tables(tenant_id: str) -> None:
    schema = _schema(tenant_id)
    engine = get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.pipeline_stages (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0,
                probability INTEGER NOT NULL DEFAULT 0,
                color TEXT NOT NULL DEFAULT '#94a3b8',
                is_default BOOLEAN NOT NULL DEFAULT false
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.companies (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL,
                industry TEXT,
                size TEXT,
                website TEXT,
                phone TEXT,
                address TEXT,
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.contacts (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                company_id UUID REFERENCES {schema}.companies(id) ON DELETE SET NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                job_title TEXT,
                is_primary BOOLEAN NOT NULL DEFAULT false,
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.deals (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                title TEXT NOT NULL,
                company_id UUID REFERENCES {schema}.companies(id) ON DELETE SET NULL,
                contact_id UUID REFERENCES {schema}.contacts(id) ON DELETE SET NULL,
                stage_id UUID NOT NULL REFERENCES {schema}.pipeline_stages(id),
                value NUMERIC(12,2) NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'EUR',
                probability INTEGER NOT NULL DEFAULT 0,
                expected_close DATE,
                owner_name TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.activities (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                type TEXT NOT NULL,
                contact_id UUID REFERENCES {schema}.contacts(id) ON DELETE SET NULL,
                deal_id UUID REFERENCES {schema}.deals(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TIMESTAMP WITH TIME ZONE,
                completed BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        # Indexes
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_contacts_company ON {schema}.contacts (company_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_deals_stage ON {schema}.deals (stage_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_deals_company ON {schema}.deals (company_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_activities_deal ON {schema}.activities (deal_id)"))

        # Insert default stages if none exist
        count_result = await conn.execute(
            text(f"SELECT COUNT(*) FROM {schema}.pipeline_stages")
        )
        count = count_result.scalar() or 0
        if count == 0:
            for name, prob, order, color in _DEFAULT_STAGES:
                await conn.execute(
                    text(f"""
                        INSERT INTO {schema}.pipeline_stages (name, probability, order_index, color, is_default)
                        VALUES (:name, :prob, :order_index, :color, true)
                    """),
                    {"name": name, "prob": prob, "order_index": order, "color": color},
                )
    logger.info("CRM tables ensured for tenant %s", tenant_id)


# ---------------------------------------------------------------------------
# Endpoints — Setup
# ---------------------------------------------------------------------------


@router.post("/setup")
async def setup_crm(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    await ensure_crm_tables(str(current_tenant.id))
    return {"status": "ready"}


# --- Companies ---


@router.get("/companies")
async def list_companies(
    search: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.companies WHERE 1=1"
        params: dict[str, Any] = {}
        if search:
            query += " AND name ILIKE :search"
            params["search"] = f"%{search}%"
        query += " ORDER BY name"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/companies", status_code=201)
async def create_company(
    payload: CompanyCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.companies
                    (name, industry, size, website, phone, address, notes)
                VALUES (:name, :industry, :size, :website, :phone, :address, :notes)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/companies/{company_id}")
async def get_company(
    company_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.companies WHERE id = :id"),
            {"id": company_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return dict(row)


@router.put("/companies/{company_id}")
async def update_company(
    company_id: str,
    payload: CompanyUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.companies WHERE id = :id"),
                {"id": company_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Company not found")
            return dict(row)
        updates["updated_at"] = datetime.utcnow()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = company_id
        result = await conn.execute(
            text(f"UPDATE {schema}.companies SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return dict(row)


@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"DELETE FROM {schema}.companies WHERE id = :id RETURNING id"),
            {"id": company_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Company not found")
        return {"status": "deleted"}


@router.get("/companies/{company_id}/contacts")
async def get_company_contacts(
    company_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.contacts WHERE company_id = :company_id ORDER BY last_name"),
            {"company_id": company_id},
        )
        return [dict(r) for r in result.mappings().all()]


@router.get("/companies/{company_id}/deals")
async def get_company_deals(
    company_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.deals WHERE company_id = :company_id ORDER BY created_at DESC"),
            {"company_id": company_id},
        )
        return [dict(r) for r in result.mappings().all()]


# --- Contacts ---


@router.get("/contacts")
async def list_contacts(
    search: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.contacts WHERE 1=1"
        params: dict[str, Any] = {}
        if search:
            query += " AND (first_name ILIKE :search OR last_name ILIKE :search OR email ILIKE :search)"
            params["search"] = f"%{search}%"
        if company_id:
            query += " AND company_id = :company_id"
            params["company_id"] = company_id
        query += " ORDER BY last_name, first_name"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/contacts", status_code=201)
async def create_contact(
    payload: ContactCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.contacts
                    (first_name, last_name, email, phone, job_title, company_id, is_primary, notes)
                VALUES (:first_name, :last_name, :email, :phone, :job_title, :company_id, :is_primary, :notes)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.contacts WHERE id = :id"),
            {"id": contact_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        return dict(row)


@router.put("/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    payload: ContactUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.contacts WHERE id = :id"),
                {"id": contact_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Contact not found")
            return dict(row)
        updates["updated_at"] = datetime.utcnow()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = contact_id
        result = await conn.execute(
            text(f"UPDATE {schema}.contacts SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        return dict(row)


@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"DELETE FROM {schema}.contacts WHERE id = :id RETURNING id"),
            {"id": contact_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {"status": "deleted"}


# --- Deals ---


@router.get("/deals")
async def list_deals(
    status: Optional[str] = Query(None),
    stage_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.deals WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if stage_id:
            query += " AND stage_id = :stage_id"
            params["stage_id"] = stage_id
        if search:
            query += " AND title ILIKE :search"
            params["search"] = f"%{search}%"
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/deals", status_code=201)
async def create_deal(
    payload: DealCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.deals
                    (title, company_id, contact_id, stage_id, value, currency,
                     probability, expected_close, owner_name, notes)
                VALUES (:title, :company_id, :contact_id, :stage_id, :value, :currency,
                        :probability, :expected_close, :owner_name, :notes)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.deals WHERE id = :id"),
            {"id": deal_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Deal not found")
        return dict(row)


@router.put("/deals/{deal_id}")
async def update_deal(
    deal_id: str,
    payload: DealUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.deals WHERE id = :id"),
                {"id": deal_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Deal not found")
            return dict(row)
        updates["updated_at"] = datetime.utcnow()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = deal_id
        result = await conn.execute(
            text(f"UPDATE {schema}.deals SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Deal not found")
        return dict(row)


@router.delete("/deals/{deal_id}")
async def delete_deal(
    deal_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"DELETE FROM {schema}.deals WHERE id = :id RETURNING id"),
            {"id": deal_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Deal not found")
        return {"status": "deleted"}


@router.put("/deals/{deal_id}/stage")
async def update_deal_stage(
    deal_id: str,
    payload: DealStageUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        # Get stage probability
        stage_result = await conn.execute(
            text(f"SELECT probability FROM {schema}.pipeline_stages WHERE id = :id"),
            {"id": payload.stage_id},
        )
        stage = stage_result.mappings().one_or_none()
        if stage is None:
            raise HTTPException(status_code=404, detail="Stage not found")

        result = await conn.execute(
            text(f"""
                UPDATE {schema}.deals
                SET stage_id = :stage_id, probability = :probability, updated_at = now()
                WHERE id = :id RETURNING *
            """),
            {"id": deal_id, "stage_id": payload.stage_id, "probability": stage["probability"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Deal not found")
        return dict(row)


# --- Pipeline (Kanban) ---


@router.get("/pipeline")
async def get_pipeline(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        stages_result = await conn.execute(
            text(f"SELECT * FROM {schema}.pipeline_stages ORDER BY order_index")
        )
        stages = [dict(r) for r in stages_result.mappings().all()]

        deals_result = await conn.execute(
            text(f"SELECT * FROM {schema}.deals WHERE status = 'open' ORDER BY created_at DESC")
        )
        deals = [dict(r) for r in deals_result.mappings().all()]

        # Group deals by stage
        deals_by_stage: dict[str, list[dict[str, Any]]] = {}
        for deal in deals:
            sid = str(deal["stage_id"])
            deals_by_stage.setdefault(sid, []).append(deal)

        for stage in stages:
            stage["deals"] = deals_by_stage.get(str(stage["id"]), [])

    return {"stages": stages}


# --- Activities ---


@router.get("/activities")
async def list_activities(
    deal_id: Optional[str] = Query(None),
    contact_id: Optional[str] = Query(None),
    completed: Optional[bool] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.activities WHERE 1=1"
        params: dict[str, Any] = {}
        if deal_id:
            query += " AND deal_id = :deal_id"
            params["deal_id"] = deal_id
        if contact_id:
            query += " AND contact_id = :contact_id"
            params["contact_id"] = contact_id
        if completed is not None:
            query += " AND completed = :completed"
            params["completed"] = completed
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/activities", status_code=201)
async def create_activity(
    payload: ActivityCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.activities
                    (type, contact_id, deal_id, title, description, due_date, completed)
                VALUES (:type, :contact_id, :deal_id, :title, :description, :due_date, :completed)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.put("/activities/{activity_id}/complete")
async def complete_activity(
    activity_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.activities SET completed = true WHERE id = :id RETURNING *"
            ),
            {"id": activity_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Activity not found")
        return dict(row)


# --- Dashboard ---


@router.get("/dashboard")
async def crm_dashboard(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        # Pipeline value
        pv = await conn.execute(text(f"""
            SELECT COALESCE(SUM(value), 0) FROM {schema}.deals WHERE status = 'open'
        """))
        pipeline_value = float(pv.scalar() or 0)

        # Deals by stage
        dbs = await conn.execute(text(f"""
            SELECT ps.name AS stage, COUNT(d.id) AS count, COALESCE(SUM(d.value), 0) AS value
            FROM {schema}.pipeline_stages ps
            LEFT JOIN {schema}.deals d ON d.stage_id = ps.id AND d.status = 'open'
            GROUP BY ps.id, ps.name, ps.order_index
            ORDER BY ps.order_index
        """))
        deals_by_stage = [dict(r) for r in dbs.mappings().all()]

        # Win rate
        wr = await conn.execute(text(f"""
            SELECT
                COUNT(*) FILTER (WHERE status = 'won') AS won,
                COUNT(*) FILTER (WHERE status IN ('won', 'lost')) AS closed
            FROM {schema}.deals
        """))
        wr_row = wr.mappings().one()
        won = wr_row["won"] or 0
        closed = wr_row["closed"] or 0
        win_rate = round((won / closed * 100) if closed > 0 else 0, 1)

        # Activities this week
        atw = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.activities
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """))
        activities_this_week = int(atw.scalar() or 0)

        # Top deals
        td = await conn.execute(text(f"""
            SELECT id::text, title, value, currency, status
            FROM {schema}.deals
            WHERE status = 'open'
            ORDER BY value DESC
            LIMIT 5
        """))
        top_deals = [dict(r) for r in td.mappings().all()]

    return {
        "pipeline_value": pipeline_value,
        "deals_by_stage": deals_by_stage,
        "win_rate": win_rate,
        "activities_this_week": activities_this_week,
        "top_deals": top_deals,
    }
