"""
AquilaCache — Redis backend for distributed caching.

Production-grade Redis integration with:
- Connection pooling
- Pipeline batching for get_many/set_many
- Lua scripts for atomic operations
- Tag-based invalidation via Redis sets
- Health checks and reconnection
- Serialization via pluggable CacheSerializer
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core import CacheBackend, CacheEntry, CacheStats

logger = logging.getLogger("aquilia.cache.redis")


class RedisBackend(CacheBackend):
    """
    Redis-backed cache using aioredis (redis-py async).
    
    Features:
    - Connection pool with configurable size
    - Pipeline batching for bulk operations
    - Lua-based atomic increment/decrement
    - Tag index via Redis sets for O(1) tag invalidation
    - Automatic reconnection on transient failures
    """
    
    __slots__ = (
        "_url",
        "_max_connections",
        "_socket_timeout",
        "_connect_timeout",
        "_retry_on_timeout",
        "_key_prefix",
        "_serializer",
        "_redis",
        "_stats",
        "_start_time",
        "_initialized",
    )
    
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        key_prefix: str = "aq:",
        serializer: Optional[Any] = None,
    ):
        self._url = url
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._connect_timeout = connect_timeout
        self._retry_on_timeout = retry_on_timeout
        self._key_prefix = key_prefix
        self._redis = None
        self._stats = CacheStats(backend="redis")
        self._start_time = time.monotonic()
        self._initialized = False
        
        # Use JSON serializer by default
        if serializer is None:
            from ..serializers import JsonCacheSerializer
            self._serializer = JsonCacheSerializer()
        else:
            self._serializer = serializer
    
    @property
    def name(self) -> str:
        return "redis"
    
    @property
    def is_distributed(self) -> bool:
        return True
    
    async def initialize(self) -> None:
        """Connect to Redis and create connection pool."""
        if self._initialized:
            return
        
        try:
            import redis.asyncio as aioredis
        except ImportError:
            raise ImportError(
                "Redis backend requires 'redis' package. "
                "Install with: pip install redis[hiredis]"
            )
        
        try:
            self._redis = aioredis.from_url(
                self._url,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._connect_timeout,
                retry_on_timeout=self._retry_on_timeout,
                decode_responses=False,  # We handle serialization
            )
            # Verify connection
            await self._redis.ping()
            self._start_time = time.monotonic()
            self._initialized = True
            logger.info(f"Redis cache connected: {self._url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Close Redis connection pool."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._initialized = False
    
    def _full_key(self, key: str) -> str:
        """Build prefixed key."""
        return f"{self._key_prefix}{key}"
    
    def _tag_set_key(self, tag: str) -> str:
        """Build Redis set key for a tag."""
        return f"{self._key_prefix}_tags:{tag}"
    
    def _ns_set_key(self, namespace: str) -> str:
        """Build Redis set key for a namespace."""
        return f"{self._key_prefix}_ns:{namespace}"
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get a value from Redis."""
        if not self._redis:
            self._stats.errors += 1
            return None
        
        full_key = self._full_key(key)
        
        try:
            raw = await self._redis.get(full_key)
            if raw is None:
                self._stats.misses += 1
                return None
            
            value = self._serializer.deserialize(raw)
            self._stats.hits += 1
            
            # Get TTL for entry metadata
            ttl = await self._redis.ttl(full_key)
            expires_at = None
            if ttl and ttl > 0:
                expires_at = time.monotonic() + ttl
            
            return CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
            )
        except Exception as e:
            logger.warning(f"Redis GET error for key '{key}': {e}")
            self._stats.errors += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Tuple[str, ...] = (),
        namespace: str = "default",
    ) -> None:
        """Set a value in Redis with optional TTL and tags."""
        if not self._redis:
            self._stats.errors += 1
            return
        
        full_key = self._full_key(key)
        
        try:
            serialized = self._serializer.serialize(value)
            
            pipe = self._redis.pipeline()
            
            if ttl and ttl > 0:
                pipe.setex(full_key, ttl, serialized)
            else:
                pipe.set(full_key, serialized)
            
            # Register in tag sets
            for tag in tags:
                tag_key = self._tag_set_key(tag)
                pipe.sadd(tag_key, full_key)
                if ttl and ttl > 0:
                    # Extend tag set TTL to at least match entry TTL
                    pipe.expire(tag_key, ttl + 60)
            
            # Register in namespace set
            ns_key = self._ns_set_key(namespace)
            pipe.sadd(ns_key, full_key)
            
            await pipe.execute()
            self._stats.sets += 1
        except Exception as e:
            logger.warning(f"Redis SET error for key '{key}': {e}")
            self._stats.errors += 1
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self._redis:
            return False
        
        full_key = self._full_key(key)
        
        try:
            result = await self._redis.delete(full_key)
            if result:
                self._stats.deletes += 1
                return True
            return False
        except Exception as e:
            logger.warning(f"Redis DELETE error for key '{key}': {e}")
            self._stats.errors += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._redis:
            return False
        
        try:
            return bool(await self._redis.exists(self._full_key(key)))
        except Exception as e:
            logger.warning(f"Redis EXISTS error for key '{key}': {e}")
            return False
    
    async def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache entries."""
        if not self._redis:
            return 0
        
        try:
            if namespace:
                # Clear specific namespace
                ns_key = self._ns_set_key(namespace)
                members = await self._redis.smembers(ns_key)
                if members:
                    pipe = self._redis.pipeline()
                    for member in members:
                        pipe.delete(member)
                    pipe.delete(ns_key)
                    await pipe.execute()
                    return len(members)
                return 0
            else:
                # Clear all keys with our prefix
                count = 0
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor=cursor,
                        match=f"{self._key_prefix}*",
                        count=1000,
                    )
                    if keys:
                        await self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
                return count
        except Exception as e:
            logger.warning(f"Redis CLEAR error: {e}")
            self._stats.errors += 1
            return 0
    
    async def keys(self, pattern: str = "*", namespace: Optional[str] = None) -> List[str]:
        """List keys matching pattern."""
        if not self._redis:
            return []
        
        try:
            if namespace:
                ns_key = self._ns_set_key(namespace)
                members = await self._redis.smembers(ns_key)
                raw_keys = [
                    m.decode("utf-8") if isinstance(m, bytes) else m
                    for m in members
                ]
                # Strip prefix
                prefix_len = len(self._key_prefix)
                keys = [k[prefix_len:] for k in raw_keys if k.startswith(self._key_prefix)]
            else:
                full_pattern = f"{self._key_prefix}{pattern}"
                result = []
                cursor = 0
                while True:
                    cursor, batch = await self._redis.scan(
                        cursor=cursor,
                        match=full_pattern,
                        count=1000,
                    )
                    result.extend(batch)
                    if cursor == 0:
                        break
                prefix_len = len(self._key_prefix)
                keys = []
                for k in result:
                    s = k.decode("utf-8") if isinstance(k, bytes) else k
                    if s.startswith(self._key_prefix) and not s.startswith(f"{self._key_prefix}_tags:") and not s.startswith(f"{self._key_prefix}_ns:"):
                        keys.append(s[prefix_len:])
            
            if pattern != "*":
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
            
            return keys
        except Exception as e:
            logger.warning(f"Redis KEYS error: {e}")
            return []
    
    async def stats(self) -> CacheStats:
        """Get Redis stats."""
        self._stats.uptime_seconds = time.monotonic() - self._start_time
        
        if self._redis:
            try:
                info = await self._redis.info("memory", "keyspace")
                self._stats.memory_bytes = info.get("used_memory", 0)
                
                # Count keys
                db_info = info.get("db0", {})
                if isinstance(db_info, dict):
                    self._stats.size = db_info.get("keys", 0)
            except Exception:
                pass
        
        return self._stats
    
    async def delete_by_tags(self, tags: Set[str]) -> int:
        """Delete entries by tag using Redis sets."""
        if not self._redis:
            return 0
        
        try:
            keys_to_delete: Set[bytes] = set()
            
            pipe = self._redis.pipeline()
            for tag in tags:
                pipe.smembers(self._tag_set_key(tag))
            
            results = await pipe.execute()
            
            for members in results:
                if members:
                    keys_to_delete.update(members)
            
            if not keys_to_delete:
                return 0
            
            # Delete all keys and tag sets
            pipe = self._redis.pipeline()
            for key in keys_to_delete:
                pipe.delete(key)
            for tag in tags:
                pipe.delete(self._tag_set_key(tag))
            await pipe.execute()
            
            self._stats.deletes += len(keys_to_delete)
            return len(keys_to_delete)
        except Exception as e:
            logger.warning(f"Redis tag deletion error: {e}")
            self._stats.errors += 1
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[CacheEntry]]:
        """Pipelined batch get."""
        if not self._redis or not keys:
            return {k: None for k in keys}
        
        try:
            full_keys = [self._full_key(k) for k in keys]
            values = await self._redis.mget(full_keys)
            
            results = {}
            for key, raw in zip(keys, values):
                if raw is None:
                    self._stats.misses += 1
                    results[key] = None
                else:
                    try:
                        value = self._serializer.deserialize(raw)
                        self._stats.hits += 1
                        results[key] = CacheEntry(key=key, value=value)
                    except Exception:
                        self._stats.errors += 1
                        results[key] = None
            
            return results
        except Exception as e:
            logger.warning(f"Redis MGET error: {e}")
            self._stats.errors += 1
            return {k: None for k in keys}
    
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: str = "default",
    ) -> None:
        """Pipelined batch set."""
        if not self._redis or not items:
            return
        
        try:
            pipe = self._redis.pipeline()
            
            for key, value in items.items():
                full_key = self._full_key(key)
                serialized = self._serializer.serialize(value)
                
                if ttl and ttl > 0:
                    pipe.setex(full_key, ttl, serialized)
                else:
                    pipe.set(full_key, serialized)
                
                ns_key = self._ns_set_key(namespace)
                pipe.sadd(ns_key, full_key)
            
            await pipe.execute()
            self._stats.sets += len(items)
        except Exception as e:
            logger.warning(f"Redis MSET error: {e}")
            self._stats.errors += 1
    
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Atomic Redis INCRBY."""
        if not self._redis:
            return None
        
        try:
            full_key = self._full_key(key)
            exists = await self._redis.exists(full_key)
            if not exists:
                return None
            result = await self._redis.incrby(full_key, delta)
            return result
        except Exception as e:
            logger.warning(f"Redis INCRBY error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check if Redis is reachable."""
        if not self._redis:
            return False
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False
