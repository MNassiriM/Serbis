"""
UI Agent — generates json-render compatible UI configurations for ERP modules.

Produces list_view, create_form, detail_view, and dashboard configs
for each entity in the validated schema.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_anthropic import ChatAnthropic
    from app.agents.orchestrator import OrchestratorState

logger = logging.getLogger(__name__)


class UIAgent:
    """
    Generates UI configurations for ERP modules.

    The output is a JSON structure compatible with @vercel/json-render
    and RJSF (React JSON Schema Form).
    """

    def __init__(self, llm: ChatAnthropic) -> None:
        self._llm = llm

    async def generate_ui_configs(
        self,
        schema: dict[str, Any],
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """
        Generate UI configs for all entities in the schema.

        Returns a list of dicts: [{"module": name, "config": {...}}, ...]
        """
        ui_updates: list[dict[str, Any]] = []

        for entity in schema.get("entities", []):
            config = self._build_module_config(entity, tenant_id)
            ui_updates.append(
                {
                    "module": entity["name"],
                    "display_name": entity.get("display_name", entity["name"]),
                    "category": entity.get("category", "general"),
                    "config": config,
                }
            )

        return ui_updates

    async def run(self, state: OrchestratorState) -> OrchestratorState:
        """LangGraph node entry point."""
        if not state.pending_schema:
            state.response_text = "Aucun schéma disponible pour générer l'interface."
            return state

        ui_configs = await self.generate_ui_configs(
            schema=state.pending_schema,
            tenant_id=state.tenant_id,
        )
        state.ui_updates = ui_configs
        state.response_text = "L'interface utilisateur a été générée."
        return state

    def _build_module_config(
        self, entity: dict[str, Any], tenant_id: str
    ) -> dict[str, Any]:
        """Build the complete UI config for a single entity/module."""
        name = entity["name"]
        display_name = entity.get("display_name", name)
        fields = entity.get("fields", [])

        # Filter out system/internal fields for UI
        visible_fields = [
            f for f in fields if f["name"] not in ("created_at", "updated_at")
        ]
        list_fields = [f for f in visible_fields if f["name"] != "id"][:6]

        return {
            "module_name": name,
            "display_name": display_name,
            "api_base": f"/api/v1/data/{tenant_id}/{name}",
            "list_view": self._build_list_view(name, display_name, list_fields),
            "create_form": self._build_form_schema(name, display_name, visible_fields),
            "detail_view": self._build_detail_view(name, display_name, visible_fields),
            "dashboard": self._build_dashboard_config(name, display_name),
        }

    @staticmethod
    def _build_list_view(
        name: str,
        display_name: str,
        fields: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a TanStack Table compatible list view configuration."""
        columns = [
            {
                "id": field["name"],
                "header": field.get("display_name", field["name"]),
                "accessorKey": field["name"],
                "type": _map_field_type_to_ui(field["type"]),
                "sortable": True,
                "filterable": field["type"] in ("text", "varchar", "boolean"),
            }
            for field in fields
        ]

        return {
            "type": "data_table",
            "title": display_name,
            "columns": columns,
            "actions": [
                {"label": "Créer", "type": "create", "variant": "primary"},
                {"label": "Modifier", "type": "edit", "variant": "secondary"},
                {"label": "Supprimer", "type": "delete", "variant": "destructive"},
            ],
            "filters": [
                {
                    "key": field["name"],
                    "label": field.get("display_name", field["name"]),
                    "type": "text",
                }
                for field in fields
                if any(
                    field["type"].startswith(t) for t in ("varchar", "text")
                )
            ][:3],
            "pagination": {"pageSize": 25, "pageSizeOptions": [10, 25, 50, 100]},
        }

    @staticmethod
    def _build_form_schema(
        name: str,
        display_name: str,
        fields: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a RJSF (React JSON Schema Form) compatible form configuration."""
        json_schema: dict[str, Any] = {
            "type": "object",
            "title": f"Créer {display_name}",
            "required": [],
            "properties": {},
        }
        ui_schema: dict[str, Any] = {}

        for field in fields:
            field_name = field["name"]
            if field_name == "id":
                continue  # auto-generated

            json_type, ui_widget = _field_to_jsonschema(field)
            json_schema["properties"][field_name] = {
                "type": json_type,
                "title": field.get("display_name", field_name),
                "description": field.get("description", ""),
            }

            if field.get("required"):
                json_schema["required"].append(field_name)

            if ui_widget:
                ui_schema[field_name] = {"ui:widget": ui_widget}

        return {
            "type": "form",
            "title": f"Créer {display_name}",
            "json_schema": json_schema,
            "ui_schema": ui_schema,
        }

    @staticmethod
    def _build_detail_view(
        name: str,
        display_name: str,
        fields: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a detail view configuration."""
        sections = [
            {
                "title": "Informations générales",
                "fields": [
                    {
                        "key": f["name"],
                        "label": f.get("display_name", f["name"]),
                        "type": _map_field_type_to_ui(f["type"]),
                    }
                    for f in fields
                    if f["name"] not in ("id",)
                ],
            }
        ]

        return {
            "type": "detail",
            "title": display_name,
            "sections": sections,
            "tabs": [
                {"label": "Détails", "key": "details"},
                {"label": "Activité", "key": "activity"},
            ],
            "actions": [
                {"label": "Modifier", "type": "edit", "variant": "primary"},
                {"label": "Supprimer", "type": "delete", "variant": "destructive"},
            ],
        }

    @staticmethod
    def _build_dashboard_config(name: str, display_name: str) -> dict[str, Any]:
        """Build a simple dashboard/metrics configuration for the module."""
        return {
            "type": "dashboard",
            "title": f"Tableau de bord — {display_name}",
            "metrics": [
                {
                    "key": "total_count",
                    "label": f"Total {display_name}",
                    "query": "count",
                    "icon": "database",
                },
                {
                    "key": "created_this_month",
                    "label": "Créés ce mois",
                    "query": "count_month",
                    "icon": "calendar",
                },
            ],
            "charts": [
                {
                    "type": "bar",
                    "title": f"Évolution {display_name}",
                    "x_key": "month",
                    "y_key": "count",
                    "data_query": "monthly_count",
                }
            ],
        }


# ---------------------------------------------------------------------------
# Type mapping helpers
# ---------------------------------------------------------------------------


def _map_field_type_to_ui(sql_type: str) -> str:
    """Map a SQL type to a generic UI type string."""
    sql_type = sql_type.lower()
    if sql_type == "boolean":
        return "boolean"
    if sql_type == "date":
        return "date"
    if sql_type in ("timestamp", "timestamptz"):
        return "datetime"
    if sql_type in ("integer", "bigint", "smallint"):
        return "number"
    if sql_type.startswith("decimal") or sql_type.startswith("numeric"):
        return "currency"
    if sql_type == "uuid":
        return "uuid"
    if sql_type == "jsonb":
        return "json"
    return "text"


def _field_to_jsonschema(field: dict[str, Any]) -> tuple[str, str | None]:
    """
    Convert a field definition to (json_schema_type, ui_widget).
    Returns the JSON Schema type and optional RJSF ui:widget.
    """
    sql_type = field.get("type", "text").lower()

    if sql_type == "boolean":
        return "boolean", None
    if sql_type in ("integer", "bigint", "smallint"):
        return "integer", None
    if sql_type.startswith("decimal") or sql_type.startswith("numeric"):
        return "number", None
    if sql_type == "date":
        return "string", "date"
    if sql_type in ("timestamp", "timestamptz"):
        return "string", "date-time"
    if sql_type == "uuid":
        return "string", None
    if sql_type == "jsonb":
        return "object", "textarea"
    if sql_type == "text":
        return "string", "textarea"

    return "string", None
