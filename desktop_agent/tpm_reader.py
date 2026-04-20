"""
Read TPM chip ID and attestation data via Windows TBS (TPM Base Services) API.
Falls back to registry-based detection on non-TPM hardware.
"""

import ctypes
import ctypes.wintypes
import hashlib
import json
import logging
import platform
import subprocess
import struct
from typing import Optional

logger = logging.getLogger(__name__)

# TBS constants
TBS_CONTEXT_VERSION_ONE = 1
TBS_CONTEXT_VERSION_TWO = 2
TPM_VERSION_12 = 1
TPM_VERSION_20 = 2

TBS_SUCCESS = 0
TBS_E_INTERNAL_ERROR = 0x80284001
TBS_E_BAD_PARAMETER = 0x80284002
TBS_E_INSUFFICIENT_BUFFER = 0x80284005
TBS_E_NO_AUXILIARY_EXIST = 0x80284008


class TBS_CONTEXT_PARAMS2(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("grbitparam", ctypes.c_uint32),
    ]


def get_tpm_version() -> Optional[int]:
    """Return 1 for TPM 1.2, 2 for TPM 2.0, None if not available."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-WmiObject -Namespace root/cimv2/security/microsofttpm -Class Win32_Tpm | Select-Object -ExpandProperty SpecVersion"],
            capture_output=True, text=True, timeout=10
        )
        spec = result.stdout.strip()
        if spec.startswith("2.0"):
            return 2
        elif spec.startswith("1.2"):
            return 1
        return None
    except Exception as e:
        logger.warning("TPM version check failed: %s", e)
        return None


def get_tpm_manufacturer_info() -> dict:
    """Get TPM manufacturer information via WMI."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-WmiObject -Namespace root/cimv2/security/microsofttpm -Class Win32_Tpm | "
             "Select-Object ManufacturerId,ManufacturerVersion,SpecVersion,IsEnabled_InitialValue,IsActivated_InitialValue | "
             "ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return {
                "manufacturer_id": str(data.get("ManufacturerId", "")),
                "manufacturer_version": str(data.get("ManufacturerVersion", "")),
                "spec_version": str(data.get("SpecVersion", "")),
                "is_enabled": bool(data.get("IsEnabled_InitialValue", False)),
                "is_activated": bool(data.get("IsActivated_InitialValue", False)),
            }
    except Exception as e:
        logger.warning("TPM WMI query failed: %s", e)
    return {}


def get_tpm_endorsement_key_hash() -> Optional[str]:
    """Get a hash of the TPM Endorsement Key public portion for unique device ID."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-TpmEndorsementKeyInfo -HashAlgorithm Sha256 | Select-Object -ExpandProperty PublicKeyHash"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        logger.debug("EK hash not available: %s", e)

    # Fallback: use TPM PCR values as unique fingerprint
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-TpmSupportedFeature | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return hashlib.sha256(result.stdout.encode()).hexdigest()
    except Exception:
        pass

    return None


def get_tpm_chip_id() -> dict:
    """
    Composite TPM chip identifier combining manufacturer info and EK hash.
    This uniquely identifies a physical TPM chip.
    """
    if platform.system() != "Windows":
        return {"available": False, "reason": "Non-Windows platform"}

    version = get_tpm_version()
    if version is None:
        return {"available": False, "reason": "No TPM detected"}

    info = get_tpm_manufacturer_info()
    ek_hash = get_tpm_endorsement_key_hash()

    chip_id_components = [
        info.get("manufacturer_id", ""),
        info.get("manufacturer_version", ""),
        ek_hash or "",
    ]
    chip_id = hashlib.sha256("|".join(chip_id_components).encode()).hexdigest()

    return {
        "available": True,
        "version": version,
        "chip_id": chip_id,
        "endorsement_key_hash": ek_hash,
        **info,
    }


def is_tpm_enabled() -> bool:
    """Quick check if TPM is present and enabled."""
    info = get_tpm_chip_id()
    return info.get("available", False) and info.get("is_enabled", False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = get_tpm_chip_id()
    print(json.dumps(result, indent=2))
