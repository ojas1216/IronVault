"""
Enterprise MDM Desktop Agent
Runs as a system service on Windows/macOS.
Communicates with MDM backend via HTTPS.
"""
import sys
import time
import logging
import platform
import threading
import schedule

from services.api_client import ApiClient
from services.heartbeat import HeartbeatService
from services.location import LocationService
from services.app_monitor import AppMonitor
from services.command_listener import CommandListener
from utils.secure_store import SecureStore
from utils.device_info import DeviceInfo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("mdm_agent.log"),
    ],
)
logger = logging.getLogger("MDMAgent")


class MDMAgent:
    def __init__(self):
        self.api = ApiClient()
        self.heartbeat = HeartbeatService(self.api)
        self.location = LocationService(self.api)
        self.app_monitor = AppMonitor(self.api)
        self.command_listener = CommandListener(self.api)
        self._running = False

    def start(self):
        logger.info(f"MDM Agent starting on {platform.system()} {platform.release()}")

        # Enroll if not already enrolled
        if not SecureStore.get("device_token"):
            logger.info("Device not enrolled. Starting enrollment...")
            if not self._enroll():
                logger.error("Enrollment failed. Exiting.")
                sys.exit(1)

        self._running = True

        # Schedule periodic tasks
        schedule.every(30).seconds.do(self.heartbeat.send)
        schedule.every(5).minutes.do(self.location.send_update)
        schedule.every(1).hours.do(self.app_monitor.sync_usage)

        # Start FCM command listener in background thread
        listener_thread = threading.Thread(
            target=self.command_listener.listen_loop,
            daemon=True,
        )
        listener_thread.start()

        logger.info("MDM Agent running.")

        while self._running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self._running = False
        logger.info("MDM Agent stopped.")

    def _enroll(self) -> bool:
        info = DeviceInfo.collect()
        result = self.api.post("/devices/enroll", {
            "device_name": info["device_name"],
            "employee_name": info.get("employee_name", ""),
            "employee_email": info.get("employee_email", ""),
            "employee_id": info.get("employee_id", ""),
            "department": info.get("department", ""),
            "platform": info["platform"],
            "device_model": info["model"],
            "os_version": info["os_version"],
            "serial_number": info["serial"],
            "enrollment_code": SecureStore.get("enrollment_code") or "",
        })
        if result and "device_token" in result:
            SecureStore.set("device_token", result["device_token"])
            SecureStore.set("device_id", result["device_id"])
            logger.info(f"Enrolled with device ID: {result['device_id']}")
            return True
        return False


def run_as_windows_service():
    """Entry point when running as Windows Service (via pywin32)."""
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    class MDMWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = "CompanyMDMAgent"
        _svc_display_name_ = "Company MDM Security Agent"
        _svc_description_ = "Manages company device security policies"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.agent = MDMAgent()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.agent.stop()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ''),
            )
            self.agent.start()

    win32serviceutil.HandleCommandLine(MDMWindowsService)


def run_as_daemon():
    """Entry point when running as macOS LaunchDaemon or Linux service."""
    agent = MDMAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    if platform.system() == "Windows" and len(sys.argv) > 1:
        run_as_windows_service()
    else:
        run_as_daemon()
