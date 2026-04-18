# Enterprise Device Security Management System (MDM)

A production-ready, OS-compliant MDM solution for managing company-owned devices.
Prevents unauthorized uninstall, enables remote monitoring, and allows secure admin control.

---

## Quick Start

```
1. Deploy backend:   cd backend && docker-compose up -d
2. Run dashboard:    cd admin_dashboard && npm run dev
3. Build mobile:     cd mobile/flutter_agent && flutter run
4. Install desktop:  cd desktop_agent && python install_windows.py install
```

---

## Project Structure

```
Antitheft/
├── ARCHITECTURE.md           ← System design diagrams
├── backend/                  ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py           ← FastAPI app entry point
│   │   ├── config.py         ← Settings (env-driven)
│   │   ├── database.py       ← Async PostgreSQL
│   │   ├── models/           ← SQLAlchemy ORM models
│   │   ├── routers/          ← API route handlers
│   │   ├── services/         ← Business logic
│   │   ├── schemas/          ← Pydantic request/response schemas
│   │   └── utils/            ← Security, rate limiting helpers
│   ├── alembic/              ← DB migrations
│   ├── Dockerfile
│   └── docker-compose.yml    ← Backend + PostgreSQL + Redis
│
├── mobile/flutter_agent/     ← Flutter mobile app (Android + iOS)
│   ├── lib/
│   │   ├── main.dart
│   │   ├── config/           ← API URL, cert pins
│   │   ├── services/         ← Enrollment, heartbeat, FCM, location
│   │   └── screens/          ← Enrollment, Status, OTP dialogs
│   └── android/              ← Device Policy Manager native code
│
├── desktop_agent/            ← Python agent (Windows/macOS service)
│   ├── agent.py              ← Main service entry point
│   ├── services/             ← Heartbeat, app monitor, commands
│   ├── utils/                ← Secure storage, device info
│   ├── install_windows.py    ← Windows Service installer
│   └── install_macos.sh      ← macOS LaunchDaemon installer
│
├── admin_dashboard/          ← React TypeScript admin UI
│   └── src/
│       ├── api/              ← Axios client + API methods
│       ├── pages/            ← Dashboard, Device Detail, Audit Logs
│       ├── components/       ← Cards, Map, Charts, OTP Modal
│       └── store/            ← Zustand auth state
│
└── docs/
    ├── API.md                ← Full API reference
    ├── DEPLOYMENT.md         ← Step-by-step deploy guide
    ├── SECURITY.md           ← Security implementation details
    ├── TESTING.md            ← Unit + integration + security tests
    └── DEMO_RECORDING.md     ← Demo video script
```

---

## Key Features

| Feature | Android | iOS | Windows | macOS |
|---|---|---|---|---|
| Uninstall protection | DevicePolicyManager | MDM Profile | Windows Service | LaunchDaemon |
| Remote lock | DPM.lockNow() | MDM Lock | LockWorkStation | CGSession |
| Remote uninstall | DPM.unblockUninstall | MDM Remove | sc delete | launchctl |
| Device wipe | DPM.wipeData() | MDM Erase | systemreset | eraseinstall |
| Location tracking | Geolocator | Geolocator | N/A | N/A |
| App usage | UsageStatsManager | Limited | Win32 API | osascript |
| Auto-start | BOOT_COMPLETED | Background Modes | Service | LaunchDaemon |
| Push commands | FCM | APNs | FCM | FCM |

---

## Security Highlights

- OTP-protected destructive commands (argon2 hash, 5-min TTL)
- JWT auth with 15-min access token rotation
- Rate-limited OTP: 3 attempts then 15-min lockout
- Certificate pinning on all device agents
- Complete audit trail (every action logged with admin ID + IP + timestamp)
- RBAC: Super Admin → Admin → Manager → Viewer

---

## Compliance

- GDPR-compatible (data minimization, retention, erasure)
- No personal data on personal apps (Android Work Profile)
- Employees informed via enrollment disclosure
- All monitoring limited to company-owned devices
- No hidden/stealth operation (OS-standard service notifications)

---

## Docs
- [Architecture](ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Security Details](docs/SECURITY.md)
- [Testing Strategy](docs/TESTING.md)
- [Demo Recording Guide](docs/DEMO_RECORDING.md)
