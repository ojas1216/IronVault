# IronVault MDM — Production Deployment Guide

## Prerequisites

| Requirement | Notes |
|---|---|
| Linux server (Ubuntu 22.04+ recommended) | 2 CPU / 4 GB RAM minimum |
| Docker 24+ and Docker Compose v2 | `apt install docker.io docker-compose-plugin` |
| Domain name | e.g. `yourdomain.com` with DNS A records |
| Firebase project | For Android push (FCM) |
| Apple Developer account | For iOS push (APNs) |

---

## Step 1 — DNS Setup

Point these DNS A records to your server IP:

```
api.yourdomain.com    →  <server-ip>
admin.yourdomain.com  →  <server-ip>
```

---

## Step 2 — TLS Certificates

```bash
# Install certbot
apt install certbot

# Obtain certificates (server must be reachable on port 80)
certbot certonly --standalone \
  -d api.yourdomain.com \
  -d admin.yourdomain.com

# Copy to nginx certs directory
mkdir -p nginx/certs
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/certs/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   nginx/certs/

# Auto-renew (add to crontab)
echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/yourdomain.com/*.pem /path/to/nginx/certs/" | crontab -
```

---

## Step 3 — Configure Environment

```bash
cp .env.production.example .env
```

Edit `.env` — required values:

```bash
# Generate secrets
openssl rand -hex 32          # → SECRET_KEY
openssl rand -base64 32       # → DEVICE_DATA_ENCRYPTION_KEY

# Set strong passwords
POSTGRES_PASSWORD=<strong-random-password>
REDIS_PASSWORD=<strong-random-password>

# Set your domains
ALLOWED_ORIGINS=["https://admin.yourdomain.com"]
ALLOWED_HOSTS=["api.yourdomain.com"]

# Set your enrollment code (share with IT for device setup)
ENROLLMENT_CODE=<your-company-secret-code>

# Firebase
FIREBASE_PROJECT_ID=your-firebase-project-id

# Dashboard API URL (used at build time)
VITE_API_URL=https://api.yourdomain.com/api/v1
```

---

## Step 4 — Firebase Setup (Android push)

1. Create project at https://console.firebase.google.com
2. Go to Project Settings → Service Accounts → Generate new private key
3. Save as `firebase-credentials.json`
4. Place it at: `/secrets/firebase-credentials.json` on the server

```bash
mkdir -p /secrets
cp firebase-credentials.json /secrets/
chmod 600 /secrets/firebase-credentials.json
```

---

## Step 5 — APNs Setup (iOS push)

1. Go to https://developer.apple.com/account/resources/authkeys/list
2. Create an APNs key (type: Apple Push Notifications service)
3. Download the `.p8` file
4. Copy to `/secrets/AuthKey_KEYID.p8`

```bash
cp AuthKey_XXXXXXXXXX.p8 /secrets/
chmod 600 /secrets/AuthKey_XXXXXXXXXX.p8
```

Update `.env`:
```
APNS_KEY_PATH=/secrets/AuthKey_XXXXXXXXXX.p8
APNS_KEY_ID=XXXXXXXXXX
APNS_TEAM_ID=YOUR_APPLE_TEAM_ID
APNS_USE_SANDBOX=false
```

---

## Step 6 — Configure Nginx

Edit `nginx/nginx.conf` — replace all occurrences of `yourdomain.com`:

```bash
sed -i 's/yourdomain.com/YOURACTUALDOMAIN.com/g' nginx/nginx.conf
```

---

## Step 7 — Deploy

```bash
# Build and start all services
docker compose up -d --build

# Check all containers are healthy
docker compose ps

# Run database migrations
docker compose exec backend alembic upgrade head

# Create admin user
docker compose exec backend python scripts/seed.py
```

Expected output: all containers show `healthy` or `running`.

---

## Step 8 — Verify

```bash
# Health check
curl https://api.yourdomain.com/health
# Expected: {"status":"healthy","version":"1.0.0"}

# Admin dashboard
# Open https://admin.yourdomain.com in browser
# Login with credentials created in seed.py
```

---

## Updating the Deployment

```bash
git pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | JWT signing key (32+ char random hex) |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `REDIS_PASSWORD` | Yes | Redis password |
| `ENROLLMENT_CODE` | Yes | Company secret for device enrollment |
| `DEVICE_DATA_ENCRYPTION_KEY` | Yes | Data encryption key (base64 32 bytes) |
| `ALLOWED_ORIGINS` | Yes | Dashboard domain(s) for CORS |
| `ALLOWED_HOSTS` | Yes | API domain(s) for host validation |
| `VITE_API_URL` | Yes | Full API URL used by dashboard build |
| `FIREBASE_PROJECT_ID` | Yes | FCM Android push |
| `FIREBASE_CREDENTIALS_PATH` | Yes | Path to service account JSON |
| `APNS_KEY_PATH` | iOS only | Path to .p8 APNs key |
| `APNS_KEY_ID` | iOS only | APNs key ID (10 chars) |
| `APNS_TEAM_ID` | iOS only | Apple Developer Team ID |
| `APNS_BUNDLE_ID` | iOS only | App bundle identifier |
| `DEBUG` | No | Set `false` in production (disables /docs) |

---

## Backup

```bash
# Database backup
docker compose exec postgres pg_dump -U mdm_user mdm_db > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T postgres psql -U mdm_user mdm_db < backup_20260418.sql
```

Schedule daily backups with cron:
```bash
echo "0 2 * * * cd /path/to/ironvault && docker compose exec -T postgres pg_dump -U \${POSTGRES_USER} \${POSTGRES_DB} > backups/backup_\$(date +\%Y\%m\%d).sql" | crontab -
```

---

## Monitoring

```bash
# View logs
docker compose logs -f backend
docker compose logs -f nginx

# Resource usage
docker stats

# Check backend health
curl http://localhost:8000/health
```

---

## Security Checklist

- [ ] `DEBUG=false` in `.env`
- [ ] Strong `SECRET_KEY` generated with `openssl rand -hex 32`
- [ ] Strong database and Redis passwords (20+ chars)
- [ ] `ENROLLMENT_CODE` changed from default
- [ ] TLS certificate installed and auto-renewing
- [ ] `ALLOWED_ORIGINS` set to production domain only
- [ ] `ALLOWED_HOSTS` set to production domain only
- [ ] PostgreSQL port (5432) NOT exposed externally
- [ ] Redis port (6379) NOT exposed externally
- [ ] `/secrets/` directory permissions: `chmod 700 /secrets`
- [ ] Firebase credentials permissions: `chmod 600 /secrets/firebase-credentials.json`
- [ ] Admin password changed from seed default
