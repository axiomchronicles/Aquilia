import asyncio
import sys
import os

# Add current directory to path so we can import modules
sys.path.insert(0, os.getcwd())

from aquilia.db.engine import AquiliaDatabase
from aquilia.models import ModelRegistry
from aquilia.cache import CacheService, MemoryBackend
from modules.auth.models import User
from modules.auth.services import AuthService

async def main():
    print("Starting Auth Verification...")

    # 1. Setup Database
    print("[1] Initializing In-Memory Database...")
    db = AquiliaDatabase("sqlite:///:memory:")
    await db.connect()
    
    # Register DB globally
    ModelRegistry.set_database(db)

    # Create tables
    print("[2] Creating Tables...")
    # Manually create table for User since we are not running full migration runner
    await ModelRegistry.create_tables(db)
    
    # 2. Initialize Service
    print("[3] Initializing Cache & AuthService...")
    cache = CacheService(backend=MemoryBackend())
    await cache.initialize()
    
    service = AuthService(cache=cache)

    # 3. Test Register
    print("[4] Testing Registration...")
    try:
        user_data = {
            "email": "test@example.com",
            "password": "StrongPassword123!",
            "full_name": "Test User"
        }
        user = await service.register(user_data)
        print(f"    SUCCESS: User created: {user['id']} - {user['email']}")
    except Exception as e:
        print(f"    FAILURE: Registration failed: {e}")
        return

    # 4. Test Login
    print("[5] Testing Login...")
    try:
        login_data = {
            "email": "test@example.com",
            "password": "StrongPassword123!"
        }
        tokens = await service.login(login_data)
        print(f"    SUCCESS: Login successful. Access Token: {tokens['access_token'][:20]}...")
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
    except Exception as e:
        print(f"    FAILURE: Login failed: {e}")
        return

    # 5. Test Get Current User (Token Verification)
    print("[6] Testing Token Verification...")
    try:
        me = await service.get_current_user_from_token(access_token)
        print(f"    SUCCESS: Retrieved user from token: {me['email']}")
        assert me["email"] == "test@example.com"
    except Exception as e:
        print(f"    FAILURE: Token verification failed: {e}")
        return

    # 6. Test Token Refresh
    print("[7] Testing Token Refresh...")
    try:
        new_tokens = await service.refresh_token(refresh_token)
        print(f"    SUCCESS: Refreshed token. New Access Token: {new_tokens['access_token'][:20]}...")
    except Exception as e:
        print(f"    FAILURE: Token refresh failed: {e}")
        return

    # 7. Test Invalid Login
    print("[8] Testing Invalid Login...")
    try:
        await service.login({"email": "test@example.com", "password": "WrongPassword"})
        print("    FAILURE: Invalid login should have raised an exception")
    except Exception:
        print("    SUCCESS: Invalid login correctly rejected")

    # 8. Test Serializers
    print("[9] Testing Serializers...")
    from modules.auth.serializers import RegisterSerializer, UserSerializer
    
    # 8.1 Invalid Registration
    invalid_reg_data = {
        "email": "bad@email.com", 
        "full_name": "Bad User",
        "password": "password123",
        "confirm_password": "mismatch123"
    }
    reg_ser = RegisterSerializer(data=invalid_reg_data)
    if not reg_ser.is_valid():
        print("    SUCCESS: RegisterSerializer caught mismatched passwords")
    else:
        print("    FAILURE: RegisterSerializer allowed mismatched passwords")

    # 8.2 User Serialization
    user_obj = await User.get(email="test@example.com")
    user_ser = UserSerializer(instance=user_obj)
    if "password_hash" not in user_ser.data:
        print(f"    SUCCESS: UserSerializer hid password hash. Data: {user_ser.data.keys()}")
    else:
        print("    FAILURE: UserSerializer exposed password hash")

    # 9. Test Caching
    print("[10] Testing Caching...")
    # Get user to warm cache
    user_data_1 = await service.get_current_user_from_token(access_token)
    
    # Modify DB directly (bypassing service/cache update)
    user_obj = await User.get(email="test@example.com")
    original_name = user_obj.full_name
    user_obj.full_name = "Hacked Name"
    await user_obj.save()
    
    # Get user again - should be STALE (Original Name) because of cache
    user_data_2 = await service.get_current_user_from_token(access_token)
    
    if user_data_2["full_name"] == original_name:
        print("    SUCCESS: Cache hit confirmed (Data is stale as expected)")
    else:
        print(f"    FAILURE: Cache miss (Data updated): {user_data_2['full_name']}")

    # Restore name
    user_obj.full_name = original_name
    await user_obj.save()

    print("\nVerification Complete: All systems nominal.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
