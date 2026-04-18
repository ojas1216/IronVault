import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SAEnum, Text, ForeignKey
from sqlalchemy import Uuid as UUID, JSON as JSONB, String as _String
from sqlalchemy.orm import relationship
from app.database import Base


class AuditAction(str, enum.Enum):
    # Auth
    ADMIN_LOGIN = "admin_login"
    ADMIN_LOGOUT = "admin_logout"
    ADMIN_LOGIN_FAILED = "admin_login_failed"
    # Device
    DEVICE_ENROLLED = "device_enrolled"
    DEVICE_UPDATED = "device_updated"
    DEVICE_DECOMMISSIONED = "device_decommissioned"
    # Commands
    COMMAND_ISSUED = "command_issued"
    COMMAND_COMPLETED = "command_completed"
    COMMAND_FAILED = "command_failed"
    # OTP
    OTP_GENERATED = "otp_generated"
    OTP_VERIFIED = "otp_verified"
    OTP_FAILED = "otp_failed"
    OTP_EXPIRED = "otp_expired"
    # Security
    ROOT_DETECTED = "root_detected"
    TAMPER_DETECTED = "tamper_detected"
    UNINSTALL_ATTEMPT = "uninstall_attempt"
    UNINSTALL_BLOCKED = "uninstall_blocked"
    UNINSTALL_AUTHORIZED = "uninstall_authorized"
    # Policy
    POLICY_UPDATED = "policy_updated"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(SAEnum(AuditAction), nullable=False, index=True)

    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True)

    description = Column(Text, nullable=True)
    extra_data = Column(JSONB, default={})
    ip_address = Column(_String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    admin_user = relationship("User", back_populates="audit_logs")
    device = relationship("Device", back_populates="audit_logs")
