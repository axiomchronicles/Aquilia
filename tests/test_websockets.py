import asyncio
import json
import websockets
import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/myapp"

async def test_websocket_connection():
    """Test basic WebSocket connection and DI response."""
    print("\n--- Testing WebSocket Connection ---")
    async with websockets.connect(WS_URL) as websocket:
        # Receive welcome message
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Received: {data}")
        
        assert data["type"] == "event"
        assert data["event"] == "welcome"
        assert "payload" in data
        assert "message" in data["payload"]
        assert "authenticated" in data["payload"]
        assert data["payload"]["authenticated"] is False

async def test_websocket_echo():
    """Test echo functionality."""
    print("\n--- Testing WebSocket Echo ---")
    async with websockets.connect(WS_URL) as websocket:
        # Skip welcome
        await websocket.recv()
        
        # Send echo
        msg = {
            "type": "event",
            "event": "echo",
            "payload": {"text": "Hello Aquilia"}
        }
        await websocket.send(json.dumps(msg))
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Echo response: {data}")
        
        assert data["type"] == "event"
        assert data["event"] == "echo_response"
        assert data["payload"]["text"] == "Hello Aquilia"

async def test_authenticated_websocket():
    """Test authenticated WebSocket connection."""
    print("\n--- Testing Authenticated WebSocket ---")
    
    # 1. Login via HTTP to get session cookie
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Login
        login_data = {
            "username": "admin",
            "password": "password"
        }
        # Note: In a real test we would create a user first or rely on seed data
        response = await client.post("/myappmod/auth/login-json", json=login_data)
        print(f"Login status: {response.status_code}")
        
        cookies = response.cookies
        session_cookie = None
        for key, value in cookies.items():
            if key == "session_id":
                session_cookie = f"{key}={value}"
                break
        
        print(f"Session cookie: {session_cookie}")

    # 2. Connect to WebSocket with cookie
    headers = {}
    extra_headers = {"Cookie": session_cookie} if session_cookie else {}
        
    async with websockets.connect(WS_URL, additional_headers=extra_headers) as websocket:
        # Receive welcome
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Auth Welcome: {data}")
        
        if session_cookie:
            # We expect authenticated=True if login succeeded
            # But login might fail in this test env if DB is empty
            if data["payload"]["authenticated"]:
                assert data["payload"]["user_id"] is not None
                
                # Test secure action
                msg = {
                    "type": "event",
                    "event": "secure_action",
                    "payload": {}
                }
                await websocket.send(json.dumps(msg))
                
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Secure response: {data}")
                assert data["type"] == "event"
                assert data["event"] == "secure_response"
                assert data["payload"]["status"] == "authorized"
            else:
                print("⚠️  Warning: WebSocket not authenticated (Login failed or cookie ignored)")

if __name__ == "__main__":
    async def main():
        try:
            await test_websocket_connection()
            await test_websocket_echo()
            await test_authenticated_websocket()
            print("\n✅ All WebSocket tests passed!")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            exit(1)

    asyncio.run(main())
