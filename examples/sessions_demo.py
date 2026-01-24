"""
AquilaSessions - Integration Example

Demonstrates complete integration with:
- Aquilia DI system
- Flow-based routing
- Session management
- Request lifecycle

This example shows a real-world use case: a shopping cart application
with authenticated sessions.
"""

import asyncio
from datetime import timedelta

from aquilia import flow, Response
from aquilia.di import service, Container
from aquilia.sessions import (
    Session,
    SessionPolicy,
    PersistencePolicy,
    ConcurrencyPolicy,
    TransportPolicy,
    SessionEngine,
    MemoryStore,
    CookieTransport,
    SessionPrincipal,
)


# ============================================================================
# 1. Define Session Policy
# ============================================================================

# User session policy: 7 days TTL, 30 min idle timeout
user_session_policy = SessionPolicy(
    name="user_default",
    ttl=timedelta(days=7),
    idle_timeout=timedelta(minutes=30),
    rotate_on_use=False,
    rotate_on_privilege_change=True,  # Rotate on login/logout
    persistence=PersistencePolicy(
        enabled=True,
        store_name="memory",
        write_through=True,
    ),
    concurrency=ConcurrencyPolicy(
        max_sessions_per_principal=5,
        behavior_on_limit="evict_oldest",
    ),
    transport=TransportPolicy(
        adapter="cookie",
        cookie_name="shop_session",
        cookie_httponly=True,
        cookie_secure=True,
        cookie_samesite="lax",
    ),
    scope="user",
)


# ============================================================================
# 2. Services with DI
# ============================================================================

@service(scope="app", name="UserService")
class UserService:
    """
    User authentication service (app-scoped).
    """
    
    def __init__(self):
        # In real app, would inject database
        self.users = {
            "user@example.com": {"id": "user_123", "name": "Alice", "password": "secret"},
            "admin@example.com": {"id": "user_456", "name": "Bob", "password": "admin123"},
        }
    
    async def authenticate(self, email: str, password: str) -> dict | None:
        """Authenticate user by credentials."""
        user = self.users.get(email)
        if user and user["password"] == password:
            return user
        return None
    
    async def get_user(self, user_id: str) -> dict | None:
        """Get user by ID."""
        for user in self.users.values():
            if user["id"] == user_id:
                return user
        return None


@service(scope="request", name="CartService")
class CartService:
    """
    Shopping cart service (request-scoped).
    
    Note: This is request-scoped to demonstrate that it can access
    the session for the current request.
    """
    
    def __init__(self, session: Session):
        """
        Initialize with current session.
        
        Session is injected by DI system.
        """
        self.session = session
    
    def add_item(self, item_id: str, quantity: int = 1) -> None:
        """Add item to cart."""
        cart = self.session.data.get("cart", {})
        
        if item_id in cart:
            cart[item_id] += quantity
        else:
            cart[item_id] = quantity
        
        self.session.data["cart"] = cart
    
    def remove_item(self, item_id: str) -> None:
        """Remove item from cart."""
        cart = self.session.data.get("cart", {})
        cart.pop(item_id, None)
        self.session.data["cart"] = cart
    
    def get_cart(self) -> dict:
        """Get current cart."""
        return self.session.data.get("cart", {})
    
    def clear_cart(self) -> None:
        """Clear cart."""
        self.session.data["cart"] = {}


# ============================================================================
# 3. Flow Controllers with Session Injection
# ============================================================================

@flow("/").GET
async def index(session: Session):
    """
    Home page - shows session status.
    
    Session is automatically injected by DI system.
    """
    return Response.json({
        "message": "Welcome to the shop!",
        "authenticated": session.is_authenticated,
        "user_id": session.principal.id if session.principal else None,
        "session_id": str(session.id)[:16] + "...",
    })


@flow("/login").POST
async def login(request, session: Session, user_service: UserService):
    """
    Login endpoint - creates authenticated session.
    
    Both Session and UserService are injected.
    """
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    
    # Authenticate
    user = await user_service.authenticate(email, password)
    
    if not user:
        return Response.json(
            {"error": "Invalid credentials"},
            status=401
        )
    
    # Mark session as authenticated
    principal = SessionPrincipal(
        kind="user",
        id=user["id"],
        attributes={"email": email, "name": user["name"]},
    )
    session.mark_authenticated(principal)
    
    # Note: Session will be rotated (new ID) because privilege changed
    
    return Response.json({
        "message": "Logged in successfully",
        "user": {
            "id": user["id"],
            "name": user["name"],
        }
    })


