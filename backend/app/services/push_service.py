import json
import logging
from typing import Optional
import firebase_admin
from firebase_admin import credentials, messaging
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_firebase_initialized = False


def init_firebase():
    global _firebase_initialized
    if not _firebase_initialized:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.error(f"Firebase init failed: {e}")


async def send_fcm_command(
    device_token: str,
    command_type: str,
    command_id: str,
    payload: Optional[dict] = None,
) -> dict:
    """Send command to Android/Windows device via FCM."""
    init_firebase()

    data = {
        "command_type": command_type,
        "command_id": command_id,
        "payload": json.dumps(payload or {}),
    }

    message = messaging.Message(
        data=data,
        token=device_token,
        android=messaging.AndroidConfig(
            priority="high",
            ttl=3600,
        ),
    )

    try:
        response = messaging.send(message)
        logger.info(f"FCM sent: {response}")
        return {"success": True, "message_id": response}
    except messaging.UnregisteredError:
        return {"success": False, "error": "device_unregistered"}
    except Exception as e:
        logger.error(f"FCM send failed: {e}")
        return {"success": False, "error": str(e)}


async def send_apns_command(
    device_token: str,
    command_type: str,
    command_id: str,
    payload: Optional[dict] = None,
) -> dict:
    """Send MDM command to iOS device via APNs."""
    try:
        from apns2.client import APNsClient
        from apns2.payload import Payload
        from apns2.credentials import TokenCredentials

        token_credentials = TokenCredentials(
            auth_key_path=settings.APNS_KEY_PATH,
            auth_key_id=settings.APNS_KEY_PATH.split("/")[-1].replace(".p8", ""),
            team_id=settings.APNS_TEAM_ID,
        )
        client = APNsClient(
            credentials=token_credentials,
            use_sandbox=settings.APNS_USE_SANDBOX,
        )

        # MDM push payload (empty body triggers device to check MDM server)
        push_payload = Payload(
            custom={
                "mdm": command_id,
                "command_type": command_type,
            }
        )

        client.send_notification(device_token, push_payload, topic=settings.APNS_BUNDLE_ID)
        return {"success": True}
    except Exception as e:
        logger.error(f"APNs send failed: {e}")
        return {"success": False, "error": str(e)}


async def send_command_to_device(
    platform: str,
    push_token: str,
    command_type: str,
    command_id: str,
    payload: Optional[dict] = None,
) -> dict:
    if platform in ("android", "windows", "macos"):
        return await send_fcm_command(push_token, command_type, command_id, payload)
    elif platform == "ios":
        return await send_apns_command(push_token, command_type, command_id, payload)
    else:
        return {"success": False, "error": f"Unknown platform: {platform}"}
