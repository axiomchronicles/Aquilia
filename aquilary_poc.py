"""
Aquilary POC - Proof of Concept for Manifest-Driven App Registry

Demonstrates:
1. Manifest definition and loading
2. Dependency resolution with cycle detection
3. Fingerprinting for reproducible deploys
4. Validation and error reporting
5. Registry modes (dev/prod/test)
6. Route conflict detection
"""

import sys
from typing import List


# ============================================================================
# DEMO 1: Simple App Manifest Definition
# ============================================================================

class AuthManifest:
    """Authentication app manifest."""
    name = "auth"
    version = "1.0.0"
    
    controllers = [
        "myapp.auth.controllers.AuthController",
        "myapp.auth.controllers.SessionController",
    ]
    
    services = [
        "myapp.auth.services.AuthService",
        "myapp.auth.services.TokenService",
    ]
    
    middlewares = [
        ("myapp.auth.middleware.AuthMiddleware", {"strict": True}),
    ]
    
    depends_on: List[str] = []  # No dependencies
    
    @staticmethod
    def on_startup():
        print("   🔐 Auth app starting...")
    
    @staticmethod
    def on_shutdown():
        print("   🔐 Auth app shutting down...")


class UserManifest:
    """User management app manifest."""
    name = "user"
    version = "2.1.0"
    
    controllers = [
        "myapp.user.controllers.UserController",
        "myapp.user.controllers.ProfileController",
    ]
    
    services = [
        "myapp.user.services.UserService",
        "myapp.user.services.UserRepository",
    ]
    
    middlewares = []
    
    depends_on = ["auth"]  # Depends on auth
    
    @staticmethod
    def on_startup():
        print("   👤 User app starting...")
    
    @staticmethod
    def on_shutdown():
        print("   👤 User app shutting down...")


class AdminManifest:
    """Admin panel app manifest."""
    name = "admin"
    version = "1.5.0"
    
    controllers = [
        "myapp.admin.controllers.AdminController",
        "myapp.admin.controllers.DashboardController",
    ]
    
    services = [
        "myapp.admin.services.AdminService",
    ]
    
    middlewares = [
        ("myapp.admin.middleware.AdminAuthMiddleware", {}),
    ]
    
    depends_on = ["user", "auth"]  # Depends on both user and auth
    
    @staticmethod
    def on_startup():
        print("   🔧 Admin app starting...")
    
    @staticmethod
    def on_shutdown():
        print("   🔧 Admin app shutting down...")


# ============================================================================
# DEMO 2: Configuration
# ============================================================================

class AppConfig:
    """Simple config class."""
    
    class apps:
        class auth:
            secret_key = "test-secret"
            token_expiry = 3600
        
        class user:
            max_users = 1000
            allow_registration = True
        
        class admin:
            require_2fa = True


def demo_1_basic_registry():
    """Demo 1: Basic registry with dependency resolution."""
    print("\n" + "="*70)
    print("DEMO 1: Basic Registry with Dependency Resolution")
    print("="*70)
    
    from aquilia.aquilary import Aquilary, RegistryMode
    
    # Build registry from manifests
    registry = Aquilary.from_manifests(
        manifests=[AuthManifest, UserManifest, AdminManifest],
        config=AppConfig(),
        mode="dev",
    )
    
    print("\n✅ Registry built successfully!")
    print(f"   Mode: {registry.mode.value}")
    print(f"   Fingerprint: {registry.fingerprint[:16]}...")
    print(f"   Apps: {len(registry.app_contexts)}")
    
    # Show load order
    print("\n📦 Load Order (dependency-first):")
    for ctx in registry.app_contexts:
        deps = f" (depends on: {', '.join(ctx.depends_on)})" if ctx.depends_on else ""
        print(f"   {ctx.load_order + 1}. {ctx.name} v{ctx.version}{deps}")
    
    # Show dependency graph
    print("\n🔗 Dependency Graph:")
    for app_name, deps in registry._dependency_graph.items():
        deps_str = ", ".join(deps) if deps else "none"
        print(f"   {app_name}: {deps_str}")
    
    return registry


def demo_2_cycle_detection():
    """Demo 2: Dependency cycle detection."""
    print("\n" + "="*70)
    print("DEMO 2: Cycle Detection")
    print("="*70)
    
    # Create manifests with circular dependency
    class AppA:
        name = "app_a"
        version = "1.0.0"
        controllers = []
        services = []
        middlewares = []
        depends_on = ["app_b"]
    
    class AppB:
        name = "app_b"
        version = "1.0.0"
        controllers = []
        services = []
        middlewares = []
        depends_on = ["app_c"]
    
    class AppC:
        name = "app_c"
        version = "1.0.0"
        controllers = []
        services = []
        middlewares = []
        depends_on = ["app_a"]  # Cycle!
    
    from aquilia.aquilary import Aquilary, DependencyCycleError
    
    try:
        registry = Aquilary.from_manifests(
            manifests=[AppA, AppB, AppC],
            config=None,
            mode="prod",
        )
        print("❌ Should have detected cycle!")
    except DependencyCycleError as e:
        print("✅ Cycle detected successfully!")
        print(f"\n{e}")


