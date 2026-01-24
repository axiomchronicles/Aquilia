# Architecture Overview

## High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                    Aquilia Server                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐    │
│  │ Registry │─────▶│  Router  │─────▶│  Engine  │    │
│  └────┬─────┘      └────┬─────┘      └────┬─────┘    │
│       │                 │                   │          │
│       ▼                 ▼                   ▼          │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐    │
│  │   Apps   │      │  Flows   │      │    DI    │    │
│  └──────────┘      └──────────┘      └──────────┘    │
│                                                         │
│       ▼                                  ▼             │
│  ┌──────────┐                      ┌──────────┐       │
│  │  Config  │                      │ Effects  │       │
│  └──────────┘                      └──────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
                       │
                       ▼
             ┌──────────────────┐
             │  ASGI Adapter    │
             └──────────────────┘
                       │
                       ▼
              HTTP / WebSocket
```

## Component Breakdown

### 1. AppManifest System

**Purpose:** Pure data declarations for applications.

**Key Features:**
- No import-time side effects
- Serializable for fingerprinting
- Validation at load time
- Lifecycle hooks (startup/shutdown)

**Data Flow:**
```
Manifest Class → ManifestLoader → Validation → Registry
```

### 2. Config System

**Purpose:** Layered typed configuration with merge precedence.

**Merge Precedence (high to low):**
1. Manual overrides
2. Environment variables (`AQ_*`)
3. .env file
4. Config files (*.py, *.json)
5. Defaults from Config classes

**Features:**
- Nested config with dot notation
- Type validation
- App-namespaced config
- Hot-reload support (dev mode)

### 3. Registry

**Purpose:** Central orchestrator for app loading and dependency management.

**Responsibilities:**
- Load manifests
- Build dependency graph
- Detect circular dependencies
- Topological sort for load order
- Register services in DI container
- Compute deployment fingerprint
- Execute lifecycle hooks

**Dependency Graph:**
```
App A
  │
  ├─▶ App B
  │     │
  │     └─▶ App C
  │
  └─▶ App C

Load Order: C → B → A
```

### 4. DI Container

**Purpose:** Scoped dependency injection with multiple lifetimes.

**Service Scopes:**
- **SINGLETON**: One instance per app (shared across requests)
- **REQUEST**: One instance per request (ephemeral, auto-cleanup)
- **TRANSIENT**: New instance every resolution

**Container Hierarchy:**
```
Global Container
  │
  ├─▶ App Container (users)
  │     │
  │     └─▶ Request Container (per request)
  │
  └─▶ App Container (auth)
        │
        └─▶ Request Container (per request)
```

**Resolution Algorithm:**
1. Check current scope cache
2. Check parent scope (for singletons)
3. Create new instance with dependency injection
4. Store in appropriate scope cache
5. Return instance

### 5. Flow System

**Purpose:** Typed directed pipelines for request handling.

**Flow Graph:**
```
Request
  │
  ▼
┌─────────────┐
│ Middleware  │ (priority ordered)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Guards    │ (boolean checks)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Transforms  │ (data preparation)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Handler   │ (main logic)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Post Hooks  │ (cleanup)
└──────┬──────┘
       │
       ▼
   Response
```

**Flow Compilation:**
```
@flow("/users/{id}").GET
async def handler(id: int)
       │
       ▼
Parse Signature
       │
       ▼
Extract Dependencies & Effects
       │
       ▼
Create FlowNode
       │
       ▼
Compile to Executable
```

### 6. Router

**Purpose:** Efficient path matching using radix trie.

**Radix Trie Structure:**
```
/
├─ users/
│  ├─ {id}/
│  │  └─ posts/
│  │     └─ {post_id}
│  └─ *
└─ api/
   └─ v1/
      └─ *
```

**Matching Algorithm:**
1. Parse path into segments
2. Traverse trie from root
3. Try static match first
4. Fall back to parameter match
5. Fall back to wildcard match
6. Extract and validate parameters
7. Return matched flow + params

**Conflict Detection:**
- Same method + same pattern structure
- Report during registration
- Emit warnings in logs

### 7. Effect System

**Purpose:** Typed capability tokens with lifecycle management.

**Effect Lifecycle:**
```
Request Start
     │
     ▼
