import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8001"

async def test_auth_flow():
    import time
    email = f"test_{int(time.time())}@example.com"
    async with httpx.AsyncClient(follow_redirects=False) as client:
        print(f"\n--- Testing Authentication Flow at {BASE_URL} ---")
        
        # 1. Register with Profile Photo
        print(f"\n[1] Registering new user with profile photo: {email}...")
        reg_data = {
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "full_name": "Script User"
        }
        with open("authentication/test_profile.jpg", "rb") as f:
            files = {"profile": ("test_profile.jpg", f, "image/jpeg")}
            res = await client.post(f"{BASE_URL}/auth/register", data=reg_data, files=files)
        
        print(f"Status: {res.status_code}")
        if res.status_code in (201, 302):
            print("SUCCESS: Registration request sent.")
        else:
            print(f"FAILURE: Registration failed: {res.text}")
            return

        # 2. Login
        print(f"\n[2] Logging in as {email}...")
        login_data = {
            "email": email,
            "password": "Password123!"
        }
        res = await client.post(f"{BASE_URL}/auth/login", data=login_data)
        print(f"Status: {res.status_code}")
        
        cookies = res.cookies
        print(f"Cookies received: {dict(cookies)}")
        
        if "access_token" in cookies:
            print("SUCCESS: access_token cookie found.")
        else:
            print("FAILURE: access_token cookie NOT found in response.")
            # Check headers manually just in case
            print(f"Headers: {dict(res.headers)}")
            import re
            error_match = re.search(r'class="error">(.*?)</div>', res.text, re.DOTALL)
            if error_match:
                print(f"ERROR MESSAGE FOUND: {error_match.group(1).strip()}")
            else:
                print("No error message found in HTML body.")
            print(f"Body snippet: {res.text[:500]}")
            return

        # 3. Access Dashboard
        print("\n[3] Accessing Dashboard with cookies...")
        res = await client.get(f"{BASE_URL}/auth/dashboard", cookies=cookies)
        print(f"Status: {res.status_code}")
        
        if res.status_code == 200:
            print("SUCCESS: Dashboard accessed successfully!")
            if "Script User" in res.text:
                print("SUCCESS: User name found in dashboard content.")
            else:
                print("WARNING: User name NOT found in dashboard content.")
            
            if "/uploads/profiles/" in res.text:
                print("SUCCESS: Profile photo path found in dashboard content.")
            else:
                print("FAILURE: Profile photo path NOT found in dashboard content.")
        elif res.status_code == 302:
             print(f"FAILURE: Dashboard redirected to {res.headers.get('location')}")
        else:
            print(f"FAILURE: Dashboard access failed with status {res.status_code}")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
