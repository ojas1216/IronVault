"""
Verify UEFI Secure Boot status on Windows and Linux.
Returns detailed Secure Boot configuration for hardware integrity validation.
"""

import json
import logging
import platform
import subprocess
import winreg
from typing import Optional

logger = logging.getLogger(__name__)

SECURE_BOOT_REGISTRY_PATH = r"SYSTEM\CurrentControlSet\Control\SecureBoot\State"
SECURE_BOOT_VALUE = "UEFISecureBootEnabled"


def _check_secure_boot_windows() -> dict:
    """Check Secure Boot via Windows registry."""
    result = {
        "platform": "windows",
        "secure_boot_enabled": False,
        "uefi_mode": False,
        "setup_mode": False,
        "policy_active": None,
    }

    # Check Secure Boot registry key
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SECURE_BOOT_REGISTRY_PATH)
        value, _ = winreg.QueryValueEx(key, SECURE_BOOT_VALUE)
        winreg.CloseKey(key)
        result["secure_boot_enabled"] = bool(value)
    except FileNotFoundError:
        result["secure_boot_enabled"] = False
        result["note"] = "Registry key absent — likely Legacy BIOS mode"
    except Exception as e:
        logger.warning("Secure Boot registry read failed: %s", e)

    # Check UEFI mode via PowerShell (Confirm-SecureBootUEFI)
    try:
        ps_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Confirm-SecureBootUEFI"],
            capture_output=True, text=True, timeout=10
        )
        stdout = ps_result.stdout.strip().lower()
        if stdout == "true":
            result["secure_boot_enabled"] = True
            result["uefi_mode"] = True
        elif stdout == "false":
            result["uefi_mode"] = True
            result["secure_boot_enabled"] = False
        # If command not found, it's BIOS mode
    except Exception as e:
        logger.debug("Confirm-SecureBootUEFI failed: %s", e)

    # Get additional firmware info
    try:
        ps_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\SecureBoot\\State' | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        if ps_result.returncode == 0 and ps_result.stdout.strip():
            data = json.loads(ps_result.stdout.strip())
            result["policy_active"] = data.get("UEFISecureBootEnabled")
    except Exception:
        pass

    return result


def _check_secure_boot_linux() -> dict:
    """Check Secure Boot via efivarfs on Linux."""
    result = {
        "platform": "linux",
        "secure_boot_enabled": False,
        "uefi_mode": False,
    }

    secure_boot_var = "/sys/firmware/efi/vars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c/data"
    setup_mode_var = "/sys/firmware/efi/vars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c/data"

    try:
        import os
        if os.path.exists("/sys/firmware/efi"):
            result["uefi_mode"] = True

        if os.path.exists(secure_boot_var):
            with open(secure_boot_var, "rb") as f:
                data = f.read()
            # SecureBoot variable is 5 bytes: 4 bytes EFI attr + 1 byte value
            if len(data) >= 5:
                result["secure_boot_enabled"] = data[4] == 1
            elif len(data) == 1:
                result["secure_boot_enabled"] = data[0] == 1

        if os.path.exists(setup_mode_var):
            with open(setup_mode_var, "rb") as f:
                data = f.read()
            if len(data) >= 1:
                result["setup_mode"] = data[-1] == 1
    except Exception as e:
        logger.warning("Linux Secure Boot check failed: %s", e)

    # Try mokutil as fallback
    try:
        proc = subprocess.run(["mokutil", "--sb-state"], capture_output=True, text=True, timeout=5)
        result["mokutil_output"] = proc.stdout.strip()
        if "SecureBoot enabled" in proc.stdout:
            result["secure_boot_enabled"] = True
    except FileNotFoundError:
        pass

    return result


def check_secure_boot() -> dict:
    """
    Platform-agnostic Secure Boot check.
    Returns dict with secure_boot_enabled, uefi_mode, and platform details.
    """
    system = platform.system()
    if system == "Windows":
        return _check_secure_boot_windows()
    elif system == "Linux":
        return _check_secure_boot_linux()
    else:
        return {"platform": system, "secure_boot_enabled": False, "note": "Unsupported platform"}


def is_secure_boot_active() -> bool:
    """Quick boolean check for Secure Boot."""
    return check_secure_boot().get("secure_boot_enabled", False)


def validate_for_enrollment() -> tuple[bool, str]:
    """
    Return (approved, reason). Devices without Secure Boot may be rejected
    depending on company policy.
    """
    state = check_secure_boot()
    if not state.get("uefi_mode", False):
        return False, "Device is in Legacy BIOS mode — UEFI required"
    if not state.get("secure_boot_enabled", False):
        return False, "Secure Boot is disabled — enable in UEFI settings"
    return True, "Secure Boot is enabled"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = check_secure_boot()
    print(json.dumps(result, indent=2))
    ok, msg = validate_for_enrollment()
    print(f"\nEnrollment check: {'PASS' if ok else 'FAIL'} — {msg}")
