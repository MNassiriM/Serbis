"""
Supply Chain module — Products, Warehouses, Stock, Suppliers, Purchase Orders.
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
router = APIRouter(prefix="/supply", tags=["supply"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    unit_price: float
    unit_cost: Optional[float] = None
    unit: str = "pcs"
    min_stock_alert: int = 0
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    unit_price: Optional[float] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = None
    min_stock_alert: Optional[int] = None
    is_active: Optional[bool] = None


class WarehouseCreate(BaseModel):
    name: str
    location: Optional[str] = None
    is_default: bool = False


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    is_default: Optional[bool] = None


class StockMovement(BaseModel):
    product_id: str
    warehouse_id: str
    type: str  # in/out/transfer/adjustment/return
    quantity: float
    reference: Optional[str] = None
    note: Optional[str] = None


class SupplierCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class POLineItem(BaseModel):
    product_id: str
    product_name: str
    quantity: float
    unit_cost: float
    total: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    line_items: list[POLineItem]
    expected_date: Optional[date] = None
    notes: Optional[str] = None


class PurchaseOrderUpdate(BaseModel):
    line_items: Optional[list[POLineItem]] = None
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class POReceiveItem(BaseModel):
    product_id: str
    quantity_received: float


class POReceive(BaseModel):
    items_received: list[POReceiveItem]
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema(tenant_id: str) -> str:
    return f"tenant_{tenant_id.replace('-', '_')}"


async def _generate_po_number(conn: Any, schema: str) -> str:
    result = await conn.execute(text(f"SELECT COUNT(*) FROM {schema}.purchase_orders"))
    count = result.scalar() or 0
    now = datetime.utcnow()
    return f"PO-{now.year}{now.month:02d}-{(count + 1):04d}"


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------


async def ensure_supply_tables(tenant_id: str) -> None:
    schema = _schema(tenant_id)
    engine = get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.warehouses (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT,
                is_default BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.product_categories (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id UUID REFERENCES {schema}.product_categories(id) ON DELETE SET NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.products (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                category_id UUID REFERENCES {schema}.product_categories(id) ON DELETE SET NULL,
                unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
                unit_cost NUMERIC(12,2),
                unit TEXT NOT NULL DEFAULT 'pcs',
                min_stock_alert INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.stock_levels (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                product_id UUID NOT NULL REFERENCES {schema}.products(id) ON DELETE CASCADE,
                warehouse_id UUID NOT NULL REFERENCES {schema}.warehouses(id) ON DELETE CASCADE,
                quantity NUMERIC(12,2) NOT NULL DEFAULT 0,
                reserved NUMERIC(12,2) NOT NULL DEFAULT 0,
                UNIQUE (product_id, warehouse_id)
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.stock_movements (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                product_id UUID NOT NULL REFERENCES {schema}.products(id) ON DELETE CASCADE,
                warehouse_id UUID NOT NULL REFERENCES {schema}.warehouses(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                quantity NUMERIC(12,2) NOT NULL,
                reference TEXT,
                note TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.suppliers (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name TEXT NOT NULL,
                contact_name TEXT,
                email TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                payment_terms TEXT,
                lead_time_days INTEGER,
                notes TEXT,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.purchase_orders (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                supplier_id UUID NOT NULL REFERENCES {schema}.suppliers(id),
                number TEXT NOT NULL,
                line_items JSONB NOT NULL DEFAULT '[]',
                subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
                total NUMERIC(12,2) NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                expected_date DATE,
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.po_receipts (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                po_id UUID NOT NULL REFERENCES {schema}.purchase_orders(id) ON DELETE CASCADE,
                items_received JSONB NOT NULL DEFAULT '[]',
                notes TEXT,
                received_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            )
        """))
        # Indexes
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_products_sku ON {schema}.products (sku)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_stock_levels_product ON {schema}.stock_levels (product_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_stock_movements_product ON {schema}.stock_movements (product_id)"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_po_supplier ON {schema}.purchase_orders (supplier_id)"))
    logger.info("Supply tables ensured for tenant %s", tenant_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/setup")
async def setup_supply(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    await ensure_supply_tables(str(current_tenant.id))
    return {"status": "ready"}


# --- Products ---


@router.get("/products")
async def list_products(
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.products WHERE 1=1"
        params: dict[str, Any] = {}
        if search:
            query += " AND (name ILIKE :search OR sku ILIKE :search)"
            params["search"] = f"%{search}%"
        if category_id:
            query += " AND category_id = :category_id"
            params["category_id"] = category_id
        if is_active is not None:
            query += " AND is_active = :is_active"
            params["is_active"] = is_active
        query += " ORDER BY name"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/products", status_code=201)
async def create_product(
    payload: ProductCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.products
                    (sku, name, description, category_id, unit_price, unit_cost,
                     unit, min_stock_alert, is_active)
                VALUES (:sku, :name, :description, :category_id, :unit_price, :unit_cost,
                        :unit, :min_stock_alert, :is_active)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.products WHERE id = :id"),
            {"id": product_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return dict(row)


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.products WHERE id = :id"),
                {"id": product_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Product not found")
            return dict(row)
        updates["updated_at"] = datetime.utcnow()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = product_id
        result = await conn.execute(
            text(f"UPDATE {schema}.products SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return dict(row)


@router.delete("/products/{product_id}")
async def deactivate_product(
    product_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.products SET is_active=false, updated_at=now()"
                " WHERE id = :id RETURNING id"
            ),
            {"id": product_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"status": "deactivated"}


@router.get("/products/{product_id}/stock")
async def get_product_stock(
    product_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"""
                SELECT
                    sl.warehouse_id::text,
                    w.name AS warehouse_name,
                    sl.quantity,
                    sl.reserved,
                    (sl.quantity - sl.reserved) AS available
                FROM {schema}.stock_levels sl
                JOIN {schema}.warehouses w ON w.id = sl.warehouse_id
                WHERE sl.product_id = :product_id
            """),
            {"product_id": product_id},
        )
        return [dict(r) for r in result.mappings().all()]


# --- Warehouses ---


@router.get("/warehouses")
async def list_warehouses(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.warehouses ORDER BY name")
        )
        return [dict(r) for r in result.mappings().all()]


@router.post("/warehouses", status_code=201)
async def create_warehouse(
    payload: WarehouseCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.warehouses (name, location, is_default)
                VALUES (:name, :location, :is_default)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.put("/warehouses/{warehouse_id}")
async def update_warehouse(
    warehouse_id: str,
    payload: WarehouseUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.warehouses WHERE id = :id"),
                {"id": warehouse_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Warehouse not found")
            return dict(row)
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = warehouse_id
        result = await conn.execute(
            text(f"UPDATE {schema}.warehouses SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        return dict(row)


# --- Stock ---


@router.get("/stock")
async def get_stock_overview(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT
                p.id::text AS product_id,
                p.name AS product,
                p.sku,
                COALESCE(SUM(sl.quantity), 0) AS total_qty,
                JSON_AGG(
                    JSON_BUILD_OBJECT(
                        'warehouse_id', sl.warehouse_id::text,
                        'warehouse_name', w.name,
                        'quantity', sl.quantity,
                        'reserved', sl.reserved
                    )
                ) FILTER (WHERE sl.id IS NOT NULL) AS warehouses
            FROM {schema}.products p
            LEFT JOIN {schema}.stock_levels sl ON sl.product_id = p.id
            LEFT JOIN {schema}.warehouses w ON w.id = sl.warehouse_id
            WHERE p.is_active = true
            GROUP BY p.id, p.name, p.sku
            ORDER BY p.name
        """))
        return [dict(r) for r in result.mappings().all()]


@router.post("/stock/movement", status_code=201)
async def create_stock_movement(
    payload: StockMovement,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        # Create movement record
        mov_result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.stock_movements
                    (product_id, warehouse_id, type, quantity, reference, note)
                VALUES (:product_id, :warehouse_id, :type, :quantity, :reference, :note)
                RETURNING *
            """),
            payload.model_dump(),
        )
        movement = dict(mov_result.mappings().one())

        # Update stock level
        delta = payload.quantity if payload.type in ("in", "return", "adjustment") else -payload.quantity

        await conn.execute(text(f"""
            INSERT INTO {schema}.stock_levels (product_id, warehouse_id, quantity)
            VALUES (:product_id, :warehouse_id, :delta)
            ON CONFLICT (product_id, warehouse_id)
            DO UPDATE SET quantity = stock_levels.quantity + :delta
        """), {
            "product_id": payload.product_id,
            "warehouse_id": payload.warehouse_id,
            "delta": delta,
        })

        return movement


@router.get("/stock/alerts")
async def get_stock_alerts(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT
                p.id::text,
                p.name,
                p.sku,
                p.min_stock_alert,
                COALESCE(SUM(sl.quantity), 0) AS total_qty
            FROM {schema}.products p
            LEFT JOIN {schema}.stock_levels sl ON sl.product_id = p.id
            WHERE p.is_active = true
            GROUP BY p.id, p.name, p.sku, p.min_stock_alert
            HAVING COALESCE(SUM(sl.quantity), 0) <= p.min_stock_alert
            ORDER BY total_qty ASC
        """))
        return [dict(r) for r in result.mappings().all()]


# --- Suppliers ---


@router.get("/suppliers")
async def list_suppliers(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.suppliers WHERE 1=1"
        params: dict[str, Any] = {}
        if search:
            query += " AND name ILIKE :search"
            params["search"] = f"%{search}%"
        if is_active is not None:
            query += " AND is_active = :is_active"
            params["is_active"] = is_active
        query += " ORDER BY name"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/suppliers", status_code=201)
async def create_supplier(
    payload: SupplierCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.suppliers
                    (name, contact_name, email, phone, address, payment_terms, lead_time_days, notes, is_active)
                VALUES (:name, :contact_name, :email, :phone, :address, :payment_terms, :lead_time_days, :notes, :is_active)
                RETURNING *
            """),
            payload.model_dump(),
        )
        return dict(result.mappings().one())


@router.get("/suppliers/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.suppliers WHERE id = :id"),
            {"id": supplier_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Supplier not found")
        return dict(row)


@router.put("/suppliers/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.suppliers WHERE id = :id"),
                {"id": supplier_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Supplier not found")
            return dict(row)
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = supplier_id
        result = await conn.execute(
            text(f"UPDATE {schema}.suppliers SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Supplier not found")
        return dict(row)


# --- Purchase Orders ---


@router.get("/purchase-orders")
async def list_purchase_orders(
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        query = f"SELECT * FROM {schema}.purchase_orders WHERE 1=1"
        params: dict[str, Any] = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if supplier_id:
            query += " AND supplier_id = :supplier_id"
            params["supplier_id"] = supplier_id
        query += " ORDER BY created_at DESC"
        result = await conn.execute(text(query), params)
        return [dict(r) for r in result.mappings().all()]


@router.post("/purchase-orders", status_code=201)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    subtotal = sum(item.quantity * item.unit_cost for item in payload.line_items)
    total = round(subtotal, 2)

    async with engine.begin() as conn:
        number = await _generate_po_number(conn, schema)
        result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.purchase_orders
                    (supplier_id, number, line_items, subtotal, total, expected_date, notes)
                VALUES (:supplier_id, :number, :line_items, :subtotal, :total, :expected_date, :notes)
                RETURNING *
            """),
            {
                "supplier_id": payload.supplier_id,
                "number": number,
                "line_items": json.dumps([item.model_dump() for item in payload.line_items]),
                "subtotal": round(subtotal, 2),
                "total": total,
                "expected_date": payload.expected_date,
                "notes": payload.notes,
            },
        )
        return dict(result.mappings().one())


@router.get("/purchase-orders/{po_id}")
async def get_purchase_order(
    po_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT * FROM {schema}.purchase_orders WHERE id = :id"),
            {"id": po_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        return dict(row)


@router.put("/purchase-orders/{po_id}")
async def update_purchase_order(
    po_id: str,
    payload: PurchaseOrderUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        updates: dict[str, Any] = {}
        if payload.line_items is not None:
            subtotal = sum(item.quantity * item.unit_cost for item in payload.line_items)
            updates["line_items"] = json.dumps([item.model_dump() for item in payload.line_items])
            updates["subtotal"] = round(subtotal, 2)
            updates["total"] = round(subtotal, 2)
        if payload.expected_date is not None:
            updates["expected_date"] = payload.expected_date
        if payload.notes is not None:
            updates["notes"] = payload.notes
        if payload.status is not None:
            updates["status"] = payload.status
        updates["updated_at"] = datetime.utcnow()

        if len(updates) == 1:
            result = await conn.execute(
                text(f"SELECT * FROM {schema}.purchase_orders WHERE id = :id"),
                {"id": po_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Purchase order not found")
            return dict(row)

        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = po_id
        result = await conn.execute(
            text(f"UPDATE {schema}.purchase_orders SET {set_clause} WHERE id = :id RETURNING *"),
            updates,
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        return dict(row)


@router.post("/purchase-orders/{po_id}/send")
async def send_purchase_order(
    po_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                f"UPDATE {schema}.purchase_orders SET status='sent', updated_at=now()"
                " WHERE id = :id RETURNING id"
            ),
            {"id": po_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        return {"status": "sent"}


@router.post("/purchase-orders/{po_id}/receive")
async def receive_purchase_order(
    po_id: str,
    payload: POReceive,
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    import json

    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.begin() as conn:
        # Get PO to find warehouse (use default or first warehouse)
        po_result = await conn.execute(
            text(f"SELECT * FROM {schema}.purchase_orders WHERE id = :id"),
            {"id": po_id},
        )
        po = po_result.mappings().one_or_none()
        if po is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        # Get default warehouse
        wh_result = await conn.execute(
            text(f"SELECT id FROM {schema}.warehouses WHERE is_default = true LIMIT 1")
        )
        wh_row = wh_result.mappings().one_or_none()
        if wh_row is None:
            # Try first warehouse
            wh_result = await conn.execute(
                text(f"SELECT id FROM {schema}.warehouses LIMIT 1")
            )
            wh_row = wh_result.mappings().one_or_none()
        if wh_row is None:
            raise HTTPException(status_code=400, detail="No warehouse configured")

        warehouse_id = str(wh_row["id"])

        # Create receipt
        receipt_result = await conn.execute(
            text(f"""
                INSERT INTO {schema}.po_receipts (po_id, items_received, notes)
                VALUES (:po_id, :items_received, :notes)
                RETURNING *
            """),
            {
                "po_id": po_id,
                "items_received": json.dumps(
                    [item.model_dump() for item in payload.items_received]
                ),
                "notes": payload.notes,
            },
        )
        receipt = dict(receipt_result.mappings().one())

        # Update stock levels for each received item
        for item in payload.items_received:
            await conn.execute(text(f"""
                INSERT INTO {schema}.stock_levels (product_id, warehouse_id, quantity)
                VALUES (:product_id, :warehouse_id, :qty)
                ON CONFLICT (product_id, warehouse_id)
                DO UPDATE SET quantity = stock_levels.quantity + :qty
            """), {
                "product_id": item.product_id,
                "warehouse_id": warehouse_id,
                "qty": item.quantity_received,
            })
            # Create stock movement
            await conn.execute(text(f"""
                INSERT INTO {schema}.stock_movements
                    (product_id, warehouse_id, type, quantity, reference)
                VALUES (:product_id, :warehouse_id, 'in', :quantity, :reference)
            """), {
                "product_id": item.product_id,
                "warehouse_id": warehouse_id,
                "quantity": item.quantity_received,
                "reference": po["number"],
            })

        # Determine new PO status
        # Check if all line items fully received (simple heuristic: mark as received)
        received_ids = {item.product_id for item in payload.items_received}
        all_items = po["line_items"]
        if isinstance(all_items, list):
            all_product_ids = {str(li.get("product_id", "")) for li in all_items}
        else:
            all_product_ids = set()
        new_status = "received" if received_ids >= all_product_ids else "partial"

        await conn.execute(
            text(
                f"UPDATE {schema}.purchase_orders SET status=:status, updated_at=now() WHERE id = :id"
            ),
            {"id": po_id, "status": new_status},
        )

        return {"status": new_status, "receipt": receipt}


# --- Dashboard ---


@router.get("/dashboard")
async def supply_dashboard(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    schema = _schema(str(current_tenant.id))
    engine = get_tenant_engine(str(current_tenant.id))
    async with engine.connect() as conn:
        # Total products
        tp = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.products WHERE is_active = true
        """))
        total_products = int(tp.scalar() or 0)

        # Total stock value
        tsv = await conn.execute(text(f"""
            SELECT COALESCE(SUM(sl.quantity * p.unit_cost), 0)
            FROM {schema}.stock_levels sl
            JOIN {schema}.products p ON p.id = sl.product_id
            WHERE p.unit_cost IS NOT NULL
        """))
        total_stock_value = float(tsv.scalar() or 0)

        # Low stock count
        lsc = await conn.execute(text(f"""
            SELECT COUNT(DISTINCT p.id)
            FROM {schema}.products p
            LEFT JOIN {schema}.stock_levels sl ON sl.product_id = p.id
            WHERE p.is_active = true
            GROUP BY p.id, p.min_stock_alert
            HAVING COALESCE(SUM(sl.quantity), 0) <= p.min_stock_alert
        """))
        low_stock_count = int(lsc.rowcount or 0)

        # Pending orders
        po_count = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.purchase_orders
            WHERE status IN ('draft', 'sent', 'partial')
        """))
        pending_orders = int(po_count.scalar() or 0)

        # Top suppliers
        ts = await conn.execute(text(f"""
            SELECT s.name, COUNT(po.id) AS po_count, COALESCE(SUM(po.total), 0) AS total_value
            FROM {schema}.suppliers s
            LEFT JOIN {schema}.purchase_orders po ON po.supplier_id = s.id
            GROUP BY s.id, s.name
            ORDER BY total_value DESC
            LIMIT 5
        """))
        top_suppliers = [dict(r) for r in ts.mappings().all()]

        # Stock movements this week
        smw = await conn.execute(text(f"""
            SELECT COUNT(*) FROM {schema}.stock_movements
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """))
        stock_movements_this_week = int(smw.scalar() or 0)

    return {
        "total_products": total_products,
        "total_stock_value": total_stock_value,
        "low_stock_count": low_stock_count,
        "pending_orders": pending_orders,
        "top_suppliers": top_suppliers,
        "stock_movements_this_week": stock_movements_this_week,
    }
