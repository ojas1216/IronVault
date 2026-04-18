"""
Shared pytest fixtures for all backend tests.
Uses SQLite in-memory so no PostgreSQL needed to run tests.
Firebase and Redis are mocked.
"""
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# ─── Set env vars BEFORE importing the app ────────────────────────────────────
os.environ.setdefault("SECRET_KEY", "testsecretkey1234567890abcdef1234567890abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_CREDENTIALS_PATH", "nonexistent.json")
os.environ.setdefault("DEVICE_DATA_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdA==")

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.device import Device, DevicePlatform, DeviceStatus
from app.utils.security import hash_password, create_access_token
from app.config import get_settings as _get_settings
from datetime import timedelta, datetime, timezone
from jose import jwt as _jwt

# ─── In-memory SQLite engine ──────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Override DB dependency ───────────────────────────────────────────────────
async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

app.dependency_overrides[get_db] = override_get_db


# ─── Create / drop tables around each test session ───────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ─── Fresh DB session per test ────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
        # Clean all tables after each test
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


# ─── HTTP client ──────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── Admin user fixture ───────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def admin_user(db):
    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("testpassword123"),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(admin_user):
    return create_access_token({
        "sub": str(admin_user.id),
        "role": admin_user.role.value,
        "type": "access",
    })


@pytest_asyncio.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ─── Device fixture ───────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def enrolled_device(db):
    device = Device(
        device_name="Test Android Device",
        employee_name="John Doe",
        employee_email="john@company.com",
        department="Engineering",
        platform=DevicePlatform.ANDROID,
        os_version="Android 14",
        agent_version="1.0.0",
        device_model="Pixel 7",
        serial_number="SN123456",
        status=DeviceStatus.ACTIVE,
        is_online=True,
        is_uninstall_blocked=True,
        push_token="fcm_test_token_xyz",
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@pytest_asyncio.fixture
def device_token(enrolled_device):
    _settings = _get_settings()
    payload = {
        "sub": str(enrolled_device.id),
        "type": "device",
        "platform": "android",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return _jwt.encode(payload, _settings.SECRET_KEY, algorithm=_settings.ALGORITHM)


# ─── Mock Firebase ────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_firebase():
    with patch("app.services.push_service.messaging") as mock_msg, \
         patch("app.services.push_service.init_firebase"):
        mock_msg.send = MagicMock(return_value="projects/test/messages/12345")
        yield mock_msg


# ─── Mock Redis ───────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_redis():
    store = {}

    mock_r = MagicMock()
    mock_r.get = AsyncMock(side_effect=lambda k: store.get(k))
    mock_r.set = AsyncMock(side_effect=lambda k, v, ex=None: store.update({k: v}))
    mock_r.setex = AsyncMock(side_effect=lambda k, t, v: store.update({k: v}))
    mock_r.delete = AsyncMock(side_effect=lambda k: store.pop(k, None))
    mock_r.ttl = AsyncMock(return_value=60)
    mock_r.expire = AsyncMock(return_value=True)

    # pipeline mock
    pipe = MagicMock()
    pipe.incr = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)

    async def _exec():
        key = list(store.keys())[-1] if store else "k"
        val = store.get(key, 0)
        if isinstance(val, int):
            store[key] = val + 1
        return [store.get(key, 1), True]

    pipe.execute = _exec
    mock_r.pipeline = MagicMock(return_value=pipe)

    with patch("app.utils.rate_limiter.get_redis", new=AsyncMock(return_value=mock_r)):
        yield mock_r
