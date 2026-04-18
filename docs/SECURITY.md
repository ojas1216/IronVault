# Security Implementation Details

## Authentication & Authorization

### Admin Portal (JWT OAuth2)
- Access tokens: 15-minute expiry (HS256)
- Refresh tokens: 7-day expiry, single-use rotation
- RBAC: SUPER_ADMIN > ADMIN > MANAGER > VIEWER
- Failed login attempts are audit-logged

### Device Authentication
- Separate device JWT issued at enrollment
- Device token identifies device, not employee
- Certificates pinned on device via AppConfig.pinnedCertHashes

---

## OTP System

```
Admin clicks "Remote Uninstall"
         ↓
Backend: generate_otp(6 digits, secrets.choice)
         ↓
OTP hashed with argon2 (time_cost=2, memory=64MB)
         ↓
Stored in DB (OTPRecord) with 5-minute TTL
         ↓
Plaintext OTP displayed to admin ONCE in dashboard
         ↓
Admin shares OTP verbally or via secure channel with employee
         ↓
Employee enters OTP on device
         ↓
Backend verifies argon2 hash (rate limited: 3 attempts / 15 min)
         ↓
On success: command issued, OTP marked used, audit log written
         ↓
On failure: attempt counter incremented, locked after 3 failures
```

**Why argon2 for OTP?**
Prevents timing attacks. Even if DB is compromised, hashed OTPs
cannot be reversed in the 5-minute window.

---

## Uninstall Protection

### Android
- `DevicePolicyManager.setUninstallBlocked(component, packageName, true)`
- Requires Device Owner privileges
- Cannot be bypassed by user — only Device Owner can unblock
- On `DeviceAdminReceiver.onDisableRequested()`, message shown to user

### iOS
- MDM supervised profile: `RemoveApplicationRestriction`
- VPP (Volume Purchase) + managed app = admin controls removal
- DEP enrollment binds device to organization

### Windows
- Installed as SYSTEM-level Windows Service
- Service SDDL restricts stop/delete to Administrators only
- Registry protection prevents casual uninstall

### macOS
- LaunchDaemon at `/Library/LaunchDaemons/` (root-owned, 644)
- SIP (System Integrity Protection) protects system locations
- Admin password required for removal

---

## Data Security

| Data | Protection |
|---|---|
| Passwords | bcrypt (cost=12) |
| OTPs | argon2id hash only |
| Device tokens (mobile) | flutter_secure_storage (Keychain/EncryptedSharedPrefs) |
| Device tokens (desktop) | OS keychain (keyring) |
| API transport | HTTPS (TLS 1.2+) |
| Certificate pinning | SHA-256 hash of server cert |
| Database | PostgreSQL with SSL, encrypted at rest |

---

## Privacy & Compliance

### GDPR
- Data minimization: only collect what's necessary
- Purpose limitation: monitoring only for company-owned devices
- Retention: default 90 days, configurable
- Right to access: admin can export device history
- Right to erasure: `DELETE /devices/{id}` removes all data
- Consent: employees sign disclosure at onboarding

### Transparency
- Agent shows clear status screen (not hidden)
- Foreground service notification on Android (required by OS)
- Device enrollment screen explicitly states monitoring
- StatusScreen lists all active monitoring features

### Scope Limitation
- Work Profile on Android: personal apps NOT monitored
- No personal device enrollment (BYOD not supported)
- App usage reports only package names (not content)
- Location collected only during work hours (configurable)

---

## Security Checklist Before Production

- [ ] Change SECRET_KEY to cryptographically random 64-char string
- [ ] Change ENROLLMENT_CODE to something unguessable
- [ ] Enable certificate pinning (add server cert hash to AppConfig)
- [ ] Enable HTTPS-only, add HSTS header
- [ ] Restrict CORS to your admin domain only
- [ ] Enable PostgreSQL SSL
- [ ] Set Redis password
- [ ] Enable database encryption at rest
- [ ] Set up WAF (Web Application Firewall)
- [ ] Enable rate limiting at nginx level
- [ ] Set up log aggregation (ELK / CloudWatch)
- [ ] Enable MFA for admin accounts
- [ ] Run OWASP ZAP / Burp Suite scan on API
- [ ] Penetration test before deployment