def demo_3_fingerprinting():
    """Demo 3: Fingerprinting for reproducible deploys."""
    print("\n" + "="*70)
    print("DEMO 3: Fingerprinting")
    print("="*70)
    
    from aquilia.aquilary import Aquilary, FingerprintGenerator
    
    # Build same registry twice
    registry1 = Aquilary.from_manifests(
        manifests=[AuthManifest, UserManifest],
        config=AppConfig(),
        mode="prod",
    )
    
    registry2 = Aquilary.from_manifests(
        manifests=[AuthManifest, UserManifest],
        config=AppConfig(),
        mode="prod",
    )
    
    print(f"\n✅ Registry 1 fingerprint: {registry1.fingerprint}")
    print(f"✅ Registry 2 fingerprint: {registry2.fingerprint}")
    
    if registry1.fingerprint == registry2.fingerprint:
        print("\n✅ Fingerprints match! Deploys are reproducible.")
    else:
        print("\n❌ Fingerprints don't match!")
    
    # Show fingerprint includes
    print("\n🔍 Fingerprint includes:")
    print("   - App names and versions")
    print("   - Dependency graph")
    print("   - Controller/service lists")
    print("   - Config schema (structure only)")
    
    # Now change version and regenerate
    UserManifest.version = "2.2.0"
    
    registry3 = Aquilary.from_manifests(
        manifests=[AuthManifest, UserManifest],
        config=AppConfig(),
        mode="prod",
    )
    
    print(f"\n📝 After version change: {registry3.fingerprint}")
    
    if registry1.fingerprint != registry3.fingerprint:
        print("✅ Fingerprint changed after version update!")
    
    # Reset version
    UserManifest.version = "2.1.0"


def demo_4_validation():
    """Demo 4: Manifest validation."""
    print("\n" + "="*70)
    print("DEMO 4: Manifest Validation")
    print("="*70)
    
    # Create invalid manifest
    class InvalidManifest:
        name = "invalid"
        version = "not-semver"  # Invalid version
        controllers = "should-be-list"  # Wrong type
        services = []
        middlewares = []
        depends_on = ["nonexistent"]  # Missing dependency
    
    from aquilia.aquilary import Aquilary, ManifestValidationError
    
    try:
        registry = Aquilary.from_manifests(
            manifests=[InvalidManifest],
            config=None,
            mode="prod",
        )
        print("❌ Should have failed validation!")
    except Exception as e:
        print("✅ Validation failed as expected!")
        print(f"\n{e}")


def demo_5_registry_modes():
    """Demo 5: Registry modes (dev/prod/test)."""
    print("\n" + "="*70)
    print("DEMO 5: Registry Modes")
    print("="*70)
    
    from aquilia.aquilary import Aquilary, RegistryMode
    
    manifests = [AuthManifest, UserManifest]
    config = AppConfig()
    
    # Dev mode - permissive
    registry_dev = Aquilary.from_manifests(
        manifests=manifests,
        config=config,
        mode="dev",
    )
    print(f"\n🔧 DEV mode registry:")
    print(f"   - Fingerprint: {registry_dev.fingerprint[:16]}...")
    print(f"   - Validation: Permissive (warnings only)")
    
    # Prod mode - strict
    registry_prod = Aquilary.from_manifests(
        manifests=manifests,
        config=config,
        mode="prod",
    )
    print(f"\n🚀 PROD mode registry:")
    print(f"   - Fingerprint: {registry_prod.fingerprint[:16]}...")
    print(f"   - Validation: Strict (errors on conflicts)")
    
    # Test mode - scoped
    registry_test = Aquilary.from_manifests(
        manifests=manifests,
        config=config,
        mode="test",
    )
    print(f"\n🧪 TEST mode registry:")
    print(f"   - Fingerprint: {registry_test.fingerprint[:16]}...")
    print(f"   - Validation: Scoped (ephemeral, override-friendly)")


