"""
AquilaSessions - Session Engine.

The SessionEngine orchestrates the complete session lifecycle:
1. Detection - Extract session ID from transport
2. Resolution - Load from store or create new
3. Validation - Check expiry, idle timeout, concurrency
4. Binding - Bind to request context and DI
5. Mutation - Handler reads/writes session data
6. Commit - Persist, rotate, or destroy
7. Emission - Transport writes updated reference

SessionEngine is request-scoped and integrates with:
- SessionStore (persistence)
- SessionTransport (delivery)
- SessionPolicy (behavior)
- DI Container (injection)
- FaultEngine (error handling)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from .core import Session, SessionID, SessionScope, SessionFlag
from .faults import (
    SessionExpiredFault,
    SessionIdleTimeoutFault,
    SessionInvalidFault,
    SessionNotFoundFault,
    SessionConcurrencyViolationFault,
    SessionRotationFailedFault,
    SessionPolicyViolationFault,
    SessionStoreUnavailableFault,
)

if TYPE_CHECKING:
    from aquilia.request import Request
    from aquilia.response import Response
    from aquilia.di import Container
    from .policy import SessionPolicy
    from .store import SessionStore
    from .transport import SessionTransport


# ============================================================================
# SessionEngine - Lifecycle Orchestrator
# ============================================================================

class SessionEngine:
    """
    Session lifecycle orchestrator.
    
    The SessionEngine is the central coordinator for all session operations.
    It enforces policy, manages storage, and emits observability events.
    
    Architecture:
        SessionEngine is app-scoped (singleton per app)
        Session instances are request-scoped (created per request)
    
    Example:
        >>> engine = SessionEngine(
        ...     policy=user_default_policy,
        ...     store=redis_store,
        ...     transport=cookie_transport
        ... )
        >>> session = await engine.resolve(request, container)
        >>> # ... handler mutates session ...
        >>> await engine.commit(session, response)
    """
    
    def __init__(
        self,
        policy: SessionPolicy,
        store: SessionStore,
        transport: SessionTransport,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize session engine.
        
        Args:
            policy: Session policy (defines behavior)
            store: Session store (persistence)
            transport: Session transport (delivery)
            logger: Optional logger
        """
        self.policy = policy
        self.store = store
        self.transport = transport
        self.logger = logger or logging.getLogger("aquilia.sessions")
        
        # Event callbacks (for observability)
        self._event_handlers: list = []
    
    # ========================================================================
    # Phase 1 & 2: Detection + Resolution
    # ========================================================================
    
    async def resolve(
        self,
        request: Request,
        container: Container | None = None,
    ) -> Session:
        """
        Resolve session for request (Phase 1-4: Detection, Resolution, Validation, Binding).
        
        This is the main entry point called at request start.
        
        Args:
            request: Incoming request
            container: DI container (for binding)
            
        Returns:
            Valid session (existing or new)
            
        Raises:
            SessionExpiredFault: Session expired
            SessionIdleTimeoutFault: Idle timeout exceeded
            SessionConcurrencyViolationFault: Too many sessions
        """
        now = datetime.utcnow()
        
        # Phase 1: Detection - Extract session ID from transport
        session_id_str = self.transport.extract(request)
        
        if session_id_str:
            # Try to load existing session
            try:
                session_id = SessionID.from_string(session_id_str)
                session = await self._load_existing(session_id, now)
                
                if session:
                    # Session loaded successfully
                    self._emit_event("session_loaded", session, request)
                    return session
            
            except ValueError:
                # Invalid session ID format
                self.logger.warning(f"Invalid session ID format: {session_id_str[:16]}...")
                self._emit_event("session_invalid", None, request)
                # Fall through to create new session
            
            except SessionExpiredFault:
                # Session expired - create new one
                self.logger.info(f"Session expired, creating new: {session_id_str[:16]}...")
                self._emit_event("session_expired", None, request)
                # Fall through to create new session
            
            except SessionIdleTimeoutFault:
                # Idle timeout - create new one
                self.logger.info(f"Session idle timeout: {session_id_str[:16]}...")
                self._emit_event("session_idle_timeout", None, request)
                # Fall through to create new session
        
        # Phase 2: Resolution - Create new session
        session = await self._create_new(now)
        self._emit_event("session_created", session, request)
        
        return session
    
    async def _load_existing(self, session_id: SessionID, now: datetime) -> Session | None:
        """
        Load existing session from store and validate.
        
        Args:
            session_id: Session identifier
            now: Current timestamp
            
        Returns:
            Valid session or None
            
        Raises:
            SessionExpiredFault: Session expired
            SessionIdleTimeoutFault: Idle timeout exceeded
        """
        # Load from store
        try:
            session = await self.store.load(session_id)
        except SessionStoreUnavailableFault:
            # Store unavailable - log and create new session
            self.logger.error("Session store unavailable, creating new session")
            return None
        
        if not session:
            return None
        
        # Phase 3: Validation - Check policy constraints
        is_valid, reason = self.policy.is_valid(session, now)
        
        if not is_valid:
            if reason == "expired":
                raise SessionExpiredFault(
                    session_id=str(session_id),
                    expires_at=session.expires_at.isoformat() if session.expires_at else None,
                )
            elif reason == "idle_timeout":
                raise SessionIdleTimeoutFault(
                    session_id=str(session_id),
                )
        
        # Touch session (update last_accessed_at)
        session.touch(now)
        
        return session
    
    async def _create_new(self, now: datetime) -> Session:
        """
        Create new session.
        
        Args:
            now: Current timestamp
            
        Returns:
            New session
        """
        from .core import SessionScope
        
        # Parse scope
        scope = SessionScope(self.policy.scope)
        
        # Create session
        session = Session(
            id=SessionID(),  # Generate random ID
            created_at=now,
            last_accessed_at=now,
            expires_at=self.policy.calculate_expiry(now),
            scope=scope,
            flags=set(),
        )
        
        # Mark as renewable if policy allows
        if self.policy.ttl and not self.policy.rotate_on_use:
            session.flags.add(SessionFlag.RENEWABLE)
        
        # Mark as ephemeral if no persistence
        if not self.policy.should_persist(session):
            session.flags.add(SessionFlag.EPHEMERAL)
        
        # Store policy name
        session._policy_name = self.policy.name
        
        return session
    
    # ========================================================================
    # Phase 6: Commit
    # ========================================================================
    
    async def commit(
        self,
        session: Session,
        response: Response,
        privilege_changed: bool = False,
    ) -> None:
        """
        Commit session changes (Phase 6-7: Commit, Emission).
        
        This is called at request end to:
        - Rotate ID if needed
        - Persist to store
        - Emit to transport
        
        Args:
            session: Session to commit
            response: Response to inject session into
            privilege_changed: Whether authentication changed
        """
        now = datetime.utcnow()
        
        # Check if rotation needed
        if self.policy.should_rotate(session, privilege_changed):
            try:
                session = await self._rotate_session(session, now)
                self._emit_event("session_rotated", session, None)
            except Exception as e:
                self.logger.error(f"Session rotation failed: {e}")
                raise SessionRotationFailedFault(
                    old_id=str(session.id),
                    new_id="unknown",
                    cause=str(e),
                )
        
        # Check concurrency if privilege changed and session is authenticated
        if privilege_changed and session.is_authenticated:
            await self.check_concurrency(session)
        
        # Persist if needed
        if self.policy.should_persist(session) and session.is_dirty:
            try:
                await self.store.save(session)
                self._emit_event("session_committed", session, None)
            except SessionStoreUnavailableFault as e:
                self.logger.error(f"Failed to persist session: {e}")
                # Don't fail request, but log error
        
        # Phase 7: Emission - Inject into response
        self.transport.inject(response, session)
    
    async def _rotate_session(self, session: Session, now: datetime) -> Session:
        """
        Rotate session ID (create new ID, keep data).
        
        Args:
            session: Session to rotate
            now: Current timestamp
            
        Returns:
            New session with rotated ID
        """
        old_id = session.id
        
        # Create new session with same data
        new_session = Session(
            id=SessionID(),  # New random ID
            principal=session.principal,
            data=session.data.copy(),
            created_at=session.created_at,
            last_accessed_at=now,
            expires_at=session.expires_at,
            scope=session.scope,
            flags=session.flags.copy(),
            version=session.version + 1,
        )
        new_session._policy_name = session._policy_name
        new_session.mark_dirty()
        
        # Delete old session atomically
        try:
            await self.store.delete(old_id)
        except Exception as e:
            self.logger.warning(f"Failed to delete old session: {e}")
        
        return new_session
    
    # ========================================================================
    # Session Operations
    # ========================================================================
    
    async def destroy(self, session: Session, response: Response) -> None:
        """
        Destroy session (logout).
        
        Args:
            session: Session to destroy
            response: Response to clear session from
        """
        # Delete from store
        try:
            await self.store.delete(session.id)
            self._emit_event("session_destroyed", session, None)
        except Exception as e:
            self.logger.error(f"Failed to destroy session: {e}")
        
        # Clear from transport
        self.transport.clear(response)
    
    async def check_concurrency(self, session: Session) -> None:
        """
        Check concurrency limits for session's principal.
        
        Args:
            session: Session to check
            
        Raises:
            SessionConcurrencyViolationFault: Too many concurrent sessions
        """
        if not session.principal:
            return  # No principal, no limit
        
        if not self.policy.concurrency.max_sessions_per_principal:
            return  # No limit configured
        
        # Count active sessions for principal
        active_count = await self.store.count_by_principal(session.principal.id)
        
        if self.policy.concurrency.violated(session.principal, active_count):
            # Handle violation based on policy
            if self.policy.concurrency.should_reject():
                raise SessionConcurrencyViolationFault(
                    principal_id=session.principal.id,
                    active_count=active_count,
                    max_allowed=self.policy.concurrency.max_sessions_per_principal,
                )
            
            elif self.policy.concurrency.should_evict_oldest():
                # Evict oldest session
                sessions = await self.store.list_by_principal(session.principal.id)
                if sessions:
                    oldest = min(sessions, key=lambda s: s.last_accessed_at)
                    await self.store.delete(oldest.id)
                    self.logger.info(f"Evicted oldest session for principal {session.principal.id}")
            
            elif self.policy.concurrency.should_evict_all():
                # Evict all existing sessions
                sessions = await self.store.list_by_principal(session.principal.id)
                for s in sessions:
                    if s.id != session.id:  # Don't evict current session
                        await self.store.delete(s.id)
                self.logger.info(f"Evicted all sessions for principal {session.principal.id}")
    
    async def refresh(self, session: Session, now: datetime | None = None) -> None:
        """
        Refresh session expiry (extend TTL).
        
        Args:
            session: Session to refresh
            now: Current timestamp
        """
        if now is None:
            now = datetime.utcnow()
        
        if SessionFlag.RENEWABLE in session.flags and self.policy.ttl:
            session.extend_expiry(self.policy.ttl, now)
            self._emit_event("session_refreshed", session, None)
    
    # ========================================================================
    # Observability
    # ========================================================================
    
    def _emit_event(
        self,
        event_name: str,
        session: Session | None,
        request: Request | None,
    ) -> None:
        """
        Emit session event for observability.
        
        Args:
            event_name: Event name
            session: Session (if available)
            request: Request (if available)
        """
        event_data = {
            "event": event_name,
            "timestamp": datetime.utcnow().isoformat(),
            "policy": self.policy.name,
        }
        
        if session:
            # Hash session ID for privacy
            import hashlib
            session_id_hash = hashlib.sha256(str(session.id).encode()).hexdigest()[:16]
            
            event_data.update({
                "session_id_hash": f"sha256:{session_id_hash}",
                "scope": session.scope.value,
                "authenticated": session.is_authenticated,
            })
            
            if session.principal:
                event_data["principal"] = {
                    "kind": session.principal.kind,
                    "id": session.principal.id,
                }
        
        if request:
            event_data.update({
                "request_path": request.path,
                "request_method": request.method,
            })
            
            if request.client:
                event_data["client_ip"] = request.client[0]
        
        # Call registered event handlers
        for handler in self._event_handlers:
            try:
                handler(event_data)
            except Exception as e:
                self.logger.error(f"Event handler error: {e}")
        
        # Also log event
        self.logger.debug(f"Session event: {event_name}", extra=event_data)
    
    def on_event(self, handler: callable) -> None:
        """
        Register event handler for observability.
        
        Args:
            handler: Callable that receives event dict
        """
        self._event_handlers.append(handler)
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired sessions from store.
        
        Returns:
            Number of sessions removed
        """
        try:
            count = await self.store.cleanup_expired()
            self.logger.info(f"Cleaned up {count} expired sessions")
            return count
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0
    
    async def shutdown(self) -> None:
        """Gracefully shutdown engine."""
        await self.store.shutdown()
