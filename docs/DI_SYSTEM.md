# Aquilia Dependency Injection System

## Overview

Production-grade, async-first Dependency Injection system for Aquilia framework with manifest awareness, multi-tenant safety, and comprehensive observability.

**Version:** 1.0.0  
**Status:** Production Ready (Core Features Complete)

## Key Features

✅ **Explicit Scopes:** singleton, app, request, transient, pooled, ephemeral  
✅ **Manifest-Aware:** Load services from declarative manifests  
✅ **Async-First:** Full async/await support with lifecycle hooks  
✅ **Low-Overhead:** <3µs cached lookups (target)  
✅ **Cycle Detection:** Tarjan's algorithm with safe lazy resolution  
✅ **Developer Ergonomics:** Decorators, Annotated injection, CLI tools  
✅ **Testability:** Mock providers, override context managers  
✅ **Diagnostics:** Rich error messages with file/line information  

## Architecture

```
aquilia/di/
├── __init__.py           # Public API exports
├── core.py               # Container, Registry, Provider protocol
├── providers.py          # Provider implementations
├── scopes.py             # Scope definitions and validation
├── decorators.py         # @service, @factory, @inject
├── lifecycle.py          # Lifecycle hooks and disposal
├── graph.py              # Dependency graph and cycle detection
├── errors.py             # Rich error types
├── testing.py            # Test utilities and fixtures
├── compat.py             # Legacy compatibility layer
└── cli.py                # CLI commands
```

## Quick Start

### 1. Define Services

```python
from aquilia.di import service, factory, inject, Inject
from typing import Annotated

# Configuration
@dataclass
class DatabaseConfig:
    url: str = "postgresql://localhost/mydb"
    pool_size: int = 10

# Repository (app-scoped - singleton)
@service(scope="app", tag="primary")
class UserRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_user(self, user_id: int) -> User:
        return await self.db.query("SELECT * FROM users WHERE id=$1", user_id)

# Service with dependency injection
@service(scope="app")
class AuthService:
    def __init__(
        self,
        repo: Annotated[UserRepository, Inject(tag="primary")],
        config: DatabaseConfig,
    ):
        self.repo = repo
        self.config = config
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        user = await self.repo.get_by_username(username)
        # Verify password...
        return user
```

### 2. Register in Manifest

```python
from aquilia import AppManifest

class UsersApp(AppManifest):
    name = "users"
    version = "1.0.0"
    
    services = [
        ("myapp.config:DatabaseConfig", {"scope": "singleton"}),
        ("myapp.repos:UserRepository", {"scope": "app", "tag": "primary"}),
        ("myapp.services:AuthService", {"scope": "app"}),
    ]
```

### 3. Build Container

```python
from aquilia.di import Registry

# Build registry from manifests
manifests = [UsersApp()]
registry = Registry.from_manifests(manifests, config=config)

# Build app container
app_container = registry.build_container()

# Resolve services
auth_service = await app_container.resolve_async(AuthService)
```

### 4. Request-Scoped Usage

```python
# In request handler
async def handle_request(request: Request):
    # Create request-scoped container
    request_container = app_container.create_request_scope()
    
    # Resolve services (reuses app-scoped singletons)
    auth = await request_container.resolve_async(AuthService)
    
    # Use service
    user = await auth.authenticate(username, password)
    
    # Cleanup
    await request_container.shutdown()
```

## Scopes

### Singleton / App
- **Lifetime:** Application lifetime
- **Cache:** Yes
- **Use Case:** Configuration, long-lived services, repositories
- **Example:** Database pools, caching layers, auth services

```python
@service(scope="app")
class ConfigService:
    pass
```

### Request
- **Lifetime:** HTTP request
- **Cache:** Yes (within request)
- **Use Case:** Request-specific context, loggers, transactions
- **Example:** Request ID, user context, DB transactions

```python
@service(scope="request")
class RequestLogger:
    def __init__(self, request_id: str):
        self.request_id = request_id
```

### Transient
- **Lifetime:** No caching
- **Cache:** No
- **Use Case:** Stateless operations, value objects
- **Example:** Validators, formatters, calculators

