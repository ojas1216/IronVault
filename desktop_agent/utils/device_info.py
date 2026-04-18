import platform
import socket
import uuid
import subprocess
import logging

logger = logging.getLogger(__name__)


class DeviceInfo:
    @staticmethod
    def collect() -> dict:
        info = {
            "platform": platform.system().lower(),
            "os_version": f"{platform.system()} {platform.release()} {platform.version()}",
            "device_name": socket.gethostname(),
            "model": platform.machine(),
            "serial": DeviceInfo._get_serial(),
        }
        return info

    @staticmethod
    def _get_serial() -> str:
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "bios", "get", "SerialNumber"],
                    capture_output=True, text=True, timeout=5,
                )
                lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
                if len(lines) > 1:
                    return lines[1]
            elif platform.system() == "Darwin":
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"],
                    capture_output=True, text=True, timeout=5,
                )
                for line in result.stdout.splitlines():
                    if "Serial Number" in line:
                        return line.split(":")[-1].strip()
        except Exception as e:
            logger.debug(f"Serial fetch failed: {e}")

        # Fallback: use a stable UUID based on hardware
        return str(uuid.getnode())
