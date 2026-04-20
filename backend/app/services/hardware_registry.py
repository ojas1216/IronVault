"""
Global registry of hardware fingerprints for stolen/resold device tracking.
Enables cross-company detection when a device is wiped and re-enrolled elsewhere.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session
import uuid

from app.database import Base

logger = logging.getLogger(__name__)


class HardwareRegistryEntry(Base):
    __tablename__ = "hardware_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hardware_fingerprint = Column(String(64), nullable=False, unique=True, index=True)
    baseboard_serial_hash = Column(String(64), nullable=True, index=True)
    bios_uuid_hash = Column(String(64), nullable=True, index=True)
    tpm_chip_id_hash = Column(String(64), nullable=True)

    original_device_id = Column(UUID(as_uuid=True), nullable=False)
    original_company_id = Column(UUID(as_uuid=True), nullable=True)
    enrolled_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    is_stolen = Column(Boolean, default=False, nullable=False)
    is_resold = Column(Boolean, default=False, nullable=False)
    flagged_at = Column(DateTime(timezone=True), nullable=True)
    flag_reason = Column(String(255), nullable=True)
    flag_notes = Column(Text, nullable=True)

    last_seen_device_id = Column(UUID(as_uuid=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_hw_registry_fingerprint", "hardware_fingerprint"),
        Index("ix_hw_registry_board_hash", "baseboard_serial_hash"),
    )


def _hash_identifier(value: str) -> str:
    """One-way hash of sensitive hardware identifiers."""
    return hashlib.sha256(value.encode()).hexdigest()


def register_hardware(
    db: Session,
    hardware_fingerprint: str,
    device_id: str,
    company_id: Optional[str] = None,
    baseboard_serial: Optional[str] = None,
    bios_uuid: Optional[str] = None,
    tpm_chip_id: Optional[str] = None,
) -> dict:
    """
    Register hardware fingerprint at enrollment. If fingerprint already exists
    for a different device, it indicates the hardware was resold/stolen.
    """
    existing = (
        db.query(HardwareRegistryEntry)
        .filter(HardwareRegistryEntry.hardware_fingerprint == hardware_fingerprint)
        .first()
    )

    if existing:
        # Hardware was seen before
        existing.last_seen_device_id = device_id
        existing.last_seen_at = datetime.now(timezone.utc)

        if str(existing.original_device_id) != str(device_id):
            # Different device — this hardware was resold or stolen
            existing.is_resold = True
            existing.flagged_at = datetime.now(timezone.utc)
            existing.flag_reason = "HARDWARE_REUSED_DIFFERENT_DEVICE"
            db.commit()

            logger.critical(
                "Hardware fingerprint %s...%s seen on NEW device %s (originally %s)",
                hardware_fingerprint[:8], hardware_fingerprint[-4:],
                device_id, existing.original_device_id
            )
            return {
                "status": "RESALE_DETECTED",
                "original_device_id": str(existing.original_device_id),
                "current_device_id": str(device_id),
                "enrolled_at": existing.enrolled_at.isoformat(),
                "action": "BLOCK_ENROLLMENT",
            }

        db.commit()
        return {"status": "ok", "existing": True}

    # Check by baseboard serial hash (catches fingerprint regeneration)
    if baseboard_serial:
        board_hash = _hash_identifier(baseboard_serial)
        board_match = (
            db.query(HardwareRegistryEntry)
            .filter(HardwareRegistryEntry.baseboard_serial_hash == board_hash)
            .first()
        )
        if board_match and str(board_match.original_device_id) != str(device_id):
            logger.warning(
                "Baseboard serial collision: device %s reusing board from device %s",
                device_id, board_match.original_device_id
            )
            return {
                "status": "BOARD_COLLISION",
                "original_device_id": str(board_match.original_device_id),
                "action": "FLAG_FOR_REVIEW",
            }

    # New hardware — register it
    entry = HardwareRegistryEntry(
        hardware_fingerprint=hardware_fingerprint,
        baseboard_serial_hash=_hash_identifier(baseboard_serial) if baseboard_serial else None,
        bios_uuid_hash=_hash_identifier(bios_uuid) if bios_uuid else None,
        tpm_chip_id_hash=_hash_identifier(tpm_chip_id) if tpm_chip_id else None,
        original_device_id=device_id,
        original_company_id=company_id,
    )
    db.add(entry)
    db.commit()

    return {"status": "registered", "existing": False}


def mark_as_stolen(
    db: Session,
    hardware_fingerprint: str,
    notes: Optional[str] = None,
) -> bool:
    """Mark a hardware fingerprint as stolen. Any re-enrollment will be blocked."""
    entry = (
        db.query(HardwareRegistryEntry)
        .filter(HardwareRegistryEntry.hardware_fingerprint == hardware_fingerprint)
        .first()
    )
    if not entry:
        return False

    entry.is_stolen = True
    entry.flagged_at = datetime.now(timezone.utc)
    entry.flag_reason = "REPORTED_STOLEN"
    entry.flag_notes = notes
    db.commit()
    return True


def lookup_hardware(db: Session, hardware_fingerprint: str) -> Optional[dict]:
    """Look up a hardware fingerprint in the registry."""
    entry = (
        db.query(HardwareRegistryEntry)
        .filter(HardwareRegistryEntry.hardware_fingerprint == hardware_fingerprint)
        .first()
    )
    if not entry:
        return None

    return {
        "hardware_fingerprint": entry.hardware_fingerprint,
        "original_device_id": str(entry.original_device_id),
        "enrolled_at": entry.enrolled_at.isoformat(),
        "is_stolen": entry.is_stolen,
        "is_resold": entry.is_resold,
        "flag_reason": entry.flag_reason,
        "last_seen_at": entry.last_seen_at.isoformat() if entry.last_seen_at else None,
    }


def get_stolen_hardware_count(db: Session) -> int:
    return db.query(HardwareRegistryEntry).filter(
        (HardwareRegistryEntry.is_stolen == True) | (HardwareRegistryEntry.is_resold == True)
    ).count()
