"""
Extended middleware components for Aquilia framework.

This module provides additional middleware beyond the core middleware.py:
- RequestScopeMiddleware: ASGI-level request-scoped DI container creation
- SimplifiedRequestScopeMiddleware: Higher-level request scope middleware
- SessionMiddleware: Session management middleware
"""

from .request_scope import RequestScopeMiddleware, SimplifiedRequestScopeMiddleware
from .session_middleware import SessionMiddleware

__all__ = [
    "RequestScopeMiddleware",
    "SimplifiedRequestScopeMiddleware",
    "SessionMiddleware",
]
