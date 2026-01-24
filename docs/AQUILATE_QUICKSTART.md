# Aquilate CLI - Quick Start Guide

## What is Aquilate?

**Aquilate** is Aquilia's native CLI for manifest-driven, artifact-first project orchestration. Unlike Django, Flask, or FastAPI, Aquilate provides a completely new paradigm:

- **Manifest-driven**: Projects defined in `.aq` YAML files, not Python settings
- **Artifact-first**: Everything compiles to immutable `.crous` artifacts
- **CLI-native**: `aq` command as primary interface, not Python imports
- **Workspace/Module**: New terminology replacing Django's project/app pattern
- **Explicit boundaries**: Clear separation between workspaces, modules, and flows

## Installation

```bash
# Install dependencies
pip install click pyyaml

# Or from requirements
pip install -r requirements-cli.txt
```

## Quick Start

### 1. Create a Workspace

```bash
# Initialize new workspace
aq init workspace my-api

# Navigate to workspace
cd my-api

# View structure
ls -la
# Output:
#   aquilia.aq        # Workspace manifest
#   modules/          # Application modules
#   config/           # Configuration files
#   artifacts/        # Compiled artifacts
#   runtime/          # Runtime state
```

### 2. Add Modules

```bash
# Add a module
aq add module users

# Add with dependencies
aq add module auth --depends-on=users

# Add with custom configuration
aq add module admin --fault-domain=ADMIN --route-prefix=/admin

# View modules
ls modules/
# Output: users/ auth/ admin/
```

### 3. Validate & Compile

```bash
# Validate manifests
aq validate

# Validate with strict mode (production-level)
aq validate --strict

# Compile to artifacts
aq compile

# View generated artifacts
ls artifacts/
# Output:
#   aquilia.crous      # Workspace metadata
#   registry.crous     # Module registry
#   routes.crous       # Routing table
#   di.crous          # DI graph
#   users.crous       # Module artifacts
```

### 4. Run Development Server

```bash
# Start dev server with hot-reload
aq run

# Custom port
aq run --port=3000

# Test mode (no reload)
aq run --mode=test --no-reload
```

### 5. Production Deployment

```bash
# Freeze artifacts (immutable)
aq freeze

# Start production server
aq serve --workers=4 --bind=0.0.0.0:8080
```

## Command Reference

### Workspace Management

```bash
# Initialize workspace
aq init workspace <name>              # Standard setup
aq init workspace <name> --minimal    # Minimal (no examples)
aq init workspace <name> --template=api  # Use template

# Diagnose issues
aq doctor
```

### Module Management

```bash
# Add module
aq add module <name>
aq add module <name> --depends-on=<dep1> --depends-on=<dep2>
aq add module <name> --fault-domain=<DOMAIN>
aq add module <name> --route-prefix=/<prefix>
```

### Validation & Compilation

```bash
# Validate
aq validate                    # Standard validation
aq validate --strict           # Production-level validation
aq validate --module=<name>    # Validate single module

# Compile
aq compile                     # Compile to artifacts/
aq compile --output=dist/      # Custom output directory
aq compile --watch            # Watch mode (auto-recompile)
```

### Runtime

```bash
# Development
aq run                         # Dev server (hot-reload)
aq run --port=<port>          # Custom port
aq run --host=<host>          # Custom host
aq run --mode=test            # Test mode
aq run --no-reload            # Disable hot-reload

# Production
aq serve                       # Prod server (frozen artifacts)
aq serve --workers=<n>        # Multi-worker
aq serve --bind=<host:port>   # Bind address
```

### Artifact Management

```bash
# Freeze
aq freeze                      # Generate immutable artifacts
aq freeze --output=<dir>      # Custom output
aq freeze --sign              # Cryptographic signing
```

### Inspection

```bash
# Inspect artifacts
aq inspect routes              # View compiled routes
aq inspect di                  # View DI graph
aq inspect modules             # List modules
aq inspect faults              # View fault domains
aq inspect config              # View resolved config
```

### Migration

```bash
# Migrate from Django-style
aq migrate legacy              # Convert Django project
aq migrate legacy --dry-run    # Preview migration
```

## Workspace Structure

```
my-api/
├── aquilia.aq              # Workspace manifest
├── modules/                # Application modules
│   ├── users/
│   │   ├── module.aq      # Module manifest
│   │   ├── flows.py       # Request handlers
│   │   ├── services.py    # Business logic
│   │   ├── faults.py      # Error handling
│   │   └── __init__.py
│   └── auth/
│       └── ...
├── config/                 # Configuration
│   ├── base.aq            # Base config (all environments)
│   ├── dev.aq             # Development config
│   └── prod.aq            # Production config
├── artifacts/             # Compiled artifacts (.crous files)
│   ├── aquilia.crous
│   ├── registry.crous
│   ├── routes.crous
│   └── ...
└── runtime/               # Runtime state (logs, temp files)
```

## Module Structure

Generated by `aq add module <name>`:

```
modules/users/
├── module.aq              # Module manifest
├── __init__.py            # Module exports
├── flows.py               # Request handlers (HTTP endpoints)
├── services.py            # Business logic (DI-injected)
└── faults.py              # Domain-specific errors
```

### Example: flows.py

