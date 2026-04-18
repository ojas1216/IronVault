# Enterprise Device Security Management System

> Production-ready, OS-compliant MDM platform for managing company-owned devices.
> Prevents unauthorized uninstall, enables real-time remote monitoring, and provides secure admin control across Android, iOS, Windows, and macOS.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android%20%7C%20iOS%20%7C%20Windows%20%7C%20macOS-lightgrey)]()
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20PostgreSQL-green)]()
[![Dashboard](https://img.shields.io/badge/dashboard-React%20%2B%20TypeScript-blue)]()

---

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/ojas1216/employee-device-security.git
cd employee-device-security
make env          # creates .env from .env.example — fill in secrets

# 2. Start everything
make deploy       # docker-compose up -d (production)
# OR
make dev          # hot-reload development mode

# 3. Access
# Admin dashboard: http://localhost:3000
# API docs:        http://localhost:8000/docs  (debug mode only)
```

---

## Architecture

```
  Employee Devices (Android / iOS / Windows / macOS)
         │  HTTPS + JWT + Certificate Pinning
         ▼
  FastAPI Backend ──── PostgreSQL (devices, logs, OTP, locations)
         │         ──── Redis     (rate limiting, OTP TTL)
         │         ──── FCM/APNs  (push commands to devices)
         ▼
  React Admin Dashboard
```

For detailed architecture diagrams see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Project Structure

```
Antitheft/
├── backend/                  ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py           ← App entry, middleware, lifespan
│   │   ├── config.py         ← Pydantic settings (env-driven)
│   │   ├── database.py       ← Async SQLAlchemy + PostgreSQL
│   │   ├── models/           ← ORM models (Device, User, OTP, Audit…)
│   │   ├── routers/          ← auth, devices, commands, sim_events, uwb
│   │   ├── services/         ← JWT, OTP (argon2), FCM/APNs push, audit
│   │   ├── schemas/          ← Pydantic request/response schemas
│   │   └── utils/            ← RBAC, rate limiter, security helpers
│   ├── alembic/              ← Database migrations
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── mobile/flutter_agent/     ← Flutter agent (Android + iOS)
│   ├── lib/
│   │   ├── main.dart
│   │   ├── config/           ← API URL, certificate pinning
│   │   ├── services/         ← Enrollment, heartbeat, FCM, SIM, UWB, location
│   │   └── screens/          ← Enrollment, Status, OTP dialog
│   ├── android/              ← Kotlin: DeviceAdmin, FRP, SilentUninstall, UWB
│   └── ios/                  ← Swift: AppDelegate, APNs, MDM channel
│
├── desktop_agent/            ← Python agent (Windows/macOS system service)
│   ├── agent.py              ← Entry point (install/uninstall/run)
│   ├── services/             ← Heartbeat, commands, app monitor
│   ├── utils/                ← Secure storage, device fingerprint
│   ├── install_windows.py    ← Windows Service (SYSTEM privileges)
│   └── install_macos.sh      ← macOS LaunchDaemon (root)
│
├── admin_dashboard/          ← React TypeScript admin UI
│   └── src/
│       ├── api/              ← auth.ts, devices.ts, audit.ts, client.ts
│       ├── pages/            ← Dashboard, DeviceDetail, AuditLogs, Login, SimAlerts
│       ├── components/       ← DeviceCard, LocationMap, UWBTracker, OTPModal…
│       └── store/            ← Zustand auth state
│
├── ironvault/                ← IronVault anti-theft / anti-resale module
│   ├── android/              ← Kotlin: BrickMode, HardwareTracker, SecureBoot
│   ├── backend/              ← Standalone FastAPI + admin panel
│   └── manufacturer_tools/   ← inject_hardware_ids.py, unlock_token_generator.py
│
└── docs/
    ├── API.md                ← Full API reference with curl examples
    ├── DEPLOYMENT.md         ← Production deploy guide
    ├── SECURITY.md           ← JWT, OTP, RBAC, audit trail
    ├── TESTING.md            ← pytest, Jest, OWASP
    ├── DEVELOPER_GUIDE.md    ← Module map, flow diagrams
    └── VIDEO_RECORDING_GUIDE.md ← Demo video scripts
```

---

## Feature Matrix

| Feature | Android | iOS | Windows | macOS |
|---|---|---|---|---|
| Uninstall protection | `DevicePolicyManager` | MDM Profile | Windows Service ACL | LaunchDaemon |
| Remote lock | `DPM.lockNow()` | MDM Lock | `LockWorkStation()` | `CGSession` |
| Remote wipe | `DPM.wipeData()` | MDM Erase | `systemreset` | `eraseinstall` |
| Remote uninstall | DPM + OTP flow | MDM Remove | Service removal | `launchctl` |
| Silent admin uninstall | Server-side OTP auto-verify | — | — | — |
| Factory Reset Protection | `DISALLOW_FACTORY_RESET` | DEP enrollment | — | — |
| Location tracking | Fused GPS (offline cache) | Geolocator | IP geolocation | IP geolocation |
| App usage monitoring | `UsageStatsManager` | Screen Time (limited) | Win32 API | `osascript` |
| SIM swap detection | `SubscriptionManager` BroadcastReceiver | — | — | — |
| Security photo on SIM swap | CameraX front camera | — | — | — |
| UWB precision tracking | `UwbManager` (Android 12+) | `NearbyInteraction` (iPhone 11+) | — | — |
| BLE fallback tracking | RSSI path-loss model | RSSI | — | — |
| Hardware fingerprinting | IMEI + eMMC CID + SHA-256 | UUID + model | BIOS UUID + disk serial | Serial + disk |
| Brick mode | Full-screen overlay + USB disable | — | — | — |
| Auto-start on boot | `BOOT_COMPLETED` | Background Modes | Service | LaunchDaemon |
| Push commands | FCM | APNs | FCM | FCM |
| Tamper detection | Airplane mode block, force-stop | — | Registry protection | SIP protection |
| Code obfuscation | ProGuard/R8, Frida detect | — | — | — |

---

## Security Design

| Mechanism | Implementation |
|---|---|
| Authentication | JWT (15-min access + 7-day refresh), bcrypt passwords |
| Destructive command auth | 6-digit OTP, argon2id hash, 5-min TTL, 3-attempt lockout |
| Transport | HTTPS + TLS 1.3 + certificate pinning on agents |
| Authorization | RBAC: Super Admin → Admin → Manager → Viewer |
| Rate limiting | SlowAPI per-endpoint (5/min auth, 100/min default) |
| Audit trail | Every admin action logged with ID, IP, timestamp, device |
| OTP storage | Never plaintext — argon2id in Redis with TTL |
| APK integrity | SHA-256 cert hash verification at runtime |
| Anti-debug | Frida/Xposed detection, debugger check, emulator block |

---

## Setup

### Prerequisites
- Docker 24+, Docker Compose V2
- Android Studio (for mobile build)
- Flutter 3.19+ (for mobile build)
- Python 3.11+ (for desktop agent)

### Environment Variables

```bash
cp .env.example .env
# Edit .env — fill in:
#   JWT_SECRET_KEY (generate: python -c "import secrets; print(secrets.token_hex(64))")
#   POSTGRES_PASSWORD
#   REDIS_PASSWORD
#   FIREBASE_CREDENTIALS_PATH (path to your firebase_credentials.json)
```

### Device Owner Enrollment (Android — required for full protection)

```bash
# Factory-reset device first (no Google accounts), then:
adb shell dpm set-device-owner com.company.mdmagent/.MDMDeviceAdminReceiver
```

### Build Mobile APK

```bash
cd mobile/flutter_agent

# Copy Firebase config
cp /path/to/google-services.json android/app/google-services.json

# Build release APK
flutter build apk --release

# Output: build/app/outputs/flutter-apk/app-release.apk
```

---

## API Overview

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/auth/login` | POST | None | Admin login |
| `/api/v1/auth/refresh` | POST | Refresh token | Rotate access token |
| `/api/v1/devices/` | GET | JWT | List all devices |
| `/api/v1/devices/{id}` | GET | JWT | Device detail |
| `/api/v1/devices/{id}/location-history` | GET | JWT | GPS trail |
| `/api/v1/commands/issue` | POST | JWT | Send command to device |
| `/api/v1/commands/generate-otp` | POST | JWT | Generate OTP for destructive command |
| `/api/v1/commands/verify-otp` | POST | Device token | Device verifies OTP entered by employee |
| `/api/v1/commands/admin-silent-uninstall` | POST | JWT | 1-click silent uninstall (no employee interaction) |
| `/api/v1/sim-events/` | GET | JWT | List SIM swap alerts |
| `/api/v1/uwb/{id}/live` | GET | JWT | Live UWB ranging data |
| `/api/v1/commands/audit-logs` | GET | JWT | Full audit trail |
| `/health` | GET | None | Health check |

Full reference: [docs/API.md](docs/API.md)

---

## Compliance

- **GDPR-compatible** — data minimization, retention policies, erasure on request
- **Employee consent** — enrollment screen shows disclosure and requires acceptance
- **Company devices only** — does not support BYOD/personal device monitoring
- **Transparent service** — OS-standard foreground service notification (not hidden)
- **Audit trail** — all monitoring activity logged and queryable

---

## Documentation

| Doc | Contents |
|-----|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flows, security architecture |
| [docs/API.md](docs/API.md) | Full API reference with curl examples |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deploy, SSL, zero-touch enrollment |
| [docs/SECURITY.md](docs/SECURITY.md) | OTP flow, JWT design, RBAC, certificate pinning |
| [docs/TESTING.md](docs/TESTING.md) | pytest, Jest, OWASP test strategy |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Module map, adding new commands |
| [docs/VIDEO_RECORDING_GUIDE.md](docs/VIDEO_RECORDING_GUIDE.md) | Demo video scripts with timestamps |
| [ironvault/IronVault_Setup_Guide.md](ironvault/IronVault_Setup_Guide.md) | IronVault anti-theft module setup |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, coding standards, PR process |

---

## License

[MIT](LICENSE) © 2026 ojas1216
