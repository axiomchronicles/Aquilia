"""
Custom decorators for the auth module.
"""

from functools import wraps
from typing import Callable, Any, TypeVar
from aquilia.response import Response
from aquilia.sessions.decorators import authenticated, AuthenticationRequiredFault, SessionRequiredFault

F = TypeVar('F', bound=Callable[..., Any])

def authenticated_ui(func: F) -> F:
    """
    Decorator for UI endpoints that require authentication.
    
    If authentication fails, it redirects to the login page
    instead of raising a fault (which usually results in a 401 JSON).
    """
    # Use the standard @authenticated to handle session check and injection
    authenticated_func = authenticated(func)
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await authenticated_func(*args, **kwargs)
        except (AuthenticationRequiredFault, SessionRequiredFault):
            # Redirect to login page
            return Response.redirect("/auth/login", status=302)
            
    return wrapper
