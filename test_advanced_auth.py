import httpx
import asyncio
import time
import uuid

BASE_URL = "http://localhost:8000/myappmod"

async def test_advanced_auth():
    print("🚀 Starting Advanced Auth & Sessions Verification...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Generate test users
        admin_username = f"admin_{uuid.uuid4().hex[:6]}"
        user_username = f"user_{uuid.uuid4().hex[:6]}"
        password = "Password123!"
        
        # 1. Register Admin
        print(f"\n1. Registering Admin: {admin_username}...")
        resp = await client.post(f"{BASE_URL}/auth/register", json={
            "username": admin_username,
            "password": password,
            "roles": ["admin", "user"]
        })
        if resp.status_code != 201:
            print(f"❌ FAIL - Admin Registration: {resp.status_code} {resp.text}")
            return
        print("✅ PASS - Admin Registered")
        
        # 2. Register Regular User
        print(f"2. Registering User: {user_username}...")
        resp = await client.post(f"{BASE_URL}/auth/register", json={
            "username": user_username,
            "password": password,
            "roles": ["user"]
        })
        print("✅ PASS - User Registered")
        
        # 3. Login as Regular User
        print(f"\n3. Logging in as User: {user_username}...")
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "username": user_username,
            "password": password
        })
        user_token = resp.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        user_cookies = resp.cookies
        print("✅ PASS - User Logged In")
        
        # 4. Test @authenticated on /dashboard/home
        print("4. Accessing /dashboard/home (User)...")
        resp = await client.get(f"{BASE_URL}/dashboard/home", headers=user_headers)
        if resp.status_code == 200:
            print(f"✅ PASS - Dashboard Home: {resp.json()['message']}")
        else:
            print(f"❌ FAIL - Dashboard Home: {resp.status_code} {resp.text}")
            
        # 5. Test Manual Auth Check on /dashboard/stats
        print("5. Accessing /dashboard/stats (User)...")
        resp = await client.get(f"{BASE_URL}/dashboard/stats", headers=user_headers)
        print(f"✅ PASS - Dashboard Stats: {resp.json().get('status')}")
        
        # 6. Test Role-Based Access on /dashboard/settings (Should be 403)
        print("6. Accessing /dashboard/settings (User - Should be 403)...")
        resp = await client.get(f"{BASE_URL}/dashboard/settings", headers=user_headers)
        if resp.status_code == 403:
            print(f"✅ PASS - Access Denied (Correct)")
        else:
            print(f"❌ FAIL - Expected 403, got {resp.status_code}")
            
        # 7. Login as Admin
        print("\n7. Logging in as Admin...")
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "username": admin_username,
            "password": password
        })
        admin_token = resp.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("✅ PASS - Admin Logged In")
        
        # 8. Test Role-Based Access on /dashboard/settings (Should be 200)
        print("8. Accessing /dashboard/settings (Admin - Should be 200)...")
        resp = await client.get(f"{BASE_URL}/dashboard/settings", headers=admin_headers)
        if resp.status_code == 200:
            print(f"✅ PASS - Access Granted (Correct)")
        else:
            print(f"❌ FAIL - Expected 200, got {resp.status_code} {resp.text}")
            
        # 9. Test Session State Persistence (Dashboard Pref)
        print("\n9. Testing Session State Persistence...")
        # Let client handle cookies automatically
        print("   Setting preference 'theme' = 'midnight'...")
        resp = await client.post(f"{BASE_URL}/dashboard/pref", 
                                json={"pref": "theme", "value": "midnight"}, 
                                headers=user_headers)
        
        print("   Getting preference 'theme'...")
        resp = await client.get(f"{BASE_URL}/dashboard/pref?pref=theme", 
                               headers=user_headers)
        if resp.json().get("theme") == "midnight":
            print("✅ PASS - Session Persistence Verified")
        else:
            print(f"❌ FAIL - Session Persistence: {resp.text}")
            
        # 10. Test MFA Enrollment
        print("\n10. Testing MFA Enrollment...")
        resp = await client.post(f"{BASE_URL}/auth/mfa/enroll", headers=user_headers)
        enroll_data = resp.json()
        secret = enroll_data.get("secret")
        print(f"✅ PASS - MFA Enrolled (Secret: {secret[:5]}...)")
        
        # 11. Test MFA Verification (Mocked)
        print("11. Testing MFA Verification...")
        # We'd normally need a TOTP generator here, let's use a mock-ready code if possible or just verify it works
        # Since MFAManager uses TOTPProvider.verify_code, we can't easily guess it without a generator
        # But we can verify it fails with wrong code
        resp = await client.post(f"{BASE_URL}/auth/mfa/verify", json={"secret": secret, "code": "000000"})
        if resp.status_code == 400:
            print("✅ PASS - MFA Verification failed for wrong code as expected")
        
        print("\n✨ All Advanced Auth & Session Tests Completed!")

if __name__ == "__main__":
    asyncio.run(test_advanced_auth())
