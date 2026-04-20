"""
Extract unique motherboard/baseboard serial number and BIOS UUID.
Combines multiple hardware identifiers into a stable hardware fingerprint.
"""

import hashlib
import json
import logging
import platform
import re
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _run_wmic(query: str) -> str:
    """Run a WMIC query and return stripped output."""
    try:
        result = subprocess.run(
            ["wmic"] + query.split() + ["get", "/format:csv"],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip()
    except Exception as e:
        logger.warning("WMIC query failed: %s", e)
        return ""


def _run_powershell(command: str) -> Optional[str]:
    """Run a PowerShell command and return output."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.warning("PowerShell command failed: %s", e)
        return None


def get_baseboard_serial() -> Optional[str]:
    """Get motherboard/baseboard serial number."""
    system = platform.system()

    if system == "Windows":
        # Primary: Win32_BaseBoard via PowerShell
        ps_out = _run_powershell(
            "Get-WmiObject Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"
        )
        if ps_out and ps_out not in ("", "None", "To be filled by O.E.M.", "Default string"):
            return ps_out

        # Fallback: WMIC baseboard
        output = _run_wmic("baseboard SerialNumber")
        for line in output.splitlines():
            if "," in line:
                serial = line.split(",")[-1].strip()
                if serial and serial not in ("SerialNumber", "To be filled by O.E.M.", ""):
                    return serial

    elif system == "Linux":
        paths = [
            "/sys/class/dmi/id/board_serial",
            "/sys/class/dmi/id/product_serial",
        ]
        for path in paths:
            try:
                with open(path) as f:
                    serial = f.read().strip()
                if serial and serial not in ("", "None", "To be filled by O.E.M."):
                    return serial
            except (IOError, PermissionError):
                pass

        # Try dmidecode
        try:
            result = subprocess.run(
                ["dmidecode", "-s", "baseboard-serial-number"],
                capture_output=True, text=True, timeout=10
            )
            serial = result.stdout.strip()
            if serial and "Not Present" not in serial:
                return serial
        except FileNotFoundError:
            pass

    return None


def get_bios_uuid() -> Optional[str]:
    """Get BIOS/SMBIOS UUID — unique per motherboard from factory."""
    system = platform.system()

    if system == "Windows":
        ps_out = _run_powershell(
            "Get-WmiObject Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"
        )
        if ps_out and ps_out not in ("", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"):
            return ps_out

    elif system == "Linux":
        try:
            with open("/sys/class/dmi/id/product_uuid") as f:
                uuid = f.read().strip()
            if uuid:
                return uuid
        except (IOError, PermissionError):
            pass

        try:
            result = subprocess.run(
                ["dmidecode", "-s", "system-uuid"],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip() or None
        except FileNotFoundError:
            pass

    return None


def get_cpu_id() -> Optional[str]:
    """Get CPU processor ID for additional hardware binding."""
    system = platform.system()

    if system == "Windows":
        ps_out = _run_powershell(
            "Get-WmiObject Win32_Processor | Select-Object -ExpandProperty ProcessorId"
        )
        return ps_out or None

    elif system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.lower().startswith("serial"):
                        return line.split(":")[1].strip()
        except Exception:
            pass

    return None


def get_motherboard_fingerprint() -> dict:
    """
    Build a stable hardware fingerprint from baseboard serial, BIOS UUID, and CPU ID.
    The fingerprint remains constant unless physical hardware is replaced.
    """
    baseboard_serial = get_baseboard_serial()
    bios_uuid = get_bios_uuid()
    cpu_id = get_cpu_id()

    components = [
        baseboard_serial or "",
        bios_uuid or "",
        cpu_id or "",
        platform.node(),  # hostname adds context but isn't hardware-bound
    ]

    # Primary fingerprint: board serial + BIOS UUID (hardware-only, survives OS reinstall)
    hardware_components = [baseboard_serial or "", bios_uuid or ""]
    hardware_fingerprint = hashlib.sha256("|".join(hardware_components).encode()).hexdigest()

    # Full fingerprint includes CPU
    full_fingerprint = hashlib.sha256("|".join(components).encode()).hexdigest()

    return {
        "baseboard_serial": baseboard_serial,
        "bios_uuid": bios_uuid,
        "cpu_id": cpu_id,
        "hardware_fingerprint": hardware_fingerprint,
        "full_fingerprint": full_fingerprint,
        "platform": platform.system(),
        "hostname": platform.node(),
    }


def is_hardware_changed(stored_fingerprint: str) -> bool:
    """Compare current hardware fingerprint against stored golden value."""
    current = get_motherboard_fingerprint()
    return current["hardware_fingerprint"] != stored_fingerprint


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    info = get_motherboard_fingerprint()
    print(json.dumps(info, indent=2))
