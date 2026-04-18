# IronVault — Complete Setup Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Android Studio | Hedgehog 2023.1+ | Build Android APK |
| JDK | 17+ | Kotlin compilation |
| Python | 3.11+ | Backend server |
| PostgreSQL | 15+ | Production DB |
| Redis | 7+ | Rate limiting / OTP |
| Firebase Project | Any | FCM push |
| Google Cloud Account | Any | Zero-touch enrollment |

---

## Step 1: Firebase Setup (5 minutes)

1. Open [Firebase Console](https://console.firebase.google.com)
2. Create project → **IronVault**
3. Add Android app → package: `com.ironvault`
4. Download `google-services.json` → place at `app/google-services.json`
5. Go to **Project Settings → Service Accounts** → Generate private key → save as `backend/firebase_credentials.json`
6. Enable **Cloud Messaging API** in Firebase Console

---

## Step 2: Build the Android APK (15 minutes)

```bash
# Clone / copy the ironvault/ folder
cd ironvault/android

# Copy your Firebase config
cp /path/to/google-services.json app/google-services.json

# Set your backend URL
# Edit app/src/main/res/values/config.xml:
#   <string name="backend_base_url">https://your-server.com/api</string>

# Generate release keystore
keytool -genkey -v -keystore ironvault-release.keystore \
  -alias ironvault -keyalg RSA -keysize 2048 -validity 10000

# Get cert hash → paste into app/build.gradle.kts EXPECTED_CERT_HASH
keytool -list -v -keystore ironvault-release.keystore | grep SHA256

# Build release APK
./gradlew assembleRelease \
  -PKEYSTORE_PATH=ironvault-release.keystore \
  -PKEYSTORE_PASSWORD=yourpassword \
  -PKEY_ALIAS=ironvault \
  -PKEY_PASSWORD=yourpassword

# APK output: app/build/outputs/apk/release/app-release.apk
```

### Device Owner Enrollment (required for uninstall block + FRP)

```bash
# ADB provisioning (before any accounts are added to device)
adb shell dpm set-device-owner com.ironvault/.DeviceAdminReceiver

# Verify
adb shell dpm list-owners
# Expected: com.ironvault/.DeviceAdminReceiver
```

### Zero-Touch Enrollment (for fleet deployment)

1. Open [Android Zero-touch Portal](https://partner.android.com/zerotouch)
2. Upload your APK or use EMM DPC token
3. Configure enrollment configuration with your backend URL
4. Assign to devices by IMEI

---

## Step 3: Deploy the Backend (10 minutes)

```bash
cd ironvault/backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env:
#   DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ironvault
#   REDIS_URL=redis://localhost:6379/0
#   JWT_SECRET=<random 64-char string>
#   DEVICE_HMAC_SECRET=<random 64-char string>
#   FIREBASE_CREDENTIALS=firebase_credentials.json
#   ADMIN_EMAIL=admin@yourcompany.com
#   ADMIN_PASSWORD_HASH=<bcrypt hash>

# Initialize database
psql -U postgres -c "CREATE DATABASE ironvault;"
psql -U postgres ironvault < database_schema.sql

# Run migrations
python -c "import asyncio; from server import create_tables; asyncio.run(create_tables())"

# Start server
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4

# For production with SSL:
uvicorn server:app --host 0.0.0.0 --port 443 \
  --ssl-keyfile /etc/ssl/key.pem \
  --ssl-certfile /etc/ssl/cert.pem \
  --workers 4
```

### Docker Deployment (recommended)

```bash
cd ironvault/backend
docker-compose up -d

# Services started:
# - ironvault-api:8000
# - ironvault-postgres:5432
# - ironvault-redis:6379
# - ironvault-nginx:443 (reverse proxy)
```

---

## Step 4: Enroll a Device (2 minutes)

1. Install APK on device (via MDM profile, ADB, or enterprise store)
2. Open app — first launch shows enrollment form
3. Fill: Device name, Owner name, Department
4. Tap **Enroll** — device registers with backend
5. Device appears in admin panel at `https://your-server.com/admin`

### Silent Enrollment (stealth mode)

```bash
# Install without icon
adb install -g app-release.apk

# Trigger enrollment via ADB
adb shell am broadcast -a com.ironvault.ENROLL \
  --es device_name "DEVICE-001" \
  --es owner "John Doe" \
  --es department "Sales"
```

---

## Step 5: Admin Panel

Open `https://your-server.com/admin` in browser.

Default login: admin@yourcompany.com / (password you bcrypt-hashed in .env)

### Admin Panel Features

| Feature | Location |
|---------|---------|
| Device list | Dashboard → All Devices |
| Real-time map | Dashboard → Live Map |
| SIM alerts | Alerts → SIM Events |
| Send command | Device Detail → Commands |
| Brick device | Device Detail → Security → Brick Mode |
| View hardware IDs | Device Detail → Hardware Identity |
| Anti-resale registry | Tools → Hardware Registry |

---

## Step 6: Manufacturer Tools

```bash
cd ironvault/manufacturer_tools

# Burn golden fingerprint during manufacturing
python inject_hardware_ids.py --device-serial ABC123 \
  --imei 490154203237518 \
  --model "Galaxy S23" \
  --manufacturer "Samsung"

# Generate unlock token for service center
python unlock_token_generator.py --device-id <UUID> \
  --reason "authorized_repair" \
  --valid-hours 24

# Emergency wipe all stolen devices
python remote_wipe_all.py --status stolen --dry-run
python remote_wipe_all.py --status stolen --confirm
```

---

## Step 7: Test the System

```bash
# Run backend tests
cd ironvault/backend
pytest tests/ -v

# Test FCM push
python -c "
from services.push_service import send_command
import asyncio
asyncio.run(send_command('DEVICE_ID', 'LOCATION', {}))
"

# Simulate SIM swap
adb shell am broadcast -a android.intent.action.SIM_STATE_CHANGED \
  --es ss absent --ei slot 0

# Test brick mode
adb shell am start -n com.ironvault/.BrickActivity
```

---

## Architecture Overview

```
[Android Device]
   IronVault App
   ├── TrackingService (foreground, persistent)
   ├── SIMIntelligence (SIM events)
   ├── HardwareTracker (fingerprint)
   ├── RemoteCommandProcessor (FCM + SMS)
   └── TamperResistance (anti-force-stop)
        │
        │ HTTPS + JWT + HMAC-SHA256
        ▼
[IronVault Backend]
   FastAPI + PostgreSQL + Redis
   ├── /register   → device enrollment
   ├── /heartbeat  → location updates
   ├── /alert      → tamper/SIM events
   ├── /command    → FCM command push
   └── /admin      → web dashboard
        │
        ▼
[Admin Dashboard]
   Browser-based, Leaflet.js map
   Real-time device tracking
   Remote command center
```

---

## Security Checklist

- [ ] JWT secret is ≥ 64 random characters
- [ ] HMAC device secret is ≥ 64 random characters
- [ ] Backend is behind HTTPS (TLS 1.3)
- [ ] APK is signed with release keystore (not debug)
- [ ] `EXPECTED_CERT_HASH` matches your release keystore SHA-256
- [ ] Device Owner enrollment complete (not just Device Admin)
- [ ] Firebase Credentials file is NOT committed to git
- [ ] `.env` file is NOT committed to git
- [ ] PostgreSQL is not exposed to public internet
- [ ] Redis is not exposed to public internet
- [ ] ProGuard enabled for release build
- [ ] `android:debuggable="false"` in release manifest

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Device Owner enrollment fails | Factory reset device first, no Google accounts added |
| IMEI returns null | Device Owner enrollment required for `READ_PRIVILEGED_PHONE_STATE` |
| FCM not received | Check `google-services.json`, verify FCM API enabled |
| SIM events not firing | Ensure `SIM_STATE_CHANGED` broadcast permission granted |
| UWB not working | Requires Pixel 6+, Samsung S21 Ultra+, Android 12+ |
| BLE fallback inaccurate | Normal — ±2m accuracy, UWB preferred |
| Backend 401 errors | JWT secret mismatch between APK and server |
| eMMC CID read fails | Root access required — non-root falls back to composite fingerprint |
