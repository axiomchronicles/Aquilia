"""
Unique Session Decorators for Aquilia.

Provides fluent, type-safe decorators for session management that are
distinctly Aquilia's own - not copied from any other framework.

Features:
- @session.require() - Require session with specific properties
- @session.ensure() - Ensure session exists (create if missing)
- @session.optional() - Session is optional
- @authenticated - Shorthand for authenticated sessions
- @stateful - Shorthand for stateful sessions

Example:
    >>> @GET("/profile")
    >>> @session.require(authenticated=True)
    >>> async def profile(ctx: RequestCtx, session: Session):
    ...     return {"user": session.principal.id}
    
    >>> @POST("/cart")
    >>> @stateful
    >>> async def cart(ctx: RequestCtx, state: SessionState):
    ...     state.cart.append(item)
"""

from typing import Callable, Optional, TypeVar, Any
from functools import wraps
import inspect

from aquilia.sessions import Session, SessionPrincipal
from aquilia.faults import Fault


F = TypeVar('F', bound=Callable[..., Any])


class SessionRequiredFault(Fault):
    """Raised when session is required but missing."""
    
    def __init__(self):
        from aquilia.faults import FaultDomain
        super().__init__(
            code="SESSION_REQUIRED",
            message="Session required for this endpoint",
            domain=FaultDomain.SECURITY,
        )


class AuthenticationRequiredFault(Fault):
    """Raised when authentication is required but session is not authenticated."""
    
    def __init__(self):
        from aquilia.faults import FaultDomain
        super().__init__(
            code="AUTHENTICATION_REQUIRED",
            message="Authentication required for this endpoint",
            domain=FaultDomain.SECURITY,
        )


class SessionDecorators:
    """Namespace for session decorators."""
    
    @staticmethod
    def require(authenticated: bool = False, **kwargs) -> Callable[[F], F]:
        """
        Require session with specific properties.
        
        Args:
            authenticated: If True, require authenticated session
            **kwargs: Additional session requirements
            
        Returns:
            Decorator function
            
        Example:
            >>> @session.require(authenticated=True)
            >>> async def profile(ctx, session: Session):
            ...     return {"user": session.principal.id}
        """
        def decorator(func: F) -> F:
            @wraps(func)
            async def wrapper(*args, **func_kwargs):
                # Extract session from kwargs
                session = func_kwargs.get('session')
                
                # If session not in kwargs, try to get from RequestCtx first, then request state
                if session is None:
                    # Find RequestCtx in args
                    ctx = None
                    for arg in args:
                        if hasattr(arg, 'session') and hasattr(arg, 'request'):
                            ctx = arg
                            break
                    
                    if ctx:
                        # Use RequestCtx.session directly (preferred)
                        session = ctx.session
                    elif ctx and hasattr(ctx, 'request'):
                        # Fallback: check request state
                        session = ctx.request.state.get('session')
                
                # Check if session exists
                if session is None:
                    raise SessionRequiredFault()
                
                # Check authentication requirement
                if authenticated and not session.is_authenticated:
                    raise AuthenticationRequiredFault()
                
                # Inject session into kwargs if not already there and if accepted by signature
                if 'session' not in func_kwargs:
                    sig = inspect.signature(func)
                    if 'session' in sig.parameters:
                        func_kwargs['session'] = session
                
                return await func(*args, **func_kwargs)
            
            # Mark function as requiring session
            wrapper.__session_required__ = True
            wrapper.__session_authenticated__ = authenticated
            
            return wrapper
        
        return decorator
    
    @staticmethod
    def ensure() -> Callable[[F], F]:
        """
        Ensure session exists (create if missing).
        
        This decorator guarantees a session will be available,
        creating one if it doesn't exist.
        
        Returns:
            Decorator function
            
        Example:
            >>> @session.ensure()
            >>> async def cart(ctx, session: Session):
            ...     session.data.cart.append(item)
        """
        def decorator(func: F) -> F:
            @wraps(func)
            async def wrapper(*args, **func_kwargs):
                # Extract session from kwargs or request state
                session = func_kwargs.get('session')
                
                if session is None:
                    # Find RequestCtx in args (preferred)
                    ctx = None
                    for arg in args:
                        if hasattr(arg, 'session') and hasattr(arg, 'request'):
                            ctx = arg
                            break
                    
                    if ctx:
                        # Use RequestCtx.session directly
                        session = ctx.session
                        
                        # If still None, attempt resolution via SessionEngine
                        if session is None:
                            try:
                                from aquilia.sessions import SessionEngine
                                # Use resolve_async since we're in an async wrapper
                                engine = await ctx.container.resolve_async(SessionEngine)
                                session = await engine.resolve(ctx.request)
                                
                                # Store back in ctx and request for downstream
                                ctx.session = session
                                ctx.request.state['session'] = session
                            except Exception:
                                # If SessionEngine not available or resolution fails,
                                # this means session middleware is not configured.
                                # For @session.ensure(), we should create a minimal session
                                # rather than failing.
                                from aquilia.sessions import Session, SessionID
                                from datetime import datetime, timezone
                                import uuid
                                
                                # Create a minimal session for this request
                                session_id = SessionID()  # Creates random ID
                                session = Session(
                                    id=session_id,
                                    created_at=datetime.now(timezone.utc),
                                    last_accessed_at=datetime.now(timezone.utc),
                                    data={},
                                    principal=None,
                                )
                                
                                # Store in ctx and request state
                                ctx.session = session
                                ctx.request.state['session'] = session
                    elif ctx and hasattr(ctx, 'request'):
                        # Fallback: check request state
                        session = ctx.request.state.get('session')
                
                # Session should now exist
                # Inject session into kwargs if accepted by signature
                if session and 'session' not in func_kwargs:
                    sig = inspect.signature(func)
                    if 'session' in sig.parameters:
                        func_kwargs['session'] = session
                
                return await func(*args, **func_kwargs)
            
            wrapper.__session_ensure__ = True
            
            return wrapper
        
        return decorator
    
    @staticmethod
    def optional() -> Callable[[F], F]:
        """
        Session is optional.
        
        The handler will receive Session | None.
        
        Returns:
            Decorator function
            
        Example:
            >>> @session.optional()
            >>> async def public(ctx, session: Session | None):
            ...     if session:
            ...         return {"user": session.principal.id}
            ...     return {"user": None}
        """
        def decorator(func: F) -> F:
            @wraps(func)
            async def wrapper(*args, **func_kwargs):
                # Extract session from kwargs or request state
                session = func_kwargs.get('session')
                
                if session is None:
                    # Find RequestCtx in args (preferred)
                    ctx = None
                    for arg in args:
                        if hasattr(arg, 'session') and hasattr(arg, 'request'):
                            ctx = arg
                            break
                    
                    if ctx:
                        # Use RequestCtx.session directly
                        session = ctx.session
                    elif ctx and hasattr(ctx, 'request'):
                        # Fallback: check request state
                        session = ctx.request.state.get('session')
                
                # Inject session (or None) into kwargs if accepted by signature
                if 'session' not in func_kwargs:
                    sig = inspect.signature(func)
                    if 'session' in sig.parameters:
                        func_kwargs['session'] = session
                
                return await func(*args, **func_kwargs)
            
            wrapper.__session_optional__ = True
            
            return wrapper
        
        return decorator


