"""
Polls the backend for pending commands (long-poll or SSE).
Executes commands locally using OS-approved APIs.
"""
import time
import logging
import platform
import subprocess
import sys
from services.api_client import ApiClient
from utils.secure_store import SecureStore

logger = logging.getLogger(__name__)


class CommandListener:
    def __init__(self, api: ApiClient):
        self.api = api
        self.poll_interval = 30  # seconds

    def listen_loop(self):
        while True:
            try:
                self._poll_and_execute()
            except Exception as e:
                logger.debug(f"Command poll error: {e}")
            time.sleep(self.poll_interval)

    def _poll_and_execute(self):
        device_id = SecureStore.get("device_id")
        if not device_id:
            return

        # Get pending commands from backend
        result = self.api.get(f"/devices/{device_id}/pending-commands")
        if not result:
            return

        for cmd in result.get("commands", []):
            self._execute(cmd)

    def _execute(self, cmd: dict):
        cmd_type = cmd.get("command_type")
        cmd_id = cmd.get("id")
        payload = cmd.get("payload", {})

        logger.info(f"Executing command: {cmd_type} ({cmd_id})")

        try:
            if cmd_type == "lock_device":
                self._lock_device()
            elif cmd_type == "remote_uninstall":
                self._handle_uninstall(cmd_id, payload)
            elif cmd_type == "wipe_device":
                self._wipe_device()
            elif cmd_type == "reboot":
                self._reboot()
            elif cmd_type == "collect_logs":
                self._collect_logs(cmd_id)
            else:
                logger.warning(f"Unknown command type: {cmd_type}")
                self._report(cmd_id, "failed", error=f"Unknown: {cmd_type}")
                return

            self._report(cmd_id, "completed")
        except Exception as e:
            self._report(cmd_id, "failed", error=str(e))

    def _lock_device(self):
        if platform.system() == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
        elif platform.system() == "Darwin":
            subprocess.run([
                "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
                "-suspend"
            ], check=True)

    def _handle_uninstall(self, cmd_id: str, payload: dict):
        """
        Uninstall requires OTP. On desktop, show a system dialog.
        The user must enter the OTP provided by admin.
        """
        otp_id = payload.get("otp_id")
        if not otp_id:
            raise ValueError("Missing OTP ID for uninstall command")

        # Show OTP input dialog (GUI)
        otp_code = self._prompt_otp()
        if not otp_code:
            raise ValueError("User cancelled OTP entry")

        # Verify OTP with backend
        device_id = SecureStore.get("device_id")
        result = self.api.post("/commands/verify-otp", {
            "otp_id": otp_id,
            "otp_code": otp_code,
            "device_id": device_id,
        })

        if result and result.get("verified"):
            logger.info("OTP verified. Proceeding with authorized uninstall.")
            self._uninstall_self()
        else:
            raise ValueError("OTP verification failed")

    def _prompt_otp(self) -> str | None:
        """Show a simple OTP dialog using tkinter."""
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            code = simpledialog.askstring(
                "Admin Authorization Required",
                "Admin authorization is required to uninstall.\n\n"
                "Enter the 6-digit passcode provided by your IT administrator:",
                parent=root,
            )
            root.destroy()
            return code
        except Exception:
            return None

    def _uninstall_self(self):
        """Uninstall the agent using OS-standard uninstall mechanism."""
        if platform.system() == "Windows":
            # Remove Windows service, then run uninstaller
            subprocess.Popen(["sc", "delete", "CompanyMDMAgent"])
        elif platform.system() == "Darwin":
            # Remove LaunchDaemon
            subprocess.Popen([
                "launchctl", "unload",
                "/Library/LaunchDaemons/com.company.mdmagent.plist"
            ])
        SecureStore.clear_all()

    def _wipe_device(self):
        """Reset device to factory defaults — admin-only, high-privilege."""
        if platform.system() == "Windows":
            subprocess.run(
                ["systemreset", "-factoryreset"],
                check=True,
            )
        elif platform.system() == "Darwin":
            subprocess.run(
                ["eraseinstall", "--confirm"],
                check=True,
            )

    def _reboot(self):
        if platform.system() == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "30", "/c", "IT admin reboot"])
        elif platform.system() == "Darwin":
            subprocess.run(["shutdown", "-r", "+1"])

    def _collect_logs(self, cmd_id: str):
        # Collect agent logs and send to backend
        pass

    def _report(self, cmd_id: str, status: str, error: str | None = None):
        self.api.post("/devices/command-result", {
            "command_id": cmd_id,
            "status": status,
            **({"error_message": error} if error else {}),
        })
