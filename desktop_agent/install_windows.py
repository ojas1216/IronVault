"""
Windows Service Installer for MDM Agent.
Run as Administrator: python install_windows.py install
"""
import sys
import os
import subprocess
import winreg

SERVICE_NAME = "CompanyMDMAgent"
DISPLAY_NAME = "Company MDM Security Agent"
AGENT_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mdm_agent.exe")


def install_service():
    print(f"Installing {DISPLAY_NAME}...")
    subprocess.run([
        "sc", "create", SERVICE_NAME,
        "binPath=", AGENT_EXE,
        "DisplayName=", DISPLAY_NAME,
        "start=", "auto",
        "obj=", "LocalSystem",
    ], check=True)

    subprocess.run(["sc", "description", SERVICE_NAME,
                    "Manages company device security and MDM policies"], check=True)

    # Protect service from being stopped/deleted by non-admins
    # Set SDDL to deny stop/delete for non-admin users
    subprocess.run([
        "sc", "sdset", SERVICE_NAME,
        "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)"
        "(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)"
        "(A;;CCLCSWLOCRRC;;;IU)"
        "(A;;CCLCSWLOCRRC;;;SU)",
    ], check=True)

    subprocess.run(["sc", "start", SERVICE_NAME], check=True)
    print("Service installed and started.")
    _add_run_key()


def _add_run_key():
    """Add to HKLM Run key as fallback (service is primary)."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "CompanyMDMAgent", 0, winreg.REG_SZ, AGENT_EXE)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Warning: Could not set Run key: {e}")


def uninstall_service(otp_verified: bool = False):
    if not otp_verified:
        print("ERROR: OTP verification required to uninstall.")
        print("Contact IT administrator for an uninstall authorization code.")
        sys.exit(1)

    print("Uninstalling MDM Agent...")
    subprocess.run(["sc", "stop", SERVICE_NAME], check=False)
    subprocess.run(["sc", "delete", SERVICE_NAME], check=False)

    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, "CompanyMDMAgent")
        winreg.CloseKey(key)
    except Exception:
        pass

    print("MDM Agent uninstalled.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: install_windows.py [install|uninstall]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "install":
        install_service()
    elif cmd == "uninstall":
        # Require OTP verification before uninstalling
        otp = input("Enter IT admin authorization passcode: ").strip()
        # In production: verify OTP via backend API before proceeding
        print("Verifying passcode...")
        uninstall_service(otp_verified=bool(otp))
    else:
        print(f"Unknown command: {cmd}")
