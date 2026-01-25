
import asyncio
import httpx
from aquilia.server import AquiliaServer
from myapp.modules.myappmod.manifest import manifest as myappmod_manifest
from aquilia.config import ConfigLoader
import logging

# Configure logging to show info/debug
logging.basicConfig(level=logging.INFO)

async def test_integration():
    print("--- Starting Integration Test ---")
    
    # 1. Initialize Server (which builds the app)
    # 1. Initialize Server (which builds the app)
    # Using the module manifest directly
    config = ConfigLoader()
    # Initialize basic apps config structure required by Aquilary
    config.config_data = {
        "debug": True,
        "mode": "test",
        "apps": {
            "myappmod": {}
        }
    }
    config._build_apps_namespace()
    
    server = AquiliaServer(
        manifests=[myappmod_manifest],
        config=config,
    )
    await server.startup()
    
    # Get the ASGI app
    app = server.get_asgi_app()
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        
        # --- 1. Test Audit Route (Request Scope + Middleware) ---
        print("\n1. Testing Audit Route (Request Scope)...")
        resp = await client.get("/myappmod/advanced/audit")
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.json()}")
        
        assert resp.status_code == 200
        assert "Accessed Audit Endpoint" in resp.json()["log_entry"]
        assert "User 123" in resp.json()["log_entry"]
        print("✅ Audit route passed (Middleware -> UserIdentity -> AuditLogger works)")

        # --- 2. Test Lazy Route (Lazy Proxy) ---
        print("\n2. Testing Lazy Route (Lazy Proxy)...")
        data_payload = "test_data"
        resp = await client.get(f"/myappmod/advanced/lazy/{data_payload}")
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.json()}")
        
        assert resp.status_code == 200
        assert "Processed 'test_data' with Factor 42" in resp.json()["result"]
        print("✅ Lazy route passed (LazyProcessor -> ExpensiveService works)")

        # --- 3. Test Advanced DI Route (Interface + Tagged) ---
        print("\n3. Testing Advanced DI Route (Interface Binding)...")
        # ID 1
        resp = await client.get("/myappmod/advanced/users/1")
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.json()}")
        
        assert resp.status_code == 200
        # Since SqlUserRepository has simulated delay, this proves async_init works too
        assert resp.json()["data"]["id"] == 1
        assert "primary_db" in resp.json()["source"] or "memory_cache" in resp.json()["source"]
        print("✅ Advanced User route passed (Interface Binding + Lifecycle Hooks work)")

    await server.shutdown()
    print("\n--- Integration Test Complete ---")

if __name__ == "__main__":
    asyncio.run(test_integration())
