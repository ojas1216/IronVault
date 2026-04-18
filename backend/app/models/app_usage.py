import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class AppUsageLog(Base):
    __tablename__ = "app_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)

    app_package = Column(String(255), nullable=False)
    app_name = Column(String(255), nullable=True)
    usage_duration_seconds = Column(Integer, nullable=False)
    is_work_app = Column(Boolean, default=False)

    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    device = relationship("Device", back_populates="app_usage_logs")
