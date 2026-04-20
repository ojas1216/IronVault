# IronVault MDM — Security Design & Requirements Compliance

## Requirements Verification Matrix

### 1. Manual Uninstall Protection

| Sub-requirement | Implementation | Status |
|---|---|---|
| Block uninstall via device settings/app store | Android: `DevicePolicyManager.setUninstallBlocked(true)` (Device Owner) | Done |
| Require unique one-time passcode | 6-digit OTP via `secrets.choice`, argon2id hashed, never plaintext | Done |
| Secure generation via backend API | `POST /commands/generate-otp` — server-side only | Done |
| Brute-force protection | 3 attempts then 15-minute Redis lockout | Done |
| Branded message on uninstall | "Admin authorization is required to uninstall. Enter passcode to proceed." | Done |
| iOS uninstall block | MDM Profile supervised mode — user cannot remove | Done |
| Windows uninstall block | Registry lock + Windows Service (SYSTEM privileges) | Done |
| macOS uninstall block | LaunchDaemon (root) + SIP protection | Done |

### 2. Admin Remote Uninstall

| Sub-requirement | Implementation | Status |
|---|---|---|
| One-click from dashboard | POST /commands/admin-silent-uninstall | Done |
| OTP auto-generated server-side | Server generates + pre-verifies OTP internally, never shown to anyone | Done |
| Delivered via secure channel | FCM (Android) / APNs HTTP2 (iOS) / polling fallback | Done |
| Device applies silently | SilentUninstallPlugin.kt handles FCM `remote_uninstall` without UI | Done |
| Audit log | audit_logs table: admin_user_id, device_id, IP, timestamp, command details | Done |

### 3. OTP Security

| Sub-requirement | Implementation | Status |
|---|---|---|
| OTP expires after 5 minutes | otp_records.expires_at = now + 300s; verified on use | Done |
| Secure hash (no plaintext) | argon2id (time=2, mem=65536 KB, parallel=2) | Done |
| Attempt limiting | Max 3 attempts; Redis-based 15-min lockout after failure | Done |

### 4. Offline Handling

| Sub-requirement | Implementation | Status |
|---|---|---|
| Queue commands when offline | SQLite local OfflineQueue on device | Done |
| Process on reconnect | Commands replayed on next successful heartbeat | Done |
| Heartbeat polling fallback | GET /devices/{id}/pending-commands called every heartbeat | Done |

### 5. Tamper Detection

| Sub-requirement | Implementation | Status |
|---|---|---|
| Root detection (Android) | Heartbeat includes is_rooted flag; TamperPlugin checks root binaries | Done |
| Jailbreak detection (iOS) | Checked in heartbeat service | Done |
| Admin alerts | Dashboard shows red "Security Alert: Rooted" badge on device card | Done |
| Tamper event reporting | POST /devices/tamper-event logs to audit_logs | Done |

### 6. Factory Reset Survival

| Platform | Method | Status |
|---|---|---|
| Android | Device Owner API persists through FRP | Done |
| iOS | MDM Profile (supervised) persists through user reset | Done |
| Windows | Service reinstalled post-reset (documented) | Documented |
| macOS | Daemon reinstalled post-reset (documented) | Documented |

### 7. Auto-Start on Boot/Restart

| Platform | Method | Status |
|---|---|---|
| Android | BootReceiver BOOT_COMPLETED + START_STICKY | Done |
| iOS | BackgroundTasks framework + LaunchAgent | Done |
| Windows | Windows Service SCM AUTO_START | Done |
| macOS | LaunchDaemon plist RunAtLoad=true | Done |

### 8. IMEI Tracking

| Feature | Implementation | Status |
|---|---|---|
| Dual-SIM IMEI collection | TelephonyManager (slot 1 and 2) | Done |
| Encrypted storage | device_identities table + DEVICE_DATA_ENCRYPTION_KEY | Done |
| Masked UI (show/hide) | DeviceIdentityPanel.tsx toggle per field | Done |
| On-demand retrieval | extract_device_identity command | Done |

### 9. UWB Precision Tracking

