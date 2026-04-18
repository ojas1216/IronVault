from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.audit_log import AuditLog, AuditAction


async def log_audit(
    db: AsyncSession,
    action: AuditAction,
    admin_user_id: Optional[UUID] = None,
    device_id: Optional[UUID] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    log = AuditLog(
        action=action,
        admin_user_id=admin_user_id,
        device_id=device_id,
        description=description,
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.flush()
    return log


async def get_audit_logs(
    db: AsyncSession,
    device_id: Optional[UUID] = None,
    admin_id: Optional[UUID] = None,
    action: Optional[AuditAction] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    if device_id:
        query = query.where(AuditLog.device_id == device_id)
    if admin_id:
        query = query.where(AuditLog.admin_user_id == admin_id)
    if action:
        query = query.where(AuditLog.action == action)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()
