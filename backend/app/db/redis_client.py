from __future__ import annotations

import json
import asyncio
from typing import Any, Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

_redis: Optional[Redis] = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            retry_on_timeout=False,
        )
    return _redis


async def get_cache(key: str) -> Optional[str]:
    try:
        return await asyncio.wait_for(get_redis().get(key), timeout=0.3)
    except (RedisError, TimeoutError, asyncio.TimeoutError):
        return None


async def set_cache(key: str, value: str, ttl: int = 3600) -> None:
    try:
        await asyncio.wait_for(get_redis().set(key, value, ex=ttl), timeout=0.3)
    except (RedisError, TimeoutError, asyncio.TimeoutError):
        return None


async def cache_json(key: str, value: Any, ttl: int = 3600) -> None:
    await set_cache(key, json.dumps(value), ttl=ttl)


async def increment_rate_limit(key: str, ttl: int = 60) -> int:
    try:
        redis = get_redis()
        value = await asyncio.wait_for(redis.incr(key), timeout=0.3)
        if value == 1:
            await asyncio.wait_for(redis.expire(key, ttl), timeout=0.3)
        return int(value)
    except (RedisError, TimeoutError, asyncio.TimeoutError):
        return 1

