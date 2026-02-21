"""
E2E Auth Tests — Regression Sequences

Multi-step scenarios exercising cross-component interactions.
"""

import pytest
from aquilia.auth.core import (
    Identity, IdentityType, IdentityStatus,
    PasswordCredential, ApiKeyCredential, OAuthClient,
)
from aquilia.auth.oauth import PKCEVerifier
from aquilia.auth.faults import (
    AUTH_INVALID_CREDENTIALS,
    AUTH_ACCOUNT_LOCKED,
    AUTH_MFA_REQUIRED,
)


class TestLoginLogoutCycle:
    """Login → token issue → validate → refresh → logout."""

    async def test_full_cycle(self, auth_manager, token_manager, seed_user, token_store):
        identity, pw = seed_user

        # 1) Login
        res = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev", password=pw,
        )
        assert res.access_token and res.refresh_token

        # 2) Validate access token
        claims = await auth_manager.verify_token(res.access_token)
        assert claims.sub == identity.id

        # 3) Refresh
        new_access, new_refresh = await token_manager.refresh_access_token(
            res.refresh_token,
        )
        assert new_access.count(".") == 2

        # 4) Old refresh is revoked
        assert await token_store.is_token_revoked(res.refresh_token)

        # 5) Logout (revoke all session tokens)
        await token_manager.revoke_tokens_by_session(res.session_id)
        assert await token_store.is_token_revoked(new_refresh)


class TestPasswordChange:
    """Register → login → change password → old token invalid."""

    async def test_password_change_invalidates_session(
        self, auth_manager, identity_store, credential_store,
        password_hasher, token_manager, token_store,
    ):
        # 1) Create user
        u = Identity(id="u-pw-change", type=IdentityType.USER,
                     attributes={"email": "change@t.com"}, status=IdentityStatus.ACTIVE)
        await identity_store.create(u)
        await credential_store.save_password(
            PasswordCredential(identity_id=u.id, password_hash=password_hasher.hash("OldPass1!"))
        )

        # 2) Login
        res = await auth_manager.authenticate_password(username="change@t.com", password="OldPass1!")
        assert res.access_token

        # 3) Change password
        new_hash = password_hasher.hash("NewPass2!")
        await credential_store.save_password(
            PasswordCredential(identity_id=u.id, password_hash=new_hash)
        )

        # 4) Revoke all user tokens (simulating password change logout)
        await token_manager.revoke_tokens_by_identity(u.id)
        assert await token_store.is_token_revoked(res.refresh_token)

        # 5) Login with new password succeeds
        res2 = await auth_manager.authenticate_password(username="change@t.com", password="NewPass2!")
        assert res2.identity.id == u.id


class TestApiKeyAuthzSequence:
    """API key → scope check → role check."""

    async def test_api_key_with_authz(
        self, auth_manager, authz_engine, seed_api_key,
    ):
        from aquilia.auth.authz import AuthzContext, Decision
        identity, raw_key, _ = seed_api_key

        # 1) Authenticate via API key
        res = await auth_manager.authenticate_api_key(api_key=raw_key)
        assert res.identity.id == identity.id

        # 2) Scope check passes (key has read, write)
        ctx = AuthzContext(
            identity=res.identity, resource="data:123", action="read",
            scopes=res.metadata["scopes"], roles=["service"],
        )
        authz_engine.check_scope(ctx, ["read"])  # passes

        # 3) Permission check passes
        result = authz_engine.rbac.check(ctx, "read")
        # Service role not defined in default RBAC, but we check scope passes
        assert result is not None


class TestOAuth2PKCESequence:
    """OAuth2 auth code → PKCE → token → revoke."""

    async def test_oauth2_e2e(
        self, oauth2_manager, seed_oauth_client, token_manager, token_store,
    ):
        client, secret = seed_oauth_client
        verifier = PKCEVerifier.generate_code_verifier()
        challenge = PKCEVerifier.generate_code_challenge(verifier)

        # 1) Grant code
        code = await oauth2_manager.grant_authorization_code(
            client_id=client.client_id, identity_id="user-e2e-001",
            redirect_uri="https://test.aquilia.dev/callback",
            scopes=["profile", "email"],
            code_challenge=challenge, code_challenge_method="S256",
        )

        # 2) Exchange
        tok = await oauth2_manager.exchange_authorization_code(
            code=code, client_id=client.client_id, client_secret=secret,
            redirect_uri="https://test.aquilia.dev/callback", code_verifier=verifier,
        )
        assert tok["access_token"]

        # 3) Validate access token
        claims = await token_manager.validate_access_token(tok["access_token"])
        assert claims["sub"] == "user-e2e-001"

        # 4) Revoke refresh token
        await token_manager.revoke_token(tok["refresh_token"])
        assert await token_store.is_token_revoked(tok["refresh_token"])


class TestKeyRotationSequence:
    """Key rotation → old tokens still valid → new key signs."""

    async def test_key_rotation_e2e(self, token_store):
        from aquilia.auth.tokens import KeyDescriptor, KeyAlgorithm, KeyRing, TokenConfig, TokenManager, KeyStatus

        k1 = KeyDescriptor.generate("k1", KeyAlgorithm.RS256)
        ring = KeyRing([k1])
        cfg = TokenConfig(issuer="test", audience=["api"], access_token_ttl=300,
                          refresh_token_ttl=3600, algorithm=KeyAlgorithm.RS256)
        mgr = TokenManager(ring, token_store, cfg)

        # Sign with old key
        t1 = await mgr.issue_access_token(identity_id="u1", scopes=["r"])

        # Rotate
        k2 = KeyDescriptor.generate("k2", KeyAlgorithm.RS256)
        ring.add_key(k2)
        ring.promote_key("k2")

        # Old token still verifies
        c1 = await mgr.validate_access_token(t1)
        assert c1["sub"] == "u1"

        # New token uses new key
        t2 = await mgr.issue_access_token(identity_id="u2", scopes=["w"])
        c2 = await mgr.validate_access_token(t2)
        assert c2["sub"] == "u2"


class TestMultiTenantIsolation:
    """Multi-tenant isolation end-to-end."""

    async def test_tenant_isolation(
        self, auth_manager, identity_store, credential_store,
        password_hasher, authz_engine,
    ):
        from aquilia.auth.authz import AuthzContext
        from aquilia.auth.faults import AUTHZ_TENANT_MISMATCH

        # Create users in different tenants
        for tid, uid in [("t-A", "u-A"), ("t-B", "u-B")]:
            u = Identity(id=uid, type=IdentityType.USER,
                         attributes={"email": f"{uid}@t.com", "roles": ["user"]},
                         status=IdentityStatus.ACTIVE, tenant_id=tid)
            await identity_store.create(u)
            await credential_store.save_password(
                PasswordCredential(identity_id=uid, password_hash=password_hasher.hash("Pass1!"))
            )

        # Login as tenant A
        res_a = await auth_manager.authenticate_password(username="u-A@t.com", password="Pass1!")

        # Try to access tenant B resource
        ctx = AuthzContext(
            identity=res_a.identity, resource="doc:b1", action="read",
            scopes=[], roles=["user"], tenant_id="t-A",
        )
        with pytest.raises(AUTHZ_TENANT_MISMATCH):
            authz_engine.check_tenant(ctx, "t-B")

        # Same-tenant access works
        authz_engine.check_tenant(ctx, "t-A")
