# IronVault MDM — Enterprise Device Management & Hardware Anti-Theft System

A complete Mobile Device Management (MDM) platform for Android with deep hardware-level tracking, anti-resale protection, and remote device control. Built for enterprises that need to secure, monitor, and recover company-issued devices — even if a device is wiped, re-flashed, or its components are swapped.

---

## What This System Can Do

### Remote Device Control
- **Remote Lock** — instantly lock the device screen from the dashboard
- **Remote Alarm** — trigger a loud siren (cannot be silenced without admin approval)
- **Remote Wipe** — factory reset the device remotely (OTP-protected)
- **Lost Mode** — display a full-screen message with contact info on the device
- **Remote Uninstall** — remove the agent remotely (OTP-protected)
- **Front Camera Capture** — silently take a photo via the front camera
- **GPS Location** — get the device's current location on demand
- **SIM Info Extraction** — read IMEI, ICCID, carrier, and SIM slot details remotely

### Hardware Anti-Resale & Theft Detection
- **Hardware Fingerprinting** — at enrollment, the system records a cryptographic hash of every hardware component: board, SoC (Snapdragon/MediaTek chip), WiFi chip MAC address, Bluetooth MAC address, device serial number, bootloader, and firmware. This becomes the "golden record."
- **Continuous Verification** — every 30 seconds, the device re-computes and sends its hardware fingerprint. If anything has changed, an alert fires immediately.
- **Chipset Swap Detection** — if the Snapdragon or any SoC is replaced, the SoC model and board ID in the fingerprint will change. The system flags this as `HARDWARE_TAMPERED`.
- **Motherboard Replacement Detection** — if the motherboard is physically replaced (baseboard serial or BIOS UUID changes), the system flags the device as `RESOLD`.
- **Factory Reset Does Not Help** — the hardware fingerprint is stored on the server, not on the device. Wiping the device does not erase the fingerprint. When the thief tries to re-enroll, the system recognises the hardware and blocks enrollment with `RESALE_DETECTED`.
- **Global Registry** — all hardware fingerprints are stored in a cross-company registry. If a stolen device is handed to another company that also uses this system, it will be flagged on their enrollment attempt too.
- **Mark as Stolen** — admins can manually mark a hardware fingerprint as stolen. Any future enrollment attempt with that hardware is permanently blocked.

### SIM Card Monitoring
- **SIM Swap Detection** — any SIM card insertion, removal, or swap triggers an automatic security response: GPS location is recorded, a front-camera photo is taken, and an incident is logged.
- **IMEI Tracking** — dual-SIM IMEI is tracked. If the baseband (modem chip) is replaced, the IMEI changes and a tamper alert fires.
- **ICCID and IMSI Logging** — carrier and subscriber identity tracked per event.

### Tamper Resistance
- **Uninstall Protection** — the agent cannot be uninstalled by the user. Attempting to uninstall requires admin OTP authorization.
- **Factory Reset Protection (FRP)** — after enrollment, the device requires company Google account authentication after any factory reset. Without that account, the device cannot be set up.
- **Force-Stop Prevention** — a watchdog service re-launches the agent if it is killed.
- **Airplane Mode Blocking** — agent re-enables network immediately if airplane mode is activated.
- **Debugger and Root Detection** — detects Frida, Xposed, and root access; reports to backend.
- **APK Signature Verification** — verifies the agent has not been repackaged or tampered with.
- **Boot Persistence** — agent restarts automatically on every device boot.
- **Foreground Service** — keeps agent alive even under aggressive battery optimization.

### Firmware Integrity Monitoring
- **Bootloader Status** — detects unlocked bootloaders (indicator of a rooting attempt).
- **Verified Boot State** — monitors Android Verified Boot (green/orange/red status).
- **Firmware Fingerprint** — SHA-256 of the build fingerprint, bootloader version, and security patch level. Any firmware flash or OS modification changes this hash and triggers an alert.
- **Security Patch Tracking** — last known security patch date is tracked per device.

### Location & Tracking
- **Real-Time GPS** — continuous location tracking with configurable intervals.
- **Shutdown Snapshot** — when the device is powered off, the last known GPS location is recorded and synced to the backend before shutdown.
- **Location History** — full history of location updates stored and viewable in the dashboard.
- **UWB Proximity Tracking** — Ultra-Wideband proximity detection for high-precision indoor tracking (on supported hardware).

