"""
E2E conftest.py — shared fixtures for controller integration tests.

Provides:
- test_server: Boots an AquiliaServer with the full authentication app config
- client: TestClient wired to the test server
- registered_user: Seeds a user via the registration endpoint
- auth_tokens: Returns access + refresh tokens from a login
- authenticated_client: Client with a valid bearer token
"""

import pytest
import pytest_asyncio
import sys
import os
import asyncio

# Ensure authentication app is on the path
AUTH_APP = os.path.join(os.path.dirname(__file__), "..", "..", "authentication")
if AUTH_APP not in sys.path:
    sys.path.insert(0, os.path.abspath(AUTH_APP))

from aquilia.testing import TestClient, TestServer
from aquilia.manifest import AppManifest


# ---------------------------------------------------------------------------
# Unique test user data generator
# ---------------------------------------------------------------------------
_user_counter = 0

def _make_user_data(suffix: str = "") -> dict:
    """Generate unique user data for test isolation."""
    global _user_counter
    _user_counter += 1
    tag = f"{_user_counter}{suffix}"
    return {
        "email": f"testuser{tag}@example.com",
        "password": "Str0ngP@ss!",
        "full_name": f"Test User {tag}",
    }


DEFAULT_USER = {
    "email": "e2e-test@example.com",
    "password": "Str0ngP@ss!",
    "full_name": "E2E Test User",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def test_server():
    """
    Boot a fully-wired TestServer with the authentication app manifests.
    
    Each test function gets a fresh server instance so state never leaks.
    """
    # Import workspace lazily — it triggers key generation + config load
    from workspace import workspace

    # Build manifests from the workspace configuration
    manifests = []
    for mod in workspace._modules:
        manifests.append(AppManifest(
            name=mod.name,
            version=mod.version or "0.0.1",
            description=mod.description or "",
            controllers=list(mod.controllers or []),
            services=list(mod.services or []),
            route_prefix=mod.route_prefix or "",
            tags=list(mod.tags or []),
        ))

    # Calculate base path for templates/static
    base_dir = os.path.dirname(os.path.abspath(workspace.__file__)) if hasattr(workspace, "__file__") else AUTH_APP

    server = TestServer(
        manifests=manifests,
        config_overrides={
            "debug": True,
            "database": {
                "url": "sqlite:///:memory:",
                "auto_create": True,
                "auto_migrate": True,
            },
            "auth": {"enabled": True},
            "sessions": {
                "enabled": True,
                "transport": {
                    "cookie_name": "aq_session"
                }
            },
            "templates": {
                "enabled": True,
                "path": os.path.join(base_dir, "templates"),
                "search_paths": [os.path.join(base_dir, "templates")],
                "auto_discover": True
            },
            "security": {
                "secret_key": "test-secret-key-keep-it-stable",
                "token_issuer": "aquilia-e2e-tester"
            }
        },
        enable_sessions=True,
        enable_auth=True,
        enable_templates=True,
        enable_cache=True,
    )
    await server.start()
    yield server
    await server.stop()


@pytest_asyncio.fixture
async def client(test_server):
    """TestClient connected to the test server."""
    return TestClient(test_server, raise_server_exceptions=False)


@pytest_asyncio.fixture
async def registered_user(client):
    """
    Register a user and return their data + the registration response.
    
    Returns: dict with keys 'data' (the request payload) and 'response' (TestResponse).
    """
    data = _make_user_data("reg")
    resp = await client.post("/auth/register", json=data)
    return {"data": data, "response": resp}


@pytest_asyncio.fixture
async def auth_tokens(client, registered_user):
    """
    Login with the registered user and return token dict.
    
    Returns: dict with 'access_token', 'refresh_token', 'user_data'.
    """
    user_data = registered_user["data"]
    resp = await client.post("/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"],
    })
    tokens = resp.json()
    return {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "user_data": user_data,
    }


@pytest_asyncio.fixture
async def authenticated_client(client, auth_tokens):
    """Client with Authorization: Bearer header set."""
    client.set_bearer_token(auth_tokens["access_token"])
    yield client
    client.clear_auth()
