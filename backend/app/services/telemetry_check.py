"""
24-hour hardware telemetry heartbeat validation.
Devices must report hardware fingerprints every 24h or be flagged as non-compliant.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.device import Device
from app.services.audit_service import create_audit_log

logger = logging.getLogger(__name__)

TELEMETRY_INTERVAL_HOURS = 24
GRACE_PERIOD_HOURS = 1  # Allow 25h before flagging as overdue


def record_hardware_telemetry(
    db: Session,
    device_id: str,
    hardware_fingerprint: str,
    tpm_chip_id: Optional[str] = None,
    secure_boot_enabled: Optional[bool] = None,
    baseboard_serial: Optional[str] = None,
    bios_uuid: Optional[str] = None,
    firmware_fingerprint: Optional[str] = None,
) -> dict:
    """
    Record a hardware telemetry report from a device.
    Triggers resale detection if fingerprint has changed.
    """
    from app.services.resale_detection import check_hardware_mismatch

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return {"error": "Device not found"}

    # Run resale detection
    mismatch_result = check_hardware_mismatch(
        db=db,
        device_id=device_id,
        reported_fingerprint=hardware_fingerprint,
        reported_baseboard_serial=baseboard_serial,
        reported_bios_uuid=bios_uuid,
    )

    # Update telemetry fields
    device.last_hardware_check = datetime.now(timezone.utc)
    device.last_tpm_chip_id = tpm_chip_id
    device.last_secure_boot_status = secure_boot_enabled
    device.last_firmware_fingerprint = firmware_fingerprint
    db.commit()

    create_audit_log(
        db=db,
        device_id=device_id,
        event_type="HARDWARE_TELEMETRY",
        severity="INFO",
        details={
            "fingerprint_prefix": hardware_fingerprint[:16] + "...",
            "tpm_present": tpm_chip_id is not None,
            "secure_boot": secure_boot_enabled,
            "mismatch": mismatch_result.get("flagged", False),
        },
    )

    return {
        "recorded": True,
        "next_check_due": (
            datetime.now(timezone.utc) + timedelta(hours=TELEMETRY_INTERVAL_HOURS)
        ).isoformat(),
        "mismatch_detected": mismatch_result.get("flagged", False),
        "mismatch_action": mismatch_result.get("action"),
    }


def get_overdue_devices(db: Session) -> list[dict]:
    """
    Return devices that have not reported hardware telemetry within the allowed window.
    These devices should be investigated or remotely locked.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=TELEMETRY_INTERVAL_HOURS + GRACE_PERIOD_HOURS
    )

    overdue = (
        db.query(Device)
        .filter(
            Device.is_enrolled == True,
            Device.is_flagged == False,
            (Device.last_hardware_check == None) | (Device.last_hardware_check < cutoff),
        )
        .all()
    )

    result = []
    for device in overdue:
        last_check = device.last_hardware_check
        hours_overdue = (
            (datetime.now(timezone.utc) - last_check).total_seconds() / 3600
            if last_check
            else None
        )
        result.append({
            "device_id": str(device.id),
            "device_name": device.device_name,
            "last_hardware_check": last_check.isoformat() if last_check else "NEVER",
            "hours_overdue": round(hours_overdue, 1) if hours_overdue else None,
            "enrolled_at": device.enrolled_at.isoformat() if device.enrolled_at else None,
        })

    return result


def run_periodic_telemetry_scan(db: Session) -> dict:
    """
    Scheduled task: scan for overdue devices and flag non-compliant ones.
    Called by the background scheduler every hour.
    """
    overdue = get_overdue_devices(db)
    flagged_count = 0

    for entry in overdue:
        hours = entry.get("hours_overdue")
        # Flag as non-compliant after 48h of silence
        if hours is None or hours > 48:
            device = db.query(Device).filter(
                Device.id == entry["device_id"]
            ).first()
            if device and not device.is_flagged:
                device.is_flagged = True
                device.flag_reason = "TELEMETRY_SILENT"
                device.flagged_at = datetime.now(timezone.utc)
                db.commit()
                flagged_count += 1

                create_audit_log(
                    db=db,
                    device_id=entry["device_id"],
                    event_type="TELEMETRY_SILENT",
                    severity="HIGH",
                    details={"hours_silent": hours},
                )
                logger.warning("Device %s flagged as TELEMETRY_SILENT", entry["device_id"])

    return {
        "overdue_devices": len(overdue),
        "newly_flagged": flagged_count,
        "scan_time": datetime.now(timezone.utc).isoformat(),
    }
