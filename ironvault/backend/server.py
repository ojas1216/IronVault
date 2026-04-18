"""
IronVault Backend Server
FastAPI + PostgreSQL + Redis
"""
import asyncio
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import firebase_admin
from fastapi import Depends, FastAPI, File, HTTPException, Header, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from firebase_admin import credentials, messaging
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    async_session,
    create_tables,
    Command,
    Device,
    LocationRecord,
    SIMEvent,
    TamperLog,
    TelemetryRecord,
)

# ─── Config ───────────────────────────────────────────────────────────────────

JWT_SECRET = os.environ["JWT_SECRET"]
DEVICE_HMAC_SECRET = os.environ["DEVICE_HMAC_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ironvault.local")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

# ─── Firebase Init ────────────────────────────────────────────────────────────

cred_path = os.environ.get("FIREBASE_CREDENTIALS", "firebase_credentials.json")
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="IronVault API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await create_tables()

# ─── Auth Helpers ─────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_admin_token(authorization: str = Header(...)) -> dict:
    try:
        token = authorization.removeprefix("Bearer ").strip()
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_device_hmac(device_id: str, device_secret: str, signature: str, body: str) -> bool:
    """Verify HMAC-SHA256 signature from device."""
    expected = hmac.new(
        device_secret.encode(),
        f"{device_id}:{body}".encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

# ─── Pydantic Models ──────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class DeviceRegistrationRequest(BaseModel):
    device_name: str
    owner_name: str
    owner_email: Optional[str] = None
    department: Optional[str] = None
    imei: Optional[str] = None
    imei2: Optional[str] = None
    serial: Optional[str] = None
    android_id: Optional[str] = None
    hardware_fingerprint: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    os_version: Optional[str] = None
    sdk_version: Optional[int] = None
    push_token: Optional[str] = None

class HeartbeatRequest(BaseModel):
    device_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    battery_level: Optional[int] = None
    is_rooted: Optional[bool] = None
    locations: Optional[List[Dict]] = None  # Batch of offline-cached locations

class AlertRequest(BaseModel):
    device_id: str
    event_type: str
    payload: Dict[str, Any] = {}
    timestamp: Optional[int] = None

class CommandRequest(BaseModel):
    device_id: str
    command_type: str
    payload: Dict[str, Any] = {}

class CommandResultRequest(BaseModel):
    command_id: str
    status: str
    result: Dict[str, Any] = {}

class TelemetryRequest(BaseModel):
    device_id: str
    hardware_fingerprint: str
    imei: Optional[str] = None
    imei2: Optional[str] = None
    serial: Optional[str] = None
    sims: List[Dict] = []
    location: Optional[Dict] = None
    checkin_timestamp: Optional[int] = None

# ─── Admin Auth ───────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
async def admin_login(req: AdminLoginRequest):
    if req.email != ADMIN_EMAIL:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not ADMIN_PASSWORD_HASH or not bcrypt.checkpw(req.password.encode(), ADMIN_PASSWORD_HASH.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": req.email, "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}

# ─── Device Registration ──────────────────────────────────────────────────────

@app.post("/api/register")
async def register_device(
    req: DeviceRegistrationRequest,
    db: AsyncSession = Depends(get_db),
):
    device_id = str(uuid.uuid4())
    device_secret = uuid.uuid4().hex + uuid.uuid4().hex  # 64-char random secret

    device = Device(
        id=device_id,
        device_name=req.device_name,
        owner_name=req.owner_name,
        owner_email=req.owner_email,
        department=req.department,
        imei=req.imei,
        imei2=req.imei2,
        serial=req.serial,
        android_id=req.android_id,
        hardware_fingerprint=req.hardware_fingerprint,
        manufacturer=req.manufacturer,
        model=req.model,
        os_version=req.os_version,
        sdk_version=req.sdk_version,
        push_token=req.push_token,
        device_secret=device_secret,
        status="active",
        enrolled_at=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc),
    )
    db.add(device)
    await db.commit()

    # If golden fingerprint exists in DB for this IMEI, verify it matches
    tamper = False
    if req.imei and req.hardware_fingerprint:
        existing = await db.execute(
            select(Device).where(Device.imei == req.imei, Device.id != device_id)
        )
        prev = existing.scalars().first()
        if prev and prev.hardware_fingerprint and prev.hardware_fingerprint != req.hardware_fingerprint:
            tamper = True
            await _log_tamper(db, device_id, "hardware_fingerprint_mismatch_on_register",
                              {"prev_fp": prev.hardware_fingerprint, "new_fp": req.hardware_fingerprint})

    return {
        "device_id": device_id,
        "device_secret": device_secret,
        "status": "enrolled",
        "should_brick": tamper,
    }

# ─── Heartbeat / Location ─────────────────────────────────────────────────────

