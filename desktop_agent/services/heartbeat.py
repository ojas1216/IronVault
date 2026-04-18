import platform
import socket
import logging
import psutil
from services.security_check import SecurityCheck

logger = logging.getLogger(__name__)


class HeartbeatService:
    def __init__(self, api):
        self.api = api

    def send(self):
        try:
            check = SecurityCheck.run()
            payload = {
                "os_version": f"{platform.system()} {platform.release()}",
                "ip_address": self._get_ip(),
                "network_type": "wifi" if self._is_wifi() else "ethernet",
                "is_rooted": check.get("is_elevated_suspicious", False),
                "agent_version": "1.0.0",
            }
            self.api.post("/devices/heartbeat", payload)
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")

    @staticmethod
    def _get_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "unknown"

    @staticmethod
    def _is_wifi() -> bool:
        try:
            stats = psutil.net_if_stats()
            for name, stat in stats.items():
                if "wi" in name.lower() or "wlan" in name.lower():
                    if stat.isup:
                        return True
        except Exception:
            pass
        return False
