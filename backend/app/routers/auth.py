from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, CreateAdminRequest
from app.services import auth_service
from app.models.user import UserRole
from app.routers.dependencies import require_role

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    return await auth_service.login(db, body.email, body.password, ip)


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    return await auth_service.refresh_access_token(body.refresh_token)


@router.post("/admin/create", dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))])
async def create_admin(
    body: CreateAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.SUPER_ADMIN)),
):
    user = await auth_service.create_admin_user(
        db, body.email, body.full_name, body.password,
        role=UserRole(body.role),
    )
    return {"id": str(user.id), "email": user.email, "role": user.role}
