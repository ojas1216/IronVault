import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()
_redis: aioredis.Redis = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def check_otp_rate_limit(device_id: str) -> tuple[bool, int]:
    """Returns (is_allowed, attempts_remaining)."""
    redis = await get_redis()
    key = f"otp_attempts:{device_id}"
    attempts = await redis.get(key)
    attempts = int(attempts) if attempts else 0

    if attempts >= settings.OTP_MAX_ATTEMPTS:
        ttl = await redis.ttl(key)
        return False, ttl

    return True, settings.OTP_MAX_ATTEMPTS - attempts


async def increment_otp_attempts(device_id: str) -> int:
    redis = await get_redis()
    key = f"otp_attempts:{device_id}"
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.OTP_RATE_LIMIT_WINDOW)
    results = await pipe.execute()
    return results[0]


async def reset_otp_attempts(device_id: str):
    redis = await get_redis()
    await redis.delete(f"otp_attempts:{device_id}")


async def cache_set(key: str, value: str, ttl: int):
    redis = await get_redis()
    await redis.set(key, value, ex=ttl)


async def cache_get(key: str) -> str | None:
    redis = await get_redis()
    return await redis.get(key)


async def cache_delete(key: str):
    redis = await get_redis()
    await redis.delete(key)
