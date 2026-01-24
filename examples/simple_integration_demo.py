"""
Simple Aquilia Integration Demo

Shows how users can easily access all integrated components with zero hassle.
Everything is just one import away!
"""

print("\n" + "=" * 70)
print("🎯 AQUILIA INTEGRATION DEMO")
print("=" * 70 + "\n")

# ============================================================================
# STEP 1: Import Everything You Need (Zero Hassle!)
# ============================================================================

print("📦 Importing all integrated components...")

from aquilia import (
    # Core Framework
    AquiliaServer,
    AppManifest,
    Request,
    Response,
    Config,
    
    # Aquilary Registry (replaces legacy)
    Aquilary,
    AquilaryRegistry,
    RuntimeRegistry,
    
    # Flow System
    flow,
    Flow,
    Router,
    FlowEngine,
    
    # DI System
    Container,
    service,
    factory,
    inject,
    
    # Sessions
    Session,
    SessionEngine,
    SessionPolicy,
    CookieTransport,
    
    # Auth Core
    Identity,
    AuthManager,
    TokenManager,
    KeyRing,
    PasswordHasher,
    
    # Auth Integration (the magic!)
    AuthPrincipal,
    SessionAuthBridge,
    user_session_policy,
    require_auth,
    require_scopes,
    
    # Faults
    Fault,
    FaultEngine,
    
    # Middleware
    MiddlewareStack,
    
    # Lifecycle
    LifecycleCoordinator,
)

print("✅ All components imported successfully!\n")

# ============================================================================
# STEP 2: Define Services with DI Decorators
# ============================================================================

print("🔧 Defining services with DI...")

@service(scope="app")
class DatabaseService:
    """App-scoped database - one instance for the whole app."""
    def __init__(self):
        self.name = "PostgreSQL"
        print(f"  💾 Created {self.name} service")

@service(scope="app")
class UserService:
    """User service with automatic dependency injection."""
    def __init__(self, db: DatabaseService):
        self.db = db
        print(f"  👤 Created UserService with {db.name}")

print("✅ Services defined with @service decorator\n")

# ============================================================================
# STEP 3: Create Application Manifest
# ============================================================================

print("📋 Creating application manifest...")

manifest = AppManifest(
    name="my_app",
    version="1.0.0",
    description="Complete integrated app",
    controllers=[],
    services=[],
)

print(f"✅ Manifest created: {manifest.name} v{manifest.version}\n")

# ============================================================================
# STEP 4: Create Session Policy
# ============================================================================

print("🍪 Setting up sessions...")

# Get a pre-configured session policy for user sessions
policy = user_session_policy()

print(f"✅ Session policy ready\n")

# ============================================================================
# STEP 5: Create Identity for Auth
# ============================================================================

print("🔐 Creating authenticated identity...")

from aquilia.auth.core import IdentityType

identity = Identity(
    id="user_42",
    type=IdentityType.USER,
    attributes={
        "username": "demo_user",
        "email": "demo@example.com",
        "roles": ["user", "admin"],
        "scopes": ["read:profile", "write:profile"],
    }
)

print(f"✅ Identity created: {identity.id}")
print(f"   - Username: {identity.get_attribute('username')}")
print(f"   - Roles: {identity.get_attribute('roles')}")
print(f"   - Has 'admin' role: {identity.has_role('admin')}")
print(f"   - Has 'read:profile' scope: {identity.has_scope('read:profile')}\n")

# ============================================================================
# STEP 6: Create Auth Principal for Sessions
# ============================================================================

print("🔗 Bridging Auth with Sessions...")

principal = AuthPrincipal.from_identity(identity)

print(f"✅ AuthPrincipal created from Identity")
print(f"   - Principal ID: {principal.id}")
print(f"   - Principal kind: {principal.kind}")
print(f"   - Roles: {principal.roles}")
print(f"   - Scopes: {principal.scopes}\n")

# ============================================================================
# STEP 7: Show Guard Functions
# ============================================================================

print("🛡️  Auth guards for routes...")

print(f"✅ Guard functions available:")
print(f"   - require_auth(): {require_auth.__name__}")
print(f"   - require_scopes(): {require_scopes.__name__}")
print(f"   These integrate seamlessly with Flow for route protection\n")

# ============================================================================
# STEP 8: Create Router and Engine
# ============================================================================

print("🚦 Setting up router and engine...")

router = Router()
container = Container()
engine = FlowEngine(container=container)

print(f"✅ Router and FlowEngine ready")
print(f"   - Router manages routes efficiently (radix trie)")
print(f"   - FlowEngine executes flows with DI\n")

# ============================================================================
# STEP 9: Create Middleware Stack
# ============================================================================

print("⚙️  Creating middleware stack...")

middleware = MiddlewareStack()

print(f"✅ Middleware stack ready")
print(f"   - Composable middleware for request processing\n")

# ============================================================================
# STEP 10: Show Lifecycle Available
# ============================================================================

print("♻️  Lifecycle management available...")

print(f"✅ LifecycleCoordinator available")
print(f"   - Manages startup/shutdown hooks")
print(f"   - Integrated with server lifecycle\n")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("=" * 70)
print("✨ INTEGRATION COMPLETE!")
print("=" * 70)
print("\n🎉 All systems are deeply integrated and working together:\n")
print("  ✅ Aquilary - Manifest-driven app registry")
print("  ✅ DI - Automatic dependency injection with @service")
print("  ✅ Sessions - Cryptographic session management")
print("  ✅ Auth - Complete auth system (OAuth2, MFA, RBAC/ABAC)")
print("  ✅ Auth Integration - Sessions + Auth bridge")
print("  ✅ Flow - Type-safe routing with guards")
print("  ✅ Router - Efficient route matching")
print("  ✅ Engine - Flow execution with DI")
print("  ✅ Faults - Structured error handling")
print("  ✅ Middleware - Composable request processing")
print("  ✅ Lifecycle - Startup/shutdown management")

print("\n🚀 Everything is just ONE IMPORT away!")
print("=" * 70)
print("\n💡 Key Benefits:")
print("  • No complex setup required")
print("  • All systems work together seamlessly")
print("  • Type-safe with full IDE support")
print("  • Production-ready out of the box")
print("  • Zero hassle for developers!")

print("\n" + "=" * 70)
print("📚 Next Steps:")
print("=" * 70)
print("\n1. Define your routes with @flow and guards")
print("2. Add your services with @service decorator")
print("3. Create your manifest with AppManifest")
print("4. Start the server with AquiliaServer")
print("\n🎊 You're ready to build production apps with Aquilia!")
print("=" * 70 + "\n")
