"""
Shared test fixtures and helpers for Aquilia test suite.
"""

import asyncio
import pytest
from typing import Any, Dict, List, Optional

from aquilia.request import Request
from aquilia.response import Response
from aquilia._datastructures import MultiDict, Headers, URL
from aquilia.di.core import Container
from aquilia.auth.core import Identity, IdentityType, IdentityStatus
from aquilia.sessions.core import Session, SessionID

# Register Aquilia testing framework fixtures
from aquilia.testing.fixtures import aquilia_fixtures
aquilia_fixtures()

# Import fixtures so pytest can discover them
from aquilia.testing.fixtures import (  # noqa: F401
    test_config,
    fault_engine,
    effect_registry,
    cache_backend,
    di_container,
    identity_factory,
    mail_outbox,
    test_request,
    test_scope,
    test_server,
    test_client,
)


# ============================================================================
# Request Helpers
# ============================================================================


def make_scope(
    method: str = "GET",
    path: str = "/",
    query_string: str = "",
    headers: Optional[List[tuple]] = None,
    scheme: str = "http",
    client: Optional[tuple] = None,
) -> dict:
    """Build a minimal ASGI HTTP scope."""
    raw_headers = []
    if headers:
        for name, value in headers:
            raw_headers.append(
                (name.encode("latin-1") if isinstance(name, str) else name,
                 value.encode("latin-1") if isinstance(value, str) else value)
            )
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string.encode("utf-8") if isinstance(query_string, str) else query_string,
        "headers": raw_headers,
        "scheme": scheme,
        "server": ("127.0.0.1", 8000),
        "client": client or ("127.0.0.1", 12345),
        "root_path": "",
    }


def make_receive(body: bytes = b"", *, chunks: Optional[List[bytes]] = None):
    """Create an ASGI receive callable from body bytes or chunked list."""
    if chunks:
        messages = []
        for i, chunk in enumerate(chunks):
            messages.append({
                "type": "http.request",
                "body": chunk,
                "more_body": i < len(chunks) - 1,
            })
    else:
        messages = [{"type": "http.request", "body": body, "more_body": False}]

    idx = 0

    async def receive():
        nonlocal idx
        if idx < len(messages):
            msg = messages[idx]
            idx += 1
            return msg
        return {"type": "http.disconnect"}

    return receive


def make_request(
    method: str = "GET",
    path: str = "/",
    query_string: str = "",
    headers: Optional[List[tuple]] = None,
    body: bytes = b"",
    scheme: str = "http",
    client: Optional[tuple] = None,
    **kwargs,
) -> Request:
    """Build a full Request object for testing."""
    scope = make_scope(
        method=method,
        path=path,
        query_string=query_string,
        headers=headers,
        scheme=scheme,
        client=client,
    )
    receive = make_receive(body)
    return Request(scope, receive, **kwargs)


# ============================================================================
# Identity / Session Helpers
# ============================================================================


def make_identity(
    id: str = "user-1",
    type: IdentityType = IdentityType.USER,
    roles: Optional[List[str]] = None,
    scopes: Optional[List[str]] = None,
    status: IdentityStatus = IdentityStatus.ACTIVE,
    tenant_id: Optional[str] = None,
    **extra_attrs,
) -> Identity:
    """Create a test Identity."""
    attrs = {
        "email": f"{id}@test.com",
        "name": f"Test User {id}",
        "roles": roles or [],
        "scopes": scopes or [],
    }
    attrs.update(extra_attrs)
    return Identity(
        id=id,
        type=type,
        attributes=attrs,
        status=status,
        tenant_id=tenant_id,
    )


def make_session(
    identity_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Session:
    """Create a test Session."""
    sid = SessionID()
    s = Session(id=sid)
    if data:
        s.data.update(data)
    return s
