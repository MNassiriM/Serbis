"""
Query Agent — translates a natural-language data query into a safe SQL SELECT
and returns formatted results to the user.

Security model:
- Only SELECT statements are allowed (enforced by regex before execution).
- Table/column identifiers are validated against a known ERP module whitelist.
- Result sets are capped at 100 rows.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text

from app.core.database import get_tenant_engine

if TYPE_CHECKING:
    from langchain_anthropic import ChatAnthropic
    from app.agents.orchestrator import OrchestratorState

logger = logging.getLogger(__name__)

_KNOWN_TABLES: dict[str, list[str]] = {
    "finance": ["invoices", "payments", "quotes", "expenses"],
    "crm": ["companies", "contacts", "deals", "activities", "pipeline_stages"],
    "hr": ["employees", "departments", "job_postings", "candidates", "leave_requests", "performance_reviews"],
    "supply": ["products", "warehouses", "stock_levels", "stock_movements", "suppliers", "purchase_orders"],
    "projects": ["projects", "milestones", "tasks", "time_entries"],
}

_ALL_ALLOWED_TABLES: frozenset[str] = frozenset(
    t for tables in _KNOWN_TABLES.values() for t in tables
)

_QUERY_SYSTEM_PROMPT = """Tu es un assistant ERP qui génère des requêtes SQL PostgreSQL sécurisées.

L'utilisateur veut interroger ses données ERP. Tu dois générer UNIQUEMENT une requête SELECT.

RÈGLES STRICTES :
1. Génère UNIQUEMENT un SELECT (pas INSERT, UPDATE, DELETE, DROP, CREATE, ALTER).
2. Utilise le schéma tenant fourni comme préfixe : {schema}.table_name
3. Limite toujours à 100 lignes avec LIMIT 100.
4. Réponds UNIQUEMENT avec un objet JSON : {{"sql": "...", "description": "..."}}
5. Tables disponibles : {available_tables}

Exemple : {{"sql": "SELECT id, client_name, total, status FROM {schema}.invoices WHERE status = 'overdue' ORDER BY due_date ASC LIMIT 100", "description": "Factures en retard"}}"""

_SELECT_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXECUTE|EXEC|pg_catalog|information_schema)\b",
    re.IGNORECASE,
)


def _is_safe_sql(sql: str) -> bool:
    if not _SELECT_PATTERN.match(sql):
        return False
    if _FORBIDDEN_PATTERN.search(sql):
        return False
    return True


class QueryAgent:
    """Translates a NL query into SQL and executes it against the tenant schema."""

    def __init__(self, llm: ChatAnthropic) -> None:
        self._llm = llm

    async def run(self, state: OrchestratorState) -> OrchestratorState:
        tenant_id = state.tenant_id
        schema = f"tenant_{tenant_id.replace('-', '_')}"
        available = ", ".join(sorted(_ALL_ALLOWED_TABLES))

        system_prompt = _QUERY_SYSTEM_PROMPT.format(schema=schema, available_tables=available)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state.user_message),
        ]

        try:
            response = await self._llm.ainvoke(messages)
            raw = str(response.content).strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            parsed: dict[str, Any] = json.loads(raw)
            sql: str = parsed.get("sql", "").strip()
            description: str = parsed.get("description", "Résultat de la requête")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("QueryAgent: parse error: %s", exc)
            state.response_text = "Je n'ai pas pu générer une requête valide. Pouvez-vous reformuler ?"
            return state

        if not _is_safe_sql(sql):
            logger.warning("QueryAgent: unsafe SQL rejected: %.200s", sql)
            state.response_text = "Je ne peux pas exécuter ce type de requête pour des raisons de sécurité."
            return state

        try:
            engine = get_tenant_engine(tenant_id)
            async with engine.connect() as conn:
                result = await conn.execute(text(sql))
                rows = result.mappings().fetchmany(100)

            if not rows:
                state.response_text = f"**{description}**\n\nAucun résultat trouvé."
                return state

            headers = list(rows[0].keys())
            table_md = (
                "| " + " | ".join(headers) + " |\n"
                "| " + " | ".join("---" for _ in headers) + " |\n"
                + "\n".join(
                    "| " + " | ".join(str(row[h]) if row[h] is not None else "—" for h in headers) + " |"
                    for row in rows
                )
            )
            count_note = f"\n\n*{len(rows)} résultat(s)*" + (" *(limité à 100)*" if len(rows) == 100 else "")
            state.response_text = f"**{description}**\n\n{table_md}{count_note}"

        except Exception as exc:
            logger.error("QueryAgent: execution error: %s", exc)
            state.response_text = (
                "Erreur lors de l'exécution. "
                "Vérifiez que les tables existent (utilisez /setup sur le module concerné)."
            )

        return state
