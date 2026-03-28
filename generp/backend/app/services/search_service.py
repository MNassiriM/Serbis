"""
Search Service — full-text search across tenant schema tables using PostgreSQL.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from app.core.database import get_tenant_engine

logger = logging.getLogger(__name__)

# Known searchable entities with their tables and display columns
_SEARCHABLE_ENTITIES: dict[str, dict[str, Any]] = {
    "invoices": {
        "display_col": "client_name",
        "search_cols": ["client_name", "number", "notes"],
        "text_col": "client_name || ' ' || number",
    },
    "quotes": {
        "display_col": "client_name",
        "search_cols": ["client_name", "number"],
        "text_col": "client_name || ' ' || number",
    },
    "companies": {
        "display_col": "name",
        "search_cols": ["name", "industry", "notes"],
        "text_col": "name",
    },
    "contacts": {
        "display_col": "first_name || ' ' || last_name",
        "search_cols": ["first_name", "last_name", "email", "job_title"],
        "text_col": "first_name || ' ' || last_name || ' ' || coalesce(email, '')",
    },
    "deals": {
        "display_col": "title",
        "search_cols": ["title", "notes"],
        "text_col": "title",
    },
    "employees": {
        "display_col": "first_name || ' ' || last_name",
        "search_cols": ["first_name", "last_name", "email", "position"],
        "text_col": "first_name || ' ' || last_name || ' ' || coalesce(email, '')",
    },
    "products": {
        "display_col": "name",
        "search_cols": ["name", "sku", "description"],
        "text_col": "name || ' ' || sku",
    },
    "suppliers": {
        "display_col": "name",
        "search_cols": ["name", "contact_name", "email"],
        "text_col": "name",
    },
    "projects": {
        "display_col": "name",
        "search_cols": ["name", "description"],
        "text_col": "name",
    },
    "tasks": {
        "display_col": "title",
        "search_cols": ["title", "description"],
        "text_col": "title",
    },
}


class SearchService:
    """Performs full-text search across tenant schema tables."""

    def __init__(self) -> None:
        pass

    async def search(
        self,
        tenant_id: str,
        query: str,
        entities: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Search across tenant tables using PostgreSQL full-text search.

        Returns {"results": {"entity_name": [{"id", "display", "score"}]}}
        """
        schema = f"tenant_{tenant_id.replace('-', '_')}"
        engine = get_tenant_engine(tenant_id)

        # Filter entities if specified
        targets = _SEARCHABLE_ENTITIES
        if entities:
            targets = {k: v for k, v in _SEARCHABLE_ENTITIES.items() if k in entities}

        results: dict[str, list[dict[str, Any]]] = {}

        async with engine.connect() as conn:
            # Check which tables actually exist in this tenant's schema
            existing_tables_result = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = :schema"
                ),
                {"schema": schema},
            )
            existing_tables = {row[0] for row in existing_tables_result.fetchall()}

            for entity_name, config in targets.items():
                if entity_name not in existing_tables:
                    continue

                try:
                    display_expr = config["display_col"]
                    text_expr = config["text_col"]

                    sql = text(f"""
                        SELECT
                            id::text,
                            ({display_expr}) AS display,
                            ts_rank(
                                to_tsvector('french', {text_expr}),
                                plainto_tsquery('french', :query)
                            ) AS score
                        FROM {schema}.{entity_name}
                        WHERE to_tsvector('french', {text_expr}) @@ plainto_tsquery('french', :query)
                           OR ({text_expr}) ILIKE :like_query
                        ORDER BY score DESC
                        LIMIT 10
                    """)

                    rows = await conn.execute(
                        sql,
                        {"query": query, "like_query": f"%{query}%"},
                    )
                    entity_results = [
                        {
                            "id": row[0],
                            "display": row[1],
                            "score": float(row[2]) if row[2] else 0.0,
                        }
                        for row in rows.fetchall()
                    ]
                    if entity_results:
                        results[entity_name] = entity_results

                except Exception as exc:
                    logger.warning(
                        "Search failed for entity %s: %s", entity_name, exc
                    )
                    continue

        return {"results": results, "query": query}
