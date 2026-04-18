import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SAEnum, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class SimEventType(str, enum.Enum):
    INSERTED = "inserted"
    REMOVED = "removed"
    SWAPPED = "swapped"
    CHANGED = "changed"


class SimEvent(Base):
    __tablename__ = "sim_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)

    event_type = Column(SAEnum(SimEventType), nullable=False)
    slot_index = Column(Integer, default=0)

    # SIM metadata at time of event
    iccid = Column(String(20), nullable=True)
    imsi = Column(String(20), nullable=True)
    carrier_name = Column(String(100), nullable=True)
    mcc = Column(String(10), nullable=True)
    mnc = Column(String(10), nullable=True)
    country_iso = Column(String(10), nullable=True)
    phone_number = Column(String(30), nullable=True)
    is_roaming = Column(Boolean, default=False)

    # Security photo path (uploaded by device)
    security_photo_url = Column(String(500), nullable=True)

    # Full raw metadata snapshot
    raw_metadata = Column(JSONB, default={})

    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String(500), nullable=True)

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    device = relationship("Device", foreign_keys=[device_id])
