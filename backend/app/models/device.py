import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum, Text, Float, ForeignKey, Integer
from sqlalchemy import Uuid as UUID, JSON as JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class DevicePlatform(str, enum.Enum):
    ANDROID = "android"
    IOS = "ios"
    WINDOWS = "windows"
    MACOS = "macos"


class DeviceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOST = "lost"
    WIPED = "wiped"
    DECOMMISSIONED = "decommissioned"


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name = Column(String(255), nullable=False)
    employee_name = Column(String(255), nullable=False)
    employee_email = Column(String(255), nullable=False, index=True)
    employee_id = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)

    platform = Column(SAEnum(DevicePlatform), nullable=False)
    status = Column(SAEnum(DeviceStatus), default=DeviceStatus.ACTIVE)

    # Hardware identifiers (collected with consent/policy)
    device_model = Column(String(255), nullable=True)
    os_version = Column(String(100), nullable=True)
    serial_number = Column(String(255), nullable=True, unique=True)
    android_id = Column(String(255), nullable=True)

    # FCM / APNs push token
    push_token = Column(Text, nullable=True)
    apns_device_token = Column(Text, nullable=True)

    # Security
    enrollment_token = Column(String(255), nullable=True)
    device_certificate = Column(Text, nullable=True)
    is_rooted = Column(Boolean, default=False)
    is_encrypted = Column(Boolean, default=True)
    is_screen_locked = Column(Boolean, default=True)
    agent_version = Column(String(50), nullable=True)

    # Location (last known)
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)
    last_location_time = Column(DateTime(timezone=True), nullable=True)
    location_accuracy = Column(Float, nullable=True)

    # Connectivity
    last_seen = Column(DateTime(timezone=True), nullable=True)
    is_online = Column(Boolean, default=False)
    ip_address = Column(String(45), nullable=True)
    network_type = Column(String(50), nullable=True)

    # Anti-resale hardware tracking
    hardware_fingerprint = Column(String(64), nullable=True, index=True)
    baseboard_serial = Column(String(255), nullable=True)
    bios_uuid = Column(String(64), nullable=True)
    is_enrolled = Column(Boolean, default=False)
    last_hardware_check = Column(DateTime(timezone=True), nullable=True)
    last_tpm_chip_id = Column(String(64), nullable=True)
    last_secure_boot_status = Column(Boolean, nullable=True)
    last_firmware_fingerprint = Column(String(64), nullable=True)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(255), nullable=True)
    flagged_at = Column(DateTime(timezone=True), nullable=True)
    security_flags = Column(Text, nullable=True)

    # Policy
    is_uninstall_blocked = Column(Boolean, default=True)
    policy_version = Column(Integer, default=1)
    extra_metadata = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    enrolled_at = Column(DateTime(timezone=True), nullable=True)
    enrolled_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    commands = relationship("DeviceCommand", back_populates="device", lazy="select")
    audit_logs = relationship("AuditLog", back_populates="device", lazy="select")
    location_history = relationship("LocationHistory", back_populates="device", lazy="select")
    app_usage_logs = relationship("AppUsageLog", back_populates="device", lazy="select")