```python
from aquilia.core import Flow, Context
from aquilia.routing import route, GET, POST
from .services import UsersService
from .faults import UserNotFoundFault

@route("/users/", methods=[GET])
async def get_users_list(ctx: Context) -> dict:
    service = await ctx.resolve(UsersService)
    items = await service.get_all()
    return {"items": items}

@route("/users/{id}", methods=[GET])
async def get_user_detail(ctx: Context) -> dict:
    user_id = ctx.params.get("id")
    service = await ctx.resolve(UsersService)
    
    user = await service.get_by_id(user_id)
    if not user:
        raise UserNotFoundFault(user_id=user_id)
    
    return user
```

### Example: services.py

```python
from aquilia.di import injectable, Scope

@injectable(scope=Scope.SINGLETON)
class UsersService:
    def __init__(self):
        self._storage = []
    
    async def get_all(self):
        return self._storage
    
    async def get_by_id(self, user_id: int):
        for user in self._storage:
            if user["id"] == user_id:
                return user
        return None
```

### Example: faults.py

```python
from aquilia.faults import Fault, FaultDomain, Severity, RecoveryStrategy

USERS = FaultDomain(name="USERS", description="Users module faults")

class UserNotFoundFault(Fault):
    domain = USERS
    severity = Severity.LOW
    code = "USER_NOT_FOUND"
    
    def __init__(self, user_id: int):
        super().__init__(
            message=f"User with id {user_id} not found",
            context={"user_id": user_id},
            recovery_strategy=RecoveryStrategy.PROPAGATE,
        )
```

## Manifests

### Workspace Manifest (aquilia.aq)

```yaml
workspace:
  name: my-api
  version: "0.1.0"
  description: "My Aquilia API"

runtime:
  mode: dev
  host: 127.0.0.1
  port: 8000
  workers: 1

modules:
  - name: users
    fault_domain: USERS
    route_prefix: /users
  - name: auth
    fault_domain: AUTH
    route_prefix: /auth

integrations:
  registry:
    enabled: true
  dependency_injection:
    enabled: true
    auto_wire: true
  routing:
    enabled: true
    strict_matching: true
  fault_handling:
    enabled: true
    default_strategy: propagate
```

### Module Manifest (module.aq)

```yaml
module:
  name: users
  version: "0.1.0"
  description: "Users module"

routing:
  prefix: /users

fault_handling:
  domain: USERS
  strategy: propagate

dependencies:
  - auth

providers:
  # Auto-discovered from services.py
  - class: UsersService
    scope: singleton

routes:
  # Auto-discovered from flows.py
  - path: /
    handler: get_users_list
    method: GET
```

## Artifacts (.crous files)

Compiled artifacts are JSON files containing immutable representations of your workspace:

### Example: users.crous

```json
{
  "type": "module",
  "name": "users",
  "version": "0.1.0",
  "description": "Users module",
  "route_prefix": "/users",
  "fault_domain": "USERS",
  "depends_on": ["auth"],
  "providers": [
    {"class": "UsersService", "scope": "singleton"}
  ],
  "routes": [
    {"path": "/", "handler": "get_users_list", "method": "GET"}
  ]
}
```

## Development Workflow

### Typical Session

```bash
# 1. Create workspace
aq init workspace my-api
cd my-api

# 2. Add modules
aq add module users
aq add module auth --depends-on=users

# 3. Develop (edit flows.py, services.py, faults.py)
# ...

# 4. Validate
aq validate

# 5. Run dev server
aq run
# Server starts at http://127.0.0.1:8000
# Hot-reload enabled

# 6. Test endpoints
curl http://127.0.0.1:8000/users/

# 7. Compile for inspection
aq compile
aq inspect routes

# 8. Freeze for production
aq freeze --output=dist/
aq serve --workers=4
```

### Testing

```bash
# Validate before committing
aq validate --strict

# Check for issues
aq doctor

# Inspect artifacts
aq inspect modules
aq inspect di
aq inspect faults
```

## Key Differences from Django

| Aspect | Django | Aquilate |
|--------|--------|----------|
| **Project unit** | Project | Workspace |
| **App unit** | App | Module |
| **Configuration** | settings.py | aquilia.aq + config/*.aq |
| **CLI** | manage.py | `aq` command |
| **Structure** | apps/, settings.py | modules/, aquilia.aq |
| **Discovery** | Auto-discovery | Manifest-driven |
| **Runtime** | Python imports | Compiled artifacts |
| **Dev mode** | runserver | `aq run` |
| **Production** | WSGI/ASGI | `aq serve` (frozen) |

## Philosophy

Aquilate follows these principles:

1. **Manifest-first**: Declare structure, don't infer it
2. **Artifact-driven**: Compile once, deploy anywhere
3. **CLI-native**: Commands over code
4. **Explicit boundaries**: Clear module boundaries
5. **Static-first**: Validate without execution
6. **Mode separation**: Dev (mutable) vs Prod (immutable)

## Next Steps

- Read the complete design: [`docs/AQUILATE_DESIGN.md`](../docs/AQUILATE_DESIGN.md)
- Explore subsystem integrations:
  - Aquilary (Registry)
  - Dependency Injection
  - Routing & Flow
  - Fault Handling
  - Pattern System (Crous)

## Implementation Status

✅ **Complete** (v2.0.0):
- CLI framework (Click-based)
- Workspace generation
- Module generation
- Manifest parsing
- Artifact compilation
- Validation
- Diagnostics
- Inspection commands

⏸️ **Pending**:
- Runtime integration (dev/prod servers)
- Hot-reload implementation
- Artifact signing
- Migration tools
- Watch mode
- Advanced inspection (graphical)

## Support

For issues, feature requests, or questions:
- Design document: `docs/AQUILATE_DESIGN.md`
- Command help: `aq --help`, `aq <command> --help`
- Diagnostics: `aq doctor`
