"""
E2E Auth Regression Tests — Shared Fixtures

All fixtures are function-scoped to guarantee full isolation between tests.
Uses in-memory stores (no Docker/Redis/DB required).
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from aquilia.auth.core import (
    Identity,
    IdentityType,
    IdentityStatus,
    PasswordCredential,
    ApiKeyCredential,
    OAuthClient,
    MFACredential,
)
from aquilia.auth.hashing import PasswordHasher
from aquilia.auth.tokens import (
    KeyDescriptor,
    KeyAlgorithm,
    KeyRing,
    TokenManager,
    TokenConfig,
)
from aquilia.auth.stores import (
    MemoryIdentityStore,
    MemoryCredentialStore,
    MemoryTokenStore,
    MemoryOAuthClientStore,
    MemoryAuthorizationCodeStore,
    MemoryDeviceCodeStore,
)
from aquilia.auth.manager import AuthManager, RateLimiter
from aquilia.auth.oauth import OAuth2Manager, PKCEVerifier
from aquilia.auth.mfa import MFAManager, TOTPProvider
from aquilia.auth.authz import (
    AuthzEngine,
    RBACEngine,
    ABACEngine,
    AuthzContext,
    Decision,
    AuthzResult,
)
from aquilia.auth.guards import (
    Guard,
    AuthGuard,
    ApiKeyGuard,
    AuthzGuard,
    ScopeGuard,
    RoleGuard,
)


# ============================================================================
# Core Stores (fresh per test)
# ============================================================================


@pytest.fixture
def identity_store():
    """Fresh in-memory identity store."""
    return MemoryIdentityStore()


@pytest.fixture
def credential_store():
    """Fresh in-memory credential store."""
    return MemoryCredentialStore()


@pytest.fixture
def token_store():
    """Fresh in-memory token store."""
    return MemoryTokenStore()


# ============================================================================
# Cryptographic Key Ring
# ============================================================================


@pytest.fixture
def key_descriptor():
    """Generate a real RSA-2048 key pair for signing/verification."""
    return KeyDescriptor.generate("test_key_001", KeyAlgorithm.RS256)


@pytest.fixture
def key_ring(key_descriptor):
    """Key ring with one active RSA key."""
    return KeyRing([key_descriptor])


# ============================================================================
# Token Manager
# ============================================================================


@pytest.fixture
def token_config():
    """Token config with short TTLs for fast testing."""
    return TokenConfig(
        issuer="aquilia-test",
        audience=["test-api"],
        access_token_ttl=300,      # 5 minutes
        refresh_token_ttl=3600,    # 1 hour
        algorithm=KeyAlgorithm.RS256,
    )


@pytest.fixture
def token_manager(key_ring, token_store, token_config):
    """Token manager wired to test stores."""
    return TokenManager(key_ring, token_store, token_config)


# ============================================================================
# Password Hasher (PBKDF2 for speed in tests)
# ============================================================================


@pytest.fixture
def password_hasher():
    """Password hasher using PBKDF2 (faster than argon2 for tests)."""
    return PasswordHasher(algorithm="pbkdf2_sha256", iterations=1000)


# ============================================================================
# Rate Limiter
# ============================================================================


@pytest.fixture
def rate_limiter():
    """Rate limiter with low thresholds for fast testing."""
    return RateLimiter(
        max_attempts=3,
        window_seconds=60,
        lockout_duration=5,  # 5 seconds for fast test cycles
    )


# ============================================================================
# Auth Manager
# ============================================================================


@pytest.fixture
def auth_manager(identity_store, credential_store, token_manager, password_hasher, rate_limiter):
    """Full AuthManager wired to all test stores."""
    return AuthManager(
        identity_store=identity_store,
        credential_store=credential_store,
        token_manager=token_manager,
        password_hasher=password_hasher,
        rate_limiter=rate_limiter,
    )


# ============================================================================
# OAuth2
# ============================================================================


@pytest.fixture
def oauth_client_store():
    """Fresh OAuth client store."""
    return MemoryOAuthClientStore()


@pytest.fixture
def auth_code_store():
    """Fresh authorization code store."""
    return MemoryAuthorizationCodeStore()


@pytest.fixture
def device_code_store():
    """Fresh device code store."""
    return MemoryDeviceCodeStore()


@pytest.fixture
def oauth2_manager(oauth_client_store, auth_code_store, device_code_store, token_manager):
    """OAuth2Manager wired to test stores."""
    return OAuth2Manager(
        client_store=oauth_client_store,
        code_store=auth_code_store,
        device_store=device_code_store,
        token_manager=token_manager,
        issuer="https://test.aquilia.dev",
    )


# ============================================================================
# MFA
# ============================================================================


@pytest.fixture
def totp_provider():
    """TOTP provider with default settings."""
    return TOTPProvider(issuer="AquiliaTest")


@pytest.fixture
def mfa_manager(totp_provider):
    """MFAManager with TOTP provider."""
    return MFAManager(totp_provider=totp_provider)


# ============================================================================
# Authorization
# ============================================================================


@pytest.fixture
def rbac_engine():
    """RBAC engine with pre-defined roles."""
    engine = RBACEngine()
    engine.define_role("viewer", ["read"])
    engine.define_role("editor", ["read", "write"], inherits=["viewer"])
    engine.define_role("admin", ["read", "write", "delete", "admin"], inherits=["editor"])
    return engine


@pytest.fixture
def abac_engine():
    """ABAC engine (empty — tests register policies as needed)."""
    return ABACEngine()


@pytest.fixture
def authz_engine(rbac_engine, abac_engine):
    """Unified AuthzEngine combining RBAC + ABAC."""
    return AuthzEngine(rbac=rbac_engine, abac=abac_engine)


# ============================================================================
# Seed Data Helpers
# ============================================================================

TEST_PASSWORD = "SecureP@ss123!"
TEST_EMAIL = "testuser@aquilia.dev"
TEST_USERNAME = "testuser"


@pytest.fixture
async def seed_user(identity_store, credential_store, password_hasher):
    """
    Create a test user identity with password credential.

    Returns (identity, raw_password) tuple.
    """
    identity = Identity(
        id="user-e2e-001",
        type=IdentityType.USER,
        attributes={
            "email": TEST_EMAIL,
            "username": TEST_USERNAME,
            "name": "E2E Test User",
            "roles": ["user"],
            "scopes": ["profile", "read"],
        },
        status=IdentityStatus.ACTIVE,
        tenant_id="tenant-001",
    )
    await identity_store.create(identity)

    pw_hash = password_hasher.hash(TEST_PASSWORD)
    credential = PasswordCredential(
        identity_id=identity.id,
        password_hash=pw_hash,
    )
    await credential_store.save_password(credential)

    return identity, TEST_PASSWORD


@pytest.fixture
async def seed_api_key(identity_store, credential_store):
    """
    Create a test service identity with an API key credential.

    Returns (identity, raw_api_key, credential) tuple.
    """
    identity = Identity(
        id="svc-e2e-001",
        type=IdentityType.SERVICE,
        attributes={
            "name": "E2E Test Service",
            "roles": ["service"],
            "scopes": ["read", "write"],
        },
        status=IdentityStatus.ACTIVE,
    )
    await identity_store.create(identity)

    raw_key = ApiKeyCredential.generate_key(env="test")
    key_hash = ApiKeyCredential.hash_key(raw_key)
    credential = ApiKeyCredential(
        identity_id=identity.id,
        key_id="key-e2e-001",
        key_hash=key_hash,
        prefix=raw_key[:8],
        scopes=["read", "write"],
    )
    await credential_store.save_api_key(credential)

    return identity, raw_key, credential


@pytest.fixture
async def seed_oauth_client(oauth_client_store, password_hasher):
    """
    Create a test OAuth2 client.

    Returns (client, raw_client_secret) tuple.
    """
    raw_secret = OAuthClient.generate_client_secret()
    secret_hash = password_hasher.hash(raw_secret)

    client = OAuthClient(
        client_id="test-app-e2e",
        client_secret_hash=secret_hash,
        name="E2E Test App",
        grant_types=["authorization_code", "client_credentials", "refresh_token"],
        redirect_uris=["https://test.aquilia.dev/callback"],
        scopes=["profile", "email", "read", "write"],
        require_pkce=True,
        require_consent=False,
        access_token_ttl=300,
        refresh_token_ttl=3600,
    )
    await oauth_client_store.create(client)

    return client, raw_secret
