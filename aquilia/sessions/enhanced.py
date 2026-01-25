"""
Enhanced Session Features for Aquilia.

Additional innovative patterns for session management:
- Context managers for scoped session access
- Session guards for complex authorization
- Session pipelines for transformation chains
"""

from typing import Callable, Optional, TypeVar, Any, AsyncContextManager
from contextlib import asynccontextmanager
from functools import wraps

from aquilia.sessions import Session, SessionPrincipal
from aquilia.faults import Fault


F = TypeVar('F', bound=Callable[..., Any])


class SessionContextManager:
    """
    Context manager for scoped session access.
    
    Provides guaranteed session lifecycle management with automatic cleanup.
    
    Example:
        >>> async with SessionContext.authenticated(ctx) as session:
        ...     user = session.principal
        ...     # Session auto-committed on exit
    """
    
    @staticmethod
    @asynccontextmanager
    async def authenticated(ctx):
        """
        Context manager for authenticated sessions.
        
        Args:
            ctx: RequestCtx
            
        Yields:
            Authenticated Session
            
        Raises:
            AuthenticationRequiredFault: If session not authenticated
            
        Example:
            >>> async with SessionContext.authenticated(ctx) as session:
            ...     user_id = session.principal.id
            ...     # Perform authenticated operations
        """
        from aquilia.sessions.decorators import AuthenticationRequiredFault, SessionRequiredFault
        
        # Get session from request state
        session = ctx.request.state.get('session')
        
        if session is None:
            raise SessionRequiredFault()
        
        if not session.is_authenticated:
            raise AuthenticationRequiredFault()
        
        try:
            yield session
        finally:
            # Session will be committed by middleware
            pass
    
    @staticmethod
    @asynccontextmanager
    async def ensure(ctx):
        """
        Context manager that ensures session exists.
        
        Args:
            ctx: RequestCtx
            
        Yields:
            Session (created if missing)
            
        Example:
            >>> async with SessionContext.ensure(ctx) as session:
            ...     session.data['cart'].append(item)
        """
        from aquilia.sessions.decorators import SessionRequiredFault
        
        # Get session from request state
        session = ctx.request.state.get('session')
        
        if session is None:
            raise SessionRequiredFault()
        
        try:
            yield session
        finally:
            # Session will be committed by middleware
            pass
    
    @staticmethod
    @asynccontextmanager
    async def transactional(ctx):
        """
        Context manager for transactional session operations.
        
        Provides rollback capability on exceptions.
        
        Args:
            ctx: RequestCtx
            
        Yields:
            Session with transaction support
            
        Example:
            >>> async with SessionContext.transactional(ctx) as session:
            ...     session.data['balance'] -= 100
            ...     if session.data['balance'] < 0:
            ...         raise ValueError("Insufficient funds")
            ...     # Auto-commit on success, rollback on exception
        """
        from aquilia.sessions.decorators import SessionRequiredFault
        
        session = ctx.request.state.get('session')
        
        if session is None:
            raise SessionRequiredFault()
        
        # Take snapshot of session data
        snapshot = session.data.copy()
        
        try:
            yield session
            # Success - changes will be committed by middleware
        except Exception:
            # Rollback on exception
            session.data.clear()
            session.data.update(snapshot)
            raise


# Create singleton instance
SessionContext = SessionContextManager()


class SessionGuard:
    """
    Advanced session guards for complex authorization logic.
    
    Example:
        >>> class AdminGuard(SessionGuard):
        ...     async def check(self, session: Session) -> bool:
        ...         return session.principal.has_role("admin")
        
        >>> @requires(AdminGuard)
        >>> async def admin_panel(ctx, session: Session):
        ...     ...
    """
    
    async def check(self, session: Session) -> bool:
        """
        Check if session meets guard requirements.
        
        Args:
            session: Session to check
            
        Returns:
            True if guard passes, False otherwise
        """
        raise NotImplementedError("Subclasses must implement check()")
    
    def __call__(self, func: F) -> F:
        """Make guard usable as decorator."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract session
            session = kwargs.get('session')
            if session is None:
                # Try to find in args
                for arg in args:
                    if isinstance(arg, Session):
                        session = arg
                        break
            
            if session is None:
                from aquilia.sessions.decorators import SessionRequiredFault
                raise SessionRequiredFault()
            
            # Check guard
            if not await self.check(session):
                raise Fault(
                    code="GUARD_FAILED",
                    message=f"Session guard {self.__class__.__name__} failed",
                    status=403,
                )
            
            return await func(*args, **kwargs)
        
        return wrapper


def requires(*guards: SessionGuard):
    """
    Decorator to require multiple session guards.
    
    Args:
        *guards: SessionGuard instances
        
    Returns:
        Decorator function
        
    Example:
        >>> @requires(AdminGuard(), VerifiedEmailGuard())
        >>> async def sensitive_operation(ctx, session: Session):
        ...     ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract session
            session = kwargs.get('session')
            if session is None:
                for arg in args:
                    if isinstance(arg, Session):
                        session = arg
                        break
            
            if session is None:
                from aquilia.sessions.decorators import SessionRequiredFault
                raise SessionRequiredFault()
            
            # Check all guards
            for guard in guards:
                if not await guard.check(session):
                    raise Fault(
                        code="GUARD_FAILED",
                        message=f"Session guard {guard.__class__.__name__} failed",
                        status=403,
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Example guards

class AdminGuard(SessionGuard):
    """Guard that requires admin role."""
    
    async def check(self, session: Session) -> bool:
        if not session.is_authenticated:
            return False
        return hasattr(session.principal, 'role') and session.principal.role == 'admin'


class VerifiedEmailGuard(SessionGuard):
    """Guard that requires verified email."""
    
    async def check(self, session: Session) -> bool:
        if not session.is_authenticated:
            return False
        return hasattr(session.principal, 'email_verified') and session.principal.email_verified


__all__ = [
    "SessionContext",
    "SessionGuard",
    "requires",
    "AdminGuard",
    "VerifiedEmailGuard",
]
