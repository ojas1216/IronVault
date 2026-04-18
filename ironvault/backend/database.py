"""
IronVault Database Models + Async Engine
"""
import os
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://ironvault:ironvault@localhost/ironvault"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ─── Models ───────────────────────────────────────────────────────────────────

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True)
    device_name = Column(String(200), nullable=False)
    owner_name = Column(String(200))
    owner_email = Column(String(200))
    department = Column(String(100))

    # Identity
    imei = Column(String(20), index=True)
    imei2 = Column(String(20))
    serial = Column(String(100))
    android_id = Column(String(64))
    hardware_fingerprint = Column(String(64), index=True)
    manufacturer = Column(String(100))
    model = Column(String(100))
    os_version = Column(String(50))
    sdk_version = Column(Integer)

    # Push
    push_token = Column(Text)
    device_secret = Column(String(128), nullable=False)

    # Status
    status = Column(String(30), default="active", index=True)
    is_online = Column(Boolean, default=False)
    is_rooted = Column(Boolean, default=False)
    battery_level = Column(Integer)
    last_latitude = Column(Float)
    last_longitude = Column(Float)

    enrolled_at = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True), index=True)


class LocationRecord(Base):
    __tablename__ = "location_history"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float)
    altitude = Column(Float)
    speed = Column(Float)
    provider = Column(String(30))
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SIMEvent(Base):
    __tablename__ = "sim_events"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    event_type = Column(String(30), nullable=False)  # swapped, removed, inserted
    payload = Column(JSON)
    photo_url = Column(Text)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(200))
    resolution_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class TamperLog(Base):
    __tablename__ = "tamper_logs"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Command(Base):
    __tablename__ = "commands"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    command_type = Column(String(50), nullable=False)
    payload = Column(JSON)
    pre_verified = Column(Boolean, default=False)
    status = Column(String(20), default="pending", index=True)
    result = Column(JSON)
    issued_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))


class TelemetryRecord(Base):
    __tablename__ = "telemetry"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    hardware_fingerprint = Column(String(64))
    imei = Column(String(20))
    sim_count = Column(Integer)
    location = Column(JSON)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
