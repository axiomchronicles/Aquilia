"""
Users Module — Middleware

Custom authentication and authorization middleware
built on Aquilia's MiddlewareStack.
"""

import base64
import json
import time

from aquilia.request import Request
from aquilia.response import Response
from aquilia.auth import Identity, IdentityType, IdentityStatus

from .faults import (
    SessionExpiredFault,
    AccountDeactivatedFault,
    InsufficientPermissionsFault,
)


def _try_resolve_identity(request):
    """
    Attempt to decode a Bearer token from the Authorization header
    and set request.identity / ctx.identity if valid.
    Returns Identity or None.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = json.loads(base64.urlsafe_b64decode(token + "=="))
        # check expiry
        if payload.get("exp", 0) < time.time():
            return None
        return Identity(
            id=payload["sub"],
            type=IdentityType.USER,
            status=IdentityStatus.ACTIVE,
            attributes={
                "roles": [payload.get("role", "customer")],
                "email": payload.get("email", ""),
            },
        )
    except Exception:
        return None


class RequireAuthMiddleware:
    """
    Ensures the request has a valid authenticated identity.
    Integrates with Aquilia's auth middleware pipeline — runs after
    AquilAuthMiddleware to enforce authentication on protected routes.
    """

    # routes that skip auth — full paths including module prefix
    EXEMPT_PREFIXES = (
        "/users/auth/login",
        "/users/auth/register",
        "/products/categories",
        "/products/products",
        "/analytics/recommendations/similar",
        "/health",
        "/testaquilia",
    )

    EXEMPT_METHODS = {"OPTIONS", "HEAD"}

    async def __call__(self, request, ctx, next_handler):
        # Try to resolve identity from Bearer token if not already set
        if not getattr(request, "identity", None) or request.identity is None:
            identity = _try_resolve_identity(request)
            if identity:
                # Set identity via request.state (property reads from there)
                request.state["identity"] = identity
                ctx.identity = identity

        # skip exempt routes
        path = request.path
        if request.method in self.EXEMPT_METHODS:
            return await next_handler(request, ctx)

        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await next_handler(request, ctx)

        # check identity
        if not getattr(request, "identity", None):
            return Response.json(
                {"error": "Authentication required", "code": "USR-020"},
                status=401,
            )

        if request.identity.status != IdentityStatus.ACTIVE:
            raise AccountDeactivatedFault()

        return await next_handler(request, ctx)


class RoleGuardMiddleware:
    """
    Role-based access control middleware.

    Configured with required roles per path prefix.
    Uses Aquilia Identity roles for RBAC enforcement.
    """

    ROLE_REQUIREMENTS = {
        "/admin/admin": ["admin", "superadmin"],
        "/analytics/analytics": ["admin", "superadmin", "moderator"],
    }

    async def __call__(self, request, ctx, next_handler):
        path = request.path

        for prefix, required_roles in self.ROLE_REQUIREMENTS.items():
            if path.startswith(prefix):
                identity = getattr(request, "identity", None)
                if not identity:
                    return Response.json(
                        {"error": "Authentication required"},
                        status=401,
                    )

                user_roles = identity.attributes.get("roles", []) if hasattr(identity, 'attributes') else []
                if not any(role in required_roles for role in user_roles):
                    raise InsufficientPermissionsFault(
                        ", ".join(required_roles)
                    )
                break

        return await next_handler(request, ctx)


class RequestLoggingMiddleware:
    """
    Logs request metadata for audit trail.
    Captures user identity, path, method, and response status.
    """

    async def __call__(self, request, ctx, next_handler):
        import time
        import logging

        logger = logging.getLogger("nexus.audit")
        start = time.monotonic()

        response = await next_handler(request, ctx)

        elapsed = (time.monotonic() - start) * 1000
        identity_id = getattr(getattr(request, "identity", None), "id", "anonymous")

        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status,
                "elapsed_ms": round(elapsed, 2),
                "identity": identity_id,
                "ip": request.client_ip(),
            },
        )

        return response