Acquire Effect (from provider)
     │
     ▼
Handler Execution (use effect)
     │
     ▼
Release Effect (commit/rollback)
     │
     ▼
Request End
```

**Provider Interface:**
```python
class EffectProvider:
    async def initialize()      # Startup (once)
    async def acquire(mode)      # Per request
    async def release(resource)  # Per request
    async def finalize()         # Shutdown (once)
```

### 8. Middleware Stack

**Purpose:** Composable request/response pipeline.

**Ordering Rules:**
1. Global middleware first
2. App middleware second
3. Controller middleware third
4. Route middleware last
5. Within same level: sort by priority (lower = earlier)

**Execution:**
```
Request
  │
  ▼
Middleware 1 (pre)
  │
  ▼
Middleware 2 (pre)
  │
  ▼
Handler
  │
  ▼
Middleware 2 (post)
  │
  ▼
Middleware 1 (post)
  │
  ▼
Response
```

### 9. Flow Engine

**Purpose:** Execute flows with DI and effect management.

**Execution Steps:**
1. Create request-scoped container
2. Create RequestCtx
3. Execute guards (short-circuit if fail)
4. Execute transforms
5. Resolve handler dependencies
6. Acquire effects
7. Execute handler
8. Execute post hooks
9. Release effects (commit/rollback)
10. Cleanup request scope

**Dependency Injection:**
```python
@flow("/users/{id}").PUT
async def update(id: int, db: DBTx, UserService: UserService):
    # id: from path params
    # db: from effect registry
    # UserService: from DI container
```

### 10. ASGI Adapter

**Purpose:** Bridge ASGI protocol to Aquilia.

**Request Flow:**
```
ASGI (scope, receive, send)
       │
       ▼
Create Request object
       │
       ▼
Match route
       │
       ▼
Build middleware chain
       │
       ▼
Execute flow
       │
       ▼
Send response via ASGI
```

## Data Flow (Complete Request)

```
1. ASGI receives HTTP request
2. ASGIAdapter creates Request object
3. Router matches path → Flow
4. Middleware stack wraps flow handler
5. Engine creates request scope
6. Engine resolves dependencies
7. Engine acquires effects
8. Handler executes
9. Effects released (commit/rollback)
10. Response sent via ASGI
11. Request scope cleaned up
```

## Deployment Fingerprint

**Purpose:** Reproducible deploy identification.

**Computed From:**
- All manifest data (serialized)
- Config schema definitions
- Flow metadata
- Load order

**Usage:**
- CI/CD gating (ensure fingerprint matches)
- Audit trail (track what's deployed)
- Rollback support (revert to fingerprint)

## Performance Considerations

**Optimizations:**
1. **Router**: Radix trie for O(k) lookup (k = path segments)
2. **DI**: Cache resolved singletons
3. **Flow Compilation**: Pre-compile flows at startup
4. **Middleware**: Pre-build chain, avoid per-request allocation
5. **Effects**: Pool resources (connection pools)

**Benchmarking:**
- Route lookup: < 1ms
- Middleware overhead: < 0.5ms per layer
- End-to-end: Target 10k+ RPS for simple handlers

## Testing Strategy

**Unit Tests:**
- Each component in isolation
- Mock dependencies
- Fast feedback

**Integration Tests:**
- Full registry + server
- Real flows and middleware
- Slower but comprehensive

**Test Registry:**
```python
registry = Registry.from_manifests(
    [TestApp],
    overrides={"Service": MockService}
)
```

## Security Considerations

1. **No import-time code execution** in manifests
2. **Scoped services** prevent cross-request leakage
3. **Effect boundaries** enforce capability control
4. **Plugin sandboxing** (optional) restricts imports
5. **Config validation** prevents injection

## Extensibility

**Extension Points:**
1. Custom effects + providers
2. Custom middleware
3. Custom config loaders
4. Custom transport adapters
5. Custom CLI commands

## Future Enhancements

1. **OpenAPI generation** from flows
2. **GraphQL adapter** using same flows
3. **gRPC adapter** for function-based RPC
4. **Plugin marketplace** with sandboxing
5. **Visual flow editor** for complex pipelines
6. **Distributed tracing** integration
