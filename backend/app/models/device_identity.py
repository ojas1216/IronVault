import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class DeviceIdentity(Base):
    """Section 4 — Stores IMEI, serial, hardware fingerprint per device."""
    __tablename__ = "device_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"),
                       nullable=False, unique=True, index=True)

    # 4.1 IMEI (Device Owner grants READ_PRIVILEGED_PHONE_STATE)
    imei_slot1 = Column(String(20), nullable=True)
    imei_slot2 = Column(String(20), nullable=True)

    # 4.2 Serial number
    serial_number = Column(String(100), nullable=True)

    # 4.3 Android ID
    android_id = Column(String(64), nullable=True)

    # 4.4 Hardware fingerprint (SHA-256 of board+brand+device+hw+manufacturer+model)
    hardware_fingerprint = Column(String(64), nullable=True)

    # Full hardware metadata
    board = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    hardware = Column(String(100), nullable=True)
    sdk_int = Column(Integer, nullable=True)

    # Raw payload snapshot
    raw_payload = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    device = relationship("Device", foreign_keys=[device_id])
