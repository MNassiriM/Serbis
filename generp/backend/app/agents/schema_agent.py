"""
Schema Agent — generates a PostgreSQL-ready data schema from a business description.

Uses Claude to produce a structured JSON schema, then presents it to the user
for validation before any DDL is executed.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

if TYPE_CHECKING:
    from langchain_anthropic import ChatAnthropic
    from app.agents.orchestrator import OrchestratorState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed SQL types whitelist (security: prevent LLM DDL injection)
# ---------------------------------------------------------------------------
ALLOWED_SQL_TYPES: frozenset[str] = frozenset(
    {
        "uuid",
        "text",
        "integer",
        "bigint",
        "smallint",
        "boolean",
        "timestamp",
        "timestamptz",
        "date",
        "jsonb",
        "json",
        "text[]",
        "uuid[]",
    }
    | {f"varchar({n})" for n in range(1, 1025)}
    | {f"decimal({p},{s})" for p in range(1, 38) for s in range(0, p)}
    | {f"numeric({p},{s})" for p in range(1, 38) for s in range(0, p)}
)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SCHEMA_SYSTEM_PROMPT = """Tu es un expert en modélisation de données ERP. Ton rôle est d'analyser \
la description métier d'une entreprise et de générer un schéma de données PostgreSQL précis et adapté.

Tu dois générer un objet JSON avec cette structure exacte :
{
  "entities": [
    {
      "name": "string (snake_case, singulier)",
      "display_name": "string (français, pluriel)",
      "description": "string",
      "category": "finance|crm|hr|supply_chain",
      "fields": [
        {
          "name": "string (snake_case)",
          "display_name": "string (français)",
          "type": "uuid|text|varchar(n)|integer|decimal(10,2)|boolean|timestamp|date|jsonb|text[]",
          "required": boolean,
          "unique": boolean,
          "default": "any|null",
          "description": "string"
        }
      ],
      "relations": [
        {
          "name": "string",
          "type": "many_to_one|one_to_many|many_to_many",
          "target_entity": "string",
          "foreign_key": "string",
          "description": "string"
        }
      ],
      "indexes": ["field_name"],
      "default_sort": "field_name"
    }
  ],
  "business_context": "string (résumé de la compréhension du métier)",
  "suggested_workflows": ["string"]
}