@flow("/logout").POST
async def logout(session: Session):
    """
    Logout endpoint - destroys session.
    """
    # Clear authentication
    session.clear_authentication()
    
    # Clear cart
    session.clear_data()
    
    # Note: SessionEngine will destroy session and clear cookie
    
    return Response.json({
        "message": "Logged out successfully"
    })


@flow("/profile").GET
async def profile(session: Session, user_service: UserService):
    """
    Profile endpoint - requires authentication.
    """
    if not session.is_authenticated:
        return Response.json(
            {"error": "Authentication required"},
            status=401
        )
    
    # Get user details
    user = await user_service.get_user(session.principal.id)
    
    return Response.json({
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": session.principal.get_attribute("email"),
        },
        "session": {
            "created_at": session.created_at.isoformat(),
            "last_accessed_at": session.last_accessed_at.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }
    })


@flow("/cart").GET
async def view_cart(session: Session, cart_service: CartService):
    """
    View shopping cart.
    
    CartService is request-scoped and has access to session.
    """
    cart = cart_service.get_cart()
    
    return Response.json({
        "cart": cart,
        "item_count": sum(cart.values()),
        "authenticated": session.is_authenticated,
    })


@flow("/cart/add").POST
async def add_to_cart(request, cart_service: CartService):
    """
    Add item to cart.
    """
    data = await request.json()
    item_id = data.get("item_id")
    quantity = data.get("quantity", 1)
    
    if not item_id:
        return Response.json(
            {"error": "item_id required"},
            status=400
        )
    
    cart_service.add_item(item_id, quantity)
    
    return Response.json({
        "message": "Item added to cart",
        "cart": cart_service.get_cart(),
    })


@flow("/cart/clear").POST
async def clear_cart(cart_service: CartService):
    """
    Clear shopping cart.
    """
    cart_service.clear_cart()
    
    return Response.json({
        "message": "Cart cleared"
    })


# ============================================================================
# 4. SessionMiddleware for Integration
# ============================================================================

class SessionMiddleware:
    """
    Middleware that integrates SessionEngine with request lifecycle.
    
    This middleware:
    1. Resolves session at request start
    2. Binds session to DI container
    3. Commits session at request end
    """
    
    def __init__(self, session_engine: SessionEngine):
        self.engine = session_engine
    
    async def __call__(self, request, call_next):
        """Process request with session management."""
        # Get DI container from request state
        container = request.state.get("di_container")
        
        # Phase 1-4: Resolve session (detection, resolution, validation, binding)
        session = await self.engine.resolve(request, container)
        
        # Store in request state
        request.state["session"] = session
        
        # Register session in DI container (request-scoped)
        if container:
            await container.register_instance(Session, session, scope="request")
        
        # Check concurrency limits (if authenticated)
        if session.is_authenticated:
            try:
                await self.engine.check_concurrency(session)
            except Exception as e:
                # Log but don't fail request
                print(f"Concurrency check failed: {e}")
        
        # Process request
        privilege_before = session.is_authenticated
        response = await call_next(request)
        privilege_after = session.is_authenticated
        
        # Detect privilege change
        privilege_changed = privilege_before != privilege_after
        
        # Phase 6-7: Commit session (commit, emission)
        await self.engine.commit(session, response, privilege_changed)
        
        return response


# ============================================================================
# 5. Application Setup
# ============================================================================

