"""
Search API — full-text search across tenant schema entities.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

_search_service = SearchService()


@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    entities: Optional[str] = Query(
        None,
        description="Comma-separated list of entities to search (e.g. 'invoices,contacts')",
    ),
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    """
    Full-text search across tenant data.

    Returns results grouped by entity:
    {"results": {"entity_name": [{"id", "display", "score"}]}, "query": "..."}
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    entity_list: Optional[list[str]] = None
    if entities:
        entity_list = [e.strip() for e in entities.split(",") if e.strip()]

    results = await _search_service.search(
        tenant_id=str(current_tenant.id),
        query=q.strip(),
        entities=entity_list,
    )
    return results
