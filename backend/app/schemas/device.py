from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class DeviceRegisterRequest(BaseModel):
    device_name: str
    employee_name: str
    employee_email: EmailStr
    employee_id: Optional[str] = None
    department: Optional[str] = None
    platform: str  # android | ios | windows | macos
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    serial_number: Optional[str] = None
    push_token: Optional[str] = None
    agent_version: Optional[str] = None
    enrollment_code: str  # Company enrollment code required
    # Hardware identity — sent at enrollment for golden fingerprint
    android_id: Optional[str] = None
    hardware_fingerprint: Optional[str] = None
    baseboard_serial: Optional[str] = None
    bios_uuid: Optional[str] = None
    tpm_chip_id: Optional[str] = None
    imei1: Optional[str] = None
    imei2: Optional[str] = None


class DeviceHeartbeatRequest(BaseModel):
    push_token: Optional[str] = None
    ip_address: Optional[str] = None
    is_rooted: bool = False
    network_type: Optional[str] = None
    os_version: Optional[str] = None
    agent_version: Optional[str] = None
    battery_level: Optional[int] = None
    is_screen_on: Optional[bool] = None
    # Hardware identity — sent periodically for resale detection
    hardware_fingerprint: Optional[str] = None
    baseboard_serial: Optional[str] = None
    bios_uuid: Optional[str] = None
    firmware_fingerprint: Optional[str] = None


class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    address: Optional[str] = None
    recorded_at: Optional[datetime] = None


class AppUsageEntry(BaseModel):
    app_package: str
    app_name: Optional[str] = None
    usage_duration_seconds: int
    is_work_app: bool = False
    date: Optional[datetime] = None


class AppUsageBatchRequest(BaseModel):
    logs: list[AppUsageEntry]


class CommandResultRequest(BaseModel):
    command_id: UUID
    status: str  # completed | failed
    result: Optional[dict] = None
    error_message: Optional[str] = None


class DeviceResponse(BaseModel):
    id: UUID
    device_name: str
    employee_name: str
    employee_email: str
    platform: str
    status: str
    is_online: bool
    last_seen: Optional[datetime]
    last_latitude: Optional[float]
    last_longitude: Optional[float]
    is_rooted: bool
    is_uninstall_blocked: bool
    agent_version: Optional[str]
    department: Optional[str]

    class Config:
        from_attributes = True
