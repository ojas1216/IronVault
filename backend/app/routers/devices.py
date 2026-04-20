import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db
from app.routers.dependencies import require_role, verify_device_token, get_current_user
from app.models.user import UserRole
from app.schemas.device import (
    DeviceRegisterRequest, DeviceHeartbeatRequest,
    LocationUpdateRequest, AppUsageBatchRequest,
    CommandResultRequest, DeviceResponse,
)
from app.services import device_service
from app.models.device import Device, DeviceStatus, DevicePlatform
from app.utils.security import create_access_token
from app.config import get_settings
from app.models.audit_log import AuditAction
from app.services.audit_service import log_audit
from app.models.command import CommandStatus, DeviceCommand
from app.services.hardware_registry import HardwareRegistryEntry

settings = get_settings()
router = APIRouter(prefix="/devices", tags=["Devices"])

COMPANY_ENROLLMENT_CODE = "COMPANY_SECRET_ENROLL_2024"  # move to env/DB in prod


# ── Device-side enrollment ────────────────────────────────────────────────────

@router.post("/enroll")
async def enroll_device(
    request: Request,
    body: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Called by agent on first install. Validates company enrollment code."""
    expected_code = getattr(settings, "ENROLLMENT_CODE", COMPANY_ENROLLMENT_CODE)
    if body.enrollment_code != expected_code:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid enrollment code")

    device = await device_service.register_device(db, body.model_dump())

    # ── Hardware registration & resale check ──────────────────────────────
    resale_warning = None
    if body.hardware_fingerprint:
        fp = body.hardware_fingerprint
        board_hash = hashlib.sha256(body.baseboard_serial.encode()).hexdigest() if body.baseboard_serial else None
        bios_hash = hashlib.sha256(body.bios_uuid.encode()).hexdigest() if body.bios_uuid else None
        tpm_hash = hashlib.sha256(body.tpm_chip_id.encode()).hexdigest() if body.tpm_chip_id else None

        existing_result = await db.execute(
            select(HardwareRegistryEntry).where(HardwareRegistryEntry.hardware_fingerprint == fp)
        )
        existing = existing_result.scalar_one_or_none()

        if existing and str(existing.original_device_id) != str(device.id):
            # Hardware fingerprint already registered to a different device — resale detected
            existing.last_seen_device_id = device.id
            existing.last_seen_at = datetime.now(timezone.utc)
            existing.is_resold = True
            existing.flagged_at = datetime.now(timezone.utc)
            existing.flag_reason = "HARDWARE_REUSED_DIFFERENT_DEVICE"
            await db.execute(
                update(Device).where(Device.id == device.id).values(
                    is_flagged=True,
                    flag_reason="RESALE_DETECTED_AT_ENROLLMENT",
                    flagged_at=datetime.now(timezone.utc),
                    hardware_fingerprint=fp,
                    baseboard_serial=body.baseboard_serial,
                    bios_uuid=body.bios_uuid,
                    last_tpm_chip_id=body.tpm_chip_id,
                    is_enrolled=True,
                )
            )
            await log_audit(db, AuditAction.TAMPER_DETECTED, device_id=device.id,
                            metadata={"reason": "RESALE_DETECTED",
                                      "original_device_id": str(existing.original_device_id)})
            resale_warning = "RESALE_DETECTED"
        else:
            if not existing:
                # First time this hardware is seen — register it
                db.add(HardwareRegistryEntry(
                    hardware_fingerprint=fp,
                    baseboard_serial_hash=board_hash,
                    bios_uuid_hash=bios_hash,
                    tpm_chip_id_hash=tpm_hash,
                    original_device_id=device.id,
                ))
            # Store golden fingerprint on the device record
            await db.execute(
                update(Device).where(Device.id == device.id).values(
                    hardware_fingerprint=fp,
                    baseboard_serial=body.baseboard_serial,
                    bios_uuid=body.bios_uuid,
                    last_tpm_chip_id=body.tpm_chip_id,
                    last_hardware_check=datetime.now(timezone.utc),
                    is_enrolled=True,
                )
            )
        await db.commit()

    # Issue device-specific JWT — long-lived (365 days) for persistent agents
    from datetime import timedelta
    from app.utils.security import create_device_token
    device_token = create_device_token(
        {"sub": str(device.id), "platform": body.platform},
        expires_delta=timedelta(days=365),
    )
    response = {
        "device_id": str(device.id),
        "device_token": device_token,
        "enrollment_token": device.enrollment_token,
        "message": "Device enrolled successfully. Uninstall protection is now active.",
    }
    if resale_warning:
        response["warning"] = resale_warning
    return response


@router.post("/heartbeat")
async def heartbeat(
    request: Request,
    body: DeviceHeartbeatRequest,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Agent sends heartbeat every 30s."""
    device_id = UUID(device_payload["sub"])
    ip = request.client.host if request.client else None
    await device_service.update_device_heartbeat(
        db, device_id,
        push_token=body.push_token,
        ip_address=ip,
        is_rooted=body.is_rooted,
        network_type=body.network_type,
        os_version=body.os_version,
        agent_version=body.agent_version,
    )

    # ── Hardware resale detection on every heartbeat ──────────────────────
    if body.hardware_fingerprint:
        dev_result = await db.execute(select(Device).where(Device.id == device_id))
        dev = dev_result.scalar_one_or_none()
        if dev:
            if not dev.hardware_fingerprint:
                # No golden fingerprint yet — store it now
                await db.execute(
                    update(Device).where(Device.id == device_id).values(
                        hardware_fingerprint=body.hardware_fingerprint,
                        baseboard_serial=body.baseboard_serial,
                        bios_uuid=body.bios_uuid,
                        last_hardware_check=datetime.now(timezone.utc),
                        is_enrolled=True,
                    )
                )
                await db.commit()
            elif not hmac.compare_digest(
                dev.hardware_fingerprint.lower(),
                body.hardware_fingerprint.lower()
            ):
                # Fingerprint mismatch — classify and flag
                board_changed = (
                    body.baseboard_serial and dev.baseboard_serial
                    and body.baseboard_serial != dev.baseboard_serial
                )
                bios_changed = (
                    body.bios_uuid and dev.bios_uuid
                    and body.bios_uuid != dev.bios_uuid
                )
                reason = "RESOLD" if (board_changed or bios_changed) else "HARDWARE_TAMPERED"
                await db.execute(
                    update(Device).where(Device.id == device_id).values(
                        is_flagged=True,
                        flag_reason=reason,
                        flagged_at=datetime.now(timezone.utc),
                        security_flags=(dev.security_flags or "") + f",{reason}",
                    )
                )
                await log_audit(db, AuditAction.TAMPER_DETECTED, device_id=device_id,
                                metadata={"reason": reason, "type": "HARDWARE_MISMATCH",
                                          "golden": dev.hardware_fingerprint[:12],
                                          "reported": body.hardware_fingerprint[:12]})
                await db.commit()
                return {"status": "ok", "security_alert": reason}
            else:
                # Match — update last check time and firmware fingerprint if provided
                update_vals: dict = {"last_hardware_check": datetime.now(timezone.utc)}
                if body.firmware_fingerprint:
                    if dev.last_firmware_fingerprint and dev.last_firmware_fingerprint != body.firmware_fingerprint:
                        # Firmware changed — log as tamper event (could be legitimate update)
                        await log_audit(db, AuditAction.TAMPER_DETECTED, device_id=device_id,
                                        metadata={"reason": "FIRMWARE_CHANGED",
                                                  "previous": dev.last_firmware_fingerprint[:12],
                                                  "current": body.firmware_fingerprint[:12]})
                    update_vals["last_firmware_fingerprint"] = body.firmware_fingerprint
                await db.execute(update(Device).where(Device.id == device_id).values(**update_vals))
                await db.commit()

    return {"status": "ok"}


@router.post("/location")
async def update_location(
    body: LocationUpdateRequest,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    device_id = UUID(device_payload["sub"])
    await device_service.record_location(db, device_id, body.model_dump())
    return {"status": "ok"}


@router.post("/app-usage")
async def report_app_usage(
    body: AppUsageBatchRequest,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    device_id = UUID(device_payload["sub"])
    await device_service.record_app_usage(db, device_id, [e.model_dump() for e in body.logs])
    return {"status": "ok"}


@router.post("/command-result")
async def command_result(
    request: Request,
    body: CommandResultRequest,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    device_id = UUID(device_payload["sub"])
    from datetime import datetime, timezone

    values = {
        "status": CommandStatus(body.status),
        "result": body.result or {},
        "completed_at": datetime.now(timezone.utc),
    }
    if body.error_message:
        values["error_message"] = body.error_message

    await db.execute(
        update(DeviceCommand)
        .where(DeviceCommand.id == body.command_id, DeviceCommand.device_id == device_id)
        .values(**values)
    )

    action = AuditAction.COMMAND_COMPLETED if body.status == "completed" else AuditAction.COMMAND_FAILED
    await log_audit(db, action, device_id=device_id,
                    metadata={"command_id": str(body.command_id)})
    return {"status": "ok"}


@router.post("/tamper-event")
async def tamper_event(
    request: Request,
    body: dict,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Section 6 — Device reports tamper attempt (force-stop, admin revoke, etc.)."""
    device_id = UUID(device_payload["sub"])
    await log_audit(
        db, AuditAction.TAMPER_DETECTED,
        device_id=device_id,
        ip_address=request.client.host if request.client else None,
        description=body.get("details"),
        metadata={"tamper_type": body.get("tamper_type")},
    )
    return {"status": "ok"}


@router.get("/{device_id}/pending-commands")
async def get_pending_commands(
    device_id: UUID,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Device polls for undelivered commands (fallback when FCM is unavailable)."""
    from app.models.command import DeviceCommand, CommandStatus
    from sqlalchemy import select
    if UUID(device_payload["sub"]) != device_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(
        select(DeviceCommand)
        .where(
            DeviceCommand.device_id == device_id,
            DeviceCommand.status == CommandStatus.PENDING,
        )
        .limit(10)
    )
    commands = result.scalars().all()
    return {
        "commands": [
            {"id": str(c.id), "command_type": c.command_type, "payload": c.payload}
            for c in commands
        ]
    }


# ── Admin-side device management ──────────────────────────────────────────────

class AdminPreRegisterRequest(BaseModel):
    device_name: str
    employee_name: str
    employee_email: str
    department: Optional[str] = None
    platform: str = "android"


@router.post("/admin-register", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def admin_register_device(
    request: Request,
    body: AdminPreRegisterRequest,
    current_user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Admin pre-registers a device slot. Returns enrollment code to share with the agent."""
    from app.utils.security import generate_secure_token
    import uuid as _uuid

    enrollment_token = generate_secure_token(32)
    device_data = {
        "device_name": body.device_name,
        "employee_name": body.employee_name,
        "employee_email": body.employee_email,
        "department": body.department,
        "platform": body.platform,
        "enrollment_code": settings.ENROLLMENT_CODE,
        "device_model": "Pre-registered",
        "os_version": None,
        "serial_number": None,
        "android_id": str(_uuid.uuid4()),
    }
    device = await device_service.register_device(db, device_data)

    expected_code = getattr(settings, "ENROLLMENT_CODE", COMPANY_ENROLLMENT_CODE)
    return {
        "device_id": str(device.id),
        "enrollment_code": expected_code,
        "enrollment_token": device.enrollment_token,
        "message": f"Share this enrollment code with the device agent: {expected_code}",
    }


@router.get("/", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def list_devices(
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    devices = await device_service.list_devices(
        db,
        status=DeviceStatus(status) if status else None,
        platform=DevicePlatform(platform) if platform else None,
        department=department,
        limit=limit,
        offset=offset,
    )
    return [DeviceResponse.model_validate(d) for d in devices]


@router.get("/{device_id}", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def get_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    device = await device_service.get_device(db, device_id)
    return DeviceResponse.model_validate(device)


@router.delete("/{device_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_device(
    request: Request,
    device_id: UUID,
    current_user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Permanently remove a device and all its associated data."""
    from app.models.device import Device
    from fastapi import HTTPException
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    from sqlalchemy import text
    device_name = device.device_name
    pid = device_id
    # Delete related records first (no CASCADE on FKs), then the device and its audit trail
    for stmt in [
        text("DELETE FROM device_commands WHERE device_id = :id"),
        text("DELETE FROM location_history WHERE device_id = :id"),
        text("DELETE FROM app_usage_logs WHERE device_id = :id"),
        text("DELETE FROM sim_events WHERE device_id = :id"),
        text("DELETE FROM uwb_ranging_points WHERE device_id = :id"),
        text("DELETE FROM device_identities WHERE device_id = :id"),
        text("DELETE FROM otp_records WHERE device_id = :id"),
        text("DELETE FROM audit_logs WHERE device_id = :id"),
        text("DELETE FROM devices WHERE id = :id"),
    ]:
        await db.execute(stmt, {"id": pid})
    await db.commit()
    return {"status": "deleted", "device_id": str(device_id)}


@router.get("/{device_id}/location-history", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def location_history(
    device_id: UUID,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    from app.models.location import LocationHistory
    from sqlalchemy import desc
    result = await db.execute(
        select(LocationHistory)
        .where(LocationHistory.device_id == device_id)
        .order_by(desc(LocationHistory.recorded_at))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [{"lat": r.latitude, "lng": r.longitude, "time": r.recorded_at,
             "accuracy": r.accuracy, "address": r.address} for r in rows]


@router.get("/{device_id}/app-usage", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def app_usage(device_id: UUID, limit: int = 200, db: AsyncSession = Depends(get_db)):
    from app.models.app_usage import AppUsageLog
    from sqlalchemy import desc
    result = await db.execute(
        select(AppUsageLog)
        .where(AppUsageLog.device_id == device_id)
        .order_by(desc(AppUsageLog.date))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [{"app": r.app_name or r.app_package,
             "duration_minutes": round(r.usage_duration_seconds / 60, 1),
             "is_work_app": r.is_work_app, "date": r.date} for r in rows]


# ── Hardware Registry (admin) ─────────────────────────────────────────────────

class MarkStolenRequest(BaseModel):
    hardware_fingerprint: str
    notes: Optional[str] = None


@router.get("/hardware-registry/flagged", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def list_flagged_devices(db: AsyncSession = Depends(get_db)):
    """List all devices flagged for hardware mismatch or resale."""
    result = await db.execute(
        select(Device).where(Device.is_flagged == True)
    )
    devices = result.scalars().all()
    return [
        {
            "device_id": str(d.id),
            "device_name": d.device_name,
            "employee_name": d.employee_name,
            "flag_reason": d.flag_reason,
            "flagged_at": d.flagged_at.isoformat() if d.flagged_at else None,
            "security_flags": d.security_flags,
            "hardware_fingerprint": d.hardware_fingerprint,
            "platform": d.platform,
        }
        for d in devices
    ]


@router.get("/hardware-registry/stats", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def hardware_registry_stats(db: AsyncSession = Depends(get_db)):
    """Return counts of registered, stolen, and resold hardware."""
    from sqlalchemy import func
    total_result = await db.execute(select(func.count(HardwareRegistryEntry.id)))
    total = total_result.scalar() or 0

    flagged_result = await db.execute(
        select(func.count(HardwareRegistryEntry.id)).where(
            (HardwareRegistryEntry.is_stolen == True) | (HardwareRegistryEntry.is_resold == True)
        )
    )
    flagged = flagged_result.scalar() or 0

    return {"total_registered": total, "stolen_or_resold": flagged}


@router.post("/hardware-registry/mark-stolen", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def mark_hardware_stolen(
    body: MarkStolenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a hardware fingerprint as stolen. Any future re-enrollment will be blocked."""
    result = await db.execute(
        select(HardwareRegistryEntry)
        .where(HardwareRegistryEntry.hardware_fingerprint == body.hardware_fingerprint)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Hardware fingerprint not in registry")

    entry.is_stolen = True
    entry.flagged_at = datetime.now(timezone.utc)
    entry.flag_reason = "REPORTED_STOLEN"
    entry.flag_notes = body.notes
    await db.commit()
    return {"status": "marked_stolen", "hardware_fingerprint": body.hardware_fingerprint}


@router.get("/hardware-registry/lookup", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def lookup_hardware(fingerprint: str, db: AsyncSession = Depends(get_db)):
    """Look up a hardware fingerprint in the global registry."""
    result = await db.execute(
        select(HardwareRegistryEntry)
        .where(HardwareRegistryEntry.hardware_fingerprint == fingerprint)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return {"found": False}
    return {
        "found": True,
        "original_device_id": str(entry.original_device_id),
        "enrolled_at": entry.enrolled_at.isoformat(),
        "is_stolen": entry.is_stolen,
        "is_resold": entry.is_resold,
        "flag_reason": entry.flag_reason,
        "last_seen_at": entry.last_seen_at.isoformat() if entry.last_seen_at else None,
    }
