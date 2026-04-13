from __future__ import annotations

import json
from typing import Any, Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

_redis: Optional[Redis] = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def get_cache(key: str) -> Optional[str]:
    try:
        return await get_redis().get(key)
    except RedisError:
        return None


async def set_cache(key: str, value: str, ttl: int = 3600) -> None:
    try:
        await get_redis().set(key, value, ex=ttl)
    except RedisError:
        return None


async def cache_json(key: str, value: Any, ttl: int = 3600) -> None:
    await set_cache(key, json.dumps(value), ttl=ttl)


async def increment_rate_limit(key: str, ttl: int = 60) -> int:
    try:
        redis = get_redis()
        value = await redis.incr(key)
        if value == 1:
            await redis.expire(key, ttl)
        return int(value)
    except RedisError:
        return 1

