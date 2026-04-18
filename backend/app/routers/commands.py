from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.dependencies import require_role, get_current_user
from app.models.user import UserRole, User
from app.models.command import CommandType
from app.services import device_service, otp_service
from app.services.audit_service import log_audit, get_audit_logs
from app.models.audit_log import AuditAction

router = APIRouter(prefix="/commands", tags=["Commands"])

DESTRUCTIVE_COMMANDS = {
    CommandType.REMOTE_UNINSTALL,
    CommandType.WIPE_DEVICE,
}


class IssueCommandRequest(BaseModel):
    device_id: UUID
    command_type: str
    payload: Optional[dict] = None
    otp_id: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    otp_id: UUID
    otp_code: str
    device_id: UUID


@router.post("/issue", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def issue_command(
    request: Request,
    body: IssueCommandRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    cmd_type = CommandType(body.command_type)
    is_destructive = cmd_type in DESTRUCTIVE_COMMANDS

    if is_destructive and not body.otp_id:
        raise HTTPException(
            status_code=400,
            detail="Destructive commands require OTP verification first. "
                   "Call /commands/generate-otp to get an OTP.",
        )

    command = await device_service.issue_command(
        db,
        device_id=body.device_id,
        admin_id=current_user.id,
        command_type=cmd_type,
        payload=body.payload,
        requires_otp=is_destructive,
        otp_id=body.otp_id,
        ip=ip,
    )
    return {
        "command_id": str(command.id),
        "status": command.status,
        "command_type": command.command_type,
    }


@router.post("/generate-otp", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def generate_otp(
    request: Request,
    device_id: UUID,
    command_type: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Generate a 6-digit OTP for admin to authorize a destructive command."""
    ip = request.client.host if request.client else "unknown"
    return await otp_service.generate_uninstall_otp(
        db, device_id, current_user.id, command_type, ip
    )


@router.post("/verify-otp")
async def verify_otp_on_device(
    request: Request,
    body: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """Called by device agent when employee enters OTP."""
    ip = request.client.host if request.client else "unknown"
    verified = await otp_service.verify_device_otp(
        db, body.otp_id, body.otp_code, body.device_id, ip
    )
    return {"verified": verified, "message": "OTP verified. Proceeding with authorized action."}


@router.post("/admin-silent-uninstall", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def admin_silent_uninstall(
    request: Request,
    device_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin one-click silent uninstall — no employee interaction required.
    Backend auto-generates + verifies OTP server-side, then sends
    the authorized uninstall command via FCM with embedded token.
    Completes within ~30 seconds if device is online.
    """
    ip = request.client.host if request.client else "unknown"

    # 1. Auto-generate OTP server-side
    otp_result = await otp_service.generate_uninstall_otp(
        db, device_id, current_user.id, "remote_uninstall", ip
    )
    otp_id = otp_result["otp_id"]
    otp_code = otp_result["otp"]

    # 2. Auto-verify OTP server-side (admin is authorizing, no employee needed)
    await otp_service.verify_device_otp(db, otp_id, otp_code, device_id, ip)

    # 3. Issue command with pre-verified OTP embedded in payload
    command = await device_service.issue_command(
        db,
        device_id=device_id,
        admin_id=current_user.id,
        command_type=CommandType.REMOTE_UNINSTALL,
        payload={"otp_id": otp_id, "pre_verified": True, "silent": True},
        requires_otp=True,
        otp_id=otp_id,
        ip=ip,
    )

    await log_audit(
        db, AuditAction.UNINSTALL_AUTHORIZED,
        admin_user_id=current_user.id, device_id=device_id, ip_address=ip,
        description="Admin silent uninstall initiated",
        metadata={"command_id": str(command.id), "admin": str(current_user.id)},
    )

    return {
        "command_id": str(command.id),
        "status": command.status,
        "message": "Silent uninstall command sent. Device will uninstall within ~30 seconds.",
        "audit_logged": True,
    }


@router.get("/audit-logs", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def audit_logs(
    device_id: Optional[UUID] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    logs = await get_audit_logs(db, device_id=device_id, limit=limit, offset=offset)
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "device_id": str(log.device_id) if log.device_id else None,
            "admin_user_id": str(log.admin_user_id) if log.admin_user_id else None,
            "description": log.description,
            "metadata": log.metadata,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "created_at": log.created_at,
        }
        for log in logs
    ]
