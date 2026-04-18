import time
import asyncio
from typing import Any, Dict, Optional

class AsyncCache:
    """
    Simple In-Memory TTL Cache for Async operations.
    Perfect for 512MB RAM environments where Redis might be overkill.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._events: Dict[str, asyncio.Event] = {}

    async def get_or_fetch(self, key: str, fetch_func, ttl: int = 3600, *args, **kwargs) -> Any:
        """
        Retrieves a value from the cache. If it doesn't exist, it calls fetch_func to get the value.
        Protects against cache stampede by ensuring only one concurrent request calls fetch_func for a given key.
        """
        async with self._lock:
            if key in self._cache:
                item = self._cache[key]
                if item["expiry"] > time.time():
                    return item["value"]
                else:
                    del self._cache[key]
            
            if key in self._events:
                event = self._events[key]
                is_fetcher = False
            else:
                event = asyncio.Event()
                self._events[key] = event
                is_fetcher = True

        if is_fetcher:
            try:
                value = await fetch_func(*args, **kwargs)
                if value is not None:
                    await self.set(key, value, ttl)
                return value
            finally:
                async with self._lock:
                    event.set()
                    if key in self._events:
                        del self._events[key]
        else:
            await event.wait()
            return await self.get(key)

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                item = self._cache[key]
                if item["expiry"] > time.time():
                    return item["value"]
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expiry": time.time() + ttl
            }

    async def delete(self, key: str):
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear_expired(self):
        """Background task to keep memory clean."""
        while True:
            async with self._lock:
                now = time.time()
                keys_to_del = [k for k, v in self._cache.items() if v["expiry"] <= now]
                for k in keys_to_del:
                    del self._cache[k]
            await asyncio.sleep(300) # Every 5 mins

cache_service = AsyncCache()
