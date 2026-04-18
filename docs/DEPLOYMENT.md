# Deployment Guide

## Prerequisites
- Ubuntu 22.04 server (2 CPU, 4GB RAM minimum)
- Docker + Docker Compose
- Domain with SSL certificate
- Firebase project (for FCM)
- Apple Developer account + APNs key (for iOS)

---

## Step 1 — Backend Setup

```bash
# Clone repo and enter backend directory
cd backend

# Copy and fill environment variables
cp .env.example .env
nano .env   # Fill in all values

# Place Firebase credentials
mkdir -p secrets
cp /path/to/firebase-credentials.json secrets/

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Create first super-admin
docker-compose exec api python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.services.auth_service import create_admin_user
from app.models.user import UserRole

async def main():
    async with AsyncSessionLocal() as db:
        user = await create_admin_user(
            db, 'admin@company.com', 'Admin Name',
            'YourSecurePassword123!', UserRole.SUPER_ADMIN
        )
        await db.commit()
        print(f'Created: {user.email}')

asyncio.run(main())
"
```

---

## Step 2 — Admin Dashboard Setup

```bash
cd admin_dashboard

# Set API URL
echo 'VITE_API_URL=https://mdm-api.yourcompany.com/api/v1' > .env

npm install
npm run build

# Serve dist/ folder via nginx or Vercel/Netlify
```

---

## Step 3 — Android App Deployment

```bash
cd mobile/flutter_agent

# Set API URL and enrollment code
# In lib/config/app_config.dart — update baseUrl

# Build release APK
flutter build apk --release \
  --dart-define=API_BASE_URL=https://mdm-api.yourcompany.com/api/v1 \
  --dart-define=ENROLLMENT_CODE=YOUR_COMPANY_CODE

# For Device Owner provisioning, use Android Enterprise Zero-Touch or:
# adb shell dpm set-device-owner com.company.mdmagent/.MDMDeviceAdminReceiver
```

---

## Step 4 — iOS Deployment

```bash
# Requires Apple Developer + MDM certificate
# 1. Enroll in Apple Business Manager
# 2. Create MDM Push Certificate in Apple Push Certificates Portal
# 3. Upload certificate to backend .env

flutter build ipa --release
# Distribute via MDM solution or Apple Business Manager
```

---

## Step 5 — Windows Agent Deployment

```bash
cd desktop_agent

# Install dependencies
pip install -r requirements.txt

# Build executable
pyinstaller --onefile --noconsole --name mdm_agent agent.py

# Set enrollment code in secure store before running
# Deploy via Group Policy or SCCM

# Install service (run as Administrator)
python install_windows.py install
```

---

## Step 6 — macOS Agent Deployment

```bash
# Build executable
pyinstaller --onefile --name mdm_agent agent.py

# Deploy via Jamf or manually
sudo bash install_macos.sh
```

---

## Nginx Configuration (HTTPS)

```nginx
server {
    listen 443 ssl http2;
    server_name mdm-api.yourcompany.com;

    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key (min 32 chars, random) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase service account JSON |
| `APNS_KEY_PATH` | Path to APNs .p8 key file |
| `ENROLLMENT_CODE` | Company enrollment code (keep secret) |
| `DEVICE_DATA_ENCRYPTION_KEY` | 32-char AES key for device data |
