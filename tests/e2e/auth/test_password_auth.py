"""
E2E Auth Tests — Password Authentication

Tests the full password authentication lifecycle via AuthManager.
"""

import pytest
from aquilia.auth.faults import (
    AUTH_INVALID_CREDENTIALS,
    AUTH_ACCOUNT_SUSPENDED,
    AUTH_ACCOUNT_LOCKED,
    AUTH_MFA_REQUIRED,
)
from aquilia.auth.core import (
    Identity,
    IdentityType,
    IdentityStatus,
    MFACredential,
)


class TestPasswordAuthentication:
    """End-to-end password authentication scenarios."""

    async def test_authenticate_valid_credentials(self, auth_manager, seed_user):
        """Successful login returns AuthResult with access + refresh tokens."""
        identity, password = seed_user
        result = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev",
            password=password,
        )
        assert result.identity.id == identity.id
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.expires_in == 300  # from token_config
        assert result.token_type == "Bearer"
        assert result.metadata["auth_method"] == "password"

    async def test_authenticate_by_username(self, auth_manager, seed_user, identity_store):
        """Login also works via the 'username' attribute."""
        identity, password = seed_user
        result = await auth_manager.authenticate_password(
            username="testuser",
            password=password,
        )
        assert result.identity.id == identity.id

    async def test_authenticate_wrong_password(self, auth_manager, seed_user):
        """Wrong password raises AUTH_INVALID_CREDENTIALS."""
        with pytest.raises(AUTH_INVALID_CREDENTIALS):
            await auth_manager.authenticate_password(
                username="testuser@aquilia.dev",
                password="WrongPassword123!",
            )

    async def test_authenticate_nonexistent_user(self, auth_manager):
        """Non-existent user raises AUTH_INVALID_CREDENTIALS."""
        with pytest.raises(AUTH_INVALID_CREDENTIALS):
            await auth_manager.authenticate_password(
                username="nobody@aquilia.dev",
                password="AnyPassword123!",
            )

    async def test_authenticate_suspended_user(
        self, auth_manager, identity_store, credential_store, password_hasher,
    ):
        """Suspended user raises AUTH_ACCOUNT_SUSPENDED."""
        suspended = Identity(
            id="user-suspended",
            type=IdentityType.USER,
            attributes={"email": "suspended@aquilia.dev", "username": "suspended"},
            status=IdentityStatus.SUSPENDED,
        )
        await identity_store.create(suspended)

        pw_hash = password_hasher.hash("ValidPassword1!")
        from aquilia.auth.core import PasswordCredential
        await credential_store.save_password(
            PasswordCredential(identity_id=suspended.id, password_hash=pw_hash)
        )

        with pytest.raises(AUTH_ACCOUNT_SUSPENDED):
            await auth_manager.authenticate_password(
                username="suspended@aquilia.dev",
                password="ValidPassword1!",
            )

    async def test_authenticate_deleted_user(
        self, auth_manager, identity_store, credential_store, password_hasher,
    ):
        """Deleted user raises AUTH_INVALID_CREDENTIALS."""
        deleted = Identity(
            id="user-deleted",
            type=IdentityType.USER,
            attributes={"email": "deleted@aquilia.dev"},
            status=IdentityStatus.DELETED,
        )
        await identity_store.create(deleted)

        pw_hash = password_hasher.hash("ValidPassword1!")
        from aquilia.auth.core import PasswordCredential
        await credential_store.save_password(
            PasswordCredential(identity_id=deleted.id, password_hash=pw_hash)
        )

        with pytest.raises(AUTH_INVALID_CREDENTIALS):
            await auth_manager.authenticate_password(
                username="deleted@aquilia.dev",
                password="ValidPassword1!",
            )

    async def test_password_rehash_on_login(
        self, identity_store, credential_store, token_manager,
    ):
        """Credential store is updated when hash parameters change."""
        # Use a hasher with low iterations
        from aquilia.auth.hashing import PasswordHasher
        old_hasher = PasswordHasher(algorithm="pbkdf2_sha256", iterations=500)
        new_hasher = PasswordHasher(algorithm="pbkdf2_sha256", iterations=2000)

        identity = Identity(
            id="user-rehash",
            type=IdentityType.USER,
            attributes={"email": "rehash@aquilia.dev"},
            status=IdentityStatus.ACTIVE,
        )
        await identity_store.create(identity)

        old_hash = old_hasher.hash("MyPassword123!")
        from aquilia.auth.core import PasswordCredential
        await credential_store.save_password(
            PasswordCredential(identity_id=identity.id, password_hash=old_hash)
        )

        # Create manager with new hasher — it should detect needs_rehash
        from aquilia.auth.manager import AuthManager as _AuthManager
        manager = _AuthManager(
            identity_store=identity_store,
            credential_store=credential_store,
            token_manager=token_manager,
            password_hasher=new_hasher,
        )

        result = await manager.authenticate_password(
            username="rehash@aquilia.dev",
            password="MyPassword123!",
        )
        assert result.identity.id == identity.id

        # Verify credential was rehashed
        updated_cred = await credential_store.get_password(identity.id)
        assert updated_cred.password_hash != old_hash

    async def test_session_id_generated_on_login(self, auth_manager, seed_user):
        """AuthResult includes an auto-generated session_id."""
        _, password = seed_user
        result = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev",
            password=password,
        )
        assert result.session_id is not None
        assert result.session_id.startswith("sess_")

    async def test_mfa_required_blocks_login(
        self, auth_manager, seed_user, credential_store,
    ):
        """If MFA credentials exist, AUTH_MFA_REQUIRED is raised instead of tokens."""
        identity, password = seed_user

        mfa_cred = MFACredential(
            identity_id=identity.id,
            mfa_type="totp",
            mfa_secret="JBSWY3DPEHPK3PXP",
        )
        await credential_store.save_mfa(mfa_cred)

        with pytest.raises(AUTH_MFA_REQUIRED):
            await auth_manager.authenticate_password(
                username="testuser@aquilia.dev",
                password=password,
            )

    async def test_custom_scopes_in_token(self, auth_manager, seed_user):
        """Custom scopes are passed through to the issued token."""
        _, password = seed_user
        result = await auth_manager.authenticate_password(
            username="testuser@aquilia.dev",
            password=password,
            scopes=["admin", "write"],
        )
        # Validate the token contains the requested scopes
        claims = await auth_manager.verify_token(result.access_token)
        assert "admin" in claims.scopes
        assert "write" in claims.scopes
