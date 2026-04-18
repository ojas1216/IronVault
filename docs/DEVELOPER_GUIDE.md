# Developer Guide — Enterprise MDM System

## Architecture Summary

```
Employee Device (Android/iOS/Windows/macOS)
    ↕ HTTPS + JWT + Certificate Pinning
FastAPI Backend (Python) ←→ PostgreSQL + Redis
    ↕
Admin Dashboard (React)
    ↕ FCM / APNs
Device Push Commands
```

---

## Module Map

### Backend (`backend/app/`)
| Module | Purpose |
|---|---|
| `models/device.py` | Device record, status, platform, location |
| `models/command.py` | Commands issued to devices |
| `models/sim_event.py` | SIM swap/insert/remove incidents |
| `models/device_identity.py` | IMEI, serial, hardware fingerprint |
| `models/uwb_session.py` | UWB/BLE ranging measurements |
| `models/audit_log.py` | Every admin and device action |
| `models/otp.py` | One-time passcode records (hashed) |
| `routers/auth.py` | Admin login, JWT, refresh |
| `routers/devices.py` | Device enrollment, heartbeat, commands |
| `routers/commands.py` | Issue commands, OTP, silent uninstall |
| `routers/sim_events.py` | SIM event reporting, identity, photos |
| `routers/uwb.py` | UWB ranging data ingestion + query |
| `services/otp_service.py` | OTP generate/verify (argon2) |
| `services/push_service.py` | FCM / APNs push gateway |
| `utils/security.py` | JWT, bcrypt, argon2, token generation |

### Mobile Flutter (`mobile/flutter_agent/lib/`)
| Service | Purpose |
|---|---|
| `services/enrollment_service.dart` | First-time device registration |
| `services/heartbeat_service.dart` | 30s status ping |
| `services/fcm_service.dart` | Firebase command receiver |
| `services/command_executor.dart` | Execute all command types |
| `services/sim_service.dart` | SIM metadata + lifecycle events |
| `services/device_identity_service.dart` | IMEI, serial, HW fingerprint |
| `services/camera_service.dart` | Security photo on SIM swap |
| `services/alarm_service.dart` | Remote alarm trigger |
| `services/uwb_service.dart` | UWB ranging (Android 12+ / iOS 11+) |
| `services/tamper_monitor.dart` | Anti-force-stop, airplane block |
| `services/factory_reset_protection.dart` | FRP via Device Owner API |
| `services/offline_queue.dart` | Queue commands when offline |
| `services/location_service.dart` | GPS location updates |
| `services/app_usage_service.dart` | App usage statistics |

### Android Native Kotlin
| Class | Purpose |
|---|---|
| `MDMDeviceAdminReceiver.kt` | Device Admin entry point |
| `DevicePolicyPlugin.kt` | Lock, wipe, uninstall block |
| `FactoryResetProtectionPlugin.kt` | FRP + safe mode + USB block |
| `SilentUninstallPlugin.kt` | Admin-authorized silent removal |
| `TamperPlugin.kt` | Airplane mode, power menu, PIN |
| `WatchdogService.kt` | Anti-force-stop, START_STICKY |
| `SimPlugin.kt` | SIM metadata extraction |
| `SimStateReceiver.kt` | SIM lifecycle events |
| `DeviceIdentityPlugin.kt` | IMEI, serial, Android ID |
| `UWBPlugin.kt` | UWB ranging + BLE fallback |
| `CameraPlugin.kt` | CameraX background capture |
| `AlarmPlugin.kt` | Remote alarm (max volume) |
| `ShutdownReceiver.kt` | Shutdown GPS snapshot |
| `BootReceiver.kt` | Auto-start on boot |
| `SecurityObfuscation.kt` | Anti-debug, Frida detect, APK verify |

---

## Uninstall Protection Flow

```
Employee presses Uninstall in Settings
         ↓
DeviceAdminReceiver.onDisableRequested() fires
         ↓
App shows PIN dialog: "Admin authorization required"
         ↓
Employee enters PIN (admin-provided OTP)
         ↓
App calls /commands/verify-otp
         ↓
Backend verifies argon2 hash (rate limit: 3 attempts)
         ↓
[FAIL] → Blocked. Attempt logged. Admin alerted.
[PASS] → Uninstall block lifted. App removed.
         ↓
Audit log: admin_id, device_id, IP, timestamp
```

