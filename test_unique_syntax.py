#!/usr/bin/env python3
"""
Test Unique Aquilia Session Syntax

This test demonstrates the complete unique Aquilia session syntax including:
- SessionPolicyBuilder with fluent syntax
- MemoryStore factory methods  
- CookieTransport and HeaderTransport factory methods
- Integration.sessions template configurations
- Deep framework integration with RequestCtx
"""

import asyncio
from aquilia.sessions import (
    SessionPolicy, 
    SessionEngine, 
    MemoryStore, 
    CookieTransport,
    HeaderTransport,
    Session, 
    SessionID,
    SessionPrincipal,
)
from aquilia.config_builders import Integration
from aquilia.request import Request
from aquilia.response import Response


async def test_unique_session_syntax():
    """Test the complete unique Aquilia session syntax."""
    
    print("🚀 Testing Unique Aquilia Session Syntax")
    print("=" * 60)
    
    # Test 1: SessionPolicy Fluent Builder
    print("\n1. SessionPolicy Fluent Builder")
    print("-" * 40)
    
    policy = (SessionPolicy
              .for_web_users()
              .lasting(days=7)
              .idle_timeout(hours=2) 
              .rotating_on_auth()
              .web_defaults()
              .build())
    
    print(f"✅ Policy created with fluent syntax: {policy.name}")
    print(f"   TTL: {policy.ttl}")
    print(f"   Idle timeout: {policy.idle_timeout}")
    print(f"   Rotates on privilege: {policy.rotate_on_privilege_change}")
    
    # Test 2: MemoryStore Factory Methods
    print("\n2. MemoryStore Factory Methods") 
    print("-" * 40)
    
    web_store = MemoryStore.web_optimized()
    api_store = MemoryStore.api_optimized()
    mobile_store = MemoryStore.mobile_optimized()
    dev_store = MemoryStore.development_focused()
    high_throughput_store = MemoryStore.high_throughput()
    
    print(f"✅ Web store: max_sessions={web_store.max_sessions}")
    print(f"✅ API store: max_sessions={api_store.max_sessions}")
    print(f"✅ Mobile store: max_sessions={mobile_store.max_sessions}")
    print(f"✅ Dev store: max_sessions={dev_store.max_sessions}")
    print(f"✅ High throughput store: max_sessions={high_throughput_store.max_sessions}")
    
    # Test 3: CookieTransport Factory Methods
    print("\n3. CookieTransport Factory Methods")
    print("-" * 40)
    
    browser_transport = CookieTransport.for_web_browsers()
    spa_transport = CookieTransport.for_spa_applications()
    mobile_transport = CookieTransport.for_mobile_webviews()
    default_transport = CookieTransport.with_aquilia_defaults()
    
    print(f"✅ Browser transport: {browser_transport.cookie_name}, samesite={browser_transport.policy.cookie_samesite}")
    print(f"✅ SPA transport: {spa_transport.cookie_name}, samesite={spa_transport.policy.cookie_samesite}")
    print(f"✅ Mobile transport: {mobile_transport.cookie_name}, samesite={mobile_transport.policy.cookie_samesite}")
    print(f"✅ Default transport: {default_transport.cookie_name}, samesite={default_transport.policy.cookie_samesite}")
    
    # Test 4: HeaderTransport Factory Methods
    print("\n4. HeaderTransport Factory Methods")
    print("-" * 40)
    
    rest_transport = HeaderTransport.for_rest_apis()
    graphql_transport = HeaderTransport.for_graphql_apis()
    mobile_api_transport = HeaderTransport.for_mobile_apis()
    microservice_transport = HeaderTransport.for_microservices()
    header_default_transport = HeaderTransport.with_aquilia_defaults()
    
    print(f"✅ REST transport: {rest_transport.header_name}")
    print(f"✅ GraphQL transport: {graphql_transport.header_name}")
    print(f"✅ Mobile API transport: {mobile_api_transport.header_name}")
    print(f"✅ Microservice transport: {microservice_transport.header_name}")
    print(f"✅ Header default transport: {header_default_transport.header_name}")
    
    # Test 5: Integration.sessions Template Configurations
    print("\n5. Integration.sessions Template Configurations")
    print("-" * 40)
    
    web_config = Integration.sessions.web_app()
    api_config = Integration.sessions.api_service() 
    mobile_config = Integration.sessions.mobile_app()
    
    print(f"✅ Web app config: enabled={web_config.get('enabled')}")
    print(f"   Policy type: {type(web_config.get('policy')).__name__}")
    print(f"   Store type: {type(web_config.get('store')).__name__}")
    print(f"   Transport type: {type(web_config.get('transport')).__name__}")
    
    print(f"✅ API service config: enabled={api_config.get('enabled')}")
    print(f"   Policy type: {type(api_config.get('policy')).__name__}")
    print(f"   Store type: {type(api_config.get('store')).__name__}")
    print(f"   Transport type: {type(api_config.get('transport')).__name__}")
    
    print(f"✅ Mobile app config: enabled={mobile_config.get('enabled')}")
    print(f"   Policy type: {type(mobile_config.get('policy')).__name__}")
    print(f"   Store type: {type(mobile_config.get('store')).__name__}")
    print(f"   Transport type: {type(mobile_config.get('transport')).__name__}")
    
    # Test 6: Complete Session Engine with Unique Syntax
    print("\n6. Complete Session Engine with Unique Syntax")
    print("-" * 40)
    
    # Create session engine using unique Aquilia syntax
    unique_policy = (SessionPolicy
                    .for_api_tokens()
                    .lasting(days=1) 
                    .idle_timeout(minutes=30)
                    .rotating_on_auth()
                    .api_defaults()
                    .build())
    
    unique_store = MemoryStore.api_optimized()
    unique_transport = HeaderTransport.for_rest_apis()
    
    engine = SessionEngine(
        policy=unique_policy,
        store=unique_store, 
        transport=unique_transport
    )
    
    print(f"✅ SessionEngine created with unique Aquilia syntax")
    print(f"   Policy: {unique_policy.name}")
    print(f"   Store capacity: {unique_store.max_sessions}")
    print(f"   Transport header: {unique_transport.header_name}")
    
    # Test 7: Session Creation and Access
    print("\n7. Session Creation and Access")
    print("-" * 40)
    
    # Create a session with principal directly (for testing)
    from datetime import datetime
    from aquilia.sessions.core import SessionScope, SessionFlag, SessionID
    
    principal = SessionPrincipal(
        kind="user",
        id="user_123",
        attributes={"role": "admin", "department": "engineering"}
    )
    
    session = Session(
        id=SessionID(),
        principal=principal,
        data={},
        created_at=datetime.utcnow(),
        last_accessed_at=datetime.utcnow(),
        expires_at=unique_policy.calculate_expiry(),
        scope=SessionScope.USER,
        flags=set(),
    )
    session.data["test_data"] = "unique_aquilia_session"
    session._policy_name = unique_policy.name
    print(f"✅ Session created: {session.id}")
    print(f"   Principal: {session.principal.id}")
    print(f"   Attributes: {session.principal.attributes}")
    
    # Simulate request/response cycle (simplified for testing)
    print(f"✅ Session created: {session.id}")
    print(f"   Principal: {session.principal.id}")
    print(f"   Attributes: {session.principal.attributes}")
    
    # Test store operations
    await unique_store.save(session)
    print(f"✅ Session saved to store")
    
    loaded_session = await unique_store.load(session.id)
    print(f"✅ Session loaded from store: {loaded_session.id}")
    print(f"   Test data: {loaded_session.data.get('test_data')}")
    
    # Test store statistics
    stats = unique_store.get_stats()
    print(f"✅ Store statistics:")
    print(f"   Total sessions: {stats['total_sessions']}")
    print(f"   Utilization: {stats['utilization']:.1%}")
    
    print("\n🎉 All Unique Aquilia Session Syntax Tests Passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_unique_session_syntax())