### Admin Dashboard
- Web-based dashboard accessible at `http://localhost:3000` (or your domain)
- Device list with online/offline status, last seen, location, and flag status
- Device detail page: location map, hardware identity, command panel, audit log
- Hardware registry: view stolen/resold devices, lookup fingerprints, mark stolen
- Role-based access: Admin, Operator, Viewer
- OTP-protected destructive commands (wipe, uninstall)

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Mobile Agent** | Flutter 3.x (Dart), Android Kotlin plugins |
| **Hardware Fingerprinting** | Native Kotlin: Android Build API, TelephonyManager, BluetoothManager, sysfs, SHA-256 |
| **Secure Key Storage** | Android Keystore (TEE-backed ECDSA keys) |
| **Firmware Verification** | Android Verified Boot API, Build.FINGERPRINT, bootloader properties |
| **Backend API** | Python 3.12 + FastAPI + SQLAlchemy (async) |
| **Database** | PostgreSQL 16 |
| **Cache / Queue** | Redis 7 |
| **Push Notifications** | Firebase Cloud Messaging (FCM) |
| **Authentication** | JWT (device tokens: 365-day, admin tokens: short-lived) |
| **Admin Dashboard** | React + TypeScript + Vite |
| **Deployment** | Docker Compose + Nginx (TLS) |
| **Encryption** | AES-256-CBC + PBKDF2 for local data, TLS 1.3 for transport |

### How Hardware Fingerprinting Works

The composite hardware fingerprint is a SHA-256 hash of these hardware identifiers:

```
SHA-256(
  board_name | brand | device_codename | hardware_platform |
  manufacturer | model | product | soc_manufacturer | soc_model |
  wifi_mac_address | bluetooth_mac_address | device_serial
)
```

This fingerprint is recorded at enrollment and becomes the **golden record** on the server. On every heartbeat (every 30 seconds), the device recomputes this hash and sends it. A mismatch means hardware was changed.

**Component → What Changing It Does:**

| Changed Component | Detected As |
|---|---|
| Snapdragon / SoC replaced | `HARDWARE_TAMPERED` |
| WiFi chip replaced | `HARDWARE_TAMPERED` |
| Bluetooth chip replaced | `HARDWARE_TAMPERED` |
| Device serial changed | `HARDWARE_TAMPERED` |
| Motherboard replaced | `RESOLD` |
| BIOS / bootloader changed | `FIRMWARE_CHANGED` |
| Firmware flashed | `FIRMWARE_CHANGED` |
| Device re-enrolled on new account | `RESALE_DETECTED` → enrollment blocked |

---

## Deployment

### Prerequisites
- A Linux server (Ubuntu 22.04 LTS recommended) — any cloud provider
- A domain name with two subdomains:
  - `admin.yourdomain.com` → Admin dashboard
  - `api.yourdomain.com` → Backend API
- Ports 80 and 443 open on your server firewall
- Minimum: 2 vCPU · 4 GB RAM · 20 GB disk (supports up to 500 devices)

### Step 1 — Install Docker

```bash
ssh user@your-server-ip
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin -y
```

### Step 2 — Upload Project

```bash
scp -r ironvault-mdm/ user@your-server-ip:/opt/ironvault-mdm
ssh user@your-server-ip
cd /opt/ironvault-mdm
```

### Step 3 — Create Environment File

```bash
cp .env.production.example .env
nano .env
```

Fill in these values:

| Variable | How to generate |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` |
| `DEVICE_DATA_ENCRYPTION_KEY` | `openssl rand -base64 32` |
| `POSTGRES_PASSWORD` | Any strong password |
| `REDIS_PASSWORD` | Any strong password |
| `ENROLLMENT_CODE` | A secret code given to employees at device setup (e.g. `ACME_SECURE_2024`) |
| `ALLOWED_ORIGINS` | `["https://admin.yourdomain.com"]` |
| `ALLOWED_HOSTS` | `["api.yourdomain.com"]` |
| `VITE_API_URL` | `https://api.yourdomain.com/api/v1` |

### Step 4 — Set Your Domain in Nginx

```bash
sed -i 's/yourdomain.com/youractualdomain.com/g' nginx/nginx.conf
```

### Step 5 — Get TLS Certificate

