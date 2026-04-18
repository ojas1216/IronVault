from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from fastapi import HTTPException

from app.models.device import Device, DeviceStatus, DevicePlatform
from app.models.command import DeviceCommand, CommandType, CommandStatus
from app.models.location import LocationHistory
from app.models.app_usage import AppUsageLog
from app.models.audit_log import AuditAction
from app.services.audit_service import log_audit
from app.services.push_service import send_command_to_device
from app.utils.security import generate_secure_token


async def register_device(db: AsyncSession, data: dict) -> Device:
    """Enroll a new device into MDM."""
    existing = await db.execute(
        select(Device).where(Device.serial_number == data.get("serial_number"))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Device already enrolled")

    enrollment_token = generate_secure_token(16)
    device = Device(
        device_name=data["device_name"],
        employee_name=data["employee_name"],
        employee_email=data["employee_email"],
        employee_id=data.get("employee_id"),
        department=data.get("department"),
        platform=DevicePlatform(data["platform"]),
        device_model=data.get("device_model"),
        os_version=data.get("os_version"),
        serial_number=data.get("serial_number"),
        push_token=data.get("push_token"),
        enrollment_token=enrollment_token,
        agent_version=data.get("agent_version"),
        enrolled_at=datetime.now(timezone.utc),
        is_uninstall_blocked=True,
    )
    db.add(device)
    await db.flush()

    await log_audit(
        db, AuditAction.DEVICE_ENROLLED, device_id=device.id,
        metadata={"platform": data["platform"], "employee": data["employee_email"]},
    )
    return device


async def update_device_heartbeat(
    db: AsyncSession,
    device_id: UUID,
    push_token: Optional[str] = None,
    ip_address: Optional[str] = None,
    is_rooted: bool = False,
    network_type: Optional[str] = None,
    os_version: Optional[str] = None,
    agent_version: Optional[str] = None,
):
    now = datetime.now(timezone.utc)
    values = {"last_seen": now, "is_online": True}

    if push_token:
        values["push_token"] = push_token
    if ip_address:
        values["ip_address"] = ip_address
    if network_type:
        values["network_type"] = network_type
    if os_version:
        values["os_version"] = os_version
    if agent_version:
        values["agent_version"] = agent_version
    if is_rooted:
        values["is_rooted"] = True

    await db.execute(update(Device).where(Device.id == device_id).values(**values))

    if is_rooted:
        device = await get_device(db, device_id)
        await log_audit(
            db, AuditAction.ROOT_DETECTED,
            device_id=device_id,
            metadata={"ip": ip_address},
        )


async def get_device(db: AsyncSession, device_id: UUID) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


async def list_devices(
    db: AsyncSession,
    status: Optional[DeviceStatus] = None,
    platform: Optional[DevicePlatform] = None,
    department: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Device]:
    query = select(Device).order_by(desc(Device.last_seen))
    if status:
        query = query.where(Device.status == status)
    if platform:
        query = query.where(Device.platform == platform)
    if department:
        query = query.where(Device.department == department)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


async def issue_command(
    db: AsyncSession,
    device_id: UUID,
    admin_id: UUID,
    command_type: CommandType,
    payload: Optional[dict] = None,
    requires_otp: bool = False,
    otp_id: Optional[str] = None,
    ip: str = "",
) -> DeviceCommand:
    device = await get_device(db, device_id)

    command = DeviceCommand(
        device_id=device_id,
        issued_by=admin_id,
        command_type=command_type,
        payload=payload or {},
        requires_otp=otp_id if requires_otp else None,
        otp_verified="yes" if otp_id else "na",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(command)
    await db.flush()

    await log_audit(
        db, AuditAction.COMMAND_ISSUED,
        admin_user_id=admin_id, device_id=device_id, ip_address=ip,
        metadata={"command_type": command_type, "command_id": str(command.id)},
    )

    if device.push_token:
        result = await send_command_to_device(
            platform=device.platform.value,
            push_token=device.push_token,
            command_type=command_type.value,
            command_id=str(command.id),
            payload=payload,
        )
        if result.get("success"):
            command.status = CommandStatus.SENT
            command.sent_at = datetime.now(timezone.utc)
    else:
        command.status = CommandStatus.PENDING

    return command


async def record_location(db: AsyncSession, device_id: UUID, data: dict):
    now = datetime.now(timezone.utc)
    loc = LocationHistory(
        device_id=device_id,
        latitude=data["latitude"],
        longitude=data["longitude"],
        accuracy=data.get("accuracy"),
        altitude=data.get("altitude"),
        speed=data.get("speed"),
        address=data.get("address"),
        recorded_at=data.get("recorded_at", now),
    )
    db.add(loc)

    await db.execute(
        update(Device).where(Device.id == device_id).values(
            last_latitude=data["latitude"],
            last_longitude=data["longitude"],
            last_location_time=now,
            location_accuracy=data.get("accuracy"),
        )
    )


async def record_app_usage(db: AsyncSession, device_id: UUID, logs: list[dict]):
    for entry in logs:
        log = AppUsageLog(
            device_id=device_id,
            app_package=entry["app_package"],
            app_name=entry.get("app_name"),
            usage_duration_seconds=entry["usage_duration_seconds"],
            is_work_app=entry.get("is_work_app", False),
            date=entry.get("date", datetime.now(timezone.utc)),
        )
        db.add(log)
