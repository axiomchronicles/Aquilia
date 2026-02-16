"""
AquilaCache — Pluggable serializers for cache value encoding.

Supports JSON (default), pickle (fast, Python-only), and msgpack
(compact, cross-language). All serializers include structured error
handling and logging for serialization failures.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("aquilia.cache.serializers")


class JsonCacheSerializer:
    """
    JSON serializer — safe, human-readable, cross-language.
    
    Default serializer. Handles most Python primitives and
    containers (dict, list, str, int, float, bool, None).
    Falls back to ``str()`` for non-serializable types.
    """
    
    def serialize(self, value: Any) -> bytes:
        """Serialize value to JSON bytes."""
        try:
            return json.dumps(value, default=str, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError, OverflowError) as e:
            logger.warning(f"JSON serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to value."""
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"JSON deserialization failed: {e}")
            raise


class PickleCacheSerializer:
    """
    Pickle serializer — fast, supports arbitrary Python objects.
    
    WARNING: Only use with trusted data. Pickle can execute
    arbitrary code during deserialization.
    """
    
    def serialize(self, value: Any) -> bytes:
        """Serialize value via pickle."""
        import pickle
        try:
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        except (pickle.PicklingError, TypeError) as e:
            logger.warning(f"Pickle serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize pickle bytes."""
        import pickle
        try:
            return pickle.loads(data)
        except (pickle.UnpicklingError, EOFError) as e:
            logger.warning(f"Pickle deserialization failed: {e}")
            raise


class MsgpackCacheSerializer:
    """
    MessagePack serializer — compact binary, cross-language.
    
    Requires `msgpack` package: pip install msgpack
    """
    
    def serialize(self, value: Any) -> bytes:
        """Serialize value to msgpack bytes."""
        try:
            import msgpack
        except ImportError:
            raise ImportError(
                "MsgpackCacheSerializer requires 'msgpack' package. "
                "Install with: pip install msgpack"
            )
        try:
            return msgpack.packb(value, use_bin_type=True, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Msgpack serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize msgpack bytes."""
        try:
            import msgpack
        except ImportError:
            raise ImportError(
                "MsgpackCacheSerializer requires 'msgpack' package. "
                "Install with: pip install msgpack"
            )
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            logger.warning(f"Msgpack deserialization failed: {e}")
            raise


def get_serializer(name: str = "json"):
    """
    Factory for serializer instances.
    
    Args:
        name: "json", "pickle", or "msgpack"
        
    Returns:
        CacheSerializer instance
    """
    serializers = {
        "json": JsonCacheSerializer,
        "pickle": PickleCacheSerializer,
        "msgpack": MsgpackCacheSerializer,
    }
    
    cls = serializers.get(name)
    if cls is None:
        raise ValueError(f"Unknown serializer: {name}. Options: {list(serializers.keys())}")
    
    return cls()
