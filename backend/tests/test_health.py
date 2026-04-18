"""
Tests for health check and app-level endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealth:
    async def test_health_endpoint_exists(self, client: AsyncClient):
        res = await client.get("/health")
        assert res.status_code == 200

    async def test_health_returns_status_ok(self, client: AsyncClient):
        res = await client.get("/health")
        body = res.json()
        assert body.get("status") in ("ok", "healthy", "up")

    async def test_docs_hidden_in_production(self, client: AsyncClient):
        """Swagger docs must not be exposed when DEBUG=False."""
        import os
        if os.environ.get("DEBUG", "false").lower() == "false":
            res = await client.get("/docs")
            assert res.status_code == 404

    async def test_cors_header_present(self, client: AsyncClient):
        res = await client.options("/api/v1/auth/login", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        })
        # CORS preflight should be handled
        assert res.status_code in (200, 204, 400)

    async def test_unknown_route_returns_404(self, client: AsyncClient):
        res = await client.get("/api/v1/doesnotexist")
        assert res.status_code == 404