```python
@service(scope="transient")
class Validator:
    pass
```

### Pooled
- **Lifetime:** Managed pool
- **Cache:** No (pooled)
- **Use Case:** Expensive resources with limited capacity
- **Example:** Database connections, HTTP clients

```python
@factory(scope="pooled", name="db_pool")
async def create_db_connection() -> DatabaseConnection:
    conn = DatabaseConnection(url)
    await conn.connect()
    return conn
```

### Ephemeral
- **Lifetime:** Very short (sub-request)
- **Cache:** Yes (within scope)
- **Use Case:** Temporary contexts, batch operations
- **Example:** Batch processors, temporary caches

## Providers

### ClassProvider
Instantiates classes by resolving constructor dependencies.

```python
from aquilia.di import ClassProvider

provider = ClassProvider(
    cls=UserService,
    scope="app",
    tags=("primary",),
)
```

**Features:**
- Automatic dependency resolution from `__init__` signature
- Supports `async_init()` convention for async initialization
- Type hint inspection for dependency tokens

### FactoryProvider
Calls factory functions to produce instances.

```python
from aquilia.di import FactoryProvider

@factory(scope="singleton")
async def create_database_pool(config: Config) -> DatabasePool:
    return await DatabasePool.connect(config.db_url)
```

**Features:**
- Supports sync and async factories
- Dependency injection for factory parameters
- Return type inference

### ValueProvider
Returns pre-bound constant values.

```python
from aquilia.di import ValueProvider

config = DatabaseConfig(url="postgresql://localhost/mydb")
provider = ValueProvider(config, DatabaseConfig, name="db_config")
```

**Features:**
- No instantiation overhead
- Useful for configuration objects
- Always singleton scope

### PoolProvider
Manages pools of instances with acquire/release semantics.

```python
from aquilia.di import PoolProvider

pool_provider = PoolProvider(
    factory=create_db_connection,
    max_size=10,
    token=DatabaseConnection,
    strategy="FIFO",  # or "LIFO"
)

# Usage
conn = await pool_provider.instantiate(ctx)
# ... use connection ...
await pool_provider.release(conn)
```

**Features:**
- FIFO or LIFO pooling strategies
- Configurable pool size
- Automatic cleanup on shutdown

### LazyProxyProvider
Creates lazy proxies for breaking circular dependencies.

```python
from aquilia.di import LazyProxyProvider

# Only use when explicitly allowed in manifest
provider = LazyProxyProvider(
    token=ServiceA,
    target_token=ServiceB,
)
```

**Features:**
- Defers resolution until first access
- Breaks circular dependencies
- Transparent proxy with `__getattr__`

## Decorators

### @service
Mark a class as a DI service.

```python
@service(scope="app", tag="primary", name="user_service")
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
```

**Parameters:**
- `scope`: Service scope (default: "app")
- `tag`: Optional tag for disambiguation
- `name`: Optional explicit name

### @factory
Mark a function as a DI factory.

```python
@factory(scope="singleton", name="db_pool")
async def create_db_pool(config: Config) -> DatabasePool:
    return await DatabasePool.connect(config.db_url)
```

**Parameters:**
- `scope`: Factory scope (default: "app")
- `tag`: Optional tag
- `name`: Optional explicit name

### @inject / Inject
Specify injection metadata.

```python
from typing import Annotated

def __init__(
    self,
    repo: Annotated[UserRepository, Inject(tag="primary")],
    cache: Annotated[Cache, Inject(optional=True)],
):
    ...
```

**Parameters:**
- `tag`: Tag for disambiguation
- `optional`: If True, inject None if not found

## CLI Commands

### aq di-check
Validate DI configuration (static analysis).

```bash
aq di-check --settings project/settings.py
```

**Checks:**
- All providers resolvable
- No cycles (unless allow_lazy)
- No scope violations
- Cross-app dependencies declared

**Output:**
```
🔍 Checking DI configuration...
✅ DI configuration is valid!

📊 Summary:
  - Providers: 42
  - singleton: 12
  - app: 18
  - request: 8
  - transient: 4
```