@app.post("/api/heartbeat")
async def heartbeat(req: HeartbeatRequest, db: AsyncSession = Depends(get_db)):
    device = await _get_device(db, req.device_id)
    update_data: Dict[str, Any] = {"last_seen": datetime.now(timezone.utc), "is_online": True}
    if req.battery_level is not None:
        update_data["battery_level"] = req.battery_level
    if req.is_rooted is not None:
        update_data["is_rooted"] = req.is_rooted
    if req.latitude is not None:
        update_data["last_latitude"] = req.latitude
        update_data["last_longitude"] = req.longitude

    await db.execute(update(Device).where(Device.id == req.device_id).values(**update_data))

    # Save location records
    locations = req.locations or []
    if req.latitude:
        locations.append({"lat": req.latitude, "lng": req.longitude,
                          "accuracy": req.accuracy, "timestamp": datetime.now(timezone.utc).isoformat()})
    for loc in locations:
        db.add(LocationRecord(
            id=str(uuid.uuid4()),
            device_id=req.device_id,
            latitude=loc.get("lat") or loc.get("latitude", 0),
            longitude=loc.get("lng") or loc.get("longitude", 0),
            accuracy=loc.get("accuracy"),
            recorded_at=datetime.fromisoformat(loc["timestamp"]) if "timestamp" in loc else datetime.now(timezone.utc),
        ))

    await db.commit()

    # Return any pending commands
    cmds = await db.execute(
        select(Command).where(Command.device_id == req.device_id, Command.status == "pending")
    )
    pending = [{"command_id": c.id, "type": c.command_type, "payload": c.payload or {}}
               for c in cmds.scalars().all()]

    return {"status": "ok", "pending_commands": pending}

# ─── Alert ───────────────────────────────────────────────────────────────────

@app.post("/api/alert")
async def receive_alert(req: AlertRequest, db: AsyncSession = Depends(get_db)):
    await _get_device(db, req.device_id)
    await _log_tamper(db, req.device_id, req.event_type, req.payload)
    await db.commit()

    # If SIM anomaly — create SIM event
    if req.event_type == "sim_anomaly":
        ev = SIMEvent(
            id=str(uuid.uuid4()),
            device_id=req.device_id,
            event_type=req.payload.get("event_type", "unknown"),
            payload=req.payload,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ev)
        await db.commit()

    return {"status": "received"}

# ─── Commands ─────────────────────────────────────────────────────────────────

