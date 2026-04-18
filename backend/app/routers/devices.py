from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.dependencies import require_role, verify_device_token, get_current_user
from app.models.user import UserRole
from app.schemas.device import (
    DeviceRegisterRequest, DeviceHeartbeatRequest,
    LocationUpdateRequest, AppUsageBatchRequest,
    CommandResultRequest, DeviceResponse,
)
from app.services import device_service
from app.models.device import DeviceStatus, DevicePlatform
from app.utils.security import create_access_token
from app.config import get_settings
from app.models.audit_log import AuditAction
from app.services.audit_service import log_audit
from app.models.command import CommandStatus
from sqlalchemy import select, update
from app.models.command import DeviceCommand

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
    if body.enrollment_code != settings.get("ENROLLMENT_CODE", COMPANY_ENROLLMENT_CODE):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid enrollment code")

    device = await device_service.register_device(db, body.model_dump())

    # Issue device-specific JWT
    device_token = create_access_token(
        {"sub": str(device.id), "type": "device", "platform": body.platform},
    )
    return {
        "device_id": str(device.id),
        "device_token": device_token,
        "enrollment_token": device.enrollment_token,
        "message": "Device enrolled successfully. Uninstall protection is now active.",
    }


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
