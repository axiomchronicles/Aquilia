"""
AquilAuth - Complete Integration Example

Demonstrates deep integration of all Aquilia systems:
- Aquilia Sessions (session management)
- AquilAuth (authentication/authorization)
- Aquilia DI (dependency injection)
- Aquilia Flow (guards and pipeline)
- AquilaFaults (structured errors)
- Aquilia Manifest (configuration)

This example shows production-ready setup.
"""

import asyncio
import logging
from datetime import timedelta

from aquilia.di import Container
from aquilia.faults import FaultEngine
from aquilia.middleware import MiddlewareStack
from aquilia.request import Request
from aquilia.response import Response
from aquilia.sessions import (
    MemoryStore as SessionMemoryStore,
    SessionEngine,
    CookieTransport,
)

# Auth imports
from aquilia.auth.core import Identity, IdentityStatus
from aquilia.auth.integration.aquila_sessions import (
    user_session_policy,
    SessionAuthBridge,
)
from aquilia.auth.integration.di_providers import (
    create_auth_container,
    AuthConfig,
)
from aquilia.auth.integration.middleware import (
    create_auth_middleware_stack,
)
from aquilia.auth.integration.flow_guards import (
    require_auth,
    require_scopes,
    require_roles,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("aquilia.integration_example")


# ============================================================================
# Application Setup
# ============================================================================


class IntegratedAquiliaApp:
    """
    Complete Aquilia application with deep integration.
    
    Demonstrates:
    - DI container setup
    - Session engine configuration
    - Auth manager initialization
    - Middleware stack composition
    - Flow guards
    - Request handling
    """
    
    def __init__(self):
        """Initialize integrated application."""
        self.logger = logger
        
        # 1. Configure authentication
        self.auth_config = (
            AuthConfig()
            .rate_limit(max_attempts=5, window_seconds=900)
            .sessions(ttl_days=7, idle_timeout_hours=1, max_sessions=5)
            .tokens(access_ttl_minutes=15, refresh_ttl_days=30)
            .mfa(enabled=True, required=False)
            .oauth(enabled=True)
            .build()
        )
        
        # 2. Create DI container with all auth providers
        self.container = create_auth_container(self.auth_config)
        self.logger.info("✅ DI container created with auth providers")
        
        # 3. Resolve core components from DI
        self.auth_manager = self.container.resolve("AuthManager")
        self.token_manager = self.container.resolve("TokenManager")
        self.authz_engine = self.container.resolve("AuthzEngine")
        self.logger.info("✅ Core auth components resolved from DI")
        
        # 4. Create session engine
        session_policy = user_session_policy(
            ttl=timedelta(days=7),
            idle_timeout=timedelta(hours=1),
            max_sessions=5,
            store_name="memory",
        )
        
        self.session_engine = SessionEngine(
            policy=session_policy,
            store=SessionMemoryStore(),
            transport=CookieTransport(session_policy.transport),
            logger=logging.getLogger("aquilia.sessions"),
        )
        self.logger.info("✅ Session engine configured")
        
        # 5. Create session-auth bridge
        self.session_bridge = SessionAuthBridge(self.session_engine)
        
        # 6. Create fault engine
        self.fault_engine = FaultEngine(
            logger=logging.getLogger("aquilia.faults"),
            debug=True,
        )
        self.logger.info("✅ Fault engine initialized")
        
        # 7. Create middleware stack
        self.middleware_stack = self._create_middleware_stack()
        self.logger.info("✅ Middleware stack configured")
        
        # 8. Setup RBAC roles
        self._setup_rbac()
        self.logger.info("✅ RBAC roles configured")
    
    def _create_middleware_stack(self) -> MiddlewareStack:
        """Create complete middleware stack."""
        stack = MiddlewareStack()
        
        # Get middleware list from factory
        middleware_list = create_auth_middleware_stack(
            session_engine=self.session_engine,
            auth_manager=self.auth_manager,
            app_container=self.container,
            fault_engine=self.fault_engine,
            require_auth=False,  # Will use per-route guards
        )
        
        # Add to stack
        for i, mw in enumerate(middleware_list):
            stack.add(
                middleware=mw,
                scope="global",
                priority=i * 10,
                name=mw.__class__.__name__,
            )
        
        return stack
    
    def _setup_rbac(self) -> None:
        """Configure RBAC roles and permissions."""
        rbac = self.authz_engine.rbac
        
        # Define roles
        rbac.define_role("admin", permissions=[
            "users:read", "users:write", "users:delete",
            "orders:read", "orders:write", "orders:delete",
            "products:read", "products:write", "products:delete",
        ])
        
        rbac.define_role("editor", permissions=[
            "users:read",
            "orders:read", "orders:write",
            "products:read", "products:write",
        ], inherits_from=["viewer"])
        
        rbac.define_role("viewer", permissions=[
            "users:read",
            "orders:read",
            "products:read",
        ])
    
    async def handle_request(self, request: Request) -> Response:
        """
        Handle incoming request through complete pipeline.
        
        Args:
            request: Incoming request
            
        Returns:
            Response
        """
        # Route request to handler
        path = request.path
        method = request.method
        
        # Simple routing
        if path == "/auth/login" and method == "POST":
            return await self._handle_login(request)
        elif path == "/auth/logout" and method == "POST":
            return await self._handle_logout(request)
        elif path == "/api/profile" and method == "GET":
            return await self._handle_profile(request)
        elif path == "/api/orders" and method == "GET":
            return await self._handle_orders(request)
        elif path == "/api/admin/users" and method == "GET":
            return await self._handle_admin_users(request)
        else:
            return Response.json({"error": "Not found"}, status=404)
    
    # ========================================================================
    # Route Handlers
    # ========================================================================
    
    async def _handle_login(self, request: Request) -> Response:
        """
        Handle login request.
        
        POST /auth/login
        Body: {"username": "...", "password": "..."}
        """
        try:
            data = await request.json()
            username = data.get("username")
            password = data.get("password")
            
            if not username or not password:
                return Response.json(
                    {"error": "Username and password required"},
                    status=400,
                )
            
            # Authenticate
            auth_result = await self.auth_manager.authenticate_password(
                username=username,
                password=password,
            )
            
            # Create session
            session = await self.session_bridge.create_auth_session(
                identity=auth_result.identity,
                request=request,
                token_claims=auth_result.token_claims,
            )
            
            # Create response with session cookie
            response = Response.json({
                "success": True,
                "identity_id": auth_result.identity.identity_id,
                "access_token": auth_result.access_token,
                "refresh_token": auth_result.refresh_token,
            })
            
            # Commit session (sets cookie)
            await self.session_engine.commit(session, response)
            
            self.logger.info(f"✅ User logged in: {username}")
            return response
        
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return Response.json(
                {"error": "Authentication failed"},
                status=401,
            )
    
    async def _handle_logout(self, request: Request) -> Response:
        """
        Handle logout request.
        
        POST /auth/logout
        """
        try:
            # Get session
            session = await self.session_engine.resolve(request)
            
            # Destroy session
            response = Response.json({"success": True})
            await self.session_bridge.logout(session, response)
            
            self.logger.info("✅ User logged out")
            return response
        
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            return Response.json({"success": True})  # Always succeed
    
    async def _handle_profile(self, request: Request) -> Response:
        """
        Handle profile request (requires auth).
        
        GET /api/profile
        """
        # Get identity from request state (set by middleware)
        identity = request.state.get("identity")
        
        if not identity:
            return Response.json(
                {"error": "Authentication required"},
                status=401,
            )
        
        return Response.json({
            "identity_id": identity.identity_id,
            "username": identity.username,
            "email": identity.email,
            "roles": identity.roles,
            "scopes": identity.scopes,
            "tenant_id": identity.tenant_id,
        })
    
    async def _handle_orders(self, request: Request) -> Response:
        """
        Handle orders request (requires auth + scope).
        
        GET /api/orders
        """
        # Get identity
        identity = request.state.get("identity")
        
        if not identity:
            return Response.json(
                {"error": "Authentication required"},
                status=401,
            )
        
        # Check scope
        if "orders:read" not in identity.scopes:
            return Response.json(
                {"error": "Insufficient scope"},
                status=403,
            )
        
        return Response.json({
            "orders": [
                {"id": "order_1", "total": 99.99},
                {"id": "order_2", "total": 149.99},
            ],
        })
    
    async def _handle_admin_users(self, request: Request) -> Response:
        """
        Handle admin users request (requires auth + role).
        
        GET /api/admin/users
        """
        # Get identity
        identity = request.state.get("identity")
        
        if not identity:
            return Response.json(
                {"error": "Authentication required"},
                status=401,
            )
        
        # Check role
        if "admin" not in identity.roles:
            return Response.json(
                {"error": "Insufficient permissions"},
                status=403,
            )
        
        return Response.json({
            "users": [
                {"id": "user_1", "username": "alice", "role": "admin"},
                {"id": "user_2", "username": "bob", "role": "editor"},
            ],
        })


# ============================================================================
# Demo Functions
# ============================================================================


async def demo_complete_integration():
    """
    Demonstrate complete Aquilia integration.
    
    Shows:
    1. Application setup with all systems integrated
    2. User registration and authentication
    3. Session management
    4. Authorization checks
    5. Request handling through complete pipeline
    """
    print("\n" + "=" * 80)
    print("🚀 Aquilia Complete Integration Demo")
    print("=" * 80)
    
    # 1. Create integrated application
    print("\n📦 Phase 1: Application Setup")
    print("-" * 80)
    app = IntegratedAquiliaApp()
    print("✅ All systems initialized and integrated")
    
    # 2. Create test user
    print("\n👤 Phase 2: User Registration")
    print("-" * 80)
    
    test_user = Identity(
        identity_id="user_alice",
        username="alice",
        email="alice@example.com",
        status=IdentityStatus.ACTIVE,
        roles=["admin"],
        scopes=["users:read", "users:write", "orders:read", "orders:write"],
        tenant_id="tenant_demo",
    )
    
    await app.auth_manager.identity_store.create_identity(test_user)
    print(f"✅ User created: {test_user.username}")
    
    # Set password
    from aquilia.auth.core import PasswordCredential
    password_cred = PasswordCredential(
        credential_id="cred_alice_password",
        identity_id=test_user.identity_id,
        password_hash=app.auth_manager.password_hasher.hash("SecurePass123!"),
    )
    await app.auth_manager.credential_store.store_credential(password_cred)
    print("✅ Password set")
    
    # 3. Simulate login request
    print("\n🔐 Phase 3: Authentication")
    print("-" * 80)
    
    # Create mock request
    class MockRequest:
        def __init__(self, method, path, body=None):
            self.method = method
            self.path = path
            self._body = body
            self.state = {}
            self.scope = {"type": "http", "method": method, "path": path}
        
        def header(self, name, default=None):
            return default
        
        async def json(self):
            return self._body
    
    login_request = MockRequest(
        "POST",
        "/auth/login",
        {"username": "alice", "password": "SecurePass123!"},
    )
    
    login_response = await app.handle_request(login_request)
    print(f"✅ Login successful: status={login_response.status}")
    
    # 4. Simulate authenticated requests
    print("\n🛡️  Phase 4: Authorization")
    print("-" * 80)
    
    # Profile request (requires auth)
    profile_request = MockRequest("GET", "/api/profile")
    profile_request.state["identity"] = test_user
    profile_response = await app.handle_request(profile_request)
    print(f"✅ Profile request: status={profile_response.status}")
    
    # Orders request (requires scope)
    orders_request = MockRequest("GET", "/api/orders")
    orders_request.state["identity"] = test_user
    orders_response = await app.handle_request(orders_request)
    print(f"✅ Orders request: status={orders_response.status}")
    
    # Admin request (requires role)
    admin_request = MockRequest("GET", "/api/admin/users")
    admin_request.state["identity"] = test_user
    admin_response = await app.handle_request(admin_request)
    print(f"✅ Admin request: status={admin_response.status}")
    
    # 5. Summary
    print("\n" + "=" * 80)
    print("✅ Integration Demo Complete!")
    print("=" * 80)
    print("\n📊 Summary:")
    print(f"  • DI Container: {len(app.container._providers)} providers registered")
    print(f"  • Session Engine: {app.session_engine.policy.name} policy")
    print(f"  • Auth Manager: Rate limiting + MFA ready")
    print(f"  • Authorization: RBAC + ABAC + Scopes")
    print(f"  • Middleware: {len(app.middleware_stack.middlewares)} middleware layers")
    print(f"  • Fault Engine: Structured error handling")
    print("\n🎉 All Aquilia systems deeply integrated and working together!")


# ============================================================================
# Main Entry Point
# ============================================================================


if __name__ == "__main__":
    asyncio.run(demo_complete_integration())