### aq di-tree
Show dependency tree.

```bash
aq di-tree --settings project/settings.py --out tree.txt
```

**Output:**
```
🌳 Dependency Tree

├── AuthService (app)
│   ├── UserRepository (app)
│   │   └── Database (singleton)
│   └── AuthConfig (singleton)
├── NotificationService (app)
    └── EmailClient (pooled)
```

### aq di-graph
Export dependency graph as Graphviz DOT.

```bash
aq di-graph --settings project/settings.py --out graph.dot
dot -Tpng graph.dot -o graph.png
```

**Output:** Graph visualization with:
- Nodes colored by scope
- Edges showing dependencies
- Labels with provider names

### aq di-profile
Benchmark DI performance.

```bash
aq di-profile --settings project/settings.py --runs 1000
```

**Output:**
```
⚡ Profiling DI performance...

1️⃣  Registry build (cold):
   ⏱️  125.45ms

2️⃣  Container build:
   ⏱️  8.32ms

3️⃣  Cached resolution (1000 iterations):
   ⏱️  Average: 1.85µs
   ⏱️  Median:  1.72µs
   ⏱️  P95:     2.45µs
   ✅ Target <3µs: PASSED

📊 Summary:
  - Registry build: 125.45ms
  - Container build: 8.32ms
  - Providers: 42
```

### aq di-manifest
Generate `di_manifest.json` for LSP integration.

```bash
aq di-manifest --settings project/settings.py
```

**Output:** JSON file with provider metadata for IDE features:
- Hover information
- Autocomplete for `Inject` tags
- "Find provider" navigation

## Error Handling

### ProviderNotFoundError
No provider found for requested token.

```python
ProviderNotFoundError: No provider found for token=UserRepo
Requested by: apps.users.services:UserService.__init__
Location: apps/users/services.py:42

Candidates found:
  - apps.users.repos:SqlUserRepo (tag=repo)
  - apps.mocks:InMemoryUserRepo (tag=test)

Suggested fixes:
  - Register a provider for UserRepo
  - Add Inject(tag='repo') to disambiguate
```

### DependencyCycleError
Circular dependency detected.

```python
DependencyCycleError: Detected cycle:
  apps.users:UserService -> apps.auth:AuthService -> apps.users:UserService

Locations:
  - apps/users/services.py:42 (UserService.__init__)
  - apps/auth/services.py:18 (AuthService.__init__)

Suggested fixes:
  - Break cycle by using LazyProxy: manifest entry allow_lazy=True
  - Extract interface to decouple directionally
  - Restructure dependencies to remove cycle
```

### ScopeViolationError
Scope violation (request-scoped injected into app-scoped).

```python
ScopeViolationError: Request-scoped provider 'RequestCache' injected into 
app-scoped 'AppCache'. Scope rules forbid this.

Suggested fixes:
  - Change 'AppCache' to request scope
  - Change 'RequestCache' to app scope
  - Use factory/provider pattern to defer instantiation
```

## Testing

### Mock Providers

```python
from aquilia.di.testing import MockProvider, override_container

# Create mock
mock_repo = MockUserRepository()
mock_provider = MockProvider(mock_repo, UserRepository)

# Override in tests
async with override_container(container, UserRepository, mock_repo):
    # Tests run with mock
    result = await auth_service.authenticate("alice", "password")
    assert result is not None
```

### Test Registry

```python
from aquilia.di.testing import TestRegistry

# Build test registry with overrides
test_registry = TestRegistry.from_manifests(
    manifests=[UsersApp()],
    overrides={
        "UserRepository": MockProvider(MockRepo(), UserRepository),
    },
    enforce_cross_app=False,  # Relaxed for tests
)

container = test_registry.build_container()
```

### Pytest Fixtures

