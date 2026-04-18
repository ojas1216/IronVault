import platform
import logging
import psutil
from datetime import datetime

logger = logging.getLogger(__name__)

# Apps considered work-related
WORK_APP_KEYWORDS = {
    "chrome", "firefox", "edge", "teams", "zoom", "slack",
    "outlook", "word", "excel", "powerpoint", "code", "pycharm",
    "intellij", "webstorm", "terminal", "cmd", "powershell",
}

NON_WORK_APP_KEYWORDS = {
    "youtube", "netflix", "spotify", "steam", "game", "discord",
    "whatsapp", "telegram", "instagram", "facebook", "tiktok",
    "vlc", "torrent",
}


class AppMonitor:
    def __init__(self, api):
        self.api = api
        self._usage: dict[str, int] = {}
        self._last_process: str | None = None
        self._last_tick = datetime.now()

    def tick(self):
        """Call every second to track active process."""
        now = datetime.now()
        elapsed = (now - self._last_tick).seconds
        self._last_tick = now

        active = self._get_active_process()
        if active and self._last_process == active:
            self._usage[active] = self._usage.get(active, 0) + elapsed
        self._last_process = active

    def sync_usage(self):
        if not self._usage:
            return
        logs = []
        for app_name, seconds in self._usage.items():
            if seconds < 5:
                continue
            logs.append({
                "app_package": app_name.lower(),
                "app_name": app_name,
                "usage_duration_seconds": seconds,
                "is_work_app": self._is_work_app(app_name),
                "date": datetime.utcnow().isoformat(),
            })
        if logs:
            self.api.post("/devices/app-usage", {"logs": logs})
        self._usage.clear()

    @staticmethod
    def _get_active_process() -> str | None:
        if platform.system() == "Windows":
            try:
                import win32gui
                import win32process
                hwnd = win32gui.GetForegroundWindow()
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                return proc.name().replace(".exe", "")
            except Exception:
                pass
        elif platform.system() == "Darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to get name of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=2
                )
                return result.stdout.strip()
            except Exception:
                pass
        return None

    @staticmethod
    def _is_work_app(name: str) -> bool:
        name_lower = name.lower()
        return any(kw in name_lower for kw in WORK_APP_KEYWORDS)
