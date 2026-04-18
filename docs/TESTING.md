# Testing Strategy

## 1. Unit Tests — Backend

```python
# backend/tests/test_otp_service.py
import pytest
from app.utils.security import generate_otp, hash_otp, verify_otp_hash

def test_otp_generation():
    otp = generate_otp(6)
    assert len(otp) == 6
    assert otp.isdigit()

def test_otp_hash_verify():
    otp = "123456"
    hashed = hash_otp(otp)
    assert verify_otp_hash(otp, hashed)
    assert not verify_otp_hash("000000", hashed)

def test_otp_uniqueness():
    otps = {generate_otp() for _ in range(1000)}
    assert len(otps) > 900  # high entropy

# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_login_success(test_db, test_admin):
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "testpass123"
        })
    assert res.status_code == 200
    assert "access_token" in res.json()

@pytest.mark.asyncio
async def test_login_invalid_password(test_db, test_admin):
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "wrongpassword"
        })
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_otp_rate_limiting(test_db, test_device, admin_token):
    # 3 wrong attempts should lock
    async with AsyncClient(app=app, base_url="http://test") as client:
        for _ in range(3):
            await client.post("/api/v1/commands/verify-otp", json={
                "otp_id": str(test_device["otp_id"]),
                "otp_code": "000000",
                "device_id": str(test_device["id"]),
            }, headers={"Authorization": f"Bearer {admin_token}"})

        res = await client.post("/api/v1/commands/verify-otp", json={
            "otp_id": str(test_device["otp_id"]),
            "otp_code": "000000",
            "device_id": str(test_device["id"]),
        }, headers={"Authorization": f"Bearer {admin_token}"})

    assert res.status_code == 429
```

---

## 2. Integration Tests

```python
# Test full uninstall flow
@pytest.mark.asyncio
async def test_full_uninstall_flow(test_db, test_device, admin_token, device_token):
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Generate OTP
        res = await client.post(
            "/api/v1/commands/generate-otp",
            params={"device_id": test_device["id"], "command_type": "remote_uninstall"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        otp_data = res.json()
        otp_id = otp_data["otp_id"]
        otp_code = otp_data["otp"]

        # Step 2: Verify OTP on device
        res = await client.post(
            "/api/v1/commands/verify-otp",
            json={"otp_id": otp_id, "otp_code": otp_code,
                  "device_id": test_device["id"]},
            headers={"Authorization": f"Bearer {device_token}"}
        )
        assert res.json()["verified"] is True

        # Step 3: Issue uninstall command
        res = await client.post(
            "/api/v1/commands/issue",
            json={"device_id": test_device["id"],
                  "command_type": "remote_uninstall",
                  "otp_id": otp_id},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200

        # Step 4: Verify audit logs
        res = await client.get(
            "/api/v1/commands/audit-logs",
            params={"device_id": test_device["id"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        actions = [log["action"] for log in res.json()]
        assert "otp_generated" in actions
        assert "otp_verified" in actions
```

---

## 3. Security Tests

```bash
# Run OWASP ZAP scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://mdm-api.yourcompany.com

# Test JWT without signature
# (should return 401)
curl -H "Authorization: Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJ0ZXN0In0." \
  https://mdm-api.yourcompany.com/api/v1/devices/

# Test SQL injection in filters
curl "https://mdm-api.yourcompany.com/api/v1/devices/?status=' OR 1=1--" \
  -H "Authorization: Bearer $TOKEN"
# Should return 422 Unprocessable Entity

# Test OTP brute force rate limiting
for i in {1..5}; do
  curl -X POST https://mdm-api.yourcompany.com/api/v1/commands/verify-otp \
    -H "Content-Type: application/json" \
    -d '{"otp_id":"uuid","otp_code":"000000","device_id":"uuid"}'
done
# 4th+ request should return 429
```

---

## 4. Flutter Tests

```dart
// test/enrollment_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:company_mdm_agent/services/enrollment_service.dart';

void main() {
  test('enrollment result parsed correctly', () {
    final result = EnrollmentResult(success: true, deviceId: 'test-id');
    expect(result.success, true);
    expect(result.deviceId, 'test-id');
  });
}
```

---

## 5. Load Testing

```python
# locust -f locustfile.py --host=https://mdm-api.yourcompany.com
from locust import HttpUser, task, between

class DeviceUser(HttpUser):
    wait_time = between(25, 35)  # simulate heartbeat interval

    def on_start(self):
        self.token = self._enroll()

    def _enroll(self):
        res = self.client.post("/api/v1/devices/enroll", json={...})
        return res.json()["device_token"]

    @task
    def heartbeat(self):
        self.client.post(
            "/api/v1/devices/heartbeat",
            json={"is_rooted": False},
            headers={"Authorization": f"Bearer {self.token}"}
        )
```
