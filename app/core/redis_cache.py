
import redis.asyncio as redis
import json
import os
from typing import Any, Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")

class RedisCache:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        if not self.redis:
            self.redis = await redis.from_url(REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            await self.connect()
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, expire: int = 3600):
        if not self.redis:
            await self.connect()
        await self.redis.set(key, json.dumps(value), ex=expire)

    async def delete(self, key: str):
        if not self.redis:
            await self.connect()
        await self.redis.delete(key)

    async def close(self):
        if self.redis:
            await self.redis.close()

cache = RedisCache()