## Admin Silent Uninstall Flow (1-click, <30 seconds)

```
Admin clicks "Remote Uninstall" in dashboard
         ↓
POST /commands/admin-silent-uninstall
         ↓
Backend auto-generates OTP (6 digits)
Backend auto-verifies OTP server-side
         ↓
FCM push sent to device with pre-authorized token
         ↓
Device receives FCM → CommandExecutor runs
→ DPM.setUninstallBlocked(false)
→ DPM.clearDeviceOwnerApp()
→ App uninstalled silently
         ↓
Audit log created (admin + timestamp + device)
```

## Factory Reset Protection

```
Device enrolled → Device Owner set
         ↓
DPM.setFactoryResetProtectionPolicy(companyAccount)
DPM.addUserRestriction(DISALLOW_FACTORY_RESET)
DPM.addUserRestriction(DISALLOW_SAFE_BOOT)
DPM.setSecureSetting(ADB_ENABLED, "0")
         ↓
Employee tries factory reset → BLOCKED by OS
         ↓
If admin authorizes reset:
→ DPM.clearUserRestriction(DISALLOW_FACTORY_RESET)
→ Device resets
→ FRP requires company Google account to unlock
→ Zero-touch enrollment re-installs agent automatically
```

---

## UWB Tracking Setup

### Android Requirements
- Android 12+ (API 33+)
- UWB hardware: Pixel 6/7/8, Samsung Galaxy S21 Ultra+, OnePlus 11
- Add to `build.gradle`: `implementation 'androidx.core.uwb:uwb:1.0.0-alpha08'`

### iOS Requirements
- iPhone 11 or newer (U1 chip)
- iOS 14+ / NearbyInteraction framework
- Requires device pairing token exchange

### BLE Fallback (all devices)
- Works on all Bluetooth devices
- Accuracy: ±1–3 m (vs ±10–30 cm for UWB)
- Automatically enabled when UWB is unavailable

### Ranging Accuracy Table
| Mode | Typical Accuracy | Update Rate |
|---|---|---|
| UWB (Android) | ±10–30 cm | 10 Hz |
| iOS NearbyInteraction | ±10 cm | 10 Hz |
| BLE RSSI | ±1–3 m | 1 Hz |

---

## Code Protection (Anti-Reverse-Engineering)

### ProGuard/R8 (Release Builds)
- All class/method/field names renamed to `a`, `b`, `c`...
- All packages flattened to `x/`
- Logging stripped completely
- String constants obfuscated

### APK Signature Verification
Update `BuildConfig.EXPECTED_CERT_HASH` in `build.gradle`:
```gradle
buildConfigField "String", "EXPECTED_CERT_HASH",
    '"your-release-cert-sha256-hash"'
```
Generate with:
```bash
keytool -list -v -keystore release.keystore | grep SHA256
```

### Runtime Checks
- Debugger detection (Debug.isDebuggerConnected)
- Frida/Xposed framework detection
- APK signature verification on startup
- Disable on debug builds via `BuildConfig.ENFORCE_EMULATOR_CHECK`

---

## Admin Usage Guide

### Enrolling a Device
1. Install APK on device (via MDM profile or manual install)
2. Open app → fill enrollment form
3. Device appears in admin dashboard within 30 seconds

### Blocking Uninstall
- Automatic after enrollment when Device Owner is set
- Status visible in Device Detail → "Uninstall Protection Active"

### Initiating Remote Actions
| Action | OTP Required | Time to Complete |
|---|---|---|
| Lock Device | No | ~5 sec |
| Trigger Alarm | No | ~5 sec |
| Capture Front Camera | No | ~10 sec |
| Extract SIM Info | No | ~10 sec |
| Remote Uninstall | Auto (server-side) | ~30 sec |
| Wipe Device | Auto (server-side) | ~30 sec |

### Viewing SIM Alerts
- Navigate to **SIM Alerts** in sidebar
- All SIM swap/remove events are auto-detected
- Security photo attached automatically
- Resolve and add notes when investigated

### UWB Live Tracking
- Open Device Detail page
- UWB Tracker panel shows live distance + direction
- Radar updates every 1 second
- Use to physically locate a device in an office/building
