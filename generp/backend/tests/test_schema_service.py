"""
Tests for SchemaService — DDL generation and type validation.
"""

from __future__ import annotations

import pytest

from app.agents.schema_agent import ALLOWED_SQL_TYPES, SchemaAgent
from app.agents.validation_agent import validate_schema
from app.services.schema_service import (
    _sanitize_default,
    _sanitize_identifier,
    _sanitize_sql_type,
)


class TestSanitizeIdentifier:
    def test_valid_identifier(self) -> None:
        assert _sanitize_identifier("client") == "client"
        assert _sanitize_identifier("facture_id") == "facture_id"

    def test_converts_hyphen_to_underscore(self) -> None:
        assert _sanitize_identifier("my-table") == "my_table"

    def test_rejects_special_chars(self) -> None:
        with pytest.raises(ValueError):
            _sanitize_identifier("table; DROP TABLE")

    def test_rejects_starting_with_digit(self) -> None:
        with pytest.raises(ValueError):
            _sanitize_identifier("1invalid")


class TestSanitizeSqlType:
    def test_valid_base_types(self) -> None:
        assert _sanitize_sql_type("text") == "text"
        assert _sanitize_sql_type("uuid") == "uuid"
        assert _sanitize_sql_type("boolean") == "boolean"
        assert _sanitize_sql_type("integer") == "integer"
        assert _sanitize_sql_type("date") == "date"
        assert _sanitize_sql_type("jsonb") == "jsonb"

    def test_valid_precision_types(self) -> None:
        assert _sanitize_sql_type("decimal(10,2)") == "decimal(10,2)"
        assert _sanitize_sql_type("varchar(255)") == "varchar(255)"

    def test_rejects_dangerous_types(self) -> None:
        with pytest.raises(ValueError):
            _sanitize_sql_type("DROP TABLE")
        with pytest.raises(ValueError):
            _sanitize_sql_type("serial; DROP")

    def test_array_types(self) -> None:
        assert _sanitize_sql_type("text[]") == "text[]"
        assert _sanitize_sql_type("uuid[]") == "uuid[]"


class TestSanitizeDefault:
    def test_safe_defaults(self) -> None:
        assert _sanitize_default("gen_random_uuid()") == "gen_random_uuid()"
        assert _sanitize_default("now()") == "now()"
        assert _sanitize_default("true") == "true"
        assert _sanitize_default("false") == "false"

    def test_safe_string_literals(self) -> None:
        assert _sanitize_default("'actif'") == "'actif'"
        assert _sanitize_default("'brouillon'") == "'brouillon'"

    def test_numeric_defaults(self) -> None:
        assert _sanitize_default("0") == "0"
        assert _sanitize_default("20.00") == "20.00"

    def test_rejects_dangerous_defaults(self) -> None:
        assert _sanitize_default("'; DROP TABLE clients; --") is None
        assert _sanitize_default("SELECT * FROM secrets") is None


class TestSchemaAgentValidation:
    def test_validate_entity_adds_system_fields(self) -> None:
        """Missing system fields should be auto-added."""
        agent = SchemaAgent(llm=None)  # type: ignore
        entity = {
            "name": "client",
            "display_name": "Clients",
            "fields": [
                {"name": "nom", "type": "text", "required": True, "unique": False,
                 "default": None, "description": ""}
            ],
            "relations": [],
        }
        agent._validate_entity(entity)
        field_names = {f["name"] for f in entity["fields"]}
        assert "id" in field_names
        assert "created_at" in field_names
        assert "updated_at" in field_names

    def test_validate_schema_rejects_too_many_entities(self) -> None:
        agent = SchemaAgent(llm=None)  # type: ignore
        schema = {
            "entities": [
                {
                    "name": f"entity_{i}",
                    "display_name": f"Entity {i}",
                    "fields": [
                        {"name": "id", "type": "uuid", "required": True, "unique": True,
                         "default": "gen_random_uuid()", "description": ""},
                        {"name": "created_at", "type": "timestamp", "required": True,
                         "unique": False, "default": "now()", "description": ""},
                        {"name": "updated_at", "type": "timestamp", "required": True,
                         "unique": False, "default": "now()", "description": ""},
                    ],
                    "relations": [],
                }
                for i in range(9)  # 9 entities > 8 max
            ]
        }
        with pytest.raises(ValueError, match="must not exceed 8"):
            agent._validate_schema(schema)

    def test_type_mapping(self) -> None:
        assert SchemaAgent._map_type("string") == "text"
        assert SchemaAgent._map_type("int") == "integer"
        assert SchemaAgent._map_type("float") == "decimal(10,2)"
        assert SchemaAgent._map_type("unknown_type_xyz") is None


class TestValidationAgent:
    def _make_valid_entity(self, name: str = "client") -> dict:
        return {
            "name": name,
            "display_name": "Clients",
            "category": "crm",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "unique": True,
                 "default": "gen_random_uuid()", "description": ""},
                {"name": "nom", "type": "text", "required": True, "unique": False,
                 "default": None, "description": ""},
                {"name": "created_at", "type": "timestamp", "required": True, "unique": False,
                 "default": "now()", "description": ""},
                {"name": "updated_at", "type": "timestamp", "required": True, "unique": False,
                 "default": "now()", "description": ""},
            ],
            "relations": [],
        }

    def test_valid_schema_passes(self) -> None:
        result = validate_schema({"entities": [self._make_valid_entity()]})
        assert result.is_valid

    def test_empty_entities_fails(self) -> None:
        result = validate_schema({"entities": []})
        assert not result.is_valid

    def test_dangerous_default_fails(self) -> None:
        entity = self._make_valid_entity()
        entity["fields"][1]["default"] = "'; DROP TABLE clients; --"
        result = validate_schema({"entities": [entity]})
        assert not result.is_valid

    def test_unknown_relation_target_warns(self) -> None:
        entity = self._make_valid_entity()
        entity["relations"] = [
            {
                "name": "nonexistent",
                "type": "many_to_one",
                "target_entity": "does_not_exist",
                "foreign_key": "nonexistent_id",
            }
        ]
        result = validate_schema({"entities": [entity]})
        # Should be a warning, not an error
        assert result.is_valid
        assert any("does_not_exist" in w for w in result.warnings)
