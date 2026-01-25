#!/usr/bin/env python3
"""
Session Component Integration Test

This demonstrates the session integration at the component level.
"""

import asyncio
from datetime import datetime, timedelta
from aquilia.sessions import SessionEngine, SessionPolicy, MemoryStore, CookieTransport, TransportPolicy
from aquilia.middleware_ext.session_middleware import SessionMiddleware
from aquilia.controller.base import RequestCtx
from aquilia.request import Request
from aquilia.response import Response


async def test_session_components():
    """Test session components integration."""
    
    print("🧪 Testing Session Components Integration")
    print("=" * 60)
    
    # 1. Create session engine
    policy = SessionPolicy(
        name="test_policy",
        ttl=timedelta(days=1),
        idle_timeout=timedelta(minutes=30),
        transport=TransportPolicy(
            adapter="cookie",
            cookie_name="test_session",
        ),
    )
    
    store = MemoryStore(max_sessions=1000)
    transport = CookieTransport(policy=policy.transport)
    
    engine = SessionEngine(policy=policy, store=store, transport=transport)
    print("✅ SessionEngine created")
    
    # 2. Create session middleware
    middleware = SessionMiddleware(engine)
    print("✅ SessionMiddleware created")
    
    # 3. Create mock request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope, lambda: None)
    request.state = {}  # Initialize state
    print("✅ Mock request created")
    
    # 4. Create RequestCtx
    ctx = RequestCtx(request=request)
    print("✅ RequestCtx created")
    
    # 5. Test session middleware
    async def mock_handler(req, context):
        """Mock handler to test session integration."""
        print(f"   Handler called with session: {getattr(context, 'session', 'None')}")
        print(f"   Request state has session: {'session' in req.state}")
        print(f"   RequestCtx has session: {hasattr(context, 'session')}")
        if hasattr(context, 'session') and context.session:
            print(f"   Session ID: {context.session.id}")
            print(f"   Session authenticated: {context.session.is_authenticated}")
        return Response("Session test complete")
    
    print("\n🔄 Testing session middleware flow...")
    try:
        response = await middleware(request, ctx, mock_handler)
        print("✅ Session middleware processed successfully")
        print(f"✅ Response: {response}")
        
        # Check results
        if hasattr(ctx, 'session') and ctx.session:
            print(f"✅ Session created: {ctx.session.id}")
            print(f"✅ Session type: {type(ctx.session)}")
        else:
            print("⚠️  No session in RequestCtx")
            
        if 'session' in request.state:
            print(f"✅ Session in request.state: {request.state['session'].id}")
        else:
            print("⚠️  No session in request.state")
            
    except Exception as e:
        print(f"❌ Session middleware failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Session components integration test complete!")
    

if __name__ == "__main__":
    asyncio.run(test_session_components())