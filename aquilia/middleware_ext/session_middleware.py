"""
Session Middleware - Integrates SessionEngine with request lifecycle.

This middleware orchestrates the complete session lifecycle:
1. Resolve session at request start (detection, resolution, validation, binding)
2. Register session in DI container (request-scoped)
3. Store session in request state
4. Commit session at request end (persistence, rotation, emission)
"""

from typing import TYPE_CHECKING, Optional
import logging

from aquilia.middleware import Handler
from aquilia.request import Request
from aquilia.response import Response
from aquilia.di import RequestCtx

if TYPE_CHECKING:
    from aquilia.sessions import SessionEngine, Session


class SessionMiddleware:
    """
    Middleware that integrates SessionEngine with request lifecycle.
    
    This middleware:
    - Resolves sessions at request start (Phase 1-4: Detection, Resolution, Validation, Binding)
    - Binds session to DI container (request-scoped)
    - Stores session in request.state for direct access
    - Commits sessions at request end (Phase 6-7: Commit, Emission)
    - Handles privilege changes (login/logout) with automatic rotation
    - Emits session events for observability
    
    Architecture:
        Request → SessionMiddleware → [resolve] → Handler → [commit] → Response
    
    Integration Points:
    - DI Container: Registers Session as request-scoped instance
    - Request State: Stores session in request.state["session"]
    - SessionEngine: Delegates all session operations
    
    Example:
        >>> from aquilia.sessions import SessionEngine, MemoryStore, CookieTransport
        >>> engine = SessionEngine(policy, store, transport)
        >>> middleware = SessionMiddleware(engine)
        >>> app.middleware_stack.add(middleware, priority=15)
    """
    
    def __init__(self, session_engine: "SessionEngine"):
        """
        Initialize session middleware.
        
        Args:
            session_engine: SessionEngine instance (app-scoped)
        """
        self.engine = session_engine
        self.logger = logging.getLogger("aquilia.middleware.session")
    
    async def __call__(
        self,
        request: Request,
        ctx: RequestCtx,
        next_handler: Handler,
    ) -> Response:
        """
        Process request with session management.
        
        Flow:
        1. Resolve session from SessionEngine
        2. Register in DI container (if available)
        3. Store in request state
        4. Check concurrency limits (if authenticated)
        5. Call next handler
        6. Detect privilege changes
        7. Commit session (persist + emit)
        
        Args:
            request: Incoming request
            ctx: Request context with DI container
            next_handler: Next middleware/handler in chain
            
        Returns:
            Response with session cookie/header
        """
        # Get DI container from request state (set by RequestScopeMiddleware)
        container = request.state.get("di_container")
        
        # Phase 1-4: Resolve session (detection, resolution, validation, binding)
        try:
            session = await self.engine.resolve(request, container)
        except Exception as e:
            self.logger.error(f"Session resolution failed: {e}", exc_info=True)
            # Continue without session on error
            return await next_handler(request, ctx)
        
        # Store in request state for direct access
        request.state["session"] = session
        
        # CRITICAL: Also store in RequestCtx if it exists
        # This ensures controllers can access sessions via ctx.session
        if hasattr(ctx, 'session'):
            ctx.session = session
        
        # Register session in DI container (request-scoped)
        if container:
            try:
                # Register as instance so it can be injected into controllers
                from aquilia.sessions import Session
                await container.register_instance(Session, session, scope="request")
            except Exception as e:
                self.logger.warning(f"Failed to register session in DI: {e}")
        
        # Check concurrency limits (if authenticated)
        if session.is_authenticated:
            # Concurrency check is enforced based on policy behavior (reject/evict)
            # We allow specific session faults to propagate to the ExceptionMiddleware
            await self.engine.check_concurrency(session)
        
        # Track privilege state before handler
        privilege_before = session.is_authenticated
        
        # Process request
        response = await next_handler(request, ctx)
        
        # Track privilege state after handler
        privilege_after = session.is_authenticated
        
        # Detect privilege change (login/logout)
        privilege_changed = privilege_before != privilege_after
        
        # Phase 6-7: Commit session (commit, emission)
        try:
            await self.engine.commit(session, response, privilege_changed)
        except Exception as e:
            self.logger.error(f"Session commit failed: {e}", exc_info=True)
            # Continue - response is already generated
        
        return response


class OptionalSessionMiddleware:
    """
    Session middleware that gracefully handles missing SessionEngine.
    
    This variant allows sessions to be optional - if SessionEngine is not
    configured, requests proceed without session management.
    
    Use this when sessions are opt-in per app/route.
    """
    
    def __init__(self, session_engine: Optional["SessionEngine"] = None):
        """
        Initialize optional session middleware.
        
        Args:
            session_engine: SessionEngine instance or None
        """
        self.engine = session_engine
        self.logger = logging.getLogger("aquilia.middleware.session")
    
    async def __call__(
        self,
        request: Request,
        ctx: RequestCtx,
        next_handler: Handler,
    ) -> Response:
        """Process request with optional session management."""
        # If no engine configured, skip session management
        if self.engine is None:
            return await next_handler(request, ctx)
        
        # Delegate to SessionMiddleware logic
        middleware = SessionMiddleware(self.engine)
        return await middleware(request, ctx, next_handler)


def create_session_middleware(
    session_engine: Optional["SessionEngine"] = None,
    optional: bool = False,
) -> SessionMiddleware | OptionalSessionMiddleware:
    """
    Factory function to create session middleware.
    
    Args:
        session_engine: SessionEngine instance
        optional: If True, create OptionalSessionMiddleware
        
    Returns:
        SessionMiddleware or OptionalSessionMiddleware
        
    Example:
        >>> middleware = create_session_middleware(engine)
        >>> app.middleware_stack.add(middleware, priority=15)
    """
    if optional:
        return OptionalSessionMiddleware(session_engine)
    
    if session_engine is None:
        raise ValueError("session_engine required when optional=False")
    
    return SessionMiddleware(session_engine)


__all__ = [
    "SessionMiddleware",
    "OptionalSessionMiddleware",
    "create_session_middleware",
]
