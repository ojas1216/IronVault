from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update

from app.database import get_db
from app.routers.dependencies import verify_device_token, require_role, get_current_user
from app.models.user import UserRole, User
from app.models.sim_event import SimEvent, SimEventType
from app.models.device_identity import DeviceIdentity
from app.models.audit_log import AuditAction
from app.services.audit_service import log_audit
import os, uuid as uuidlib

router = APIRouter(prefix="/sim-events", tags=["SIM Events"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/mdm_photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class SimEventReport(BaseModel):
    event_type: str
    slot_index: int = 0
    sim_metadata: dict
    timestamp: Optional[str] = None


class DeviceIdentityReport(BaseModel):
    imei_slot1: Optional[str] = None
    imei_slot2: Optional[str] = None
    serial_number: Optional[str] = None
    android_id: Optional[str] = None
    hardware_fingerprint: Optional[str] = None
    board: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    hardware: Optional[str] = None
    sdk_int: Optional[int] = None
    raw_payload: Optional[dict] = None


# ── Device-side endpoints ──────────────────────────────────────────────────

@router.post("/report")
async def report_sim_event(
    request: Request,
    body: SimEventReport,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Called by device when SIM is inserted/removed/swapped."""
    device_id = UUID(device_payload["sub"])
    now = datetime.now(timezone.utc)
    meta = body.sim_metadata

    # Extract slot info from metadata
    slots = meta.get("slots", [{}])
    slot_data = next((s for s in slots if s.get("slot_index") == body.slot_index), slots[0] if slots else {})

    event = SimEvent(
        device_id=device_id,
        event_type=SimEventType(body.event_type),
        slot_index=body.slot_index,
        iccid=slot_data.get("iccid"),
        carrier_name=str(slot_data.get("carrier_name", "")) or None,
        mcc=slot_data.get("mcc"),
        mnc=slot_data.get("mnc"),
        country_iso=slot_data.get("country_iso"),
        phone_number=slot_data.get("phone_number"),
        is_roaming=slot_data.get("is_roaming", False),
        raw_metadata=meta,
        recorded_at=now,
    )
    db.add(event)
    await db.flush()

    await log_audit(
        db, AuditAction.TAMPER_DETECTED,
        device_id=device_id,
        ip_address=request.client.host if request.client else None,
        description=f"SIM {body.event_type} on slot {body.slot_index}",
        metadata={"iccid": slot_data.get("iccid"), "carrier": str(slot_data.get("carrier_name", ""))},
    )

    return {"event_id": str(event.id), "status": "recorded"}


@router.post("/upload-photo/{command_id}")
async def upload_security_photo(
    command_id: str,
    device_payload: dict = Depends(verify_device_token),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Receive security photo captured on SIM swap or remote command."""
    if photo.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Invalid image type")

    filename = f"{uuidlib.uuid4()}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await photo.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=413, detail="Photo too large")

    with open(filepath, "wb") as f:
        f.write(content)

    # Link photo to most recent SIM event for this device
    device_id = UUID(device_payload["sub"])
    result = await db.execute(
        select(SimEvent)
        .where(SimEvent.device_id == device_id, SimEvent.security_photo_url.is_(None))
        .order_by(desc(SimEvent.created_at))
        .limit(1)
    )
    event = result.scalar_one_or_none()
    if event:
        event.security_photo_url = f"/photos/{filename}"

    return {"photo_url": f"/photos/{filename}"}


@router.post("/device-identity")
async def report_device_identity(
    body: DeviceIdentityReport,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Store/update device identity payload from agent."""
    device_id = UUID(device_payload["sub"])

    result = await db.execute(
        select(DeviceIdentity).where(DeviceIdentity.device_id == device_id)
    )
    identity = result.scalar_one_or_none()

    if identity:
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(identity, field, value)
        identity.raw_payload = body.raw_payload or {}
    else:
        identity = DeviceIdentity(
            device_id=device_id,
            **body.model_dump(exclude_none=True),
            raw_payload=body.raw_payload or {},
        )
        db.add(identity)

    return {"status": "identity_recorded"}


# ── Admin-side endpoints ───────────────────────────────────────────────────

@router.get("/", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def list_sim_events(
    device_id: Optional[UUID] = None,
    unresolved_only: bool = False,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    query = select(SimEvent).order_by(desc(SimEvent.created_at))
    if device_id:
        query = query.where(SimEvent.device_id == device_id)
    if unresolved_only:
        query = query.where(SimEvent.is_resolved == False)
    query = query.limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "device_id": str(e.device_id),
            "event_type": e.event_type,
            "slot_index": e.slot_index,
            "iccid": e.iccid,
            "carrier_name": e.carrier_name,
            "country_iso": e.country_iso,
            "phone_number": e.phone_number,
            "is_roaming": e.is_roaming,
            "security_photo_url": e.security_photo_url,
            "is_resolved": e.is_resolved,
            "recorded_at": e.recorded_at,
            "created_at": e.created_at,
        }
        for e in events
    ]


@router.patch("/{event_id}/resolve", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def resolve_sim_event(
    event_id: UUID,
    notes: str = "",
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(SimEvent).where(SimEvent.id == event_id).values(
            is_resolved=True,
            resolved_by=current_user.id,
            resolved_at=datetime.now(timezone.utc),
            notes=notes,
        )
    )
    return {"status": "resolved"}


@router.get("/device-identity/{device_id}", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def get_device_identity(device_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceIdentity).where(DeviceIdentity.device_id == device_id)
    )
    identity = result.scalar_one_or_none()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    return {
        "device_id": str(identity.device_id),
        "imei_slot1": identity.imei_slot1,
        "imei_slot2": identity.imei_slot2,
        "serial_number": identity.serial_number,
        "android_id": identity.android_id,
        "hardware_fingerprint": identity.hardware_fingerprint,
        "manufacturer": identity.manufacturer,
        "model": identity.model,
        "brand": identity.brand,
        "sdk_int": identity.sdk_int,
        "updated_at": identity.updated_at,
    }