@app.get("/api/command/{device_id}")
async def get_commands(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Device polls this endpoint for pending commands (FCM fallback)."""
    cmds = await db.execute(
        select(Command).where(Command.device_id == device_id, Command.status == "pending")
    )
    commands = cmds.scalars().all()
    result = [{"command_id": c.id, "type": c.command_type, "payload": c.payload or {},
               "pre_verified": c.pre_verified} for c in commands]
    return {"commands": result}

@app.post("/api/command/{device_id}/result")
async def command_result(
    device_id: str,
    req: CommandResultRequest,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Command).where(Command.id == req.command_id).values(
            status=req.status,
            result=req.result,
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return {"status": "ok"}

# ─── Admin: Send Command ──────────────────────────────────────────────────────

@app.post("/api/admin/command")
async def admin_send_command(
    req: CommandRequest,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(verify_admin_token),
):
    device = await _get_device(db, req.device_id)
    command_id = str(uuid.uuid4())
    pre_verified = req.command_type in ("WIPE", "BRICK")  # Admin-initiated = pre-authorized

    cmd = Command(
        id=command_id,
        device_id=req.device_id,
        command_type=req.command_type,
        payload=req.payload,
        pre_verified=pre_verified,
        status="pending",
        issued_at=datetime.now(timezone.utc),
    )
    db.add(cmd)
    await db.commit()

    # Push via FCM
    if device.push_token:
        await _send_fcm(device.push_token, {
            "command": req.command_type,
            "command_id": command_id,
            "payload": json.dumps(req.payload),
            "pre_verified": str(pre_verified).lower(),
        })

    return {"command_id": command_id, "status": "sent"}

@app.post("/api/admin/wipe")
async def admin_wipe_device(
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(verify_admin_token),
):
    device = await _get_device(db, device_id)
    command_id = str(uuid.uuid4())
    cmd = Command(
        id=command_id, device_id=device_id, command_type="WIPE",
        payload={}, pre_verified=True, status="pending",
        issued_at=datetime.now(timezone.utc),
    )
    db.add(cmd)
    await db.execute(update(Device).where(Device.id == device_id).values(status="wiping"))
    await db.commit()

    if device.push_token:
        await _send_fcm(device.push_token, {
            "command": "WIPE", "command_id": command_id,
            "pre_verified": "true",
        })

    return {"status": "wipe_command_sent"}

@app.post("/api/admin/brick")
async def admin_brick_device(
    device_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(verify_admin_token),
):
    device = await _get_device(db, device_id)
    command_id = str(uuid.uuid4())
    cmd = Command(
        id=command_id, device_id=device_id, command_type="BRICK",
        payload={"reason": "admin_marked_stolen"}, pre_verified=True, status="pending",
        issued_at=datetime.now(timezone.utc),
    )
    db.add(cmd)
    await db.execute(update(Device).where(Device.id == device_id).values(status="stolen"))
    await db.commit()

    if device.push_token:
        await _send_fcm(device.push_token, {
            "command": "BRICK", "command_id": command_id,
            "payload": '{"reason":"admin_marked_stolen"}',
            "pre_verified": "true",
        })

    return {"status": "brick_command_sent"}

# ─── Telemetry ────────────────────────────────────────────────────────────────

@app.post("/api/telemetry")
async def receive_telemetry(req: TelemetryRequest, db: AsyncSession = Depends(get_db)):
    device = await _get_device(db, req.device_id)

    # Detect hardware fingerprint change
    should_brick = False
    if device.hardware_fingerprint and req.hardware_fingerprint:
        if device.hardware_fingerprint != req.hardware_fingerprint:
            await _log_tamper(db, req.device_id, "hardware_fingerprint_changed", {
                "old_fp": device.hardware_fingerprint,
                "new_fp": req.hardware_fingerprint,
            })
            should_brick = True

    # Log telemetry
    record = TelemetryRecord(
        id=str(uuid.uuid4()),
        device_id=req.device_id,
        hardware_fingerprint=req.hardware_fingerprint,
        imei=req.imei,
        sim_count=len(req.sims),
        location=req.location,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.execute(
        update(Device).where(Device.id == req.device_id).values(
            last_seen=datetime.now(timezone.utc),
            hardware_fingerprint=req.hardware_fingerprint,
        )
    )
    await db.commit()

    return {"status": "ok", "should_brick": should_brick}

# ─── Admin: Device List ───────────────────────────────────────────────────────

@app.get("/api/admin/devices")
async def list_devices(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(verify_admin_token),
):
    query = select(Device)
    if status:
        query = query.where(Device.status == status)
    result = await db.execute(query.order_by(Device.enrolled_at.desc()))
    devices = result.scalars().all()
    return {"devices": [_device_to_dict(d) for d in devices]}

@app.get("/api/admin/devices/{device_id}")
async def get_device_detail(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(verify_admin_token),
):
    device = await _get_device(db, device_id)
    loc_result = await db.execute(
        select(LocationRecord)
        .where(LocationRecord.device_id == device_id)
        .order_by(LocationRecord.recorded_at.desc())
        .limit(100)
    )
    locations = [{"lat": l.latitude, "lng": l.longitude, "accuracy": l.accuracy,
                  "ts": l.recorded_at.isoformat()} for l in loc_result.scalars()]

    sim_result = await db.execute(
        select(SIMEvent).where(SIMEvent.device_id == device_id)
        .order_by(SIMEvent.created_at.desc()).limit(20)
    )
    sim_events = [{"id": s.id, "type": s.event_type, "payload": s.payload,
                   "ts": s.created_at.isoformat()} for s in sim_result.scalars()]

    return {
        "device": _device_to_dict(device),
        "locations": locations,
        "sim_events": sim_events,
    }

@app.get("/api/admin/alerts")
async def list_alerts(
    unresolved_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(verify_admin_token),
):
    query = select(TamperLog).order_by(TamperLog.created_at.desc()).limit(200)
    if unresolved_only:
        query = query.where(TamperLog.resolved == False)
    result = await db.execute(query)
    logs = result.scalars().all()
    return {"alerts": [
        {"id": l.id, "device_id": l.device_id, "event": l.event_type,
         "payload": l.payload, "ts": l.created_at.isoformat(), "resolved": l.resolved}
        for l in logs
    ]}

# ─── Admin Panel HTML ─────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    with open("admin_panel.html") as f:
        return f.read()

# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_device(db: AsyncSession, device_id: str) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

async def _log_tamper(db: AsyncSession, device_id: str, event_type: str, payload: dict):
    log = TamperLog(
        id=str(uuid.uuid4()),
        device_id=device_id,
        event_type=event_type,
        payload=payload,
        resolved=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)

async def _send_fcm(token: str, data: Dict[str, str]):
    try:
        message = messaging.Message(
            data=data,
            token=token,
            android=messaging.AndroidConfig(priority="high"),
        )
        messaging.send(message)
    except Exception as e:
        print(f"FCM send failed: {e}")

def _device_to_dict(d: Device) -> dict:
    return {
        "id": d.id,
        "device_name": d.device_name,
        "owner_name": d.owner_name,
        "owner_email": d.owner_email,
        "department": d.department,
        "status": d.status,
        "manufacturer": d.manufacturer,
        "model": d.model,
        "imei": d.imei,
        "hardware_fingerprint": d.hardware_fingerprint,
        "is_online": d.is_online,
        "is_rooted": d.is_rooted,
        "battery_level": d.battery_level,
        "last_latitude": d.last_latitude,
        "last_longitude": d.last_longitude,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        "enrolled_at": d.enrolled_at.isoformat() if d.enrolled_at else None,
    }
