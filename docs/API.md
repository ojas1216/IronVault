# API Reference

Base URL: `https://mdm-api.yourcompany.com/api/v1`

All endpoints require `Authorization: Bearer <token>` except `/auth/login` and `/devices/enroll`.

---

## Authentication

### POST /auth/login
Login admin user.
```json
Request: { "email": "admin@company.com", "password": "secret" }
Response: {
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "uuid", "email": "...", "role": "admin" }
}
```

### POST /auth/refresh
Refresh access token.
```json
Request: { "refresh_token": "eyJ..." }
Response: { "access_token": "eyJ...", "token_type": "bearer" }
```

---

## Devices (Agent → Backend)

### POST /devices/enroll
Enroll new device. Returns device JWT.
```json
Request: {
  "device_name": "John's Laptop",
  "employee_name": "John Doe",
  "employee_email": "john@company.com",
  "platform": "android",  // android|ios|windows|macos
  "enrollment_code": "COMPANY_CODE",
  "push_token": "fcm_token_here"
}
Response: {
  "device_id": "uuid",
  "device_token": "eyJ...",
  "enrollment_token": "...",
  "message": "Device enrolled successfully."
}
```

### POST /devices/heartbeat
Periodic status update. Auth: device JWT.
```json
Request: { "is_rooted": false, "network_type": "wifi", "push_token": "updated_token" }
```

### POST /devices/location
Send location update. Auth: device JWT.
```json
Request: {
  "latitude": 28.6139,
  "longitude": 77.2090,
  "accuracy": 15.0,
  "recorded_at": "2024-01-15T10:30:00Z"
}
```

### POST /devices/app-usage
Batch app usage sync. Auth: device JWT.
```json
Request: {
  "logs": [
    { "app_package": "com.whatsapp", "app_name": "WhatsApp",
      "usage_duration_seconds": 3600, "is_work_app": false }
  ]
}
```

### POST /devices/command-result
Report command execution result. Auth: device JWT.
```json
Request: {
  "command_id": "uuid",
  "status": "completed",  // completed|failed
  "result": {},
  "error_message": null
}
```

---

## Devices (Admin → Backend)

### GET /devices/
List all devices. Auth: VIEWER+
```
Query: status, platform, department, limit, offset
Response: [{ DeviceResponse }]
```

### GET /devices/{id}
Get device details.

### GET /devices/{id}/location-history
Get location history. Query: `limit`

### GET /devices/{id}/app-usage
Get app usage logs.

---

## Commands (Admin)

### POST /commands/generate-otp
Generate OTP for destructive command. Auth: ADMIN+
```
Query: device_id=uuid, command_type=remote_uninstall
Response: {
  "otp_id": "uuid",
  "otp": "123456",
  "expires_in_seconds": 300,
  "message": "Share this OTP with the employee..."
}
```

### POST /commands/issue
Issue command to device. Auth: ADMIN+
```json
Request: {
  "device_id": "uuid",
  "command_type": "lock_device",  // See CommandType enum
  "payload": {},
  "otp_id": "uuid"  // Required for remote_uninstall, wipe_device
}
```

### POST /commands/verify-otp
Verify OTP entered on device. Auth: device JWT.
```json
Request: {
  "otp_id": "uuid",
  "otp_code": "123456",
  "device_id": "uuid"
}
Response: { "verified": true, "message": "OTP verified." }
```

### GET /commands/audit-logs
Get audit logs. Auth: VIEWER+
```
Query: device_id (optional), limit, offset
```

---

## Command Types

| Command | OTP Required | Description |
|---|---|---|
| `lock_device` | No | Lock screen immediately |
| `unlock_device` | No | Unlock device |
| `location_request` | No | Request immediate GPS update |
| `app_block` | No | Block specific app |
| `policy_update` | No | Push policy update |
| `enable_lost_mode` | No | Enable lost mode with message |
| `collect_logs` | No | Collect diagnostic logs |
| `reboot` | No | Reboot device |
| `remote_uninstall` | **Yes** | Authorized agent removal |
| `wipe_device` | **Yes** | Factory reset (irreversible) |

---

## Error Responses

```json
{ "detail": "Error message" }

HTTP 400 - Bad request
HTTP 401 - Unauthorized / expired token
HTTP 403 - Insufficient role
HTTP 404 - Not found
HTTP 410 - OTP expired
HTTP 429 - Rate limit exceeded
HTTP 422 - Validation error
HTTP 500 - Server error
```
