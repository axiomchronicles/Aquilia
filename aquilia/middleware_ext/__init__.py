"""
Extended middleware components for Aquilia framework.

This module provides additional middleware beyond the core middleware.py.
"""

from .request_scope import RequestScopeMiddleware

__all__ = ["RequestScopeMiddleware"]
