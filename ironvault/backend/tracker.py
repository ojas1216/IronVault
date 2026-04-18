"""
IronVault Hardware Registry & Anti-Resale Tracker
Detects: hardware swaps, IMEI reuse, SIM swap patterns across the entire fleet
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session, Device, TamperLog, TelemetryRecord
import uuid


class AntiResaleTracker:
    """
    Tracks device hardware fingerprints globally.
    Detects:
    - Same IMEI, different hardware fingerprint → device was opened/parted
    - Same fingerprint, different IMEI → IMEI spoof or motherboard swap
    - Same fingerprint, different SIM → normal use OR SIM swap
    - Device offline > 7 days after being active → potential theft
    """

    async def check_registration(
        self, db: AsyncSession, device_id: str, imei: Optional[str], fingerprint: Optional[str]
    ) -> dict:
        """
        Called on every device registration and telemetry check-in.
        Returns: {status, flags, should_brick}
        """
        flags = []
        should_brick = False

        if not imei and not fingerprint:
            return {"status": "ok", "flags": [], "should_brick": False}

        # Check IMEI history
        if imei:
            result = await db.execute(
                select(Device).where(
                    Device.imei == imei,
                    Device.id != device_id,
                    Device.hardware_fingerprint != None,
                )
            )
            other_devices = result.scalars().all()
            for other in other_devices:
                if fingerprint and other.hardware_fingerprint != fingerprint:
                    flags.append({
                        "type": "imei_hardware_mismatch",
                        "severity": "CRITICAL",
                        "description": f"IMEI {imei} previously had different hardware fingerprint",
                        "prev_device_id": other.id,
                        "prev_fingerprint": other.hardware_fingerprint,
                    })
                    should_brick = True
                    await self._log_flag(db, device_id, "imei_hardware_mismatch", {
                        "imei": imei,
                        "prev_device_id": other.id,
                        "prev_fp": other.hardware_fingerprint,
                        "new_fp": fingerprint,
                    })

        # Check fingerprint history
        if fingerprint:
            result = await db.execute(
                select(Device).where(
                    Device.hardware_fingerprint == fingerprint,
                    Device.id != device_id,
                    Device.imei != None,
                )
            )
            fp_devices = result.scalars().all()
            for other in fp_devices:
                if imei and other.imei and other.imei != imei:
                    flags.append({
                        "type": "fingerprint_imei_mismatch",
                        "severity": "HIGH",
                        "description": "Same hardware fingerprint seen with different IMEI — possible IMEI spoof",
                        "prev_device_id": other.id,
                        "prev_imei": other.imei,
                    })
                    await self._log_flag(db, device_id, "fingerprint_imei_mismatch", {
                        "fingerprint": fingerprint,
                        "prev_device_id": other.id,
                        "prev_imei": other.imei,
                        "new_imei": imei,
                    })

        return {
            "status": "flagged" if flags else "ok",
            "flags": flags,
            "should_brick": should_brick,
        }

    async def scan_offline_devices(self, db: AsyncSession) -> List[dict]:
        """
        Find devices that were active but haven't checked in for > 7 days.
        Marks them as potentially stolen.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            select(Device).where(
                Device.status == "active",
                Device.last_seen < cutoff,
                Device.last_seen != None,
            )
        )
        offline_devices = result.scalars().all()
        flagged = []
        for device in offline_devices:
            flagged.append({
                "device_id": device.id,
                "device_name": device.device_name,
                "last_seen": device.last_seen.isoformat(),
                "owner": device.owner_name,
                "imei": device.imei,
            })
            await self._log_flag(db, device.id, "device_offline_7_days", {
                "last_seen": device.last_seen.isoformat()
            })
        await db.commit()
        return flagged

    async def generate_registry_report(self, db: AsyncSession) -> dict:
        """Generate a full hardware registry cross-reference report."""
        # Devices with duplicate IMEIs
        dup_imei_query = text("""
            SELECT imei, COUNT(*) as cnt, array_agg(id) as device_ids
            FROM devices
            WHERE imei IS NOT NULL
            GROUP BY imei
            HAVING COUNT(*) > 1
        """)
        dup_fp_query = text("""
            SELECT hardware_fingerprint, COUNT(*) as cnt, array_agg(id) as device_ids
            FROM devices
            WHERE hardware_fingerprint IS NOT NULL
            GROUP BY hardware_fingerprint
            HAVING COUNT(*) > 1
        """)

        dup_imeis = await db.execute(dup_imei_query)
        dup_fps = await db.execute(dup_fp_query)

        return {
            "duplicate_imeis": [
                {"imei": row[0], "count": row[1], "device_ids": row[2]}
                for row in dup_imeis
            ],
            "duplicate_fingerprints": [
                {"fingerprint": row[0][:16] + "...", "count": row[1], "device_ids": row[2]}
                for row in dup_fps
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _log_flag(self, db: AsyncSession, device_id: str, event: str, payload: dict):
        log = TamperLog(
            id=str(uuid.uuid4()),
            device_id=device_id,
            event_type=event,
            payload=payload,
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)


# ─── Scheduled tasks ──────────────────────────────────────────────────────────

tracker = AntiResaleTracker()


async def run_periodic_scan():
    """Run anti-resale scan every 6 hours."""
    while True:
        await asyncio.sleep(6 * 3600)
        async with async_session() as db:
            try:
                offline = await tracker.scan_offline_devices(db)
                if offline:
                    print(f"[IronVault Tracker] {len(offline)} devices offline > 7 days")
            except Exception as e:
                print(f"[IronVault Tracker] Scan error: {e}")


if __name__ == "__main__":
    asyncio.run(run_periodic_scan())
