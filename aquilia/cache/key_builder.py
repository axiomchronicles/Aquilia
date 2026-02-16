"""
AquilaCache — Cache key builder implementations.

Deterministic, collision-free key generation with namespace
isolation, optional hashing for long keys, and version support
for mass-invalidation.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional


class DefaultKeyBuilder:
    """
    Default key builder using colon-separated segments.
    
    Pattern: ``{prefix}v{version}:{namespace}:{key}``
    
    Example: ``aq:v1:users:user:123``
    
    Version support enables mass-invalidation by incrementing
    the version number in config, making all old keys invisible.
    """
    
    def __init__(self, version: int = 0):
        """
        Args:
            version: Key version. When > 0, embeds version in key.
                     Incrementing invalidates all previous keys.
        """
        self._version = version
    
    def build(self, namespace: str, key: str, prefix: str = "") -> str:
        """Build qualified cache key with optional version."""
        if self._version > 0:
            return f"{prefix}v{self._version}:{namespace}:{key}"
        return f"{prefix}{namespace}:{key}"
    
    def from_args(
        self,
        namespace: str,
        func_name: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        prefix: str = "",
    ) -> str:
        """
        Build cache key from function call arguments.
        
        Used by @cached decorator for automatic key generation.
        """
        parts = [prefix, namespace, func_name]
        
        if args:
            parts.append(":".join(str(a) for a in args))
        
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            parts.append(":".join(f"{k}={v}" for k, v in sorted_kwargs))
        
        return ":".join(filter(None, parts))


class HashKeyBuilder:
    """
    Hash-based key builder for long or complex keys.
    
    Uses SHA-256 to produce fixed-length keys, preventing
    issues with Redis key length limits or memory overhead.
    
    Pattern: ``{prefix}v{version}:{namespace}:{sha256_hex[:16]}``
    """
    
    def __init__(self, hash_length: int = 16, version: int = 0):
        """
        Args:
            hash_length: Length of hex hash suffix (max 64 for SHA-256)
            version: Key version for mass-invalidation
        """
        self._hash_length = min(hash_length, 64)
        self._version = version
    
    def build(self, namespace: str, key: str, prefix: str = "") -> str:
        """Build hash-based cache key."""
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()[:self._hash_length]
        if self._version > 0:
            return f"{prefix}v{self._version}:{namespace}:{key_hash}"
        return f"{prefix}{namespace}:{key_hash}"
    
    def from_args(
        self,
        namespace: str,
        func_name: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        prefix: str = "",
    ) -> str:
        """Build hashed key from function call arguments."""
        raw_parts = [func_name]
        
        if args:
            raw_parts.append(str(args))
        
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            raw_parts.append(str(sorted_kwargs))
        
        raw_key = ":".join(raw_parts)
        return self.build(namespace, raw_key, prefix)
