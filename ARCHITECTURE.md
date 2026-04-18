# Enterprise Device Security Management System (MDM)
## System Architecture

---

## 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ADMIN PANEL (React Web)                       │
│  - Device Dashboard    - Remote Commands    - Audit Logs             │
│  - OTP Management      - Location Map       - App Usage Reports      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS (JWT Auth)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND API (FastAPI / Python)                     │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Auth Service│  │Device Service│  │  OTP Service │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Push Service │  │ Audit Service│  │Monitor Service│              │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└──────┬───────────────────┬────────────────────┬────────────────────-┘
       │                   │                    │
       ▼                   ▼                    ▼
┌──────────────┐  ┌──────────────┐   ┌─────────────────────────────┐
│  PostgreSQL  │  │    Redis     │   │  FCM / APNs Push Gateway    │
│  (Main DB)   │  │  (Cache/OTP) │   │  (Command delivery)         │
└──────────────┘  └──────────────┘   └──────────────┬──────────────┘
                                                     │
              ┌──────────────────────────────────────┼───────────────┐
              ▼                                       ▼               ▼
┌─────────────────────┐          ┌─────────────────────┐  ┌────────────────────┐
│  Flutter Mobile App │          │  Flutter Mobile App  │  │ Python Desktop     │
│  (Android Agent)    │          │  (iOS Agent)         │  │ Agent (Win/macOS)  │
│                     │          │                      │  │                    │
│ - Device Owner API  │          │ - MDM Profile        │  │ - Windows Service  │
│ - Work Profile      │          │ - Supervised Mode    │  │ - macOS LaunchD    │
│ - FCM Receiver      │          │ - APNs Receiver      │  │ - FCM WebPush      │
│ - Location Service  │          │ - Location Service   │  │ - Monitoring       │
│ - App Usage Monitor │          │ - App Monitor        │  │ - App Usage        │
└─────────────────────┘          └─────────────────────┘  └────────────────────┘
```

---

## 2. SECURITY ARCHITECTURE

```
Admin Login
    │
    ▼
OAuth2 (Password Flow) → JWT Access Token (15 min) + Refresh Token (7 days)
    │
    ▼
All API Calls → JWT Middleware → Role-Based Access Control (RBAC)
    │
    ├── ADMIN role → full access
    ├── MANAGER role → view + limited commands
    └── VIEWER role → read-only

OTP Flow:
    Admin requests uninstall
    → Backend generates 6-digit TOTP
    → Stored as argon2 hash in Redis (TTL: 5 min)
    → Displayed to admin in dashboard
    → Employee must enter OTP on device
    → Backend verifies (rate limited: 3 attempts)
    → On success: uninstall command sent via FCM/APNs
    → Audit log created

Device Registration:
    Device installs agent
    → Generates device UUID + public key
    → Sends registration request with company enrollment token
    → Backend verifies enrollment token
    → Issues device certificate
    → Device enrolled
```

---

## 3. DATA FLOW

```
[Device] --heartbeat (30s)--> [Backend] --> [PostgreSQL: device_status]
[Device] --location update--> [Backend] --> [PostgreSQL: location_history]
[Device] --app usage log---> [Backend] --> [PostgreSQL: app_usage]

[Admin] --issue command-----> [Backend] --> [FCM/APNs] --> [Device]
[Device] --command result---> [Backend] --> [PostgreSQL: command_log]
[Device] --audit event------> [Backend] --> [PostgreSQL: audit_logs]
```

---

## 4. ENROLLMENT MODELS

### Android (Device Owner)
- IT admin provisions device using QR code / NFC / DPC identifier
- App gets Device Owner privileges via Android Enterprise
- `DevicePolicyManager.setUninstallBlocked()` prevents removal
- Remote commands via `DevicePolicyManager` + FCM

### iOS (MDM Profile)
- DEP (Device Enrollment Program) / Apple Business Manager
- MDM profile installed - cannot be removed without passcode
- App pinned via `ManagedAppConfiguration`
- Commands via APNs MDM channel

### Windows
- App installed as Windows Service (SYSTEM privileges)
- Registry-based uninstall protection (admin required)
- FCM Web Push for command delivery

### macOS
- LaunchDaemon (root-level persistent service)
- SIP + admin privileges for protection
- APNs / FCM for commands

---

## 5. COMPLIANCE & PRIVACY

- All location data stored with user consent disclosure
- Data retention policy: 90 days (configurable)
- GDPR: right to access / right to erasure supported
- Only company-owned devices (BYOD not in scope)
- Employee notified the device is monitored (onboarding disclosure)
- No personal app monitoring (Work Profile separation on Android)