RÈGLES IMPÉRATIVES :
- Toujours inclure id (uuid), created_at (timestamp), updated_at (timestamp) dans chaque entité
- Nommer les foreign keys : {entity_name}_id
- Utiliser decimal(10,2) pour tous les montants financiers
- Ne jamais stocker de mots de passe ou données sensibles en clair
- Proposer au maximum 5-8 entités pour un MVP
- Préférer des schémas simples et extensibles plutôt que complexes
- Répondre UNIQUEMENT avec le JSON valide, sans texte avant ou après"""


class SchemaAgent:
    """Agent responsible for generating ERP data schemas from business descriptions."""

    def __init__(self, llm: ChatAnthropic) -> None:
        self._llm = llm

    async def run(self, state: OrchestratorState) -> OrchestratorState:
        """
        Main entry point called by the LangGraph orchestrator.
        Generates a schema and stores it as pending_schema for user confirmation.
        """
        try:
            schema = await self._generate_schema(state.user_message)
            validated = self._validate_schema(schema)

            state.pending_schema = validated
            state.response_text = self._format_confirmation_message(validated)
            state.actions.append(
                {"action": "schema_generated", "schema": validated}
            )
        except Exception as exc:
            logger.exception("SchemaAgent error: %s", exc)
            state.response_text = (
                "Je n'ai pas pu générer le schéma de données. "
                "Pourriez-vous décrire votre activité plus en détail ? "
                "Par exemple : le type d'entreprise, les entités principales que vous gérez, "
                "et les informations clés que vous souhaitez enregistrer."
            )
            state.error = str(exc)

        return state

    async def _generate_schema(self, business_description: str) -> dict[str, Any]:
        """Call Claude to generate a JSON schema from the business description."""
        messages = [
            SystemMessage(content=_SCHEMA_SYSTEM_PROMPT),
            HumanMessage(content=business_description),
        ]
        response = await self._llm.ainvoke(messages)
        content = str(response.content).strip()

        # Strip potential markdown code fences
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()

        parsed: dict[str, Any] = json.loads(content)
        return parsed

    def _validate_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Validate the LLM-generated schema for security and correctness.

        Raises ValueError if validation fails.
        """
        if "entities" not in schema or not isinstance(schema["entities"], list):
            raise ValueError("Schema must contain an 'entities' list")

        if len(schema["entities"]) > 8:
            raise ValueError("Schema must not exceed 8 entities for MVP")

        for entity in schema["entities"]:
            self._validate_entity(entity)

        return schema

    def _validate_entity(self, entity: dict[str, Any]) -> None:
        """Validate a single entity definition."""
        required_keys = {"name", "display_name", "fields"}
        missing = required_keys - entity.keys()
        if missing:
            raise ValueError(f"Entity missing required keys: {missing}")

        name = entity["name"]
        if not name.replace("_", "").isalnum():
            raise ValueError(f"Entity name contains invalid characters: {name!r}")

        required_fields = {"id", "created_at", "updated_at"}
        field_names = {f["name"] for f in entity.get("fields", [])}
        missing_fields = required_fields - field_names
        if missing_fields:
            # Auto-add missing system fields rather than rejecting
            for field_name in missing_fields:
                entity["fields"].append(self._make_system_field(field_name))

        for field in entity["fields"]:
            self._validate_field(field)

    def _validate_field(self, field: dict[str, Any]) -> None:
        """Validate a single field definition, checking type against the whitelist."""
        field_name = field.get("name", "")
        if not field_name.replace("_", "").isalnum():
            raise ValueError(f"Field name contains invalid characters: {field_name!r}")

        field_type = field.get("type", "").lower()
        if field_type not in ALLOWED_SQL_TYPES:
            # Try to map common aliases
            mapped = self._map_type(field_type)
            if mapped is None:
                raise ValueError(
                    f"Field '{field_name}' has disallowed SQL type: {field_type!r}. "
                    f"Allowed types: {sorted(ALLOWED_SQL_TYPES)[:10]}..."
                )
            field["type"] = mapped

    @staticmethod
    def _map_type(raw_type: str) -> str | None:
        """Map common LLM type aliases to whitelisted SQL types."""
        aliases: dict[str, str] = {
            "string": "text",
            "str": "text",
            "int": "integer",
            "float": "decimal(10,2)",
            "number": "decimal(10,2)",
            "bool": "boolean",
            "datetime": "timestamp",
            "timestamp with time zone": "timestamptz",
            "character varying": "text",
        }
        return aliases.get(raw_type.lower())

    @staticmethod
    def _make_system_field(name: str) -> dict[str, Any]:
        """Generate a standard system field (id, created_at, updated_at)."""
        definitions: dict[str, dict[str, Any]] = {
            "id": {
                "name": "id",
                "display_name": "Identifiant",
                "type": "uuid",
                "required": True,
                "unique": True,
                "default": "gen_random_uuid()",
                "description": "Identifiant unique",
            },
            "created_at": {
                "name": "created_at",
                "display_name": "Créé le",
                "type": "timestamp",
                "required": True,
                "unique": False,
                "default": "now()",
                "description": "Date de création",
            },
            "updated_at": {
                "name": "updated_at",
                "display_name": "Modifié le",
                "type": "timestamp",
                "required": True,
                "unique": False,
                "default": "now()",
                "description": "Date de dernière modification",
            },
        }
        return definitions[name]

    @staticmethod
    def _format_confirmation_message(schema: dict[str, Any]) -> str:
        """Format a human-readable schema summary for user confirmation."""
        context = schema.get("business_context", "")
        entities = schema.get("entities", [])

        lines = [f"Voici ce que j'ai compris de votre activité : {context}", ""]
        lines.append("J'ai défini les éléments suivants :")
        for entity in entities:
            display = entity.get("display_name", entity["name"])
            fields = entity.get("fields", [])
            visible_fields = [
                f["display_name"]
                for f in fields
                if f["name"] not in ("id", "created_at", "updated_at")
            ][:5]
            lines.append(
                f"  • **{display}** — {', '.join(visible_fields)}"
                + ("…" if len(fields) > 8 else "")
            )

        workflows = schema.get("suggested_workflows", [])
        if workflows:
            lines.append("")
            lines.append("Processus suggérés :")
            for w in workflows[:3]:
                lines.append(f"  → {w}")

        lines.append("")
        lines.append(
            "Est-ce que cela correspond à vos besoins ? "
            "Répondez **Oui** pour déployer votre ERP, "
            "ou décrivez les modifications souhaitées."
        )

        return "\n".join(lines)
