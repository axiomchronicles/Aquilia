"""
Test 11: Auth System (auth/)

Tests Identity, Credentials, PasswordHasher, KeyDescriptor, tokens,
AuthzEngine concepts, flow_guards.
"""

import pytest
from datetime import datetime, timezone

from aquilia.auth.core import (
    Identity,
    IdentityType,
    IdentityStatus,
    PasswordCredential,
    ApiKeyCredential,
)
from aquilia.auth.hashing import PasswordHasher


# ============================================================================
# Identity
# ============================================================================

class TestIdentity:

    def test_create(self):
        identity = Identity(
            id="user-1",
            type=IdentityType.USER,
            attributes={"name": "Alice"},
        )
        assert identity.id == "user-1"
        assert identity.type == IdentityType.USER
        assert identity.attributes["name"] == "Alice"

    def test_identity_types(self):
        assert IdentityType.USER is not None
        assert IdentityType.SERVICE is not None
        assert IdentityType.DEVICE is not None
        assert IdentityType.ANONYMOUS is not None

    def test_identity_status(self):
        assert IdentityStatus.ACTIVE is not None
        assert IdentityStatus.SUSPENDED is not None
        assert IdentityStatus.DELETED is not None

    def test_identity_default_status(self):
        identity = Identity(
            id="user-2",
            type=IdentityType.USER,
            attributes={},
        )
        assert identity.status == IdentityStatus.ACTIVE

    def test_identity_frozen(self):
        identity = Identity(
            id="user-3",
            type=IdentityType.USER,
            attributes={},
        )
        with pytest.raises(AttributeError):
            identity.id = "new-id"

    def test_identity_with_tenant(self):
        identity = Identity(
            id="user-4",
            type=IdentityType.USER,
            attributes={},
            tenant_id="tenant-1",
        )
        assert identity.tenant_id == "tenant-1"

    def test_identity_with_roles(self):
        identity = Identity(
            id="user-5",
            type=IdentityType.USER,
            attributes={"roles": ["admin", "user"]},
        )
        assert "admin" in identity.attributes["roles"]


# ============================================================================
# Credentials
# ============================================================================

class TestPasswordCredential:

    def test_create(self):
        cred = PasswordCredential(
            identity_id="user-1",
            password_hash="$argon2id$hash",
        )
        assert cred.identity_id == "user-1"
        assert cred.password_hash == "$argon2id$hash"


class TestApiKeyCredential:

    def test_create(self):
        cred = ApiKeyCredential(
            identity_id="svc-1",
            key_id="key-1",
            key_hash="hashed_key",
            prefix="ak_live_",
            scopes=["read"],
        )
        assert cred.identity_id == "svc-1"
        assert cred.key_id == "key-1"


# ============================================================================
# PasswordHasher
# ============================================================================

class TestPasswordHasher:

    def test_create_auto(self):
        hasher = PasswordHasher()
        assert hasher.algorithm in ("argon2id", "pbkdf2_sha256")

    def test_hash(self):
        hasher = PasswordHasher()
        hashed = hasher.hash("MySecret123")
        assert hashed is not None
        assert len(hashed) > 10
        assert hashed != "MySecret123"

    def test_verify_correct(self):
        hasher = PasswordHasher()
        hashed = hasher.hash("password")
        assert hasher.verify(hashed, "password") is True

    def test_verify_wrong(self):
        hasher = PasswordHasher()
        hashed = hasher.hash("correct")
        assert hasher.verify(hashed, "wrong") is False

    def test_different_hashes_same_password(self):
        hasher = PasswordHasher()
        h1 = hasher.hash("same")
        h2 = hasher.hash("same")
        # Due to random salt, hashes differ
        assert h1 != h2

    def test_pbkdf2_fallback(self):
        hasher = PasswordHasher(algorithm="pbkdf2_sha256")
        hashed = hasher.hash("test")
        assert hasher.verify(hashed, "test") is True
        assert hasher.verify(hashed, "wrong") is False


# ============================================================================
# Token system (KeyDescriptor)
# ============================================================================

class TestKeyDescriptor:

    def test_create(self):
        from aquilia.auth.tokens import KeyDescriptor, KeyStatus
        kd = KeyDescriptor(
            kid="key_001",
            algorithm="RS256",
            public_key_pem="-----BEGIN PUBLIC KEY-----...",
        )
        assert kd.kid == "key_001"
        assert kd.is_active() is True
        assert kd.can_verify() is True

    def test_retired_key(self):
        from aquilia.auth.tokens import KeyDescriptor, KeyStatus
        kd = KeyDescriptor(
            kid="key_002",
            algorithm="RS256",
            public_key_pem="pub",
            status=KeyStatus.RETIRED,
        )
        assert kd.is_active() is False
        assert kd.can_verify() is True

    def test_revoked_key(self):
        from aquilia.auth.tokens import KeyDescriptor, KeyStatus
        kd = KeyDescriptor(
            kid="key_003",
            algorithm="RS256",
            public_key_pem="pub",
            status=KeyStatus.REVOKED,
        )
        assert kd.is_active() is False
        assert kd.can_verify() is False

    def test_to_dict(self):
        from aquilia.auth.tokens import KeyDescriptor
        kd = KeyDescriptor(
            kid="key_004",
            algorithm="ES256",
            public_key_pem="pub_key",
        )
        d = kd.to_dict()
        assert d["kid"] == "key_004"
        assert d["algorithm"] == "ES256"
        assert "created_at" in d

    def test_from_dict_roundtrip(self):
        from aquilia.auth.tokens import KeyDescriptor
        kd = KeyDescriptor(
            kid="key_005",
            algorithm="RS256",
            public_key_pem="pub",
        )
        d = kd.to_dict()
        kd2 = KeyDescriptor.from_dict(d)
        assert kd2.kid == kd.kid
        assert kd2.algorithm == kd.algorithm


# ============================================================================
# Auth exports / Flow Guards
# ============================================================================

class TestAuthExports:

    def test_auth_init_imports(self):
        from aquilia.auth import Identity, PasswordHasher
        assert Identity is not None
        assert PasswordHasher is not None

    def test_flow_guard_imports(self):
        from aquilia.auth.integration.flow_guards import FlowGuard
        assert FlowGuard is not None

    def test_guards_module(self):
        from aquilia.auth.guards import Guard
        assert Guard is not None
