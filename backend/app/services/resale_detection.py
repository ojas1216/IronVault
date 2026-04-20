"""
Detects hardware resale by comparing current device fingerprints against
the golden fingerprint recorded at enrollment time.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.audit_log import AuditLog
from app.services.audit_service import create_audit_log

logger = logging.getLogger(__name__)

RESALE_FLAG = "RESOLD"
TAMPER_FLAG = "HARDWARE_TAMPERED"


def _fingerprints_match(golden: str, current: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    import hmac
    return hmac.compare_digest(golden.lower(), current.lower())


def check_hardware_mismatch(
    db: Session,
    device_id: str,
    reported_fingerprint: str,
    reported_baseboard_serial: Optional[str] = None,
    reported_bios_uuid: Optional[str] = None,
) -> dict:
    """
    Compare reported hardware fingerprint against the golden fingerprint
    stored at enrollment. Returns mismatch details and flags device if resold.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return {"error": "Device not found", "flagged": False}

    golden_fingerprint = device.hardware_fingerprint
    if not golden_fingerprint:
        # No golden fingerprint — this is first enrollment, store it
        device.hardware_fingerprint = reported_fingerprint
        device.baseboard_serial = reported_baseboard_serial
        device.bios_uuid = reported_bios_uuid
        db.commit()
        return {
            "status": "enrolled",
            "flagged": False,
            "message": "Golden fingerprint stored",
        }

    fingerprint_match = _fingerprints_match(golden_fingerprint, reported_fingerprint)

    if fingerprint_match:
        device.last_hardware_check = datetime.now(timezone.utc)
        db.commit()
        return {"status": "ok", "flagged": False, "match": True}

    # Mismatch detected — determine severity
    reason = _classify_mismatch(
        device,
        reported_fingerprint,
        reported_baseboard_serial,
        reported_bios_uuid,
    )

    # Flag device
    device.security_flags = (device.security_flags or "") + f",{reason}"
    device.is_flagged = True
    device.flag_reason = reason
    device.flagged_at = datetime.now(timezone.utc)
    db.commit()

    # Audit log
    create_audit_log(
        db=db,
        device_id=device_id,
        event_type="HARDWARE_MISMATCH",
        severity="CRITICAL",
        details={
            "golden_fingerprint": golden_fingerprint[:16] + "...",
            "reported_fingerprint": reported_fingerprint[:16] + "...",
            "reason": reason,
        },
    )

    logger.critical(
        "Hardware mismatch on device %s: %s | golden=%s current=%s",
        device_id, reason, golden_fingerprint[:8], reported_fingerprint[:8]
    )

    return {
        "status": "mismatch",
        "flagged": True,
        "reason": reason,
        "device_id": device_id,
        "action": "BRICK_DEVICE" if reason == RESALE_FLAG else "ALERT_ADMIN",
    }


def _classify_mismatch(
    device: Device,
    reported_fingerprint: str,
    reported_baseboard_serial: Optional[str],
    reported_bios_uuid: Optional[str],
) -> str:
    """
    Classify whether mismatch is resale (motherboard swapped) or tampering.
    """
    # If baseboard serial changed, the physical motherboard was replaced
    if reported_baseboard_serial and device.baseboard_serial:
        if reported_baseboard_serial != device.baseboard_serial:
            return RESALE_FLAG

    # If BIOS UUID changed, likely motherboard replacement
    if reported_bios_uuid and device.bios_uuid:
        if reported_bios_uuid != device.bios_uuid:
            return RESALE_FLAG

    # Fingerprint changed but board identifiers unknown — treat as tamper
    return TAMPER_FLAG


def scan_all_devices_for_resale(db: Session) -> list[dict]:
    """
    Scan all enrolled devices whose last hardware check is overdue (>25h).
    Used by the background telemetry checker.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
    overdue_devices = (
        db.query(Device)
        .filter(
            Device.is_enrolled == True,
            Device.is_flagged == False,
            (Device.last_hardware_check == None) | (Device.last_hardware_check < cutoff),
        )
        .all()
    )

    results = []
    for device in overdue_devices:
        results.append({
            "device_id": str(device.id),
            "device_name": device.device_name,
            "last_hardware_check": device.last_hardware_check.isoformat() if device.last_hardware_check else None,
            "status": "OVERDUE_CHECK",
        })

    return results


def get_flagged_devices(db: Session) -> list[dict]:
    """Return all devices flagged for hardware mismatch or resale."""
    flagged = db.query(Device).filter(Device.is_flagged == True).all()
    return [
        {
            "device_id": str(d.id),
            "device_name": d.device_name,
            "flag_reason": d.flag_reason,
            "flagged_at": d.flagged_at.isoformat() if d.flagged_at else None,
            "security_flags": d.security_flags,
        }
        for d in flagged
    ]