```bash
apt install certbot -y
certbot certonly --standalone \
  -d api.youractualdomain.com \
  -d admin.youractualdomain.com
cp /etc/letsencrypt/live/youractualdomain.com/fullchain.pem nginx/certs/
cp /etc/letsencrypt/live/youractualdomain.com/privkey.pem   nginx/certs/
```

### Step 6 — Start the Application

```bash
docker compose up -d --build
```

Wait 60 seconds, then verify:

```bash
docker compose ps           # All services should show healthy/running
curl https://api.youractualdomain.com/health   # Should return {"status":"healthy"}
```

### Step 7 — Set Up the Database

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
```

### Step 8 — First Login

Open `https://admin.youractualdomain.com`

**Default credentials:**
- Email: `admin@ironvault.com`
- Password: `Admin1234!`

> Change these immediately after first login.

---

## Enrolling a Device

1. Install the agent APK on the Android device
2. In the admin dashboard: click **Add Device**, fill in employee details
3. Give the employee the **Enrollment Code** (the `ENROLLMENT_CODE` from your `.env`)
4. Employee opens the app, enters the server URL and enrollment code
5. Device activates Device Administrator, collects hardware fingerprint, and appears in the dashboard

At enrollment the system:
- Records IMEI, serial number, Android ID, hardware fingerprint, firmware fingerprint
- Stores the golden hardware record in the global registry
- Issues the device a 365-day JWT token for authenticated communication

---

## Using the Dashboard

### Send Commands

Open any device → Command Panel:

| Command | OTP Required | Effect |
|---|---|---|
| Lock Device | No | Locks screen immediately |
| Trigger Alarm | No | Plays loud siren |
| Request Location | No | Fetches current GPS |
| Capture Front Camera | No | Silent front-camera photo |
| Extract SIM Info | No | Returns IMEI, ICCID, carrier |
| Get Device ID | No | Returns hardware identity |
| Lost Mode | No | Shows full-screen lost notice |
| Remote Uninstall | **Yes** | Removes agent remotely |
| Wipe Device | **Yes** | Factory resets device |

### Hardware Registry

**Dashboard → Hardware Registry:**
- View all devices flagged for hardware mismatch or resale
- Look up any hardware fingerprint to check stolen/resale status
- Mark a hardware fingerprint as stolen to block all future enrollments

---

## Certificate Auto-Renewal

```bash
# Add to crontab (crontab -e)
0 3 * * * certbot renew --quiet && \
  cp /etc/letsencrypt/live/youractualdomain.com/fullchain.pem /opt/ironvault-mdm/nginx/certs/ && \
  cp /etc/letsencrypt/live/youractualdomain.com/privkey.pem /opt/ironvault-mdm/nginx/certs/ && \
  cd /opt/ironvault-mdm && docker compose restart nginx
```

---

## Database Backup

```bash
# Backup
docker compose exec postgres pg_dump -U mdm_user mdm_db > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T postgres psql -U mdm_user mdm_db < backup_20240101.sql
```

---

## Maintenance

```bash
# View logs
docker compose logs -f backend
docker compose logs -f nginx

# Restart a service
docker compose restart backend

# Stop everything
docker compose down

# Start again
docker compose up -d
```

---

## Common Issues

**Dashboard not loading?**
```bash
docker compose logs nginx
docker compose logs dashboard
```

**API returning errors?**
```bash
docker compose logs backend
```

**Device not appearing after enrollment?**
- Confirm the employee entered the correct Enrollment Code
- Confirm the device can reach your server (same network, or server is publicly accessible)
- Check `docker compose logs backend` for enrollment errors

**Certificate error in browser?**
- Confirm DNS for both subdomains resolves to your server IP
- Re-run Step 5 to regenerate certificates

---

## License

See [LICENSE](LICENSE) for full terms.

This software is licensed for **authorized enterprise MDM use only**. The author expressly disclaims all liability for any misuse. Deploying organizations bear full legal responsibility for compliance with applicable privacy and employment laws. See LICENSE Section 3 for full misuse disclaimer.

---

## Legal Notice

Hardware fingerprinting, IMEI logging, location tracking, and remote device control features are intended exclusively for company-owned devices enrolled with employee knowledge and consent. Any deployment must comply with applicable local laws governing employee monitoring and device management. See LICENSE for full terms.
