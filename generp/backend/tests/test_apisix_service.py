"""
Tests for APISIXService — route registration payload generation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.apisix_service import APISIXService


class TestAPISIXServicePayload:
    def test_build_route_payload_structure(self) -> None:
        """Verify the route payload has all required APISIX fields."""
        payload = APISIXService._build_route_payload(
            uri="/api/v1/data/tenant123/client",
            methods=["GET"],
            upstream_url="http://backend:8000/api/v1/data/tenant123/client",
            tenant_id="tenant-uuid-123",
        )
        assert "uri" in payload
        assert "methods" in payload
        assert "upstream" in payload
        assert "plugins" in payload
        assert payload["methods"] == ["GET"]
        assert payload["status"] == 1

    def test_cors_plugin_present(self) -> None:
        payload = APISIXService._build_route_payload(
            uri="/test",
            methods=["GET", "POST"],
            upstream_url="http://backend:8000/test",
            tenant_id="t1",
        )
        assert "cors" in payload["plugins"]

    def test_tenant_header_injected(self) -> None:
        tenant_id = "abc-123"
        payload = APISIXService._build_route_payload(
            uri="/test",
            methods=["GET"],
            upstream_url="http://backend:8000/test",
            tenant_id=tenant_id,
        )
        rewrite = payload["plugins"].get("proxy-rewrite", {})
        assert rewrite.get("headers", {}).get("X-Tenant-ID") == tenant_id


class TestAPISIXServiceIntegration:
    @pytest.mark.asyncio
    async def test_register_creates_five_routes(self) -> None:
        """register_module_routes should attempt to create 5 CRUD routes."""
        service = APISIXService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        call_count = 0

        async def mock_put(*args, **kwargs):  # type: ignore
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.put = mock_put
            mock_client_cls.return_value = mock_client

            result = await service.register_module_routes(
                tenant_id="550e8400-e29b-41d4-a716-446655440000",
                module_name="client",
                entity_fields=[],
            )

        assert call_count == 5
        assert len(result["route_ids"]) == 5
        assert result["module"] == "client"

    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_200(self) -> None:
        service = APISIXService()

        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_get(*args, **kwargs):  # type: ignore
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = mock_get
            mock_client_cls.return_value = mock_client

            result = await service.health_check()

        assert result is True
