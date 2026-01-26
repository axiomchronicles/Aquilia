"""
Bytecode Cache - Template compilation caching system.

Supports:
- In-memory cache (dev/testing)
- Crous-backed persistent cache (production)
- Optional Redis cache (high-throughput deployments)
"""

from typing import Optional, Dict
from pathlib import Path
import hashlib
import json
import pickle
from datetime import datetime
from jinja2 import BytecodeCache as Jinja2BytecodeCache
from jinja2.bccache import Bucket


class BytecodeCache(Jinja2BytecodeCache):
    """
    Abstract base for bytecode caching.
    
    Implements Jinja2's BytecodeCache interface with async extensions.
    """
    
    async def load_bytecode_async(self, key: str) -> Optional[bytes]:
        """Load bytecode asynchronously (optional optimization)."""
        return self.load_bytecode(key)
    
    async def store_bytecode_async(self, key: str, data: bytes) -> None:
        """Store bytecode asynchronously (optional optimization)."""
        self.dump_bytecode(data)
    
    async def clear_async(self) -> None:
        """Clear cache asynchronously."""
        self.clear()


class InMemoryBytecodeCache(BytecodeCache):
    """
    In-memory bytecode cache.
    
    Fast, non-persistent cache for development and testing.
    LRU eviction with configurable capacity.
    
    Args:
        capacity: Maximum number of compiled templates to cache
    """
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._cache: Dict[str, bytes] = {}
        self._access_order: list[str] = []
    
    def load_bytecode(self, bucket: Bucket) -> None:
        """Load bytecode from cache."""
        key = bucket.key
        if key in self._cache:
            # Update access order
            self._access_order.remove(key)
            self._access_order.append(key)
            
            bucket.bytecode_from_string(self._cache[key])
    
    def dump_bytecode(self, bucket: Bucket) -> None:
        """Store bytecode in cache."""
        key = bucket.key
        bytecode = bucket.bytecode_to_string()
        
        # Check capacity
        if len(self._cache) >= self.capacity and key not in self._cache:
            # Evict least recently used
            if self._access_order:
                evict_key = self._access_order.pop(0)
                del self._cache[evict_key]
        
        self._cache[key] = bytecode
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear all cached bytecode."""
        self._cache.clear()
        self._access_order.clear()
    
    def invalidate(self, key: str) -> None:
        """Invalidate specific template cache."""
        if key in self._cache:
            del self._cache[key]
            self._access_order.remove(key)


class CrousBytecodeCache(BytecodeCache):
    """
    Crous artifact-backed bytecode cache.
    
    Stores compiled templates in artifacts/templates.bytecode.crous
    with fingerprinting and atomic writes.
    
    Envelope format:
    {
        "__format__": "crous",
        "schema_version": "1.0",
        "artifact_type": "template_bytecode",
        "fingerprint": "sha256:...",
        "created_at": "2026-01-26T...",
        "payload": {
            "bytecode": {
                "template_key": "base64_bytecode",
                ...
            },
            "metadata": {
                "template_key": {
                    "source_path": "...",
                    "source_hash": "sha256:...",
                    "compiled_at": "2026-01-26T...",
                    "size": 12345
                },
                ...
            }
        }
    }
    
    Args:
        cache_dir: Directory to store cache files
        filename: Cache file name (default: templates.bytecode.crous)
    """
    
    def __init__(
        self,
        cache_dir: str = "artifacts",
        filename: str = "templates.bytecode.crous"
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / filename
        
        # In-memory cache for performance
        self._cache: Dict[str, bytes] = {}
        self._metadata: Dict[str, dict] = {}
        self._dirty = False
        
        # Load existing cache
        self._load()
    
    def load_bytecode(self, bucket: Bucket) -> None:
        """Load bytecode from cache."""
        key = bucket.key
        if key in self._cache:
            bucket.bytecode_from_string(self._cache[key])
    
    def dump_bytecode(self, bucket: Bucket) -> None:
        """Store bytecode in cache."""
        key = bucket.key
        bytecode = bucket.bytecode_to_string()
        
        self._cache[key] = bytecode
        self._metadata[key] = {
            "source_hash": self._compute_key_hash(key),
            "compiled_at": datetime.utcnow().isoformat(),
            "size": len(bytecode),
        }
        self._dirty = True
    
    def clear(self) -> None:
        """Clear all cached bytecode."""
        self._cache.clear()
        self._metadata.clear()
        self._dirty = True
        self._save()
    
    def invalidate(self, key: str) -> None:
        """Invalidate specific template cache."""
        if key in self._cache:
            del self._cache[key]
            if key in self._metadata:
                del self._metadata[key]
            self._dirty = True
    
    def save(self) -> None:
        """Persist cache to disk."""
        if self._dirty:
            self._save()
            self._dirty = False
    
    def _load(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, "rb") as f:
                data = pickle.load(f)
            
            # Validate envelope
            if not isinstance(data, dict) or data.get("__format__") != "crous":
                return
            
            payload = data.get("payload", {})
            
            # Load bytecode (base64 decoded -> pickle)
            bytecode_data = payload.get("bytecode", {})
            for key, encoded in bytecode_data.items():
                try:
                    self._cache[key] = encoded
                except Exception:
                    pass
            
            # Load metadata
            self._metadata = payload.get("metadata", {})
            
        except Exception:
            # Cache load failed, start fresh
            pass
    
    def _save(self) -> None:
        """Save cache to disk."""
        # Compute fingerprint
        fingerprint = self._compute_fingerprint()
        
        # Build envelope
        envelope = {
            "__format__": "crous",
            "schema_version": "1.0",
            "artifact_type": "template_bytecode",
            "fingerprint": fingerprint,
            "created_at": datetime.utcnow().isoformat(),
            "payload": {
                "bytecode": self._cache.copy(),
                "metadata": self._metadata.copy(),
            }
        }
        
        # Atomic write
        temp_file = self.cache_file.with_suffix(".tmp")
        try:
            with open(temp_file, "wb") as f:
                pickle.dump(envelope, f)
            temp_file.replace(self.cache_file)
        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            raise
    
    def _compute_fingerprint(self) -> str:
        """Compute cache fingerprint."""
        # Hash all template keys and their source hashes
        items = sorted(
            (key, meta.get("source_hash", ""))
            for key, meta in self._metadata.items()
        )
        canonical = json.dumps(items, separators=(",", ":"))
        hash_digest = hashlib.sha256(canonical.encode()).hexdigest()
        return f"sha256:{hash_digest}"
    
    def _compute_key_hash(self, key: str) -> str:
        """Compute hash of template key."""
        hash_digest = hashlib.sha256(key.encode()).hexdigest()
        return f"sha256:{hash_digest}"


class RedisBytecodeCache(BytecodeCache):
    """
    Redis-backed bytecode cache for high-throughput deployments.
    
    Requires redis-py (optional dependency).
    
    Args:
        redis_url: Redis connection URL
        key_prefix: Key prefix for cache entries
        ttl: Cache entry TTL in seconds (None = no expiration)
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "aquilia:templates:",
        ttl: Optional[int] = None
    ):
        try:
            import redis.asyncio as aioredis
            self._redis_module = aioredis
        except ImportError:
            raise ImportError(
                "Redis cache requires redis-py. "
                "Install with: pip install redis"
            )
        
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis connection (lazy)."""
        if self._redis is None:
            self._redis = await self._redis_module.from_url(self.redis_url)
        return self._redis
    
    def load_bytecode(self, bucket: Bucket) -> None:
        """Load bytecode from Redis (sync wrapper)."""
        # Sync loading not ideal for Redis, but required by Jinja2 interface
        # In practice, use async methods
        pass
    
    def dump_bytecode(self, bucket: Bucket) -> None:
        """Store bytecode in Redis (sync wrapper)."""
        # Sync dumping not ideal for Redis, but required by Jinja2 interface
        pass
    
    async def load_bytecode_async(self, key: str) -> Optional[bytes]:
        """Load bytecode from Redis asynchronously."""
        redis = await self._get_redis()
        cache_key = f"{self.key_prefix}{key}"
        data = await redis.get(cache_key)
        return data
    
    async def store_bytecode_async(self, key: str, data: bytes) -> None:
        """Store bytecode in Redis asynchronously."""
        redis = await self._get_redis()
        cache_key = f"{self.key_prefix}{key}"
        if self.ttl:
            await redis.setex(cache_key, self.ttl, data)
        else:
            await redis.set(cache_key, data)
    
    def clear(self) -> None:
        """Clear all cached bytecode."""
        # Sync clear not ideal for Redis
        pass
    
    async def clear_async(self) -> None:
        """Clear all cached bytecode asynchronously."""
        redis = await self._get_redis()
        pattern = f"{self.key_prefix}*"
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
