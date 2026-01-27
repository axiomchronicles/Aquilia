import asyncio
import httpx
import sys
import os

BASE_URL = "http://127.0.0.1:8000"
MODULE_PREFIX = "/myappmod"

async def test_all_routes():
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=False) as client:
        print("\n--- Testing Public Routes ---")
        
        # 1. Root redirect
        resp = await client.get(f"{MODULE_PREFIX}/")
        print(f"GET {MODULE_PREFIX}/ -> {resp.status_code}")
        
        # 2. Login Page
        resp = await client.get(f"{MODULE_PREFIX}/auth/login")
        print(f"GET {MODULE_PREFIX}/auth/login -> {resp.status_code}")

        print("\n--- Testing Authentication ---")
        
        # 3. Form Login
        login_data = {"username": "admin", "password": "password"}
        resp_form = await client.post(f"{MODULE_PREFIX}/auth/login", data=login_data)
        print(f"POST {MODULE_PREFIX}/auth/login (Form) -> {resp_form.status_code}")
        session_cookie = resp_form.cookies.get("aquilia_session")
        if session_cookie:
            print("✓ Session cookie received")
        
        # 4. JSON Login
        resp_json = await client.post(f"{MODULE_PREFIX}/auth/login-json", json=login_data)
        print(f"POST {MODULE_PREFIX}/auth/login-json (JSON) -> {resp_json.status_code}")
        auth_token = None
        if resp_json.status_code == 200:
            auth_token = resp_json.json().get("access_token")
            print("✓ JWT Token received")

        # Create an authenticated client (using Form login cookies)
        auth_client = httpx.AsyncClient(base_url=BASE_URL, cookies=resp_form.cookies, follow_redirects=True)
        
        print("\n--- Testing Authenticated UI Routes ---")
        ui_routes = [
            "/dashboard",
            "/profile",
            "/auth/me",
            "/sessions/list"
        ]
        for route in ui_routes:
            resp = await auth_client.get(f"{MODULE_PREFIX}{route}")
            print(f"GET {MODULE_PREFIX}{route} -> {resp.status_code}")

        print("\n--- Testing Items API (CRUD) ---")
        # List
        resp = await auth_client.get(f"{MODULE_PREFIX}/items/")
        print(f"GET {MODULE_PREFIX}/items/ -> {resp.status_code}")
        
        # Create
        item_data = {"name": "Test Item", "description": "Created by test script"}
        resp = await auth_client.post(f"{MODULE_PREFIX}/items/", json=item_data)
        print(f"POST {MODULE_PREFIX}/items/ -> {resp.status_code}")
        item_id = 1
        if resp.status_code == 201:
            item_id = resp.json().get("id", 1)
        
        # Detail
        resp = await auth_client.get(f"{MODULE_PREFIX}/items/{item_id}")
        print(f"GET {MODULE_PREFIX}/items/{item_id} -> {resp.status_code}")
        
        # Update
        resp = await auth_client.put(f"{MODULE_PREFIX}/items/{item_id}", json={"name": "Updated Item"})
        print(f"PUT {MODULE_PREFIX}/items/{item_id} -> {resp.status_code}")
        
        # Delete
        resp = await auth_client.delete(f"{MODULE_PREFIX}/items/{item_id}")
        print(f"DELETE {MODULE_PREFIX}/items/{item_id} -> {resp.status_code}")

        print("\n--- Testing Advanced Features ---")
        adv_routes = [
            "/advanced/audit",
            "/advanced/lazy/test_data",
            "/advanced/users/1",
            "/advanced/users/config"
        ]
        for route in adv_routes:
            resp = await auth_client.get(f"{MODULE_PREFIX}{route}")
            print(f"GET {MODULE_PREFIX}{route} -> {resp.status_code}")

        print("\n--- Testing JWT Protected Routes ---")
        if auth_token:
            headers = {"Authorization": f"Bearer {auth_token}"}
            jwt_client = httpx.AsyncClient(base_url=BASE_URL, headers=headers)
            jwt_routes = [
                "/jwt/protected",
                "/jwt/info"
            ]
            for route in jwt_routes:
                resp = await jwt_client.get(f"{MODULE_PREFIX}{route}")
                print(f"GET {MODULE_PREFIX}{route} -> {resp.status_code}")
            await jwt_client.aclose()
        else:
            print("Skipping JWT routes (no token)")

        print("\n--- Testing API Dashboard & Sessions ---")
        api_routes = [
            "/api/dashboard/home",
            "/api/dashboard/stats",
            "/api/dashboard/settings",
            "/api/sessions/",
            "/api/sessions/profile",
            "/api/sessions/context"
        ]
        for route in api_routes:
            resp = await auth_client.get(f"{MODULE_PREFIX}{route}")
            print(f"GET {MODULE_PREFIX}{route} -> {resp.status_code}")

        await auth_client.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(test_all_routes())
    except Exception as e:
        print(f"Test failed: {e}")
