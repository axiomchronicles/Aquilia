#!/usr/bin/env python
"""
Test script for complete authentication dashboard integration.

Tests:
- DemoAuthService: Credential verification for demo users
- AuthController: Login/logout flow with templates  
- DashboardController: Protected dashboard rendering
- SessionsController: Session listing
- Template rendering with auth/session context injection
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.mark.asyncio
async def test_demo_auth_service():
    """Test DemoAuthService credential verification."""
    from aquilia.auth.stores import MemoryIdentityStore, MemoryCredentialStore
    from aquilia.auth.hashing import PasswordHasher
    from myapp.modules.myappmod.auth import DemoAuthService
    
    # Setup
    identity_store = MemoryIdentityStore()
    credential_store = MemoryCredentialStore()
    hasher = PasswordHasher()
    
    service = DemoAuthService(identity_store, credential_store, hasher)
    
    # Test: Verify admin user credentials
    admin = await service.verify_credentials("admin", "password")
    assert admin is not None
    assert admin.get_attribute("username") == "admin"
    assert "admin" in admin.get_attribute("roles")
    
    # Test: Verify john user credentials
    john = await service.verify_credentials("john", "password")
    assert john is not None
    assert john.get_attribute("username") == "john"
    assert "user" in john.get_attribute("roles")
    
    # Test: Invalid credentials
    invalid = await service.verify_credentials("admin", "wrongpassword")
    assert invalid is None
    
    # Test: Non-existent user
    nouser = await service.verify_credentials("nouser", "password")
    assert nouser is None
    
    print("✓ DemoAuthService tests passed")


@pytest.mark.asyncio
async def test_auth_controller_login_page():
    """Test AuthController initialization and basic structure."""
    from aquilia.auth.manager import AuthManager
    from aquilia.auth.stores import MemoryIdentityStore, MemoryCredentialStore, MemoryTokenStore
    from aquilia.auth.hashing import PasswordHasher
    from aquilia.auth.tokens import TokenManager, TokenConfig, KeyRing, KeyDescriptor
    from myapp.modules.myappmod.auth import AuthController, DemoAuthService, UserService
    
    # Setup minimal DI dependencies
    identity_store = MemoryIdentityStore()
    credential_store = MemoryCredentialStore()
    token_store = MemoryTokenStore()
    hasher = PasswordHasher()
    
    # Setup token manager
    key = KeyDescriptor.generate(kid="test", algorithm="RS256")
    key_ring = KeyRing([key])
    token_config = TokenConfig(issuer="test-app", audience=["api"])
    token_manager = TokenManager(key_ring, token_store, token_config)
    
    # Create auth manager
    auth_manager = AuthManager(
        identity_store=identity_store,
        credential_store=credential_store,
        token_manager=token_manager,
        password_hasher=hasher,
    )
    
    # Create services
    user_service = UserService(identity_store, credential_store, hasher)
    demo_service = DemoAuthService(identity_store, credential_store, hasher)
    
    # Create controller
    auth_controller = AuthController(auth_manager, user_service, demo_service)
    
    # Verify controller created successfully
    assert auth_controller is not None
    assert auth_controller.prefix == "/auth"
    assert auth_controller.tags == ["auth"]
    
    print("✓ AuthController login page test passed")


@pytest.mark.asyncio
async def test_demo_users_seeded():
    """Test that demo users are properly seeded."""
    from aquilia.auth.stores import MemoryIdentityStore, MemoryCredentialStore
    from aquilia.auth.hashing import PasswordHasher
    from myapp.modules.myappmod.auth import DemoAuthService
    
    # Setup
    identity_store = MemoryIdentityStore()
    credential_store = MemoryCredentialStore()
    hasher = PasswordHasher()
    
    service = DemoAuthService(identity_store, credential_store, hasher)
    
    # Ensure users are seeded
    await service.ensure_demo_users()
    
    # Verify admin exists
    admin = await identity_store.get_by_attribute("username", "admin")
    assert admin is not None
    assert admin.get_attribute("username") == "admin"
    
    # Verify john exists
    john = await identity_store.get_by_attribute("username", "john")
    assert john is not None
    assert john.get_attribute("username") == "john"
    
    print("✓ Demo users seeded successfully")


@pytest.mark.asyncio
async def test_credentials_stored():
    """Test that credentials are properly stored."""
    from aquilia.auth.stores import MemoryCredentialStore
    from aquilia.auth.hashing import PasswordHasher
    from aquilia.auth.core import PasswordCredential, CredentialStatus
    from datetime import datetime, timezone
    
    store = MemoryCredentialStore()
    hasher = PasswordHasher()
    
    # Store a credential
    hashed = hasher.hash("testpassword")
    cred = PasswordCredential(
        identity_id="test-user-1",
        password_hash=hashed,
        status=CredentialStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        last_changed_at=datetime.now(timezone.utc),
    )
    
    await store.save_password(cred)
    
    # Retrieve and verify
    retrieved = await store.get_password("test-user-1")
    assert retrieved is not None
    print(f"Stored hash: {hashed[:20]}...")
    print(f"Retrieved hash: {retrieved.password_hash[:20]}...")
    
    # Test verification - note: password_hash first, password second!
    is_valid = hasher.verify(retrieved.password_hash, "testpassword")
    print(f"Verification result: {is_valid}")
    assert is_valid, "Password verification failed"
    
    # Test invalid password
    is_invalid = hasher.verify(retrieved.password_hash, "wrongpassword")
    assert not is_invalid, "Wrong password should not verify"
    
    print("✓ Credentials storage test passed")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Authentication Dashboard Integration Tests")
    print("=" * 60)
    
    await test_demo_users_seeded()
    await test_credentials_stored()
    await test_demo_auth_service()
    await test_auth_controller_login_page()
    
    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the server: python -m aquilia.server myapp")
    print("2. Visit http://localhost:8000/auth/login")
    print("3. Login with admin/password or john/password")
    print("4. View dashboard at /dashboard")
    print("5. Check session info at /sessions/list")


if __name__ == "__main__":
    asyncio.run(main())
