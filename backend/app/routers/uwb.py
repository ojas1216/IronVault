from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.routers.dependencies import verify_device_token, require_role
from app.models.user import UserRole
from app.models.uwb_session import UWBRangingPoint

router = APIRouter(prefix="/uwb", tags=["UWB Tracking"])


class RangingPoint(BaseModel):
    device_id: str
    distance_meters: Optional[float] = None
    azimuth_degrees: Optional[float] = None
    elevation_degrees: Optional[float] = None
    rssi: Optional[int] = None
    mode: str = "uwb"
    anchor_id: Optional[str] = None
    timestamp: Optional[str] = None


@router.post("/ranging")
async def record_ranging(
    body: RangingPoint,
    device_payload: dict = Depends(verify_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Device streams ranging data to backend for live tracking."""
    device_id = UUID(device_payload["sub"])
    now = datetime.now(timezone.utc)

    point = UWBRangingPoint(
        device_id=device_id,
        mode=body.mode,
        distance_meters=body.distance_meters,
        azimuth_degrees=body.azimuth_degrees,
        elevation_degrees=body.elevation_degrees,
        rssi=body.rssi,
        anchor_id=body.anchor_id,
        recorded_at=now,
    )
    db.add(point)
    return {"status": "recorded"}


@router.get("/{device_id}/live", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def get_live_ranging(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get most recent ranging point for a device."""
    result = await db.execute(
        select(UWBRangingPoint)
        .where(UWBRangingPoint.device_id == device_id)
        .order_by(desc(UWBRangingPoint.recorded_at))
        .limit(1)
    )
    point = result.scalar_one_or_none()
    if not point:
        return {"distance_meters": None, "mode": "no_data"}
    return {
        "distance_meters": point.distance_meters,
        "azimuth_degrees": point.azimuth_degrees,
        "elevation_degrees": point.elevation_degrees,
        "rssi": point.rssi,
        "mode": point.mode,
        "recorded_at": point.recorded_at,
    }


@router.get("/{device_id}/history", dependencies=[Depends(require_role(UserRole.VIEWER))])
async def get_ranging_history(
    device_id: UUID,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UWBRangingPoint)
        .where(UWBRangingPoint.device_id == device_id)
        .order_by(desc(UWBRangingPoint.recorded_at))
        .limit(limit)
    )
    points = result.scalars().all()
    return [
        {
            "distance_meters": p.distance_meters,
            "azimuth_degrees": p.azimuth_degrees,
            "mode": p.mode,
            "recorded_at": p.recorded_at,
        }
        for p in points
    ]