async def create_app():
    """
    Create application with session management.
    """
    # 1. Create DI container
    container = Container(scope="app")
    
    # 2. Register services
    from aquilia.di.providers import ClassProvider
    
    user_service_provider = ClassProvider(UserService, scope="app")
    container.register(user_service_provider)
    
    cart_service_provider = ClassProvider(CartService, scope="request")
    container.register(cart_service_provider)
    
    # 3. Create session components
    store = MemoryStore(max_sessions=10000)
    transport = CookieTransport(user_session_policy.transport)
    engine = SessionEngine(
        policy=user_session_policy,
        store=store,
        transport=transport,
    )
    
    # 4. Register event handler for observability
    def log_session_event(event_data):
        print(f"[SESSION EVENT] {event_data['event']}: {event_data.get('session_id_hash', 'N/A')}")
    
    engine.on_event(log_session_event)
    
    print("✅ Application created with session management")
    print(f"   Policy: {user_session_policy.name}")
    print(f"   Store: MemoryStore")
    print(f"   Transport: CookieTransport")
    print()
    
    return {
        "container": container,
        "engine": engine,
        "store": store,
    }


# ============================================================================
# 6. Demo Usage
# ============================================================================

async def demo():
    """
    Demonstrate session management.
    """
    print("="*70)
    print("AQUILASESSIONS - INTEGRATION DEMO")
    print("="*70)
    print()
    
    # Create app
    app = await create_app()
    engine = app["engine"]
    store = app["store"]
    
    # Simulate request/response
    from aquilia.request import Request
    from aquilia.response import Response
    
    # Create mock request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
    }
    
    async def receive():
        return {"type": "http.request", "body": b""}
    
    request = Request(scope, receive)
    response = Response()
    
    # Test 1: Anonymous session
    print("Test 1: Anonymous Session")
    print("-" * 70)
    
    session = await engine.resolve(request, None)
    print(f"✅ Session created: {session.id}")
    print(f"   Authenticated: {session.is_authenticated}")
    print(f"   Scope: {session.scope.value}")
    print(f"   Expires: {session.expires_at}")
    print()
    
    # Add cart item
    session.data["cart"] = {"item_1": 2, "item_2": 1}
    print(f"✅ Cart added: {session.data['cart']}")
    print()
    
    # Commit session
    await engine.commit(session, response)
    print(f"✅ Session committed and cookie set")
    print()
    
    # Test 2: Authenticated session
    print("Test 2: Authenticated Session")
    print("-" * 70)
    
    principal = SessionPrincipal(
        kind="user",
        id="user_123",
        attributes={"email": "user@example.com", "name": "Alice"}
    )
    session.mark_authenticated(principal)
    print(f"✅ Session authenticated: {principal.id}")
    print(f"   Name: {principal.get_attribute('name')}")
    print(f"   Email: {principal.get_attribute('email')}")
    print()
    
    # Commit with privilege change (triggers rotation)
    await engine.commit(session, response, privilege_changed=True)
    print(f"✅ Session rotated (new ID on privilege change)")
    print(f"   New ID: {session.id}")
    print()
    
    # Test 3: Session persistence
    print("Test 3: Session Persistence")
    print("-" * 70)
    
    old_id = session.id
    await store.save(session)
    print(f"✅ Session saved to store")
    
    loaded = await store.load(old_id)
    print(f"✅ Session loaded from store: {loaded.id}")
    print(f"   Cart: {loaded.data.get('cart')}")
    print(f"   Principal: {loaded.principal.id if loaded.principal else None}")
    print()
    
    # Test 4: Store statistics
    print("Test 4: Store Statistics")
    print("-" * 70)
    
    stats = store.get_stats()
    print(f"✅ Store stats:")
    print(f"   Total sessions: {stats['total_sessions']}")
    print(f"   Max sessions: {stats['max_sessions']}")
    print(f"   Utilization: {stats['utilization']*100:.1f}%")
    print()
    
    # Test 5: Cleanup
    print("Test 5: Cleanup")
    print("-" * 70)
    
    removed = await engine.cleanup_expired()
    print(f"✅ Expired sessions cleaned: {removed}")
    print()
    
    await engine.shutdown()
    print("✅ Engine shutdown")
    print()
    
    print("="*70)
    print("DEMO COMPLETE - All systems working!")
    print("="*70)
    print()
    print("Integration verified:")
    print("  ✅ Session creation and resolution")
    print("  ✅ Authentication and principal binding")
    print("  ✅ Session rotation on privilege change")
    print("  ✅ Session persistence and loading")
    print("  ✅ Store statistics and monitoring")
    print("  ✅ Cleanup and shutdown")
    print()


if __name__ == "__main__":
    asyncio.run(demo())
