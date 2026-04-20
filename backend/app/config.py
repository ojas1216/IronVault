from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Enterprise MDM API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str
    ASYNC_DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Firebase (FCM)
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"
    FIREBASE_PROJECT_ID: str

    # APNs (iOS)
    APNS_CERT_PATH: Optional[str] = None
    APNS_KEY_PATH: Optional[str] = None
    APNS_TEAM_ID: Optional[str] = None
    APNS_BUNDLE_ID: str = "com.company.mdmagent"
    APNS_USE_SANDBOX: bool = False

    # OTP
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RATE_LIMIT_WINDOW: int = 900  # 15 minutes lockout

    # Enrollment
    ENROLLMENT_CODE: str = "COMPANY_SECRET_ENROLL_2024"
    ENROLLMENT_TOKEN_EXPIRE_HOURS: int = 24

    # Encryption
    DEVICE_DATA_ENCRYPTION_KEY: str

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://admin.company.com"]

    # Trusted hosts (comma-separated, used by TrustedHostMiddleware)
    ALLOWED_HOSTS: list[str] = ["*"]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
