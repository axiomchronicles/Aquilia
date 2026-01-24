# Aquilary Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Manifest Structure](#manifest-structure)
5. [Dependency Resolution](#dependency-resolution)
6. [Fingerprinting](#fingerprinting)
7. [Registry Modes](#registry-modes)
8. [CLI Commands](#cli-commands)
9. [API Reference](#api-reference)
10. [Best Practices](#best-practices)
11. [Migration Guide](#migration-guide)
12. [Troubleshooting](#troubleshooting)

---

## Introduction

**Aquilary** is a production-grade, manifest-driven app registry system for Aquilia that provides:

- **Safe Loading**: No import-time side effects
- **Deterministic**: Reproducible builds with fingerprinting
- **Validated**: Compile-time validation with rich error messages
- **Dependency-Aware**: Automatic dependency resolution with cycle detection
- **Multi-Mode**: Dev, prod, and test modes for different environments

### Why Aquilary?

Traditional app loading in web frameworks suffers from:

1. **Import-time side effects**: Code runs unexpectedly during imports
2. **Manual dependency management**: Easy to introduce circular dependencies
3. **Runtime failures**: Errors only caught when code executes
4. **Non-reproducible**: Hard to ensure same state across deploys
5. **Poor diagnostics**: Unclear error messages

Aquilary solves these problems with a **two-phase architecture**:

1. **Static Phase**: Load manifests, validate structure, resolve dependencies
2. **Runtime Phase**: Lazy import controllers, compile routes, start services

---

## Quick Start

### Installation

Aquilary is included with Aquilia v0.2.0+:

```bash
pip install aquilia>=0.2.0
```

### Basic Example

**1. Define a manifest:**

```python
# apps/auth/manifest.py
class AuthManifest:
    name = "auth"
    version = "1.0.0"
    
    controllers = [
        "myapp.auth.controllers.AuthController",
    ]
    
    services = [
        "myapp.auth.services.AuthService",
    ]
    
    depends_on = []  # No dependencies
```

**2. Build registry:**

```python
from aquilia.aquilary import Aquilary
from config import Config

registry = Aquilary.from_manifests(
    manifests=["apps/auth/manifest.py"],
    config=Config(),
    mode="dev",
)

print(f"✅ Registry built: {registry.fingerprint[:16]}...")
```

**3. Use CLI:**

```bash
# Validate manifests
aquilary validate apps/*/manifest.py --config config.py

# Inspect registry
aquilary inspect --manifests apps/*/manifest.py

# Freeze for deploy
aquilary freeze --manifests apps/*/manifest.py --output frozen.json
```

---

## Core Concepts

### 1. Manifests

Manifests are declarative app descriptors that define:

- App identity (name, version)
- Components (controllers, services, middlewares)
- Dependencies (other apps)
- Lifecycle hooks (startup, shutdown)

**No import-time side effects**: Manifests are pure data structures.

### 2. Registry

The registry orchestrates app loading:

1. **Load** manifests from files/classes
2. **Validate** structure and dependencies
3. **Resolve** load order via topological sort
4. **Generate** fingerprint for deployment
5. **Build** runtime with DI containers

### 3. Dependency Graph

Apps can depend on other apps:

```python
class UserManifest:
    depends_on = ["auth"]  # User depends on auth
```

Aquilary:
- Detects circular dependencies with **Tarjan's algorithm**
- Computes optimal load order
- Identifies parallel loading opportunities

### 4. Fingerprinting

Each registry has a **deterministic fingerprint**:

```python
registry.fingerprint
# => "ce5a052661166441a3fa8cb4556737759644647e..."
```

Fingerprints ensure:
- **Reproducible deploys**: Same manifest = same fingerprint
- **Deployment gating**: Verify production matches staging
- **Audit trail**: Track what was deployed when

### 5. Modes

Three registry modes for different environments:

| Mode | Use Case | Validation | Hot Reload |
|------|----------|------------|------------|
| **dev** | Development | Permissive (warnings) | ✅ Planned |
| **prod** | Production | Strict (errors) | ❌ No |
| **test** | Testing | Scoped | ✅ Yes |

---

## Manifest Structure

### Full Manifest Example

```python
class ExampleManifest:
    """Example app manifest with all fields."""
    
    # Required fields
    name = "example"           # Unique app name
    version = "1.0.0"          # Semver version
    
    # Optional: Controllers (routes)
    controllers = [
        "myapp.example.controllers.ExampleController",
        "myapp.example.controllers.AdminController",
    ]
    
    # Optional: Services (DI registrations)
    services = [
        "myapp.example.services.ExampleService",
        "myapp.example.services.ExampleRepository",
    ]
    
    # Optional: Middlewares (request processing)
    middlewares = [
        ("myapp.example.middleware.AuthMiddleware", {"strict": True}),
        ("myapp.example.middleware.LogMiddleware", {}),
    ]
    
    # Optional: Dependencies (other apps)
    depends_on = ["auth", "user"]
    
    # Optional: Startup hook
    @staticmethod
    def on_startup():
        """Run when app starts."""
        print("Example app starting...")
        # Initialize resources, connect to DB, etc.
    
    # Optional: Shutdown hook
    @staticmethod
    def on_shutdown():
        """Run when app shuts down."""
        print("Example app shutting down...")
        # Clean up resources, close connections, etc.
```

### Field Reference

#### name (required)

**Type**: `str`  
**Description**: Unique identifier for the app  
**Rules**:
- Must be unique across all manifests
- Use lowercase with underscores (e.g., `auth`, `user_management`)
- Cannot start with underscore

```python
name = "user_management"
```

#### version (required)

**Type**: `str`  
**Description**: Semantic version  
**Rules**:
- Must follow semver format: `MAJOR.MINOR.PATCH`
- Used in fingerprint generation
- Shown in diagnostics

```python
version = "2.1.0"
```

#### controllers (optional)

**Type**: `List[str]`  
**Description**: Controller import paths  
**Rules**:
- Must be valid Python import paths
- Controllers not imported until runtime
- Used for route registration

```python
controllers = [
    "myapp.auth.controllers.AuthController",
    "myapp.auth.controllers.SessionController",
]
```

#### services (optional)

**Type**: `List[str]`  
**Description**: Service import paths for DI  
**Rules**:
- Must be valid Python import paths
- Registered in app's DI container
- Lazy loaded on first use

```python
services = [
    "myapp.auth.services.AuthService",
    "myapp.auth.services.TokenService",
]
```

#### middlewares (optional)

**Type**: `List[Tuple[str, dict]]`  
**Description**: Middleware configurations  
**Rules**:
- Each tuple: `(import_path, kwargs)`
- Applied in order
- Kwargs passed to middleware constructor

```python
middlewares = [
    ("myapp.auth.middleware.AuthMiddleware", {"strict": True}),
    ("myapp.logging.middleware.LogMiddleware", {"level": "INFO"}),
]
```

#### depends_on (optional)

**Type**: `List[str]`  
**Description**: App dependencies  
**Rules**:
- Must reference existing apps
- Cycles detected and rejected
- Determines load order

```python
depends_on = ["auth", "user"]
```

#### on_startup / on_shutdown (optional)

**Type**: `Callable[[], None]`  
**Description**: Lifecycle hooks  
**Rules**:
- Must be static methods or functions
- Called in load order (startup) / reverse (shutdown)
- Should be idempotent

```python
@staticmethod
def on_startup():
    """Initialize resources."""
    init_db_pool()
    load_cache()

@staticmethod
def on_shutdown():
    """Clean up resources."""
    close_db_pool()
    clear_cache()
```

### DSL Manifests (YAML)

Manifests can also be defined in YAML:

```yaml
# apps/auth/manifest.yaml
name: auth
version: 1.0.0

controllers:
  - myapp.auth.controllers.AuthController
  - myapp.auth.controllers.SessionController

services:
  - myapp.auth.services.AuthService
  - myapp.auth.services.TokenService

middlewares:
  - path: myapp.auth.middleware.AuthMiddleware
    kwargs:
      strict: true

depends_on:
  - base
```

Load with:

```python
registry = Aquilary.from_manifests(
    manifests=["apps/auth/manifest.yaml"],
    config=Config(),
    mode="dev",
)
```

---

## Dependency Resolution

### How It Works

Aquilary uses **Tarjan's strongly connected components algorithm** to:

1. Detect circular dependencies
2. Compute topological sort
3. Determine load order

**Time Complexity**: O(V + E) where V = apps, E = dependencies

### Example

```python
class AuthManifest:
    name = "auth"
    depends_on = []

class UserManifest:
    name = "user"
    depends_on = ["auth"]

class AdminManifest:
    name = "admin"
    depends_on = ["user", "auth"]
```

**Load Order**: `auth → user → admin`

### Cycle Detection

```python
class AppA:
    name = "app_a"
    depends_on = ["app_b"]

class AppB:
    name = "app_b"
    depends_on = ["app_c"]

class AppC:
    name = "app_c"
    depends_on = ["app_a"]  # Cycle!
```

**Error**:
```
❌ DependencyCycleError: Circular dependency detected: 
   app_c → app_b → app_a → app_c

   💡 Suggestion: Break the cycle by removing one dependency or 
      introducing an intermediate abstraction.
```

### Parallel Loading

Aquilary computes **parallel loading layers**:

```python
graph = DependencyGraph()
graph.add_node("auth", [])
graph.add_node("user", ["auth"])
graph.add_node("api", ["user"])
graph.add_node("admin", ["user", "auth"])

layers = graph.get_layers()
# => [
#      ["auth"],           # Layer 1
#      ["user"],           # Layer 2
#      ["api", "admin"],   # Layer 3 (parallel!)
#    ]
```

Apps in the same layer can load simultaneously.

---

## Fingerprinting

### What Is a Fingerprint?

A **SHA-256 hash** of the canonical registry state:

```python
registry.fingerprint
# => "ce5a052661166441a3fa8cb4556737759644647effe38c21faace58ac5033290"
```

### What's Included?

✅ **Included**:
- App names and versions
- Dependency graph
- Controller/service lists
- Config schema (structure only)

❌ **Excluded**:
- Runtime state
- Timestamps (except generation time)
- Environment-specific paths
- Config values (only structure)

### Why Fingerprinting?

#### 1. Reproducible Deploys

```bash
# CI/CD: Generate frozen manifest
aquilary freeze --manifests apps/*/manifest.py --output frozen.json

# Production: Verify fingerprint
aquilary run --frozen frozen.json --config config.py
```

#### 2. Deployment Gating

```python
# Load staging registry
staging_registry = load_frozen("staging_frozen.json")

# Load production manifest
prod_registry = build_from_manifests(...)

# Verify match
if staging_registry.fingerprint != prod_registry.fingerprint:
    raise DeploymentError("Manifests don't match staging!")
```

#### 3. Audit Trail

```json
{
  "deploy_id": "20260124-001",
  "fingerprint": "ce5a052661166441...",
  "timestamp": "2026-01-24T10:30:00Z",
  "apps": ["auth", "user", "admin"]
}
```

### Determinism Guarantees

Fingerprints are deterministic across:
- ✅ Python versions (3.10+)
- ✅ Operating systems (Linux, macOS, Windows)
- ✅ File systems (ext4, APFS, NTFS)
- ✅ Time zones

### Sensitivity

Fingerprints change when:
- ✅ App version changes
- ✅ Dependencies added/removed
- ✅ Controllers/services modified
- ❌ Config **values** change (only structure matters)
- ❌ Comments or whitespace

---

## Registry Modes

### DEV Mode

**Use**: Local development

```python
registry = Aquilary.from_manifests(
    manifests=[...],
    config=Config(),
    mode="dev",
)
```

**Features**:
- ⚠️ Warnings instead of errors
- 🔥 Hot-reload enabled (planned)
- 🔍 Verbose diagnostics
- 🚫 Route conflicts allowed

**Best For**:
- Rapid iteration
- Experimenting with dependencies
- Testing new features

### PROD Mode

**Use**: Production deployments

```python
registry = Aquilary.from_manifests(
    manifests=[...],
    config=Config(),
    mode="prod",
)
```

**Features**:
- ❌ Strict validation (errors on issues)
- 🔒 Immutable after build
- ✅ Route conflicts rejected
- 🧊 Frozen manifest support

**Best For**:
- Production deploys
- Staging environments
- CI/CD pipelines

### TEST Mode

**Use**: Unit/integration tests

```python
registry = Aquilary.from_manifests(
    manifests=[...],
    config=TestConfig(),
    mode="test",
)
```

**Features**:
- 🔄 Scoped (ephemeral)
- ⚡ Override-friendly
- 🧪 Mock support
- 🚀 Fast teardown

**Best For**:
- Unit tests
- Integration tests
- E2E tests

---

## CLI Commands

### validate

Validate manifests and dependencies.

```bash
aquilary validate apps/*/manifest.py --config config.py --mode prod
```

**Options**:
- `manifests`: Manifest files or directories (positional)
- `--config PATH`: Config file path
- `--mode {dev,prod,test}`: Registry mode (default: prod)
- `--autodiscover`: Auto-discover manifests in `apps/`

**Output**:
```
🔍 Validating manifests in mode: prod
   Manifests: apps/auth/manifest.py, apps/user/manifest.py

✅ Validation passed!
   Apps: 2
   Fingerprint: ce5a052661166441...

📦 Load Order:
   1. auth v1.0.0
   2. user v2.1.0 (→ auth)
```

### inspect

Inspect registry diagnostics.

```bash
aquilary inspect --manifests apps/*/manifest.py --json diagnostics.json
```

**Options**:
- `--manifests PATH [PATH...]`: Manifest files
- `--config PATH`: Config file path
- `--mode {dev,prod,test}`: Registry mode (default: dev)
- `--autodiscover`: Auto-discover manifests
- `--json PATH`: Export diagnostics to JSON

**Output**:
```
======================================================================
Registry Diagnostics
======================================================================

📊 Summary:
   Fingerprint: ce5a052661166441a3fa8cb4556737759644647e...
   Mode: dev
   App Count: 3

📦 Applications:
   auth v1.0.0
      Load Order: 0
      Controllers: 2
      Services: 2
      Dependencies: none

   user v2.1.0
      Load Order: 1
      Controllers: 2
      Services: 2
      Dependencies: auth

🔗 Dependency Graph:
   auth: none
   user: auth
```

### freeze

Freeze manifest for deployment.

```bash
aquilary freeze --manifests apps/*/manifest.py --output frozen.json
```

**Options**:
- `--manifests PATH [PATH...]`: Manifest files
- `--config PATH`: Config file path
- `--output PATH`: Output file (default: frozen_manifest.json)
- `--autodiscover`: Auto-discover manifests

**Output**:
```
🧊 Freezing manifest...

✅ Frozen manifest exported!
   Path: frozen.json
   Fingerprint: ce5a052661166441a3fa8cb4556737759644647e...
   Apps: 2

📋 Apps included:
   - auth v1.0.0
   - user v2.1.0

💡 Usage in production:
   1. Commit frozen.json to version control
   2. Deploy with: aquilary run --frozen frozen.json
   3. Verify fingerprint matches
```

### graph

Visualize dependency graph.

```bash
aquilary graph --manifests apps/*/manifest.py --output graph.dot
```

**Options**:
- `--manifests PATH [PATH...]`: Manifest files
- `--config PATH`: Config file path
- `--mode {dev,prod,test}`: Registry mode
- `--output PATH`: Output DOT file

**Output**:
```
📊 Generating dependency graph...

✅ Graph exported to: graph.dot

💡 Visualize with:
   dot -Tpng graph.dot -o graph.png
   Or view at: https://dreampuf.github.io/GraphvizOnline/

⚡ Parallel Loading Layers:
   Layer 1: auth
   Layer 2: user
   Layer 3: api, admin
```

### run

Run application with registry.

```bash
aquilary run --frozen frozen.json --config config.py
```

**Options**:
- `--frozen PATH`: Frozen manifest file
- `--manifests PATH [PATH...]`: Manifest files (if not frozen)
- `--config PATH`: Config file (required)
- `--mode {dev,prod,test}`: Registry mode (default: prod)
- `--autodiscover`: Auto-discover manifests

**Output**:
```
🚀 Starting application...
   Loading from frozen manifest: frozen.json

✅ Registry loaded:
   Fingerprint: ce5a052661166441a3fa8cb4556737759644647e...
   Apps: 2

🔨 Building runtime...
   Compiling routes...

✅ Runtime ready!

📦 Startup sequence:
   1. Starting auth...
   🔐 Auth app starting...
   2. Starting user...
   👤 User app starting...
```

---

## API Reference

### Aquilary

Main entry point for building registries.

```python
from aquilia.aquilary import Aquilary

registry = Aquilary.from_manifests(
    manifests: List[Type | str],
    config: Any,
    mode: Literal["dev", "prod", "test"] = "prod",
    *,
    allow_fs_autodiscovery: bool = False,
    freeze_manifest_path: Optional[str] = None,
) -> AquilaryRegistry
```

**Parameters**:
- `manifests`: List of manifest classes, file paths, or directories
- `config`: Configuration object
- `mode`: Registry mode (`"dev"`, `"prod"`, or `"test"`)
- `allow_fs_autodiscovery`: If True, scan `apps/` for manifests
- `freeze_manifest_path`: Load from frozen manifest file

**Returns**: `AquilaryRegistry` instance

**Raises**:
- `DependencyCycleError`: Circular dependencies detected
- `ManifestValidationError`: Invalid manifest structure
- `ConfigValidationError`: Config validation failed

### AquilaryRegistry

Validated registry metadata.

```python
class AquilaryRegistry:
    fingerprint: str
    app_contexts: List[AppContext]
    mode: RegistryMode
    
    def build_runtime(self) -> RuntimeRegistry:
        """Build runtime registry."""
    
    def inspect(self) -> Dict[str, Any]:
        """Get diagnostics."""
    
    def export_manifest(self, path: str) -> None:
        """Export frozen manifest."""
```

### DependencyGraph

Dependency graph with cycle detection.

```python
from aquilia.aquilary import DependencyGraph

graph = DependencyGraph()
graph.add_node(name: str, dependencies: List[str])

# Analysis
load_order = graph.topological_sort() -> List[str]
cycle = graph.find_cycle() -> Optional[List[str]]
layers = graph.get_layers() -> List[List[str]]
dot = graph.to_dot() -> str
```

### FingerprintGenerator

Generate deterministic fingerprints.

```python
from aquilia.aquilary import FingerprintGenerator

gen = FingerprintGenerator()
fingerprint = gen.generate(
    app_contexts: List[AppContext],
    config: Any,
    mode: RegistryMode,
) -> str

is_valid = gen.verify_fingerprint(
    expected: str,
    app_contexts: List[AppContext],
    config: Any,
    mode: RegistryMode,
) -> bool
```

---

## Best Practices

### 1. Manifest Organization

**Good**:
```
apps/
  auth/
    __init__.py
    manifest.py       # ✅ One manifest per app
    controllers.py
    services.py
  user/
    __init__.py
    manifest.py       # ✅ Clear structure
    controllers.py
    services.py
```

**Bad**:
```
manifests/
  all_manifests.py  # ❌ All manifests in one file
```

### 2. Dependency Management

**Good**:
```python
class UserManifest:
    depends_on = ["auth"]  # ✅ Explicit, minimal
```

**Bad**:
```python
class UserManifest:
    depends_on = ["auth", "logging", "metrics", "email"]  # ❌ Too many
```

**Tip**: Keep dependencies minimal. Use events for loose coupling.

### 3. Versioning

**Good**:
```python
version = "2.1.0"  # ✅ Semver
```

**Bad**:
```python
version = "v2"  # ❌ Not semver
```

**Tip**: Follow semantic versioning strictly.

### 4. Controllers

**Good**:
```python
controllers = [
    "myapp.auth.controllers.AuthController",  # ✅ Full paths
]
```

**Bad**:
```python
controllers = [
    "AuthController",  # ❌ Ambiguous
]
```

**Tip**: Always use absolute import paths.

### 5. Frozen Manifests

**Good**:
```bash
# CI/CD
aquilary freeze --manifests apps/*/manifest.py --output deploy/frozen.json
git add deploy/frozen.json
git commit -m "Update frozen manifest"

# Production
aquilary run --frozen deploy/frozen.json --config config.py
```

**Tip**: Always deploy with frozen manifests in production.

---

## Migration Guide

### From Legacy Registry

#### Before (Legacy):

```python
from aquilia import Registry

registry = Registry()
registry.register_app("auth", AuthApp())
registry.register_app("user", UserApp())
registry.load_all()
```

#### After (Aquilary):

```python
from aquilia.aquilary import Aquilary

# 1. Define manifests
class AuthManifest:
    name = "auth"
    version = "1.0.0"
    controllers = ["myapp.auth.controllers.AuthController"]

class UserManifest:
    name = "user"
    version = "1.0.0"
    controllers = ["myapp.user.controllers.UserController"]
    depends_on = ["auth"]

# 2. Build registry
registry = Aquilary.from_manifests(
    manifests=[AuthManifest, UserManifest],
    config=Config(),
    mode="prod",
)

# 3. Build runtime
runtime = registry.build_runtime()
```

### Migration Steps

1. **Create manifests** for each app
2. **Define dependencies** explicitly
3. **Update config** to namespace by app
4. **Test locally** in dev mode
5. **Freeze manifest** for staging
6. **Deploy** with frozen manifest

---

## Troubleshooting

### Circular Dependency Error

**Error**:
```
❌ DependencyCycleError: Circular dependency detected: 
   app_a → app_b → app_c → app_a
```

**Solution**:
1. Identify the cycle in dependency graph
2. Break cycle by removing one dependency
3. Use events for loose coupling if needed

```python
# Before (cycle)
class AppA:
    depends_on = ["app_b"]

class AppB:
    depends_on = ["app_c"]

class AppC:
    depends_on = ["app_a"]  # Cycle!

# After (fixed)
class AppA:
    depends_on = []  # Removed dependency

class AppB:
    depends_on = ["app_a"]

class AppC:
    depends_on = ["app_b"]
```

### Manifest Validation Error

**Error**:
```
❌ ManifestValidationError: Field 'controllers' must be a list
```

**Solution**: Fix manifest structure

```python
# Before (wrong)
class Manifest:
    controllers = "myapp.controllers.Controller"  # ❌ String

# After (correct)
class Manifest:
    controllers = ["myapp.controllers.Controller"]  # ✅ List
```

### Fingerprint Mismatch

**Error**:
```
❌ FrozenManifestMismatchError: Fingerprint mismatch!
   Expected: ce5a052661166441...
   Actual:   94b183a5d203ae9d...
```

**Solution**:
1. Check if manifests changed
2. Regenerate frozen manifest
3. Or revert code to match frozen manifest

```bash
# Regenerate
aquilary freeze --manifests apps/*/manifest.py --output frozen.json

# Or compare
aquilary inspect --manifests apps/*/manifest.py --json current.json
diff current.json frozen.json
```

### Import Errors

**Error**:
```
ImportError: cannot import name 'AuthController'
```

**Solution**: Check import paths are correct

```python
# Verify path exists
from myapp.auth.controllers import AuthController  # Test import

# Update manifest
class AuthManifest:
    controllers = [
        "myapp.auth.controllers.AuthController",  # ✅ Full path
    ]
```

---

**Aquilary v1.0.0** | Production-Ready Manifest-Driven Registry