# Create singleton instance
session = SessionDecorators()


def authenticated(func: F) -> F:
    """
    Shorthand decorator for authenticated sessions.
    
    Automatically extracts SessionPrincipal from authenticated session.
    
    Example:
        >>> @authenticated
        >>> async def profile(ctx, user: SessionPrincipal):
        ...     return {"user_id": user.id}
    """
    @wraps(func)
    async def wrapper(*args, **func_kwargs):
        # Extract session from kwargs or request state
        sess = func_kwargs.get('session')
        
        if sess is None:
            # Find RequestCtx in args (preferred)
            ctx = None
            for arg in args:
                if hasattr(arg, 'session') and hasattr(arg, 'request'):
                    ctx = arg
                    break
            
            if ctx:
                # Use RequestCtx.session directly
                sess = ctx.session
            elif ctx and hasattr(ctx, 'request'):
                # Fallback: check request state
                sess = ctx.request.state.get('session')
        
        # Check session exists and is authenticated
        if sess is None:
            raise SessionRequiredFault()
        
        if not sess.is_authenticated:
            raise AuthenticationRequiredFault()
        
        # Check if function expects 'user' or 'principal' parameter
        sig = inspect.signature(func)
        if 'user' in sig.parameters:
            func_kwargs['user'] = sess.principal
        elif 'principal' in sig.parameters:
            func_kwargs['principal'] = sess.principal
        else:
            # Fallback: inject session if accepted by signature
            if 'session' in sig.parameters:
                func_kwargs['session'] = sess
        
        return await func(*args, **func_kwargs)
    
    wrapper.__authenticated__ = True
    
    return wrapper


def stateful(func: F) -> F:
    """
    Shorthand decorator for stateful sessions.
    
    Automatically provides SessionState wrapper for session.data.
    
    Example:
        >>> @stateful
        >>> async def save_prefs(ctx, state: SessionState):
        ...     state.theme = "dark"
    """
    @wraps(func)
    async def wrapper(*args, **func_kwargs):
        # Extract session from kwargs or request state
        sess = func_kwargs.get('session')
        
        if sess is None:
            # Find RequestCtx in args (preferred)
            ctx = None
            for arg in args:
                if hasattr(arg, 'session') and hasattr(arg, 'request'):
                    ctx = arg
                    break
            
            if ctx:
                # Use RequestCtx.session directly
                sess = ctx.session
            elif ctx and hasattr(ctx, 'request'):
                # Fallback: check request state
                sess = ctx.request.state.get('session')
        
        # Session should exist (created by middleware)
        if sess is None:
            raise SessionRequiredFault()
        
        # Check if function expects 'state' parameter
        sig = inspect.signature(func)
        if 'state' in sig.parameters:
            # Wrap session.data in SessionState
            from aquilia.sessions.state import SessionState
            func_kwargs['state'] = SessionState(sess.data)
        else:
            # Fallback: inject session if accepted by signature
            if 'session' in sig.parameters:
                func_kwargs['session'] = sess
        
        return await func(*args, **func_kwargs)
    
    wrapper.__stateful__ = True
    
    return wrapper


__all__ = [
    "session",
    "authenticated",
    "stateful",
    "SessionRequiredFault",
    "AuthenticationRequiredFault",
]
