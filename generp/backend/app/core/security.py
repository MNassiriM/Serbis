"""JWT verification and tenant context extraction."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Raises:
        JWTError: if the token is invalid or expired.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError as exc:
        raise exc


def create_access_token(data: dict[str, Any]) -> str:
    """Create a signed JWT token from the provided payload."""
    from datetime import datetime, timedelta, timezone

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def extract_tenant_id(payload: dict[str, Any]) -> UUID:
    """
    Extract and validate the tenant_id claim from a decoded JWT payload.

    Raises:
        ValueError: if tenant_id is missing or invalid.
    """
    tenant_id_raw = payload.get("tenant_id")
    if not tenant_id_raw:
        raise ValueError("Token missing 'tenant_id' claim")
    try:
        return UUID(str(tenant_id_raw))
    except ValueError:
        raise ValueError(f"Invalid tenant_id in token: {tenant_id_raw!r}")
