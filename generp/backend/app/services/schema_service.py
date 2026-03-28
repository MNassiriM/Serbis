"""
Schema Service — generates and executes PostgreSQL DDL from a validated schema definition.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import create_tenant_schema, get_tenant_engine

logger = logging.getLogger(__name__)

# Types that map to "has precision" in DDL
_PRECISION_TYPES = ("decimal", "numeric", "varchar", "character varying")


class SchemaService:
    """Handles DDL generation and execution in tenant-scoped schemas."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def generate_and_execute_ddl(
        self,
        tenant_id: str,
        schema_definition: dict[str, Any],
    ) -> dict[str, Any]:
        """
        1. Ensures the tenant schema exists.
        2. Generates DDL for each entity.
        3. Executes DDL in the tenant schema.

        Returns {"tables_created": [...], "schema_name": "..."}
        """
        schema_name = await create_tenant_schema(tenant_id)
        entities = schema_definition.get("entities", [])

        tables_created: list[str] = []
        tenant_engine = get_tenant_engine(tenant_id)

        async with tenant_engine.begin() as conn:
            # Ensure uuid-ossp extension
            await conn.execute(
                text(f'CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA {schema_name}')
            )
            # pgcrypto for gen_random_uuid() (PostgreSQL < 13)
            await conn.execute(
                text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
            )

            for entity in entities:
                ddl = self._generate_table_ddl(entity, schema_name)
                try:
                    await conn.execute(text(ddl))
                    tables_created.append(entity["name"])
                    logger.info(
                        "Created table '%s.%s'", schema_name, entity["name"]
                    )

                    # Auto-update trigger for updated_at
                    trigger_ddl = self._generate_updated_at_trigger(
                        entity["name"], schema_name
                    )
                    await conn.execute(text(trigger_ddl["function"]))
                    await conn.execute(text(trigger_ddl["trigger"]))

                    # Enable RLS
                    await conn.execute(
                        text(
                            f"ALTER TABLE {schema_name}.{entity['name']} "
                            f"ENABLE ROW LEVEL SECURITY"
                        )
                    )
                    # Permissive RLS policy for the service role
                    await conn.execute(
                        text(
                            f"DO $$ BEGIN "
                            f"  IF NOT EXISTS ("
                            f"    SELECT 1 FROM pg_policies "
                            f"    WHERE tablename = '{entity['name']}' "
                            f"    AND schemaname = '{schema_name}'"
                            f"  ) THEN "
                            f"    EXECUTE 'CREATE POLICY tenant_isolation ON "
                            f"      {schema_name}.{entity[\"name\"]} USING (true)';"
                            f"  END IF; "
                            f"END $$"
                        )
                    )

                except Exception as exc:
                    logger.error(
                        "Error creating table '%s': %s", entity["name"], exc
                    )
                    raise

        return {"tables_created": tables_created, "schema_name": schema_name}

    def _generate_table_ddl(
        self, entity: dict[str, Any], schema_name: str
    ) -> str:
        """Generate a CREATE TABLE IF NOT EXISTS statement for an entity."""
        table_name = _sanitize_identifier(entity["name"])
        fields = entity.get("fields", [])
        relations = entity.get("relations", [])

        column_defs: list[str] = []

        for field in fields:
            col_def = self._field_to_column_def(field)
            column_defs.append(f"  {col_def}")

        # Add foreign key constraints
        fk_constraints: list[str] = []
        for rel in relations:
            if rel.get("type") == "many_to_one":
                fk_col = _sanitize_identifier(rel.get("foreign_key", ""))
                target = _sanitize_identifier(rel.get("target_entity", ""))
                if fk_col and target:
                    fk_constraints.append(
                        f"  CONSTRAINT fk_{table_name}_{fk_col} "
                        f"FOREIGN KEY ({fk_col}) "
                        f"REFERENCES {schema_name}.{target}(id) "
                        f"ON DELETE RESTRICT"
                    )

        all_defs = column_defs + fk_constraints

        ddl = (
            f"CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (\n"
            + ",\n".join(all_defs)
            + "\n);"
        )

        # Add indexes
        index_ddls = self._generate_indexes(entity, schema_name, table_name)
        return ddl + "\n" + "\n".join(index_ddls)

    @staticmethod
    def _field_to_column_def(field: dict[str, Any]) -> str:
        """Convert a field dict to a PostgreSQL column definition string."""
        name = _sanitize_identifier(field["name"])
        sql_type = _sanitize_sql_type(field.get("type", "text"))
        parts = [f"{name} {sql_type}"]

        if field.get("required", False) or field["name"] == "id":
            parts.append("NOT NULL")

        if field.get("unique", False):
            parts.append("UNIQUE")

        default = field.get("default")
        if default is not None and str(default).strip():
            safe_default = _sanitize_default(str(default))
            if safe_default:
                parts.append(f"DEFAULT {safe_default}")

        if field["name"] == "id":
            parts.append("PRIMARY KEY")

        return " ".join(parts)

    @staticmethod
    def _generate_indexes(
        entity: dict[str, Any], schema_name: str, table_name: str
    ) -> list[str]:
        """Generate CREATE INDEX statements for specified fields."""
        indexes: list[str] = []
        index_fields = entity.get("indexes", [])

        # Always index foreign keys
        for rel in entity.get("relations", []):
            fk = rel.get("foreign_key")
            if fk and fk not in index_fields:
                index_fields.append(fk)

        for field_name in index_fields:
            safe_field = _sanitize_identifier(field_name)
            idx_name = f"idx_{table_name}_{safe_field}"
            indexes.append(
                f"CREATE INDEX IF NOT EXISTS {idx_name} "
                f"ON {schema_name}.{table_name} ({safe_field});"
            )

        return indexes

    @staticmethod
    def _generate_updated_at_trigger(
        table_name: str, schema_name: str
    ) -> dict[str, str]:
        """Generate function + trigger DDL to auto-update updated_at."""
        func_name = f"{schema_name}.set_{table_name}_updated_at"
        trigger_name = f"trg_{table_name}_updated_at"

        function_ddl = f"""
CREATE OR REPLACE FUNCTION {func_name}()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;
""".strip()

        trigger_ddl = f"""
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = '{trigger_name}'
    AND tgrelid = '{schema_name}.{table_name}'::regclass
  ) THEN
    CREATE TRIGGER {trigger_name}
    BEFORE UPDATE ON {schema_name}.{table_name}
    FOR EACH ROW EXECUTE FUNCTION {func_name}();
  END IF;
END $$;
""".strip()

        return {"function": function_ddl, "trigger": trigger_ddl}


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")

