"""
AquilaSessions - Session storage abstraction.

Defines SessionStore protocol and concrete implementations:
- MemoryStore: In-memory storage (dev/testing)
- FileStore: File-based storage (debugging)
- RedisStore: Redis-based storage (production) [future]
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, Any
from datetime import datetime

from .core import Session, SessionID
from .faults import (
    SessionNotFoundFault,
    SessionStoreUnavailableFault,
    SessionStoreCorruptedFault,
)


# ============================================================================
# SessionStore Protocol
# ============================================================================

class SessionStore(Protocol):
    """
    Abstract session storage interface.
    
    Stores are responsible ONLY for persistence - they do NOT enforce policy.
    Policy enforcement happens in SessionEngine.
    
    All methods must be async and cancellation-safe.
    """
    
    async def load(self, session_id: SessionID) -> Session | None:
        """
        Load session from store.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session if found, None otherwise
            
        Raises:
            SessionStoreUnavailableFault: Store is unavailable
            SessionStoreCorruptedFault: Data is corrupted
        """
        ...
    
    async def save(self, session: Session) -> None:
        """
        Save session to store.
        
        Args:
            session: Session to save
            
        Raises:
            SessionStoreUnavailableFault: Store is unavailable
        """
        ...
    
    async def delete(self, session_id: SessionID) -> None:
        """
        Delete session from store.
        
        Args:
            session_id: Session identifier
            
        Raises:
            SessionStoreUnavailableFault: Store is unavailable
        """
        ...
    
    async def exists(self, session_id: SessionID) -> bool:
        """
        Check if session exists in store.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if exists, False otherwise
        """
        ...
    
    async def list_by_principal(self, principal_id: str) -> list[Session]:
        """
        List all sessions for a principal (for concurrency checks).
        
        Args:
            principal_id: Principal identifier
            
        Returns:
            List of sessions for this principal
        """
        ...
    
    async def count_by_principal(self, principal_id: str) -> int:
        """
        Count sessions for a principal (faster than list).
        
        Args:
            principal_id: Principal identifier
            
        Returns:
            Number of sessions for this principal
        """
        ...
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired sessions from store.
        
        Returns:
            Number of sessions removed
        """
        ...
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown store (close connections, flush buffers).
        """
        ...


# ============================================================================
# MemoryStore - In-Memory Storage
# ============================================================================

class MemoryStore:
    """
    In-memory session storage for development and testing.
    
    Features:
    - Fast in-memory dict storage
    - Automatic cleanup of expired sessions
    - Principal index for fast lookup
    - Max session limit (LRU eviction)
    
    NOT suitable for production (no persistence across restarts).
    
    Example:
        >>> store = MemoryStore(max_sessions=10000)
        >>> await store.save(session)
        >>> loaded = await store.load(session.id)
        >>> assert loaded.id == session.id
    """
    
    def __init__(self, max_sessions: int = 10000):
        """
        Initialize memory store.
        
        Args:
            max_sessions: Maximum sessions to keep (LRU eviction)
        """
        self.max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}
        self._principal_index: dict[str, set[str]] = {}  # principal_id -> session_ids
        self._access_order: list[str] = []  # For LRU eviction
        self._lock = asyncio.Lock()
    
    async def load(self, session_id: SessionID) -> Session | None:
        """Load session from memory."""
        async with self._lock:
            session = self._sessions.get(str(session_id))
            
            if session:
                # Update access order for LRU
                self._touch_access(str(session_id))
            
            return session
    
    async def save(self, session: Session) -> None:
        """Save session to memory."""
        async with self._lock:
            session_id_str = str(session.id)
            
            # Evict if at capacity and this is a new session
            if session_id_str not in self._sessions and len(self._sessions) >= self.max_sessions:
                await self._evict_lru()
            
            # Store session
            self._sessions[session_id_str] = session
            
            # Update principal index
            if session.principal:
                principal_id = session.principal.id
                if principal_id not in self._principal_index:
                    self._principal_index[principal_id] = set()
                self._principal_index[principal_id].add(session_id_str)
            
            # Update access order
            self._touch_access(session_id_str)
            
            # Mark session as clean after save
            session.mark_clean()
    
    async def delete(self, session_id: SessionID) -> None:
        """Delete session from memory."""
        async with self._lock:
            session_id_str = str(session_id)
            session = self._sessions.pop(session_id_str, None)
            
            if session and session.principal:
                # Remove from principal index
                principal_id = session.principal.id
                if principal_id in self._principal_index:
                    self._principal_index[principal_id].discard(session_id_str)
                    if not self._principal_index[principal_id]:
                        del self._principal_index[principal_id]
            
            # Remove from access order
            if session_id_str in self._access_order:
                self._access_order.remove(session_id_str)
    
    async def exists(self, session_id: SessionID) -> bool:
        """Check if session exists."""
        return str(session_id) in self._sessions
    
    async def list_by_principal(self, principal_id: str) -> list[Session]:
        """List all sessions for principal."""
        async with self._lock:
            session_ids = self._principal_index.get(principal_id, set())
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
    
    async def count_by_principal(self, principal_id: str) -> int:
        """Count sessions for principal."""
        async with self._lock:
            session_ids = self._principal_index.get(principal_id, set())
            # Count only sessions that still exist
            return sum(1 for sid in session_ids if sid in self._sessions)
    
    async def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired_ids = []
        
        async with self._lock:
            for session_id, session in list(self._sessions.items()):
                if session.is_expired(now):
                    expired_ids.append(session_id)
            
            # Delete expired sessions
            for session_id in expired_ids:
                session = self._sessions.pop(session_id, None)
                if session and session.principal:
                    principal_id = session.principal.id
                    if principal_id in self._principal_index:
                        self._principal_index[principal_id].discard(session_id)
                
                if session_id in self._access_order:
                    self._access_order.remove(session_id)
        
        return len(expired_ids)
    
    async def shutdown(self) -> None:
        """Shutdown store (clear memory)."""
        async with self._lock:
            self._sessions.clear()
            self._principal_index.clear()
            self._access_order.clear()
    
    def _touch_access(self, session_id: str) -> None:
        """Update LRU access order."""
        if session_id in self._access_order:
            self._access_order.remove(session_id)
        self._access_order.append(session_id)
    
    async def _evict_lru(self) -> None:
        """Evict least recently used session."""
        if not self._access_order:
            return
        
        # Evict oldest
        oldest_id = self._access_order[0]
        session = self._sessions.pop(oldest_id, None)
        
        if session and session.principal:
            principal_id = session.principal.id
            if principal_id in self._principal_index:
                self._principal_index[principal_id].discard(oldest_id)
        
        self._access_order.pop(0)
    
    # Utility methods for debugging
    def get_stats(self) -> dict[str, Any]:
        """Get store statistics."""
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": self.max_sessions,
            "total_principals": len(self._principal_index),
            "utilization": len(self._sessions) / self.max_sessions if self.max_sessions > 0 else 0,
        }


# ============================================================================
# FileStore - File-Based Storage
# ============================================================================

class FileStore:
    """
    File-based session storage for debugging and development.
    
    Features:
    - One file per session (JSON)
    - Human-readable format
    - Simple filesystem-based storage
    
    NOT suitable for production (slow, no locking, file system limits).
    
    Example:
        >>> store = FileStore(directory="/tmp/sessions")
        >>> await store.save(session)
        >>> loaded = await store.load(session.id)
    """
    
    def __init__(self, directory: str | Path):
        """
        Initialize file store.
        
        Args:
            directory: Directory to store session files
        """
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
    
    def _get_path(self, session_id: SessionID) -> Path:
        """Get file path for session."""
        return self.directory / f"{session_id}.json"
    
    async def load(self, session_id: SessionID) -> Session | None:
        """Load session from file."""
        path = self._get_path(session_id)
        
        if not path.exists():
            return None
        
        try:
            async with self._lock:
                # Read file
                data = path.read_text()
                session_dict = json.loads(data)
                
                # Deserialize
                session = Session.from_dict(session_dict)
                return session
        
        except json.JSONDecodeError as e:
            raise SessionStoreCorruptedFault(
                message=f"Session file corrupted: {e}",
                session_id=str(session_id)
            )
        except Exception as e:
            raise SessionStoreUnavailableFault(
                store_name="file",
                cause=str(e)
            )
    
    async def save(self, session: Session) -> None:
        """Save session to file."""
        path = self._get_path(session.id)
        
        try:
            async with self._lock:
                # Serialize
                session_dict = session.to_dict()
                data = json.dumps(session_dict, indent=2)
                
                # Write file atomically (write to temp, then rename)
                temp_path = path.with_suffix(".tmp")
                temp_path.write_text(data)
                temp_path.rename(path)
                
                # Mark clean
                session.mark_clean()
        
        except Exception as e:
            raise SessionStoreUnavailableFault(
                store_name="file",
                cause=str(e)
            )
    
    async def delete(self, session_id: SessionID) -> None:
        """Delete session file."""
        path = self._get_path(session_id)
        
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            raise SessionStoreUnavailableFault(
                store_name="file",
                cause=str(e)
            )
    
    async def exists(self, session_id: SessionID) -> bool:
        """Check if session file exists."""
        return self._get_path(session_id).exists()
    
    async def list_by_principal(self, principal_id: str) -> list[Session]:
        """List sessions for principal (slow - scans all files)."""
        sessions = []
        
        async with self._lock:
            for path in self.directory.glob("sess_*.json"):
                try:
                    data = path.read_text()
                    session_dict = json.loads(data)
                    
                    # Check if principal matches
                    if session_dict.get("principal") and session_dict["principal"]["id"] == principal_id:
                        session = Session.from_dict(session_dict)
                        sessions.append(session)
                
                except Exception:
                    # Skip corrupted files
                    continue
        
        return sessions
    
    async def count_by_principal(self, principal_id: str) -> int:
        """Count sessions for principal."""
        sessions = await self.list_by_principal(principal_id)
        return len(sessions)
    
    async def cleanup_expired(self) -> int:
        """Remove expired session files."""
        now = datetime.utcnow()
        removed = 0
        
        async with self._lock:
            for path in self.directory.glob("sess_*.json"):
                try:
                    data = path.read_text()
                    session_dict = json.loads(data)
                    session = Session.from_dict(session_dict)
                    
                    if session.is_expired(now):
                        path.unlink()
                        removed += 1
                
                except Exception:
                    # Skip corrupted files
                    continue
        
        return removed
    
    async def shutdown(self) -> None:
        """Shutdown store (no-op for files)."""
        pass
    
    def get_stats(self) -> dict[str, Any]:
        """Get store statistics."""
        total_files = len(list(self.directory.glob("sess_*.json")))
        total_size = sum(p.stat().st_size for p in self.directory.glob("sess_*.json"))
        
        return {
            "total_sessions": total_files,
            "total_size_bytes": total_size,
            "directory": str(self.directory),
        }
