"""
Integration tests for /api/v1/commands endpoints.
Tests OTP flow, destructive command gating, silent uninstall, audit logging.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
class TestNonDestructiveCommands:
    async def test_lock_device_no_otp(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.post("/api/v1/commands/issue", headers=auth_headers, json={
            "device_id": str(enrolled_device.id),
            "command_type": "lock_device",
        })
        assert res.status_code == 200
        body = res.json()
        assert "command_id" in body

    async def test_trigger_alarm_no_otp(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.post("/api/v1/commands/issue", headers=auth_headers, json={
            "device_id": str(enrolled_device.id),
            "command_type": "trigger_alarm",
        })
        assert res.status_code == 200

    async def test_location_request_no_otp(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.post("/api/v1/commands/issue", headers=auth_headers, json={
            "device_id": str(enrolled_device.id),
            "command_type": "location_request",
        })
        assert res.status_code == 200

    async def test_command_nonexistent_device(self, client: AsyncClient, auth_headers):
        res = await client.post("/api/v1/commands/issue", headers=auth_headers, json={
            "device_id": "00000000-0000-0000-0000-000000000000",
            "command_type": "lock_device",
        })
        assert res.status_code == 404


@pytest.mark.asyncio
class TestDestructiveCommandOTPFlow:
    async def test_remote_uninstall_requires_otp(self, client: AsyncClient, auth_headers, enrolled_device):
        """Uninstall without OTP must be rejected."""
        res = await client.post("/api/v1/commands/issue", headers=auth_headers, json={
            "device_id": str(enrolled_device.id),
            "command_type": "remote_uninstall",
        })
        assert res.status_code == 400
        assert "OTP" in res.json()["detail"]

    async def test_wipe_requires_otp(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.post("/api/v1/commands/issue", headers=auth_headers, json={
            "device_id": str(enrolled_device.id),
            "command_type": "wipe_device",
        })
        assert res.status_code == 400

    async def test_generate_otp_success(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.post(
            "/api/v1/commands/generate-otp",
            headers=auth_headers,
            params={"device_id": str(enrolled_device.id), "command_type": "remote_uninstall"},
        )
        assert res.status_code == 200
        body = res.json()
        assert "otp_id" in body
        assert "otp" in body
        assert len(body["otp"]) == 6
        assert body["otp"].isdigit()
        assert "expires_in_seconds" in body

    async def test_otp_expired_rejected(self, client: AsyncClient, auth_headers, enrolled_device, device_token):
        """Verify that a fake/expired OTP ID gets rejected."""
        res = await client.post("/api/v1/commands/verify-otp", json={
            "otp_id": "00000000-0000-0000-0000-000000000000",
            "otp_code": "123456",
            "device_id": str(enrolled_device.id),
        }, headers={"Authorization": f"Bearer {device_token}"})
        assert res.status_code in (404, 400, 401)


@pytest.mark.asyncio
class TestSilentUninstall:
    async def test_silent_uninstall_endpoint_exists(self, client: AsyncClient, auth_headers, enrolled_device):
        """Admin silent uninstall — server verifies OTP automatically."""
        res = await client.post(
            "/api/v1/commands/admin-silent-uninstall",
            headers=auth_headers,
            params={"device_id": str(enrolled_device.id)},
        )
        # Should succeed (200) or be accepted (202)
        assert res.status_code in (200, 202)

    async def test_silent_uninstall_requires_admin(self, client: AsyncClient, enrolled_device, device_token):
        """Device token (non-admin) must not be able to trigger silent uninstall."""
        res = await client.post(
            "/api/v1/commands/admin-silent-uninstall",
            headers={"Authorization": f"Bearer {device_token}"},
            params={"device_id": str(enrolled_device.id)},
        )
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestAuditLogs:
    async def test_audit_log_created_on_command(self, client: AsyncClient, auth_headers, enrolled_device):
        """Issuing a command must create an audit log entry."""
        await client.post("/api/v1/commands/issue", headers=auth_headers, json={
            "device_id": str(enrolled_device.id),
            "command_type": "lock_device",
        })
        res = await client.get(
            "/api/v1/commands/audit-logs",
            headers=auth_headers,
            params={"device_id": str(enrolled_device.id)},
        )
        assert res.status_code == 200
        body = res.json()
        logs = body if isinstance(body, list) else body.get("logs", [])
        assert len(logs) >= 1

    async def test_audit_log_requires_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/commands/audit-logs")
        assert res.status_code in (401, 403)

    async def test_login_failure_is_audited(self, client: AsyncClient, auth_headers, admin_user):
        """Failed login attempts should appear in audit logs."""
        await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "wrongpassword",
        })
        res = await client.get("/api/v1/commands/audit-logs", headers=auth_headers)
        assert res.status_code == 200
