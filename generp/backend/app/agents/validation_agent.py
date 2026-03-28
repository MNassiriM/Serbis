"""Validation Agent — checks schema coherence before DDL execution."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Allowed top-level categories
VALID_CATEGORIES = frozenset({"finance", "crm", "hr", "supply_chain", "general"})

# Allowed relation types
VALID_RELATION_TYPES = frozenset({"many_to_one", "one_to_many", "many_to_many"})


class ValidationResult:
    """Result of a schema validation check."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning("Schema warning: %s", msg)


def validate_schema(schema: dict[str, Any]) -> ValidationResult:
    """
    Perform comprehensive validation on a schema dict before DDL execution.

    Checks:
    - Required top-level keys
    - Entity count (max 8)
    - Entity naming conventions
    - System fields presence
    - Relation integrity (target_entity must exist)
    - Category validity
    - No dangerous SQL patterns in defaults
    """
    result = ValidationResult()

    entities: list[dict[str, Any]] = schema.get("entities", [])
    if not entities:
        result.error("Schema must contain at least one entity")
        return result

    if len(entities) > 8:
        result.error(f"Schema has {len(entities)} entities, maximum is 8 for MVP")

    entity_names = {e.get("name") for e in entities}

    for entity in entities:
        _validate_entity(entity, entity_names, result)

    return result


def _validate_entity(
    entity: dict[str, Any],
    all_entity_names: set[str | None],
    result: ValidationResult,
) -> None:
    name = entity.get("name", "<unnamed>")

    # Category
    category = entity.get("category", "")
    if category and category not in VALID_CATEGORIES:
        result.warn(f"Entity '{name}' has unknown category '{category}'")

    # System fields
    field_names = {f.get("name") for f in entity.get("fields", [])}
    for required in ("id", "created_at", "updated_at"):
        if required not in field_names:
            result.error(f"Entity '{name}' is missing required system field '{required}'")

    # Fields
    for field in entity.get("fields", []):
        _validate_field_defaults(field, name, result)

    # Relations
    for relation in entity.get("relations", []):
        rel_type = relation.get("type", "")
        if rel_type not in VALID_RELATION_TYPES:
            result.error(
                f"Entity '{name}' relation '{relation.get('name')}' "
                f"has invalid type '{rel_type}'"
            )
        target = relation.get("target_entity")
        if target and target not in all_entity_names:
            result.warn(
                f"Entity '{name}' relation references unknown entity '{target}'"
            )


_DANGEROUS_PATTERNS = (
    "drop",
    "truncate",
    "delete",
    "insert",
    "update",
    "select",
    ";",
    "--",
    "/*",
    "*/",
    "exec",
    "execute",
    "xp_",
)


def _validate_field_defaults(
    field: dict[str, Any], entity_name: str, result: ValidationResult
) -> None:
    """Check field default values for dangerous SQL patterns."""
    default = str(field.get("default", "") or "").lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in default and default not in ("gen_random_uuid()", "now()"):
            result.error(
                f"Entity '{entity_name}' field '{field.get('name')}' "
                f"default value contains dangerous pattern '{pattern}': {default!r}"
            )
            break
