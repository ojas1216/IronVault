import platform
import os
import subprocess
import logging

logger = logging.getLogger(__name__)


class SecurityCheck:
    @staticmethod
    def run() -> dict:
        result = {
            "is_elevated_suspicious": False,
            "debugger_attached": False,
            "disk_encrypted": False,
        }

        try:
            if platform.system() == "Windows":
                result.update(SecurityCheck._windows_checks())
            elif platform.system() == "Darwin":
                result.update(SecurityCheck._macos_checks())
        except Exception as e:
            logger.debug(f"Security check error: {e}")

        return result

    @staticmethod
    def _windows_checks() -> dict:
        checks = {}
        try:
            import ctypes
            # Check if BitLocker is enabled on system drive
            result = subprocess.run(
                ["manage-bde", "-status", "C:"],
                capture_output=True, text=True, timeout=5
            )
            checks["disk_encrypted"] = "Percentage Encrypted: 100%" in result.stdout
        except Exception:
            pass
        return checks

    @staticmethod
    def _macos_checks() -> dict:
        checks = {}
        try:
            result = subprocess.run(
                ["fdesetup", "status"],
                capture_output=True, text=True, timeout=5,
            )
            checks["disk_encrypted"] = "FileVault is On" in result.stdout
        except Exception:
            pass
        return checks
