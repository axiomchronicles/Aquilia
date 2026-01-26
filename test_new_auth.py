
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def print_result(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"   {details}")
    if not passed:
        sys.exit(1)

def main():
    print("Testing Auth Implementation...")
    
    # Generate random user
    ts = int(time.time())
    username = f"user_{ts}"
    password = "password123"
    email = f"{username}@example.com"
    
    # 1. Register
    print(f"\n1. Registering user {username}...")
    resp = requests.post(f"{BASE_URL}/myappmod/auth/register", json={
        "username": username,
        "password": password,
        "email": email
    })
    
    if resp.status_code != 201:
        print_result("Register", False, f"Status: {resp.status_code}, Body: {resp.text}")
    else:
        print_result("Register", True, f"ID: {resp.json().get('id')}")

    # 2. Login
    print("\n2. Logging in...")
    resp = requests.post(f"{BASE_URL}/myappmod/auth/login", json={
        "username": username,
        "password": password
    })
    
    if resp.status_code != 200:
        print_result("Login", False, f"Status: {resp.status_code}, Body: {resp.text}")
    else:
        print_result("Login", True)
        tokens = resp.json()
        access_token = tokens.get("access_token")
        if not access_token:
            print_result("Token Check", False, "No access_token in response")
        else:
            print_result("Token Check", True)

    # 3. Access Protected Endpoint (With Token)
    print("\n3. Accessing /me (Authenticated)...")
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{BASE_URL}/myappmod/auth/me", headers=headers)
    
    if resp.status_code != 200:
        print_result("Access /me (Auth)", False, f"Status: {resp.status_code}, Body: {resp.text}")
    else:
        user_data = resp.json()
        if user_data.get("username") == username:
            print_result("Access /me (Auth)", True, f"Got username: {user_data.get('username')}")
        else:
             print_result("Access /me (Auth)", False, f"Username mismatch: {user_data}")

    # 4. Access Protected Endpoint (No Token)
    print("\n4. Accessing /me (Unauthenticated)...")
    resp = requests.get(f"{BASE_URL}/myappmod/auth/me")
    
    if resp.status_code == 401:
        print_result("Access /me (No Auth)", True, "Got 401 as expected")
    else:
        print_result("Access /me (No Auth)", False, f"Expected 401, got {resp.status_code}")

    print("\n🎉 All Verification Steps Passed!")

if __name__ == "__main__":
    main()
