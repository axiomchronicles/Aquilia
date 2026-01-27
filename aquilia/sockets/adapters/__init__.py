"""
Adapters Package - WebSocket scaling adapters
"""

from .base import Adapter, RoomInfo
from .inmemory import InMemoryAdapter
from .redis import RedisAdapter

__all__ = [
    "Adapter",
    "RoomInfo",
    "InMemoryAdapter",
    "RedisAdapter",
]
