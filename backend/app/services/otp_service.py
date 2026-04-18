from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.otp import OTPRecord
from app.models.audit_log import AuditAction
from app.utils.security import generate_otp, hash_otp, verify_otp_hash
from app.utils.rate_limiter import (
    check_otp_rate_limit, increment_otp_attempts, reset_otp_attempts
)
from app.services.audit_service import log_audit
from app.config import get_settings

settings = get_settings()


async def generate_uninstall_otp(
    db: AsyncSession,
    device_id: UUID,
    admin_id: UUID,
    command_type: str,
    ip: str,
) -> dict:
    """Generate OTP for destructive device commands. Returns OTP to show admin."""
    otp_plain = generate_otp(6)
    otp_hash = hash_otp(otp_plain)

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRE_SECONDS)

    record = OTPRecord(
        device_id=device_id,
        admin_id=admin_id,
        command_type=command_type,
        otp_hash=otp_hash,
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()

    await log_audit(
        db, AuditAction.OTP_GENERATED,
        admin_user_id=admin_id, device_id=device_id,
        ip_address=ip,
        metadata={"command_type": command_type, "otp_id": str(record.id)},
    )

    return {
        "otp_id": str(record.id),
        "otp": otp_plain,  # shown to admin only, never stored
        "expires_in_seconds": settings.OTP_EXPIRE_SECONDS,
        "message": "Share this OTP with the employee for device uninstall authorization.",
    }


async def verify_device_otp(
    db: AsyncSession,
    otp_id: UUID,
    otp_entered: str,
    device_id: UUID,
    ip: str,
) -> bool:
    """Verify OTP entered on device. Rate-limited per device."""
    is_allowed, remaining = await check_otp_rate_limit(str(device_id))
    if not is_allowed:
        await log_audit(
            db, AuditAction.OTP_FAILED, device_id=device_id, ip_address=ip,
            metadata={"reason": "rate_limited"},
        )
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {remaining} seconds.",
        )

    result = await db.execute(
        select(OTPRecord).where(
            OTPRecord.id == otp_id,
            OTPRecord.device_id == device_id,
            OTPRecord.is_used == False,
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="OTP record not found")

    if datetime.now(timezone.utc) > record.expires_at.replace(tzinfo=timezone.utc):
        await log_audit(db, AuditAction.OTP_EXPIRED, device_id=device_id, ip_address=ip)
        raise HTTPException(status_code=410, detail="OTP has expired")

    record.attempts += 1
    await increment_otp_attempts(str(device_id))

    if not verify_otp_hash(otp_entered, record.otp_hash):
        await log_audit(
            db, AuditAction.OTP_FAILED, device_id=device_id, ip_address=ip,
            metadata={"attempts": record.attempts},
        )
        raise HTTPException(status_code=401, detail="Invalid OTP")

    record.is_used = True
    record.used_at = datetime.now(timezone.utc)
    await reset_otp_attempts(str(device_id))

    await log_audit(db, AuditAction.OTP_VERIFIED, device_id=device_id, ip_address=ip)
    return True
