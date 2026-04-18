import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class UWBRangingPoint(Base):
    """Single UWB/BLE ranging measurement from a device."""
    __tablename__ = "uwb_ranging_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"),
                       nullable=False, index=True)

    mode = Column(String(20), nullable=False)       # uwb | ble_fallback | ios_nearby
    distance_meters = Column(Float, nullable=True)
    azimuth_degrees = Column(Float, nullable=True)  # horizontal direction
    elevation_degrees = Column(Float, nullable=True)
    rssi = Column(Integer, nullable=True)           # BLE RSSI (fallback)
    accuracy_cm = Column(Float, nullable=True)      # estimated accuracy

    # Anchor / peer info
    anchor_id = Column(String(100), nullable=True)
    peer_address = Column(String(100), nullable=True)

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    device = relationship("Device", foreign_keys=[device_id])


class IMEILog(Base):
    """Timestamped IMEI record for forensic tracking."""
    __tablename__ = "imei_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"),
                       nullable=False, index=True)
    imei_slot1 = Column(String(20), nullable=True)
    imei_slot2 = Column(String(20), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
