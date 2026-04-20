"""
Challenge-response hardware authentication.
Backend issues a cryptographic challenge; device proves possession of its
golden hardware fingerprint without transmitting it in plaintext.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Optional

logger = logging.getLogger(__name__)

CHALLENGE_TTL_SECONDS = 300  # Challenges expire after 5 minutes
CHALLENGE_STORE: dict[str, dict] = {}  # In production: use Redis


def generate_challenge(device_id: str) -> dict:
    """
    Issue a time-limited nonce challenge to a device.
    The device must respond with HMAC(nonce, golden_fingerprint).
    """
    nonce = secrets.token_hex(32)
    issued_at = int(time.time())

    CHALLENGE_STORE[device_id] = {
        "nonce": nonce,
        "issued_at": issued_at,
        "expires_at": issued_at + CHALLENGE_TTL_SECONDS,
    }

    return {
        "device_id": device_id,
        "nonce": nonce,
        "expires_at": issued_at + CHALLENGE_TTL_SECONDS,
        "algorithm": "HMAC-SHA256",
        "instructions": "Respond with HMAC-SHA256(nonce, hardware_fingerprint)",
    }


def verify_challenge_response(
    device_id: str,
    response: str,
    golden_fingerprint: str,
) -> dict:
    """
    Verify the device's challenge response.
    Expected response = HMAC-SHA256(nonce, golden_hardware_fingerprint).
    """
    challenge = CHALLENGE_STORE.get(device_id)
    if not challenge:
        return {"verified": False, "reason": "No active challenge for this device"}

    now = int(time.time())
    if now > challenge["expires_at"]:
        del CHALLENGE_STORE[device_id]
        return {"verified": False, "reason": "Challenge expired"}

    nonce = challenge["nonce"]
    expected = compute_response(nonce, golden_fingerprint)

    # Constant-time comparison
    is_valid = hmac.compare_digest(expected.lower(), response.lower())

    # Invalidate challenge after use (prevent replay)
    del CHALLENGE_STORE[device_id]

    if is_valid:
        return {
            "verified": True,
            "device_id": device_id,
            "authenticated_at": now,
        }
    else:
        return {
            "verified": False,
            "reason": "Response does not match — hardware fingerprint mismatch",
            "action": "FLAG_DEVICE",
        }


def compute_response(nonce: str, hardware_fingerprint: str) -> str:
    """
    Client-side: compute the expected challenge response.
    Called on the device to generate the proof.
    """
    return hmac.new(
        hardware_fingerprint.encode(),
        nonce.encode(),
        hashlib.sha256,
    ).hexdigest()


def authenticate_device(
    device_id: str,
    hardware_fingerprint: str,
    backend_url: Optional[str] = None,
) -> dict:
    """
    Full client-side authentication flow.
    1. Request challenge from backend
    2. Compute HMAC response using local hardware fingerprint
    3. Submit response for verification

    In production this calls the backend API. Here it self-verifies for testing.
    """
    # Step 1: Get challenge
    challenge = generate_challenge(device_id)
    nonce = challenge["nonce"]

    # Step 2: Compute response
    response = compute_response(nonce, hardware_fingerprint)

    # Step 3: Verify (in production: POST to backend)
    result = verify_challenge_response(device_id, response, hardware_fingerprint)

    return {
        "device_id": device_id,
        "authenticated": result["verified"],
        "reason": result.get("reason"),
        "timestamp": int(time.time()),
    }


def batch_authenticate_devices(device_fingerprints: dict[str, str]) -> list[dict]:
    """
    Authenticate multiple devices in a manufacturing/audit scenario.
    device_fingerprints: {device_id: golden_fingerprint}
    """
    results = []
    for device_id, fingerprint in device_fingerprints.items():
        auth_result = authenticate_device(device_id, fingerprint)
        results.append(auth_result)
        if not auth_result["authenticated"]:
            logger.warning("Device %s failed authentication: %s", device_id, auth_result.get("reason"))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_device_id = "test-device-001"
    test_fingerprint = hashlib.sha256(b"test-golden-fingerprint").hexdigest()

    print("=== Remote Hardware Authentication Test ===\n")
    result = authenticate_device(test_device_id, test_fingerprint)
    print(json.dumps(result, indent=2))

    print("\n=== Tamper Simulation (wrong fingerprint) ===\n")
    challenge = generate_challenge(test_device_id)
    wrong_response = compute_response(challenge["nonce"], "tampered-fingerprint-value")
    verify_result = verify_challenge_response(test_device_id, wrong_response, test_fingerprint)
    print(json.dumps(verify_result, indent=2))
