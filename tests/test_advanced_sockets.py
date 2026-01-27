import asyncio
import sys
import json
import logging
import httpx
from websockets.client import connect
from websockets.exceptions import InvalidStatusCode, ConnectionClosedOK, ConnectionClosedError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test_sockets")

BASE_URL = "http://127.0.0.1:8000"
WS_BASE_URL = "ws://127.0.0.1:8000"
MODULE_PREFIX = "/myappmod"

async def test_sockets():
    print("\n--- Testing Advanced WebSockets ---")
    
    # 1. Test Public Feed (Anonymous)
    print("\n[1] Testing Public Feed (Anonymous)...")
    try:
        async with connect(f"{WS_BASE_URL}{MODULE_PREFIX}/ws/feed") as ws:
            print("✓ Connected anonymously")
            # Should be able to receive messages if any broadcast happens
            # For this test, we just verify connection
    except Exception as e:
        print(f"✗ Failed to connect to Public Feed: {e}")
        return

    # 2. Test Chat (Anonymous - Should Fail)
    print("\n[2] Testing Chat (Anonymous - Should Fail)...")
    try:
        async with connect(f"{WS_BASE_URL}{MODULE_PREFIX}/ws/chat") as ws:
            print("✗ Error: Connected anonymously to protected endpoint")
            await ws.recv() # Wait for close
    except (InvalidStatusCode, ConnectionClosedOK, ConnectionClosedError) as e:
        print(f"✓ Correctly rejected anonymous connection: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {type(e)} {e}")

    # 3. Authenticate to get Session
    print("\n[3] Authenticating...")
    cookies = {}
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        login_data = {"username": "admin", "password": "password"}
        resp = await client.post(f"{MODULE_PREFIX}/auth/login", data=login_data)
        if resp.status_code not in (200, 307, 303):
            print(f"✗ Login failed: {resp.status_code}")
            return
        cookies = dict(resp.cookies)
        print("✓ Logged in, session cookie obtained")

    # 4. Test Chat (Authenticated)
    print("\n[4] Testing Chat (Authenticated)...")
    
    # Convert cookies to string for WebSocket header
    cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    headers = {"Cookie": cookie_header}
    
    print(f"DEBUG TEST: Cookies obtained: {cookies}")
    print(f"DEBUG TEST: Sending headers: {headers}")
    
    try:
        async with connect(f"{WS_BASE_URL}{MODULE_PREFIX}/ws/chat", extra_headers=headers) as ws:
            print("✓ Connected authenticated")
            
            # Wait for welcome message
            welcome = json.loads(await ws.recv())
            print(f"✓ Received welcome: {welcome}")
            
            # Join Room
            join_msg = {
                "type": "event",
                "event": "chat.join",
                "payload": {"room": "general"},
                "ack": True,
                "id": "1"
            }
            await ws.send(json.dumps(join_msg))
            
            # Expect Ack
            ack = json.loads(await ws.recv())
            print(f"✓ Received Ack: {ack}")
            
            # Send Message
            send_msg = {
                "type": "event",
                "event": "chat.message",
                "payload": {
                    "room": "general",
                    "text": "Hello Aquilia!"
                },
                "ack": True,
                "id": "2"
            }
            await ws.send(json.dumps(send_msg))
            
            # Expect two messages: The Ack for "sent" AND the Broadcast of the message
            # The order might vary depending on server processing speed
            
            # We assume we get Ack first or Broadcast first.
            
            msg1 = json.loads(await ws.recv())
            print(f"✓ Received Msg 1: {msg1}")
            
            msg2 = json.loads(await ws.recv())
            print(f"✓ Received Msg 2: {msg2}")
            
            # Verify one is ack and one is the message
            # ...
            
    except Exception as e:
        print(f"✗ Chat test failed: {e}")

    # 5. Test Notifications (Authenticated)
    print("\n[5] Testing Notifications...")
    try:
        async with connect(f"{WS_BASE_URL}{MODULE_PREFIX}/ws/notifications", extra_headers=headers) as ws:
            print("✓ Connected to Notifications")
            # Just verify connection logic for now
    except Exception as e:
        print(f"✗ Notification test failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_sockets())
    except KeyboardInterrupt:
        pass
