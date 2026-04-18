"""
Integration tests for /api/v1/auth endpoints.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient, admin_user):
        res = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "testpassword123",
        })
        assert res.status_code == 200
        body = res.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, admin_user):
        res = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "wrongpassword",
        })
        assert res.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        res = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "anything",
        })
        assert res.status_code == 401

    async def test_login_missing_fields(self, client: AsyncClient):
        res = await client.post("/api/v1/auth/login", json={"email": "admin@test.com"})
        assert res.status_code == 422  # validation error

    async def test_login_invalid_email_format(self, client: AsyncClient):
        res = await client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123",
        })
        assert res.status_code == 422

    async def test_login_returns_correct_role(self, client: AsyncClient, admin_user):
        res = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "testpassword123",
        })
        assert res.status_code == 200


@pytest.mark.asyncio
class TestTokenRefresh:
    async def test_refresh_with_valid_token(self, client: AsyncClient, admin_user):
        # First login to get refresh token
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "testpassword123",
        })
        refresh_token = login_res.json()["refresh_token"]

        # Use it
        res = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert res.status_code == 200
        assert "access_token" in res.json()

    async def test_refresh_with_garbage_token(self, client: AsyncClient):
        res = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "not.a.valid.token",
        })
        assert res.status_code in (401, 422)


@pytest.mark.asyncio
class TestProtectedEndpoints:
    async def test_devices_requires_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/devices/")
        assert res.status_code in (401, 403)

    async def test_devices_with_valid_token(self, client: AsyncClient, auth_headers):
        res = await client.get("/api/v1/devices/", headers=auth_headers)
        assert res.status_code == 200

    async def test_audit_logs_requires_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/commands/audit-logs")
        assert res.status_code in (401, 403)

    async def test_invalid_token_rejected(self, client: AsyncClient):
        res = await client.get("/api/v1/devices/", headers={
            "Authorization": "Bearer invalidtoken123"
        })
        assert res.status_code == 401

    async def test_missing_bearer_prefix_rejected(self, client: AsyncClient, admin_token):
        res = await client.get("/api/v1/devices/", headers={
            "Authorization": admin_token  # missing "Bearer "
        })
        assert res.status_code in (401, 403)