_SAFE_DEFAULTS = frozenset(
    {"gen_random_uuid()", "now()", "current_timestamp", "true", "false", "null", "0", "''"}
)

# Whitelist of base SQL types (without parameters)
_ALLOWED_BASE_TYPES = frozenset(
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
    }
)


def _sanitize_identifier(name: str) -> str:
    """Ensure an identifier only contains safe characters."""
    cleaned = name.lower().replace("-", "_")
    if not _IDENTIFIER_PATTERN.match(cleaned):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return cleaned


def _sanitize_sql_type(sql_type: str) -> str:
    """Validate and return a safe SQL type string."""
    t = sql_type.lower().strip()

    # Check base type
    base = re.sub(r"\(.*\)", "", t).strip()
    if base in _ALLOWED_BASE_TYPES:
        return t

    # Types with parameters
    for prefix in _PRECISION_TYPES:
        if t.startswith(prefix):
            # Validate the parameter part
            match = re.match(r"^[\w\s]+\((\d+)(?:,(\d+))?\)$", t)
            if match:
                return t
            raise ValueError(f"Invalid SQL type with parameters: {sql_type!r}")

    # text[] and uuid[]
    if t in ("text[]", "uuid[]"):
        return t

    raise ValueError(f"Disallowed SQL type: {sql_type!r}")


def _sanitize_default(default: str) -> str | None:
    """Validate a column default value against an allowlist."""
    d = default.strip().lower()
    if d in _SAFE_DEFAULTS:
        return default.strip()

    # Allow simple string literals like 'actif', 'brouillon'
    if re.match(r"^'[a-z0-9_\-\s]{0,100}'$", d):
        return default.strip()

    # Allow numeric literals
    if re.match(r"^\d+(\.\d+)?$", d):
        return default.strip()

    logger.warning("Rejecting unsafe column default: %r", default)
    return None
