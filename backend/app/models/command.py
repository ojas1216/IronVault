import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SAEnum, Text, ForeignKey
from sqlalchemy import Uuid as UUID, JSON as JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class CommandType(str, enum.Enum):
    LOCK_DEVICE = "lock_device"
    UNLOCK_DEVICE = "unlock_device"
    TRIGGER_ALARM = "trigger_alarm"
    REMOTE_UNINSTALL = "remote_uninstall"
    WIPE_DEVICE = "wipe_device"
    LOCATION_REQUEST = "location_request"
    POLICY_UPDATE = "policy_update"
    APP_BLOCK = "app_block"
    APP_UNBLOCK = "app_unblock"
    REBOOT = "reboot"
    COLLECT_LOGS = "collect_logs"
    ENABLE_LOST_MODE = "enable_lost_mode"
    DISABLE_LOST_MODE = "disable_lost_mode"
    CAPTURE_FRONT_CAMERA = "capture_front_camera"
    EXTRACT_SIM_METADATA = "extract_sim_metadata"
    EXTRACT_DEVICE_IDENTITY = "extract_device_identity"


class CommandStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DeviceCommand(Base):
    __tablename__ = "device_commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    issued_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    command_type = Column(SAEnum(CommandType), nullable=False)
    status = Column(SAEnum(CommandStatus), default=CommandStatus.PENDING)

    # Command payload (encrypted at rest)
    payload = Column(JSONB, default={})
    result = Column(JSONB, default={})
    error_message = Column(Text, nullable=True)

    # OTP verification (for destructive commands)
    requires_otp = Column(String(10), nullable=True)  # stores OTP id, not value
    otp_verified = Column(String(10), default="no")  # yes/no/na

    # Tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    device = relationship("Device", back_populates="commands")
    issued_by_user = relationship("User", back_populates="issued_commands")
