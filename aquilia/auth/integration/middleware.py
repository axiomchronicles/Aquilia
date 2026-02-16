"""
AquilAuth - Unified Middleware

Comprehensive middleware integrating:
- Aquilia Sessions (session management)
- AquilAuth (authentication/authorization)
- Aquilia DI (dependency injection)
- AquilaFaults (structured error handling)
- Flow pipeline (guards and transforms)

This is the primary middleware for production Aquilia applications.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from aquilia.di import Container
from aquilia.faults import FaultEngine
from aquilia.middleware import Handler, Middleware
from aquilia.request import Request
from aquilia.response import Response
from aquilia.sessions import SessionEngine

from ..core import Identity
from ..faults import AUTH_REQUIRED, AUTH_TOKEN_INVALID
from ..manager import AuthManager
from .aquila_sessions import (
    SessionAuthBridge,
    bind_identity,
    bind_token_claims,
    get_identity_id,
)

if TYPE_CHECKING:
    from aquilia.di import RequestCtx


# ============================================================================
# Unified Auth Middleware
# ============================================================================


class AquilAuthMiddleware:
    """
    Unified middleware for Auth + Sessions + DI integration.
    
    This middleware:
    1. Resolves session from SessionEngine
    2. Extracts auth data from session or token
    3. Injects identity into DI container
    4. Handles authentication errors with FaultEngine
    5. Commits session changes on response
    
    Order in middleware stack:
    1. RequestScopeMiddleware (creates DI container)
    2. FaultHandlerMiddleware (fault handling)
    3. AquilAuthMiddleware (this one)
    4. Application handlers
    """
    
    def __init__(
        self,
        session_engine: SessionEngine,
        auth_manager: AuthManager,
        fault_engine: FaultEngine | None = None,
        require_auth: bool = False,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize unified auth middleware.
        
        Args:
            session_engine: Aquilia SessionEngine
            auth_manager: AquilAuth AuthManager
            fault_engine: Optional FaultEngine for error handling
            require_auth: If True, require authentication for all routes
            logger: Optional logger
        """
        self.session_engine = session_engine
        self.auth_manager = auth_manager
        self.session_bridge = SessionAuthBridge(session_engine)
        self.fault_engine = fault_engine
        self.require_auth = require_auth
        self.logger = logger or logging.getLogger("aquilia.auth.middleware")
    
    async def __call__(
        self,
        request: Request,
        ctx: RequestCtx,
        next: Handler,
    ) -> Response:
        """
        Process request through auth pipeline.
        
        Args:
            request: Incoming request
            ctx: Request context (DI container)
            next: Next handler in chain
            
        Returns:
            Response from handler
        """
        # Get DI container from context
        container = getattr(ctx, "container", None)
        
        # Phase 1: Resolve session
        session = await self.session_engine.resolve(request, container)
        
        # Store session in request state
        request.state["session"] = session
        
        # Also set on ctx for template rendering
        ctx.session = session
        
        # Phase 2: Resolve identity (Bearer token overrides session)
        identity = None
        
        # 1. Try Authorization header
        auth_header = request.header("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                identity = await self.auth_manager.get_identity_from_token(token)
                if identity:
                    # Sync identity to session
                    bind_identity(session, identity)
                    
                    # Sync token claims to session
                    claims = await self.auth_manager.verify_token(token)
                    if claims:
                        bind_token_claims(session, claims)
            except Exception as e:
                self.logger.warning(f"Token authentication failed: {e}")
                # Continue and try session
        
        # 2. If no token, use identity from session
        if not identity:
            identity_id = get_identity_id(session)
            if identity_id:
                try:
                    identity = await self.auth_manager.identity_store.get(identity_id)
                except Exception as e:
                    self.logger.warning(f"Failed to load identity from session: {e}")
                    # Continue without identity
        
        # Phase 3: Check authentication requirement
        if self.require_auth and not identity:
            # No identity and auth required
            response = self._handle_auth_required()
            await self.session_engine.commit(session, response)
            return response
        
        # Phase 4: Inject identity into request and DI
        request.state["identity"] = identity
        request.state["authenticated"] = identity is not None
        
        # Also set on ctx for template rendering
        ctx.identity = identity
        
        if container and identity:
            # Register identity in DI container for injection
            if not container.is_registered(Identity):
                await container.register_instance(
                    Identity,
                    identity,
                    scope="request",
                )
        
        # Phase 5: Execute handler
        try:
            response = await next(request, ctx)
        except Exception as e:
            # Let all exceptions propagate to ExceptionMiddleware
            # which properly maps Faults to HTTP status codes.
            # The fault_engine is used for auth-specific operations
            # (e.g., _handle_auth_required) not for general exception handling.
            raise
        
        # Phase 6: Commit session
        await self.session_engine.commit(session, response)
        
        return response
    
    def _handle_auth_required(self) -> Response:
        """Create response for missing authentication."""
        if self.fault_engine:
            fault = AUTH_REQUIRED()
            # Convert to response
            return Response.json(
                {
                    "error": {
                        "code": fault.error_code,
                        "message": fault.public_message,
                        "retryable": fault.retryable,
                    }
                },
                status=401,
            )
        else:
            return Response.json(
                {"error": "Authentication required"},
                status=401,
            )
    
    def _fault_to_response(self, fault_result: Any) -> Response:
        """Convert fault result to HTTP response."""
        from aquilia.faults import Resolved, Fault, FaultDomain
        
        # If the result is a Resolved with a response, use it
        if hasattr(fault_result, 'value') and isinstance(fault_result.value, Response):
            return fault_result.value
        
        # If the result wraps a Fault, map to status code
        fault = getattr(fault_result, 'fault', None) or getattr(fault_result, 'original', None)
        if isinstance(fault, Fault):
            status_map = {
                FaultDomain.ROUTING: 404,
                FaultDomain.SECURITY: 403,
                FaultDomain.IO: 502,
                FaultDomain.EFFECT: 503,
            }
            status = status_map.get(fault.domain, 500)
            message = fault.message if (getattr(fault, 'public', False)) else "Internal server error"
            return Response.json(
                {"error": {"code": fault.code, "message": message, "domain": fault.domain.value}},
                status=status,
            )
        
        # Fallback
        return Response.json(
            {"error": "Internal server error"},
            status=500,
        )


# ============================================================================
# Optional Auth Middleware
# ============================================================================


class OptionalAuthMiddleware(AquilAuthMiddleware):
    """
    Auth middleware that doesn't require authentication.
    
    Same as AquilAuthMiddleware but with require_auth=False.
    Use this for public endpoints that can benefit from auth if present.
    """
    
    def __init__(
        self,
        session_engine: SessionEngine,
        auth_manager: AuthManager,
        fault_engine: FaultEngine | None = None,
        logger: logging.Logger | None = None,
    ):
        super().__init__(
            session_engine=session_engine,
            auth_manager=auth_manager,
            fault_engine=fault_engine,
            require_auth=False,
            logger=logger,
        )


# ============================================================================
# Session-only Middleware
# ============================================================================


class SessionMiddleware:
    """
    Session-only middleware without authentication.
    
    Use this for applications that need sessions but not auth.
    """
    
    def __init__(
        self,
        session_engine: SessionEngine,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize session middleware.
        
        Args:
            session_engine: Aquilia SessionEngine
            logger: Optional logger
        """
        self.session_engine = session_engine
        self.logger = logger or logging.getLogger("aquilia.sessions.middleware")
    
    async def __call__(
        self,
        request: Request,
        ctx: RequestCtx,
        next: Handler,
    ) -> Response:
        """Process request with session management."""
        # Get DI container
        container = getattr(ctx, "container", None)
        
        # Resolve session
        session = await self.session_engine.resolve(request, container)
        
        # Store in request state
        request.state["session"] = session
        
        # Also set on ctx for template rendering
        ctx.session = session
        
        # Register in DI if available
        if container:
            from aquilia.di.providers import ValueProvider
            from aquilia.sessions import Session
            container.register(
                ValueProvider(
                    value=session,
                    token=Session,
                    scope="request",
                )
            )
        
        # Execute handler
        response = await next(request, ctx)
        
        # Commit session
        await self.session_engine.commit(session, response)
        
        return response


# ============================================================================
# Fault Handler Middleware
# ============================================================================


class FaultHandlerMiddleware:
    """
    Middleware for handling faults with FaultEngine.
    
    Should be registered early in middleware stack.
    """
    
    def __init__(
        self,
        fault_engine: FaultEngine,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize fault handler middleware.
        
        Args:
            fault_engine: FaultEngine instance
            logger: Optional logger
        """
        self.fault_engine = fault_engine
        self.logger = logger or logging.getLogger("aquilia.faults.middleware")
    
    async def __call__(
        self,
        request: Request,
        ctx: RequestCtx,
        next: Handler,
    ) -> Response:
        """Process request with fault handling."""
        try:
            return await next(request, ctx)
        except Exception as e:
            # Process fault
            from aquilia.faults import FaultContext, Resolved
            
            result = await self.fault_engine.process(e)
            
            if isinstance(result, Resolved):
                # Fault was resolved, return response
                if hasattr(result, "response") and result.response:
                    return result.response
                
                # Create response from fault
                if hasattr(e, "error_code"):
                    # Structured fault
                    return Response.json(
                        {
                            "error": {
                                "code": e.error_code,
                                "message": e.public_message,
                                "retryable": e.retryable,
                            }
                        },
                        status=e.http_status if hasattr(e, "http_status") else 500,
                    )
                else:
                    # Unknown error
                    self.logger.error(f"Unhandled exception: {e}", exc_info=True)
                    return Response.json(
                        {"error": "Internal server error"},
                        status=500,
                    )
            else:
                # Fault not resolved, re-raise
                raise


# ============================================================================
# Request Scope Middleware (Enhanced)
# ============================================================================


class EnhancedRequestScopeMiddleware:
    """
    Enhanced request scope middleware with better integration.
    
    Creates request-scoped DI container and provides access to:
    - Request object
    - Session (if SessionMiddleware is used)
    - Identity (if AuthMiddleware is used)
    """
    
    def __init__(
        self,
        app_container: Container,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize request scope middleware.
        
        Args:
            app_container: App-scoped DI container
            logger: Optional logger
        """
        self.app_container = app_container
        self.logger = logger or logging.getLogger("aquilia.di.middleware")
    
    async def __call__(
        self,
        request: Request,
        ctx: RequestCtx,
        next: Handler,
    ) -> Response:
        """Process request with request-scoped DI."""
        # Create request-scoped container
        request_container = self.app_container.create_request_scope()
        
        # Store in context
        ctx.container = request_container
        request.state["di_container"] = request_container
        
        # Register request in DI
        from aquilia.di.providers import ValueProvider
        request_container.register(
            ValueProvider(
                value=request,
                token=Request,
                scope="request",
            )
        )
        
        try:
            # Execute handler
            response = await next(request, ctx)
        finally:
            # Cleanup request-scoped resources
            # Properly dispose of the request-scoped container to release
            # any held resources (DB connections, file handles, etc.)
            try:
                if hasattr(request_container, 'shutdown'):
                    await request_container.shutdown()
                elif hasattr(request_container, 'dispose'):
                    request_container.dispose()
            except Exception as cleanup_err:
                self.logger.debug(f"Container cleanup error (non-fatal): {cleanup_err}")
        
        return response


# ============================================================================
# Complete Middleware Stack Factory
# ============================================================================


def create_auth_middleware_stack(
    session_engine: SessionEngine,
    auth_manager: AuthManager,
    app_container: Container,
    fault_engine: FaultEngine | None = None,
    require_auth: bool = False,
) -> list[Middleware]:
    """
    Create complete middleware stack for authenticated app.
    
    Args:
        session_engine: SessionEngine instance
        auth_manager: AuthManager instance
        app_container: App-scoped DI container
        fault_engine: Optional FaultEngine
        require_auth: Require auth for all routes
        
    Returns:
        List of middleware in correct order
    """
    stack = []
    
    # 1. Request scope (creates DI container)
    stack.append(EnhancedRequestScopeMiddleware(app_container))
    
    # 2. Fault handler (catches errors)
    if fault_engine:
        stack.append(FaultHandlerMiddleware(fault_engine))
    
    # 3. Auth + Sessions (authentication)
    stack.append(
        AquilAuthMiddleware(
            session_engine=session_engine,
            auth_manager=auth_manager,
            fault_engine=fault_engine,
            require_auth=require_auth,
        )
    )
    
    return stack


# ============================================================================
# Exports
# ============================================================================


__all__ = [
    "AquilAuthMiddleware",
    "OptionalAuthMiddleware",
    "SessionMiddleware",
    "FaultHandlerMiddleware",
    "EnhancedRequestScopeMiddleware",
    "create_auth_middleware_stack",
]
