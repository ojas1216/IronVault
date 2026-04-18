"""
Secure credential storage using OS keychain:
- Windows: Windows Credential Manager (via keyring)
- macOS: Keychain Access (via keyring)
"""
import keyring
import logging

logger = logging.getLogger(__name__)

SERVICE_NAME = "CompanyMDMAgent"


class SecureStore:
    @staticmethod
    def set(key: str, value: str):
        try:
            keyring.set_password(SERVICE_NAME, key, value)
        except Exception as e:
            logger.error(f"SecureStore.set failed for {key}: {e}")

    @staticmethod
    def get(key: str) -> str | None:
        try:
            return keyring.get_password(SERVICE_NAME, key)
        except Exception as e:
            logger.error(f"SecureStore.get failed for {key}: {e}")
            return None

    @staticmethod
    def delete(key: str):
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except Exception:
            pass

    @staticmethod
    def clear_all():
        for key in ("device_token", "device_id", "enrollment_token", "enrollment_code"):
            SecureStore.delete(key)