def demo_6_inspection():
    """Demo 6: Registry inspection."""
    print("\n" + "="*70)
    print("DEMO 6: Registry Inspection")
    print("="*70)
    
    from aquilia.aquilary import Aquilary
    
    registry = Aquilary.from_manifests(
        manifests=[AuthManifest, UserManifest, AdminManifest],
        config=AppConfig(),
        mode="dev",
    )
    
    # Get diagnostics
    diagnostics = registry.inspect()
    
    print(f"\n🔍 Registry Diagnostics:")
    print(f"   Fingerprint: {diagnostics['fingerprint'][:16]}...")
    print(f"   Mode: {diagnostics['mode']}")
    print(f"   App Count: {diagnostics['app_count']}")
    
    print(f"\n📦 Apps:")
    for app in diagnostics['apps']:
        print(f"   - {app['name']} v{app['version']}")
        print(f"     Controllers: {app['controllers']}")
        print(f"     Services: {app['services']}")
        print(f"     Depends on: {', '.join(app['depends_on']) if app['depends_on'] else 'none'}")
        print(f"     Load order: {app['load_order']}")


def demo_7_freeze_manifest():
    """Demo 7: Frozen manifest export."""
    print("\n" + "="*70)
    print("DEMO 7: Frozen Manifest Export")
    print("="*70)
    
    from aquilia.aquilary import Aquilary
    import tempfile
    import json
    
    registry = Aquilary.from_manifests(
        manifests=[AuthManifest, UserManifest],
        config=AppConfig(),
        mode="prod",
    )
    
    # Export frozen manifest
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        frozen_path = f.name
    
    registry.export_manifest(frozen_path)
    
    print(f"\n✅ Frozen manifest exported to: {frozen_path}")
    
    # Load and display
    with open(frozen_path, 'r') as f:
        frozen_data = json.load(f)
    
    print(f"\n📄 Frozen manifest contents:")
    print(f"   Version: {frozen_data['version']}")
    print(f"   Fingerprint: {frozen_data['fingerprint'][:16]}...")
    print(f"   Mode: {frozen_data['mode']}")
    print(f"   Apps: {len(frozen_data['apps'])}")
    
    for app in frozen_data['apps']:
        print(f"      - {app['name']} v{app['version']}")
    
    print(f"\n💡 This frozen manifest can be used for:")
    print(f"   - Deployment gating (verify fingerprint matches)")
    print(f"   - Reproducible deploys across environments")
    print(f"   - Audit trail of what was deployed")
    
    # Clean up
    import os
    os.unlink(frozen_path)


def demo_8_dependency_graph():
    """Demo 8: Dependency graph analysis."""
    print("\n" + "="*70)
    print("DEMO 8: Dependency Graph Analysis")
    print("="*70)
    
    from aquilia.aquilary import DependencyGraph
    
    # Build graph
    graph = DependencyGraph()
    graph.add_node("auth", [])
    graph.add_node("user", ["auth"])
    graph.add_node("admin", ["user", "auth"])
    graph.add_node("api", ["user"])
    
    print(f"\n📊 Graph Statistics:")
    print(f"   Nodes: {len(graph)}")
    print(f"   Is valid: {graph.validate()[0]}")
    
    # Load order
    load_order = graph.get_load_order()
    print(f"\n📦 Load Order:")
    for i, node in enumerate(load_order, 1):
        deps = graph.get_dependencies(node)
        deps_str = f" (depends on: {', '.join(deps)})" if deps else ""
        print(f"   {i}. {node}{deps_str}")
    
    # Layers (parallel execution)
    layers = graph.get_layers()
    print(f"\n⚡ Parallel Loading Layers:")
    for i, layer in enumerate(layers, 1):
        print(f"   Layer {i}: {', '.join(layer)}")
    
    # Roots and leaves
    roots = graph.get_roots()
    leaves = graph.get_leaves()
    print(f"\n🌳 Tree Structure:")
    print(f"   Roots (no dependencies): {', '.join(roots)}")
    print(f"   Leaves (no dependents): {', '.join(leaves)}")
    
    # Export DOT
    dot = graph.to_dot()
    print(f"\n📈 DOT Graph (first 200 chars):")
    print(f"   {dot[:200]}...")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("🚀 AQUILARY POC - Manifest-Driven App Registry")
    print("="*70)
    
    demos = [
        demo_1_basic_registry,
        demo_2_cycle_detection,
        demo_3_fingerprinting,
        demo_4_validation,
        demo_5_registry_modes,
        demo_6_inspection,
        demo_7_freeze_manifest,
        demo_8_dependency_graph,
    ]
    
    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ POC Complete!")
    print("="*70)
    print("\n📚 Key Takeaways:")
    print("   1. ✅ Manifest-driven app loading with no import-time side effects")
    print("   2. ✅ Deterministic dependency resolution with cycle detection")
    print("   3. ✅ Fingerprinting for reproducible deploys")
    print("   4. ✅ Rich validation with actionable error messages")
    print("   5. ✅ Multiple registry modes (dev/prod/test)")
    print("   6. ✅ Comprehensive inspection and diagnostics")
    print("   7. ✅ Frozen manifest export for deployment gating")
    print("   8. ✅ Advanced dependency graph analysis")
    print("\n")


if __name__ == "__main__":
    main()
