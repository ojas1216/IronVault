"""
Integration tests for /api/v1/devices endpoints.
"""
import pytest
from httpx import AsyncClient


ENROLL_PAYLOAD = {
    "enrollment_code": "COMPANY_SECRET_ENROLL_2024",
    "device_name": "Test Phone",
    "employee_name": "Alice Smith",
    "employee_email": "alice@company.com",
    "department": "HR",
    "platform": "android",
    "os_version": "Android 14",
    "agent_version": "1.0.0",
    "manufacturer": "Samsung",
    "model": "Galaxy S23",
    "imei": "356938035643809",
    "serial_number": "R58T4021BXN",
    "push_token": "fcm_token_test_abc123",
}


@pytest.mark.asyncio
class TestDeviceEnrollment:
    async def test_enroll_success(self, client: AsyncClient):
        res = await client.post("/api/v1/devices/enroll", json=ENROLL_PAYLOAD)
        assert res.status_code == 200
        body = res.json()
        assert "device_id" in body
        assert "device_token" in body

    async def test_enroll_wrong_code(self, client: AsyncClient):
        payload = {**ENROLL_PAYLOAD, "enrollment_code": "WRONG_CODE"}
        res = await client.post("/api/v1/devices/enroll", json=payload)
        assert res.status_code == 403

    async def test_enroll_missing_required_fields(self, client: AsyncClient):
        res = await client.post("/api/v1/devices/enroll", json={
            "enrollment_code": "COMPANY_SECRET_ENROLL_2024",
            "platform": "android",
            # missing device_name, employee_name
        })
        assert res.status_code == 422

    async def test_enroll_invalid_platform(self, client: AsyncClient):
        payload = {**ENROLL_PAYLOAD, "platform": "fridge"}
        res = await client.post("/api/v1/devices/enroll", json=payload)
        assert res.status_code in (400, 422)


@pytest.mark.asyncio
class TestDeviceList:
    async def test_list_devices_empty(self, client: AsyncClient, auth_headers):
        res = await client.get("/api/v1/devices/", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list) or isinstance(body, dict)

    async def test_list_devices_with_enrolled(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.get("/api/v1/devices/", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        devices = data if isinstance(data, list) else data.get("devices", [])
        ids = [str(d["id"]) for d in devices]
        assert str(enrolled_device.id) in ids

    async def test_list_requires_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/devices/")
        assert res.status_code in (401, 403)

    async def test_filter_by_platform(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.get("/api/v1/devices/", headers=auth_headers,
                               params={"platform": "android"})
        assert res.status_code == 200


@pytest.mark.asyncio
class TestDeviceDetail:
    async def test_get_device_by_id(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.get(f"/api/v1/devices/{enrolled_device.id}", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert body["device_name"] == "Test Android Device"
        assert body["platform"] == "android"

    async def test_get_nonexistent_device(self, client: AsyncClient, auth_headers):
        res = await client.get(
            "/api/v1/devices/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        assert res.status_code == 404

    async def test_location_history_empty(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.get(
            f"/api/v1/devices/{enrolled_device.id}/location-history",
            headers=auth_headers
        )
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)

    async def test_app_usage_empty(self, client: AsyncClient, auth_headers, enrolled_device):
        res = await client.get(
            f"/api/v1/devices/{enrolled_device.id}/app-usage",
            headers=auth_headers
        )
        assert res.status_code == 200


@pytest.mark.asyncio
class TestHeartbeat:
    async def test_heartbeat_updates_device(self, client: AsyncClient, enrolled_device, device_token):
        headers = {"Authorization": f"Bearer {device_token}"}
        res = await client.post("/api/v1/devices/heartbeat", headers=headers, json={
            "device_id": str(enrolled_device.id),
            "latitude": 28.6139,
            "longitude": 77.2090,
            "accuracy": 5.0,
            "battery_level": 85,
            "is_rooted": False,
        })
        assert res.status_code == 200

    async def test_heartbeat_without_token(self, client: AsyncClient, enrolled_device):
        res = await client.post("/api/v1/devices/heartbeat", json={
            "device_id": str(enrolled_device.id),
        })
        assert res.status_code in (401, 403)
