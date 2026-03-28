"""
Finance module — Invoices, Quotes, Payments, Expenses.
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
router = APIRouter(prefix="/finance", tags=["finance"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float


class InvoiceCreate(BaseModel):
    client_name: str
    client_email: Optional[str] = None
    line_items: list[LineItem]
    tax_rate: float = 20.0
    due_date: Optional[date] = None
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    line_items: Optional[list[LineItem]] = None
    tax_rate: Optional[float] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class QuoteCreate(BaseModel):
    client_name: str
    client_email: Optional[str] = None
    line_items: list[LineItem]
    tax_rate: float = 20.0
    valid_until: Optional[date] = None
    notes: Optional[str] = None


class QuoteUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    line_items: Optional[list[LineItem]] = None
    tax_rate: Optional[float] = None
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float
    method: str  # bank_transfer/check/credit_card/cash
    reference: Optional[str] = None
    paid_at: Optional[datetime] = None


class ExpenseCreate(BaseModel):
    category: str
    amount: float
    description: str
    date: date
    receipt_url: Optional[str] = None
    status: str = "pending"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema(tenant_id: str) -> str:
    return f"tenant_{tenant_id.replace('-', '_')}"


def _calculate_totals(line_items: list[LineItem], tax_rate: float) -> dict[str, float]:
    subtotal = sum(item.quantity * item.unit_price for item in line_items)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    return {"subtotal": round(subtotal, 2), "tax_amount": tax_amount, "total": total}


async def _generate_invoice_number(conn: Any, schema: str) -> str:
    result = await conn.execute(text(f"SELECT COUNT(*) FROM {schema}.invoices"))
    count = result.scalar() or 0
    now = datetime.utcnow()
    return f"INV-{now.year}{now.month:02d}-{(count + 1):04d}"


async def _generate_quote_number(conn: Any, schema: str) -> str:
    result = await conn.execute(text(f"SELECT COUNT(*) FROM {schema}.quotes"))
    count = result.scalar() or 0
    now = datetime.utcnow()
    return f"QUO-{now.year}{now.month:02d}-{(count + 1):04d}"


async def _generate_po_number(conn: Any, schema: str) -> str:
    result = await conn.execute(text(f"SELECT COUNT(*) FROM {schema}.purchase_orders"))
    count = result.scalar() or 0
    now = datetime.utcnow()
    return f"PO-{now.year}{now.month:02d}-{(count + 1):04d}"


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------


async def ensure_finance_tables(tenant_id: str) -> None:
    schema = _schema(tenant_id)
    engine = get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.invoices (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                number TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_email TEXT,
                line_items JSONB NOT NULL DEFAULT '[]',
                subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
                tax_rate NUMERIC(5,2) NOT NULL DEFAULT 20,
                tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
                total NUMERIC(12,2) NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                due_date DATE,
                paid_at TIMESTAMP WITH TIME ZONE,
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.payments (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                invoice_id UUID NOT NULL REFERENCES {schema}.invoices(id) ON DELETE CASCADE,
                amount NUMERIC(12,2) NOT NULL,
                method TEXT NOT NULL,
                reference TEXT,
                paid_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.quotes (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                number TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_email TEXT,
                line_items JSONB NOT NULL DEFAULT '[]',
                subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
                tax_rate NUMERIC(5,2) NOT NULL DEFAULT 20,
                tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
                total NUMERIC(12,2) NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                valid_until DATE,
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.expenses (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                category TEXT NOT NULL,
                amount NUMERIC(12,2) NOT NULL,
                description TEXT NOT NULL,
                date DATE NOT NULL,
                receipt_url TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        # Indexes
        await conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_invoices_status ON {schema}.invoices (status)
        """))
        await conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_invoices_client ON {schema}.invoices (client_name)
        """))
        await conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_payments_invoice ON {schema}.payments (invoice_id)
        """))
    logger.info("Finance tables ensured for tenant %s", tenant_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/setup")
async def setup_finance(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    await ensure_finance_tables(str(current_tenant.id))
    return {"status": "ready"}


# --- Invoices ---


@router.get("/invoices/overdue")
async def get_overdue_invoices(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT * FROM {schema}.invoices
            WHERE due_date < CURRENT_DATE
              AND status IN ('sent', 'overdue')
            ORDER BY due_date ASC
        """))
        rows = result.mappings().all()
        return [dict(r) for r in rows]


@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.invoices WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if search:
            query += " AND (client_name ILIKE :search OR number ILIKE :search)"
            params["search"] = f"%{search}%"
        if date_from:
            query += " AND created_at::date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND created_at::date <= :date_to"
            params["date_to"] = date_to
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]


@router.post("/invoices", status_code=201)
async def create_invoice(
    payload: InvoiceCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    totals = _calculate_totals(payload.line_items, payload.tax_rate)
    import json

    async with engine.begin() as conn:
        number = await _generate_invoice_number(conn, schema)
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.invoices
                    (number, client_name, client_email, line_items,
                     subtotal, tax_rate, tax_amount, total, due_date, notes)
                VALUES
                    (:number, :client_name, :client_email, :line_items,
                     :subtotal, :tax_rate, :tax_amount, :total, :due_date, :notes)
                RETURNING *
            """),
            {
                "number": number,
                "client_name": payload.client_name,
                "client_email": payload.client_email,
                "line_items": json.dumps(
                    [item.model_dump() for item in payload.line_items]
                ),
                "subtotal": totals["subtotal"],
                "tax_rate": payload.tax_rate,
                "tax_amount": totals["tax_amount"],
                "total": totals["total"],
                "due_date": payload.due_date,
                "notes": payload.notes,
            },
        )
        row = result.mappings().one()
        return dict(row)


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.invoices WHERE id = :id"),
            {"id": invoice_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return dict(row)


@router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        # Fetch existing
        existing = await conn.execute(
            text(f"SELECT * FROM {schema}.invoices WHERE id = :id"),
            {"id": invoice_id},
        )
        row = existing.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Invoice not found")

        updates: dict[str, Any] = {}
        if payload.client_name is not None:
            updates["client_name"] = payload.client_name
        if payload.client_email is not None:
            updates["client_email"] = payload.client_email
        if payload.due_date is not None:
            updates["due_date"] = payload.due_date
        if payload.notes is not None:
            updates["notes"] = payload.notes
        if payload.status is not None:
            updates["status"] = payload.status
        if payload.line_items is not None:
            tax_rate = payload.tax_rate or row["tax_rate"]
            totals = _calculate_totals(payload.line_items, float(tax_rate))
            updates["line_items"] = json.dumps(
                [item.model_dump() for item in payload.line_items]
            )
            updates["subtotal"] = totals["subtotal"]
            updates["tax_amount"] = totals["tax_amount"]
            updates["total"] = totals["total"]
        if payload.tax_rate is not None:
            updates["tax_rate"] = payload.tax_rate
        updates["updated_at"] = datetime.utcnow()

        if not updates:
            return dict(row)

        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = invoice_id
        result = await conn.execute(
            text(f"UPDATE {schema}.invoices SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        return dict(result.mappings().one())


@router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.invoices SET status='cancelled', updated_at=now()"
                " WHERE id = :id RETURNING id"
            ),
            {"id": invoice_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return {"status": "cancelled"}


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.invoices SET status='sent', updated_at=now()"
                " WHERE id = :id RETURNING id"
            ),
            {"id": invoice_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return {"status": "sent"}


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: str,
    method: str = "bank_transfer",
    reference: Optional[str] = None,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        # Get invoice total
        inv_result = await conn.execute(
            text(f"SELECT * FROM {schema}.invoices WHERE id = :id"),
            {"id": invoice_id},
        )
        invoice = inv_result.mappings().one_or_none()
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")

        now = datetime.utcnow()
        await conn.execute(
            text(
                f"UPDATE {schema}.invoices SET status='paid', paid_at=:paid_at, updated_at=:updated_at"
                " WHERE id = :id"
            ),
            {"id": invoice_id, "paid_at": now, "updated_at": now},
        )
        # Create payment record
        pay_result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.payments (invoice_id, amount, method, reference, paid_at)
                VALUES (:invoice_id, :amount, :method, :reference, :paid_at)
                RETURNING *
            """),
            {
                "invoice_id": invoice_id,
                "amount": invoice["total"],
                "method": method,
                "reference": reference,
                "paid_at": now,
            },
        )
        payment = dict(pay_result.mappings().one())
        return {"status": "paid", "payment": payment}


# --- Quotes ---


@router.get("/quotes")
async def list_quotes(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.quotes WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if search:
            query += " AND (client_name ILIKE :search OR number ILIKE :search)"
            params["search"] = f"%{search}%"
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/quotes", status_code=201)
async def create_quote(
    payload: QuoteCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    totals = _calculate_totals(payload.line_items, payload.tax_rate)
    async with engine.begin() as conn:
        number = await _generate_quote_number(conn, schema)
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.quotes
                    (number, client_name, client_email, line_items,
                     subtotal, tax_rate, tax_amount, total, valid_until, notes)
                VALUES
                    (:number, :client_name, :client_email, :line_items,
                     :subtotal, :tax_rate, :tax_amount, :total, :valid_until, :notes)
                RETURNING *
            """),
            {
                "number": number,
                "client_name": payload.client_name,
                "client_email": payload.client_email,
                "line_items": json.dumps(
                    [item.model_dump() for item in payload.line_items]
                ),
                "subtotal": totals["subtotal"],
                "tax_rate": payload.tax_rate,
                "tax_amount": totals["tax_amount"],
                "total": totals["total"],
                "valid_until": payload.valid_until,
                "notes": payload.notes,
            },
        )
        return dict(result.mappings().one())


@router.get("/quotes/{quote_id}")
async def get_quote(
    quote_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.quotes WHERE id = :id"),
            {"id": quote_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Quote not found")
        return dict(row)


@router.put("/quotes/{quote_id}")
async def update_quote(
    quote_id: str,
    payload: QuoteUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        existing = await conn.execute(
            text(f"SELECT * FROM {schema}.quotes WHERE id = :id"),
            {"id": quote_id},
        )
        row = existing.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Quote not found")

        updates: dict[str, Any] = {}
        if payload.client_name is not None:
            updates["client_name"] = payload.client_name
        if payload.client_email is not None:
            updates["client_email"] = payload.client_email
        if payload.valid_until is not None:
            updates["valid_until"] = payload.valid_until
        if payload.notes is not None:
            updates["notes"] = payload.notes
        if payload.status is not None:
            updates["status"] = payload.status
        if payload.line_items is not None:
            tax_rate = payload.tax_rate or row["tax_rate"]
            totals = _calculate_totals(payload.line_items, float(tax_rate))
            updates["line_items"] = json.dumps(
                [item.model_dump() for item in payload.line_items]
            )
            updates["subtotal"] = totals["subtotal"]
            updates["tax_amount"] = totals["tax_amount"]
            updates["total"] = totals["total"]
        if payload.tax_rate is not None:
            updates["tax_rate"] = payload.tax_rate
        updates["updated_at"] = datetime.utcnow()

        if not updates:
            return dict(row)

        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = quote_id
        result = await conn.execute(
            text(f"UPDATE {schema}.quotes SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        return dict(result.mappings().one())


@router.post("/quotes/{quote_id}/accept")
async def accept_quote(
    quote_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        quote_result = await conn.execute(
            text(f"SELECT * FROM {schema}.quotes WHERE id = :id"),
            {"id": quote_id},
        )
        quote = quote_result.mappings().one_or_none()
        if quote is None:
            raise HTTPException(status_code=404, detail="Quote not found")

        # Mark quote as accepted
        await conn.execute(
            text(
                f"UPDATE {schema}.quotes SET status='accepted', updated_at=now() WHERE id = :id"
            ),
            {"id": quote_id},
        )

        # Convert to invoice
        inv_number = await _generate_invoice_number(conn, schema)
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.invoices
                    (number, client_name, client_email, line_items,
                     subtotal, tax_rate, tax_amount, total, notes)
                VALUES
                    (:number, :client_name, :client_email, :line_items,
                     :subtotal, :tax_rate, :tax_amount, :total, :notes)
                RETURNING *
            """),
            {
                "number": inv_number,
                "client_name": quote["client_name"],
                "client_email": quote["client_email"],
                "line_items": json.dumps(quote["line_items"])
                if not isinstance(quote["line_items"], str)
                else quote["line_items"],
                "subtotal": quote["subtotal"],
                "tax_rate": quote["tax_rate"],
                "tax_amount": quote["tax_amount"],
                "total": quote["total"],
                "notes": quote["notes"],
            },
        )
        invoice = dict(result.mappings().one())
        return {"quote_accepted": True, "invoice": invoice}


# --- Payments ---


@router.get("/payments")
async def list_payments(
    invoice_id: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.payments WHERE 1=1"
        params: dict[str, Any] = {}
        if invoice_id:
            query += " AND invoice_id = :invoice_id"
            params["invoice_id"] = invoice_id
        query += " ORDER BY paid_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


# --- Expenses ---


@router.get("/expenses")
async def list_expenses(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.expenses WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if category:
            query += " AND category = :category"
            params["category"] = category
        query += " ORDER BY date DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/expenses", status_code=201)
async def create_expense(
    payload: ExpenseCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.expenses
                    (category, amount, description, date, receipt_url, status)
                VALUES (:category, :amount, :description, :date, :receipt_url, :status)
                RETURNING *
            """),
            {
                "category": payload.category,
                "amount": payload.amount,
                "description": payload.description,
                "date": payload.date,
                "receipt_url": payload.receipt_url,
                "status": payload.status,
            },
        )
        return dict(result.mappings().one())


# --- Dashboard ---


@router.get("/dashboard")
async def finance_dashboard(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        # Monthly revenue (last 12 months)
        monthly = await conn.execute(text(f"""
            SELECT
                TO_CHAR(DATE_TRUNC('month', paid_at), 'YYYY-MM') AS month,
                SUM(total) AS total
            FROM {schema}.invoices
            WHERE status = 'paid'
              AND paid_at >= NOW() - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', paid_at)
            ORDER BY DATE_TRUNC('month', paid_at)
        """))
        monthly_revenue = [dict(r) for r in monthly.mappings().all()]

        # Outstanding amount (sent invoices)
        outstanding = await conn.execute(text(f"""
            SELECT COALESCE(SUM(total), 0) AS amount
            FROM {schema}.invoices WHERE status = 'sent'
        """))
        outstanding_amount = float(outstanding.scalar() or 0)

        # Overdue amount
        overdue = await conn.execute(text(f"""
            SELECT COALESCE(SUM(total), 0) AS amount
            FROM {schema}.invoices WHERE status = 'overdue'
        """))
        overdue_amount = float(overdue.scalar() or 0)

        # Paid this month
        paid_month = await conn.execute(text(f"""
            SELECT COALESCE(SUM(total), 0) AS amount
            FROM {schema}.invoices
            WHERE status = 'paid'
              AND DATE_TRUNC('month', paid_at) = DATE_TRUNC('month', NOW())
        """))
        paid_this_month = float(paid_month.scalar() or 0)

        # Count by status
        counts = await conn.execute(text(f"""
            SELECT status, COUNT(*) AS count
            FROM {schema}.invoices
            GROUP BY status
        """))
        invoice_count_by_status = {r["status"]: r["count"] for r in counts.mappings().all()}

        # Top clients
        top_clients = await conn.execute(text(f"""
            SELECT client_name, SUM(total) AS total_revenue
            FROM {schema}.invoices
            WHERE status = 'paid'
            GROUP BY client_name
            ORDER BY total_revenue DESC
            LIMIT 5
        """))
        top_clients_list = [dict(r) for r in top_clients.mappings().all()]

    return {
        "monthly_revenue": monthly_revenue,
        "outstanding_amount": outstanding_amount,
        "overdue_amount": overdue_amount,
        "paid_this_month": paid_this_month,
        "invoice_count_by_status": invoice_count_by_status,
        "top_clients": top_clients_list,
    }
