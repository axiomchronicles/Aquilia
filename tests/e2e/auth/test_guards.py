"""
E2E Auth Tests — Guards Pipeline

Tests AuthGuard, ApiKeyGuard, ScopeGuard, RoleGuard as Flow pipeline nodes.
"""

import time
import pytest

from aquilia.auth.core import Identity, IdentityType, IdentityStatus, TokenClaims
from aquilia.auth.guards import AuthGuard, ScopeGuard, RoleGuard
from aquilia.auth.faults import (
    AUTH_REQUIRED,
    AUTHZ_INSUFFICIENT_SCOPE,
    AUTHZ_INSUFFICIENT_ROLE,
)


class _FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


def _claims(scopes=None, roles=None, sub="user-001"):
    now = int(time.time())
    return TokenClaims(
        iss="aquilia-test", sub=sub, aud=["test-api"],
        exp=now + 3600, iat=now, nbf=now, jti="test-jti",
        scopes=scopes or [], roles=roles or [],
    )


class TestAuthGuard:
    async def test_valid_token(self, auth_manager, seed_user):
        identity, pw = seed_user
        res = await auth_manager.authenticate_password(username="testuser@aquilia.dev", password=pw)
        guard = AuthGuard(auth_manager)
        ctx = await guard({"request": _FakeRequest({"authorization": f"Bearer {res.access_token}"})})
        assert ctx["identity"].id == identity.id

    async def test_missing_token(self, auth_manager):
        with pytest.raises(AUTH_REQUIRED):
            await AuthGuard(auth_manager)({"request": _FakeRequest({})})

    async def test_optional_missing(self, auth_manager):
        ctx = await AuthGuard(auth_manager, optional=True)({"request": _FakeRequest({})})
        assert ctx["identity"] is None

    async def test_optional_invalid(self, auth_manager):
        ctx = await AuthGuard(auth_manager, optional=True)(
            {"request": _FakeRequest({"authorization": "Bearer bad.token"})}
        )
        assert ctx["identity"] is None


class TestScopeGuard:
    async def test_passes(self):
        ctx = await ScopeGuard(required_scopes=["read"])({"token_claims": _claims(scopes=["read", "write"])})
        assert ctx

    async def test_fails(self):
        with pytest.raises(AUTHZ_INSUFFICIENT_SCOPE):
            await ScopeGuard(required_scopes=["admin"])({"token_claims": _claims(scopes=["read"])})


class TestRoleGuard:
    async def test_any(self):
        ctx = await RoleGuard(required_roles=["admin", "mod"])({"token_claims": _claims(roles=["mod"])})
        assert ctx

    async def test_all_fails(self):
        with pytest.raises(AUTHZ_INSUFFICIENT_ROLE):
            await RoleGuard(required_roles=["admin", "editor"], require_all=True)(
                {"token_claims": _claims(roles=["admin"])}
            )

    async def test_chain(self, auth_manager, seed_user):
        _, pw = seed_user
        res = await auth_manager.authenticate_password(username="testuser@aquilia.dev", password=pw, scopes=["profile", "read"])
        ctx = await AuthGuard(auth_manager)({"request": _FakeRequest({"authorization": f"Bearer {res.access_token}"})})
        ctx = await ScopeGuard(required_scopes=["profile"])(ctx)
        assert ctx["identity"] is not None