```python
import pytest
from aquilia.di.testing import di_container, request_container, mock_provider

@pytest.mark.asyncio
async def test_auth_service(di_container, mock_provider):
    # Register mock
    mock_repo = mock_provider(MockRepo(), UserRepository)
    di_container.register(mock_repo)
    
    # Resolve service
    auth = await di_container.resolve_async(AuthService)
    
    # Test
    result = await auth.authenticate("alice", "password")
    assert result is not None
```

## Performance

### Targets

- **Cached lookup:** <3µs (median)
- **New instance:** <100µs (with 3 dependencies)
- **Pool acquire:** <200µs
- **Registry build:** <1s (for 1000 providers)

### Optimizations

1. **`__slots__`** for provider metadata and cache entries
2. **Precomputed resolve plans** (no reflection per-resolve)
3. **Nested dict lookup** `{token: {tag: provider}}` for O(1)
4. **Small allocation strategy** for request containers
5. **Fast-path short-circuits** for pool operations

## Lifecycle Management

### Startup Hooks

```python
from aquilia.di import Lifecycle

lifecycle = Lifecycle()

lifecycle.on_startup(
    async def init_database():
        await db.connect()
    ,
    name="db_init",
    priority=10,  # Higher runs first
)

await lifecycle.run_startup_hooks()
```

### Shutdown Hooks

```python
lifecycle.on_shutdown(
    async def close_database():
        await db.close()
    ,
    name="db_close",
    priority=10,
)

await lifecycle.run_shutdown_hooks()
```

### Finalizers (LIFO)

```python
lifecycle.register_finalizer(lambda: db.close())
lifecycle.register_finalizer(lambda: cache.flush())

# Cleanup in reverse order
await lifecycle.run_finalizers()
```

## Best Practices

### ✅ DO

1. **Use explicit scopes** - Be intentional about service lifetimes
2. **Prefer app scope for services** - Reuse instances across requests
3. **Use request scope for context** - Request ID, user info, transactions
4. **Tag disambiguate** - Use tags when multiple providers for same type
5. **Type hint everything** - DI relies on type annotations
6. **Test with mocks** - Override providers in tests
7. **Monitor performance** - Use `aq di-profile` regularly

### ❌ DON'T

1. **Don't use singletons for per-tenant data** - Use request scope
2. **Don't create cycles without lazy proxies** - Restructure dependencies
3. **Don't violate scope rules** - Request can't inject into app
4. **Don't forget cleanup** - Always shutdown request containers
5. **Don't over-use transient** - Adds overhead with no caching
6. **Don't ignore diagnostics** - Fix errors reported by `aq di-check`

## Migration from Legacy DI

### Legacy Code

```python
from aquilia.di import DIContainer, ServiceScope

container = DIContainer()
container.register("db", create_db, ServiceScope.SINGLETON)
db = container.resolve("db")
```

### New Code

```python
from aquilia.di import Registry, service, inject

@service(scope="app")
class Database:
    pass

registry = Registry.from_manifests([manifest])
container = registry.build_container()
db = await container.resolve_async(Database)
```

### Compatibility Layer

```python
from aquilia.di.compat import RequestCtx

# Legacy API still works
ctx = RequestCtx.from_container(container)
db = await ctx.get_async(Database)
```

## Roadmap

### ✅ Completed (v1.0)
- Core container and registry
- All provider types
- Scope management
- Decorators and injection
- Cycle detection
- CLI tools
- Testing utilities
- Documentation

### 🚧 In Progress (v1.1)
- OpenTelemetry integration
- Prometheus metrics
- Comprehensive test suite
- Benchmark suite
- Property-based tests

### 📋 Planned (v1.2)
- LSP integration (hover, autocomplete)
- mypy plugin for static checking
- Migration tool from other DI frameworks
- Performance profiler UI
- Advanced pooling strategies

## Examples

See:
- `di_poc.py` - Proof of concept with all core features
- `examples/di_example.py` - Full integration with Aquilia
- `tests/di/` - Comprehensive test suite (TODO)

## Support

**Issues:** https://github.com/embrake/Aquilify/issues  
**Docs:** https://aquilia.dev/di  
**Discord:** https://discord.gg/aquilia

## License

MIT License - see LICENSE file