| Feature | Implementation | Status |
|---|---|---|
| UWB ranging Android 12+ | UWBPlugin.kt (IEEE 802.15.4a, U1 chip) | Done |
| UWB ranging iOS 11+ | NearbyInteraction framework | Done |
| BLE RSSI fallback | Both platforms fall back when UWB unavailable | Done |
| Live radar dashboard | UWBTracker.tsx canvas radar, distance + azimuth + direction | Done |
| Direction guidance | "Turn right 45°", "Straight ahead 3.2m" text hints | Done |
| History | GET /uwb/{device_id}/history (200 points) | Done |

### 10. SIM Swap Detection

| Feature | Implementation | Status |
|---|---|---|
| SIM state change detection | SimStateReceiver.kt BroadcastReceiver | Done |
| Server alert within seconds | POST /sim-events/report | Done |
| Security photo on swap | CameraPlugin CameraX headless capture | Done |
| Location snapshot on swap | LocationService triggered simultaneously | Done |
| Admin dashboard alerts | SimAlertsPage.tsx — resolve with notes | Done |

### 11. Installation File Protection / Obfuscation

| Feature | Implementation | Status |
|---|---|---|
| APK code obfuscation | ProGuard/R8 rules (proguard-rules.pro) | Done |
| Anti-debug (Frida) | SecurityObfuscation.kt runtime ptrace + Frida lib check | Done |
| APK signature check | Runtime hash verification against expected certificate | Done |
| Hidden from launcher | No LAUNCHER activity in AndroidManifest | Done |
| Enrollment code not in APK | Verified against backend at enrollment time only | Done |

### 12. Multi-Platform Coverage

| Platform | Agent | Push | Uninstall Block | Boot Start |
|---|---|---|---|---|
| Android | Flutter + Kotlin | FCM | Device Owner API | BootReceiver |
| iOS | Flutter + Swift | APNs | MDM Profile | BackgroundTasks |
| Windows | Python Service | FCM Web Push | Registry + SYSTEM | Windows SCM |
| macOS | Python LaunchDaemon | FCM Web Push | SIP + root | RunAtLoad |

---

## Cryptography Reference

### Admin Password Hashing
- Algorithm: bcrypt
- Cost factor: 12
- Library: `bcrypt` Python (direct, no passlib wrapper)

### OTP Hashing
- Algorithm: argon2id
- Parameters: time_cost=2, memory_cost=65536 (64 MB), parallelism=2
- Library: argon2-cffi
- TTL: 300 seconds, max 3 attempts

### JWT Tokens
- Algorithm: HS256
- Admin access token: 15 minutes
- Admin refresh token: 7 days
- Device token: 365 days (type="device" — distinct from admin type="access")

### Transport Security
- TLS 1.2 / 1.3 enforced by Nginx
- HSTS: `max-age=31536000; includeSubDomains`
- Certificate pinning in mobile agents

---

## Role-Based Access Control

| Role | Capabilities |
|---|---|
| SUPER_ADMIN | All operations + create/deactivate admin users |
| ADMIN | Issue all commands (including destructive with OTP), manage devices |
| MANAGER | Non-destructive commands, view all data |
| VIEWER | Read-only access |

---

## Rate Limiting (Double Layer)

| Layer | Limit |
|---|---|
| Nginx | 30 req/s per IP, burst 60 |
| SlowAPI (backend) | 60 req/min per IP (default, configurable) |
| Login endpoint | 5 req/min per IP |
| OTP generation | 10 req/min per IP |

---

## Audit Trail Fields

Every admin action records:
- `action` — type (admin_login, command_issued, otp_generated, tamper_detected, etc.)
- `admin_user_id` — who performed the action
- `device_id` — which device was affected
- `ip_address` — originating IP
- `created_at` — UTC timestamp
- `metadata` — JSON with action-specific details (command type, OTP ID, etc.)

Audit logs are append-only and never deleted (even when a device is removed).

---

## Compliance Notes

- **GDPR**: Data minimisation, audit trail, right-to-erasure (DELETE /devices/{id} deletes all associated data)
- **HIPAA**: TLS transport, encrypted at-rest storage, RBAC, full audit logs
- **Data residency**: Fully self-hosted — no data leaves your infrastructure
- **No plaintext secrets**: Passwords (bcrypt), OTPs (argon2id), tokens (JWT signed)
