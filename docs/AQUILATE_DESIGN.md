# Aquilate - Aquilia Native CLI & Project System

## Design Document

**Status**: Final Design
**Version**: 1.0.0
**Date**: 2026-01-24

---

## Philosophy

Aquilate is Aquilia's **manifest-driven, artifact-first project orchestration system**. It treats applications as **compiled artifacts** with explicit boundaries, not implicit Python modules.

### Core Principles

1. **Manifest-first, not settings-first**
   - Projects defined by declarative manifests
   - No global `settings.py`
   
2. **Composition over centralization**
   - No "god" module
   - Loose coupling via manifests
   
3. **Artifacts over runtime magic**
   - CLI operates on metadata and crous artifacts
   - Validation without execution
   
4. **Explicit boundaries**
   - Clear separation: workspace → modules → flows
   
5. **CLI as primary UX**
   - `aq` is the entry point, not Python imports
   
6. **Static-first**
   - Most validation happens at compile time

---

## Terminology

| Term | Definition | Example |
|------|------------|---------|
| **Workspace** | Root project unit (replaces "project") | `my-api-workspace/` |
| **Module** | Self-contained app unit (replaces "app") | `users`, `auth` |
| **Runtime Instance** | Live server process | `aq run --mode=dev` |
| **Manifest** | Declarative definition file | `aquilia.aq`, `module.aq` |
| **Artifact** | Compiled metadata | `registry.crous`, `di.crous` |
| **Aquilate** | CLI orchestration system | `aq` command |

---

## CLI Command Grammar

### Structure

```
aq <verb> [<noun>] [<args>] [<flags>]
```

**Verbs** (primary action):
- `init` - Create new workspace/module
- `add` - Add module to workspace
- `validate` - Static validation
- `compile` - Generate artifacts
- `run` - Development server
- `serve` - Production server
- `freeze` - Immutable artifact generation
- `inspect` - Query compiled artifacts
- `migrate` - Convert legacy layouts

**Nouns** (target):
- `workspace` - Workspace-level operations
- `module` - Module-level operations
- `config` - Configuration operations

### Complete Command Reference

```bash
# Workspace Creation
aq init workspace <name>                    # Create new workspace
aq init workspace <name> --minimal          # Minimal setup (no examples)
aq init workspace <name> --template=api     # Use template

# Module Management
aq add module <name>                        # Add module to workspace
aq add module <name> --depends-on=auth      # With dependency
aq add module <name> --fault-domain=USERS   # Custom fault domain
aq remove module <name>                     # Remove module (safe)

# Validation & Compilation
aq validate                                 # Validate all manifests
aq validate --strict                        # Strict mode (prod-level)
aq validate --module=users                  # Validate single module
aq compile                                  # Compile to artifacts
aq compile --watch                          # Watch for changes
aq compile --output=dist/                   # Custom output dir

# Runtime
aq run                                      # Start dev server (hot-reload)
aq run --mode=dev                           # Explicit mode
aq run --port=8000                          # Custom port
aq run --reload-on-change                   # Auto-reload (default in dev)
aq serve                                    # Production server (immutable)
aq serve --workers=4                        # Multi-worker
aq serve --bind=0.0.0.0:8000               # Custom bind

# Artifact Management
aq freeze                                   # Generate immutable artifacts
aq freeze --output=dist/                    # Custom output
aq freeze --sign                            # Sign artifacts
aq inspect routes                           # Show compiled routes
aq inspect di                               # Show DI graph
aq inspect modules                          # List all modules
aq inspect faults                           # Show fault domains
aq inspect config                           # Show resolved config

# Migration & Utilities
aq migrate legacy                           # Convert Django-style layout
aq migrate legacy --dry-run                 # Preview migration
aq check                                    # Quick health check
aq version                                  # Show version info
aq doctor                                   # Diagnose issues
```

---

## Workspace Layout

### Directory Structure

```
my-workspace/
├── aquilia.aq              # Workspace manifest (human-readable)
├── aquilia.crous           # Compiled workspace (generated)
│
├── modules/                # All modules (flat or nested)
│   ├── users/
│   │   ├── module.aq       # Module manifest
│   │   ├── module.crous    # Compiled module
│   │   ├── flows.py        # Controllers & handlers
│   │   ├── services.py     # DI providers
│   │   ├── faults.py       # Module-specific faults
│   │   ├── models.py       # Data models (optional)
│   │   └── tests/
│   │       ├── test_flows.py
│   │       └── test_services.py
│   │
│   ├── auth/
│   │   └── ...
│   │
│   └── common/             # Shared utilities
│       └── ...
│
├── config/                 # Configuration files
│   ├── base.aq             # Base config
│   ├── dev.aq              # Dev overrides
│   ├── test.aq             # Test overrides
│   ├── prod.aq             # Prod overrides
│   └── config.crous        # Compiled config (generated)
│
├── artifacts/              # Compiled artifacts (generated)
│   ├── registry.crous      # RuntimeRegistry
│   ├── routes.crous        # Compiled routes
│   ├── di.crous            # DI graph
│   ├── patterns.crous      # Flow patterns
│   ├── faults.crous        # Fault taxonomy
│   └── fingerprint.json    # Deployment fingerprint
│
├── runtime/                # Runtime state (ephemeral)
│   ├── dev.pid             # Process ID
│   ├── dev.lock            # Runtime lock
│   └── logs/
│       ├── access.log
│       ├── error.log
│       └── faults.log
│
├── .env                    # Environment variables
├── .gitignore
└── README.md
```

### Key Differences from Django

| Django | Aquilate | Reason |
|--------|----------|--------|
| `manage.py` | `aq` CLI | CLI-native, not script wrapper |
| `settings.py` | `aquilia.aq` | Manifest-first |
| `apps/` | `modules/` | Clear terminology |
| `INSTALLED_APPS` | `workspace.modules` | Explicit declaration |
| Auto-discovery | Explicit registration | No magic |
| Python imports | Manifest compilation | Static-first |

---

## Manifest Schemas

### Workspace Manifest (`aquilia.aq`)

```yaml
# Workspace-level configuration
workspace:
  name: my-api-workspace
  version: 0.1.0
  description: "User management API"

# Module composition
modules:
  - users
  - auth
  - common

# Runtime configuration
runtime:
  server: uvicorn              # or: hypercorn, daphne
  host: 0.0.0.0
  port: 8000
  entry: aquilia.runtime.http  # Entry point factory

# Mode-specific defaults
modes:
  dev:
    strict_routes: false
    hot_reload: true
    debug: true
    log_level: DEBUG
  
  test:
    strict_routes: true
    debug: false
    log_level: WARNING
  
  prod:
    strict_routes: true
    hot_reload: false
    debug: false
    log_level: ERROR
    require_frozen: true        # Must use frozen artifacts

# Dependencies (workspace-level)
dependencies:
  python: ">=3.14"
  aquilia: "^2.0.0"

# Artifact configuration
artifacts:
  output_dir: artifacts/
  compression: gzip
  sign: false                   # Enable for production

# Metadata
meta:
  author: "Your Name"
  license: "MIT"
  repository: "https://github.com/user/repo"
```

### Module Manifest (`module.aq`)

```yaml
# Module identity
module:
  name: users
  version: 1.0.0
  description: "User management module"

# What this module exports
exposes:
  flows:
    - UserFlows              # Flow class name
    - UserAdminFlows
  
  services:
    - UserService           # DI provider class name
    - UserRepository
  
  faults:
    - UserNotFoundFault     # Custom fault types
    - UserValidationFault

# Dependencies on other modules
depends_on:
  - auth                    # Required module
  - common                  # Shared utilities

# Fault configuration
fault_domain: USERS         # Domain for module faults

# Routing prefix (optional)
route_prefix: /api/users

# DI configuration
di:
  scope: app                # Default scope for providers
  lazy: false               # Lazy initialization

# Feature flags (optional)
features:
  enable_soft_delete: true
  enable_audit_log: false

# Metadata
meta:
  owner: "Backend Team"
  stability: "stable"        # stable, beta, experimental
```

### Config Manifest (`config/base.aq`)

```yaml
# Configuration (hierarchical)
config:
  database:
    url: ${DATABASE_URL}     # Env var interpolation
    pool_size: 10
    timeout: 30
  
  redis:
    url: ${REDIS_URL}
    max_connections: 50
  
  auth:
    jwt_secret: ${JWT_SECRET}
    token_expiry: 3600
  
  logging:
    level: INFO
    format: json
    handlers:
      - console
      - file

# Secrets (never committed)
secrets:
  - JWT_SECRET
  - DATABASE_URL
  - REDIS_URL
```

---

## Artifact Lifecycle

### Compilation Pipeline

```
Source Manifests → Parser → Validator → Compiler → Artifacts
     ↓                ↓          ↓          ↓          ↓
  .aq files        AST      Faults?    Crous      .crous
```

### Artifact Types

| Artifact | Content | Used By |
|----------|---------|---------|
| `aquilia.crous` | Compiled workspace | Runtime |
| `module.crous` | Compiled module | Registry |
| `config.crous` | Resolved config | All subsystems |
| `registry.crous` | RuntimeRegistry | Server |
| `routes.crous` | Compiled routes | Router |
| `di.crous` | DI graph | Container |
| `patterns.crous` | Flow patterns | Flow engine |
| `faults.crous` | Fault taxonomy | Fault engine |
| `fingerprint.json` | Deployment hash | CI/CD |

### Artifact Generation

```bash
# Development (mutable)
aq compile
# → artifacts/*.crous (overwrites)

# Production (immutable)
aq freeze
# → artifacts/registry.<fingerprint>.crous
# → artifacts/di.<fingerprint>.crous
# → artifacts/fingerprint.json
```

### Artifact Loading Priority

```
1. Frozen artifacts (*.crous with fingerprint)
2. Compiled artifacts (*.crous without fingerprint)
3. Source manifests (*.aq) - dev only
```

---

## Runtime Semantics

### Development Mode (`aq run`)

```python
# Pseudo-code
def run_dev():
    # 1. Load or compile artifacts
    if not artifacts.exist():
        compile_manifests()
    
    # 2. Create runtime registry
    registry = load_artifacts()
    
    # 3. Setup hot-reload watcher
    watcher = FileWatcher(["modules/**/*.py", "**/*.aq"])
    watcher.on_change(recompile_and_reload)
    
    # 4. Start server
    server = create_server(registry, mode="dev")
    server.run(hot_reload=True)
```

### Production Mode (`aq serve`)

```python
# Pseudo-code
def serve_prod():
    # 1. Require frozen artifacts
    if not frozen_artifacts.exist():
        raise RuntimeError("Production requires frozen artifacts")
    
    # 2. Verify fingerprint
    if not verify_fingerprint():
        raise RuntimeError("Artifact fingerprint mismatch")
    
    # 3. Load immutable artifacts
    registry = load_frozen_artifacts()
    
    # 4. No hot-reload, no compilation
    server = create_server(registry, mode="prod")
    server.run(hot_reload=False, workers=N)
```

### Mode Comparison

| Feature | Dev (`aq run`) | Prod (`aq serve`) |
|---------|----------------|-------------------|
| Hot reload | ✓ | ✗ |
| Compilation | On-demand | Forbidden |
| Artifacts | Mutable | Frozen |
| Validation | Permissive | Strict |
| Debug | Enabled | Disabled |
| Source access | Required | Optional |

---

## Integration with Aquilia Subsystems

### 1. Aquilary (Registry)

```python
# Aquilary reads from module manifests
registry = AquilaryRegistry.from_artifacts("artifacts/registry.crous")

# No Python imports during validation
registry.validate()  # Uses compiled metadata only
```

### 2. DI (Dependency Injection)

```python
# DI graph built from module.aq `exposes.services`
container = Container.from_artifact("artifacts/di.crous")

# Providers registered after manifest validation
for module in registry.modules:
    for service in module.exposes.services:
        container.register(service)
```

### 3. Patterns (Flow Engine)

```python
# Flow patterns compiled from module.aq `exposes.flows`
patterns = PatternRegistry.from_artifact("artifacts/patterns.crous")

# Route compilation uses flow metadata
router = compile_routes(patterns)
```

### 4. Faults (Fault System)

```python
# Fault domains from module.aq `fault_domain`
fault_engine = FaultEngine()

for module in registry.modules:
    fault_engine.register_domain(
        domain=module.fault_domain,
        faults=module.exposes.faults,
    )
```

### 5. Crous (Artifacts)

```python
# All artifacts are crous-serialized
from aquilia.crous import dump, load

# Compilation
artifacts = compile_workspace(workspace_manifest)
dump(artifacts, "artifacts/registry.crous")

# Loading
registry = load("artifacts/registry.crous")
```

---

## Strict Rules (Enforced)

### ✅ Allowed

- Explicit manifest declarations
- Compile-time validation
- Artifact-based loading
- Static analysis

### ❌ Forbidden

- Implicit discovery (no `autodiscover()`)
- Runtime manifest parsing in prod
- Python path manipulation (`sys.path.insert`)
- Global settings module
- Side effects during validation
- Magic folder conventions

---

## Migration from Django-style

### Detection

```bash
aq migrate legacy --scan
```

Detects:
- `manage.py`
- `settings.py`
- `INSTALLED_APPS`
- `apps.py` files

### Conversion

```bash
aq migrate legacy
```

Creates:
1. `aquilia.aq` from `settings.py`
2. `module.aq` for each app in `INSTALLED_APPS`
3. Moves `apps/` → `modules/`
4. Generates `config/` from `settings.DATABASES`, etc.
5. Creates `.gitignore` for `artifacts/`, `runtime/`

### Manual Steps

After migration:
1. Review generated manifests
2. Update imports (no relative imports from project root)
3. Run `aq validate --strict`
4. Test with `aq run`

---

## CLI Implementation Architecture

### Structure

```
aquilia/cli/
├── __init__.py
├── __main__.py          # Entry point (aq command)
├── commands/
│   ├── __init__.py
│   ├── init.py          # aq init
│   ├── add.py           # aq add
│   ├── validate.py      # aq validate
│   ├── compile.py       # aq compile
│   ├── run.py           # aq run
│   ├── serve.py         # aq serve
│   ├── freeze.py        # aq freeze
│   ├── inspect.py       # aq inspect
│   └── migrate.py       # aq migrate
├── generators/
│   ├── workspace.py     # Workspace generator
│   ├── module.py        # Module generator
│   └── config.py        # Config generator
├── parsers/
│   ├── manifest.py      # .aq parser
│   └── validator.py     # Manifest validator
├── compilers/
│   ├── workspace.py     # Workspace compiler
│   ├── module.py        # Module compiler
│   └── artifact.py      # Artifact generator
└── utils/
    ├── fs.py            # File system utilities
    ├── templates.py     # File templates
    └── colors.py        # Terminal colors
```

### Technology Stack

- **CLI Framework**: Click or Typer (modern, typed CLI)
- **Manifest Parser**: PyYAML or TOML
- **Watcher**: watchfiles (async file watching)
- **Server**: Uvicorn/Hypercorn integration
- **Validation**: Pydantic for manifest schemas

---

## Success Criteria

This design is complete when:

1. ✅ New users understand Aquilia without knowing Django
2. ✅ CLI feels like compiler + orchestrator, not dev server wrapper
3. ✅ Project structure directly reflects architecture
4. ✅ All subsystems (Aquilary, DI, Patterns, Faults, Crous) align
5. ✅ CI can validate and freeze without executing app logic
6. ✅ Manifest → Artifact → Runtime is explicit and traceable

---

## Appendix: Example Session

```bash
# Create workspace
$ aq init workspace my-api
✓ Created workspace 'my-api'
  aquilia.aq
  config/base.aq
  modules/
  
# Add modules
$ aq add module users
✓ Created module 'users'
  modules/users/module.aq
  modules/users/flows.py
  modules/users/services.py

$ aq add module auth --depends-on=users
✓ Created module 'auth'
✓ Updated workspace manifest

# Validate
$ aq validate
Validating workspace...
✓ Workspace manifest valid
✓ Module 'users' valid
✓ Module 'auth' valid
✓ Dependencies resolved: auth → users
✓ No route conflicts
✓ DI graph acyclic

# Compile
$ aq compile
Compiling workspace...
✓ Compiled workspace → aquilia.crous
✓ Compiled modules → module.crous
✓ Generated artifacts:
  artifacts/registry.crous
  artifacts/routes.crous
  artifacts/di.crous
  artifacts/faults.crous

# Run dev server
$ aq run
Starting Aquilia runtime (dev mode)...
✓ Loaded artifacts from artifacts/
✓ Hot-reload enabled
✓ Listening on http://127.0.0.1:8000
✓ 2 modules loaded: users, auth
✓ 8 routes compiled
✓ 3 DI providers registered

# Inspect
$ aq inspect routes
Routes:
  GET  /api/users          → UserFlows.list_users
  POST /api/users          → UserFlows.create_user
  GET  /api/users/:id      → UserFlows.get_user
  POST /api/auth/login     → AuthFlows.login

# Freeze for production
$ aq freeze
Freezing workspace...
✓ Validated in strict mode
✓ Generated fingerprint: a3f9c2d1e5b7
✓ Created frozen artifacts:
  artifacts/registry.a3f9c2d1e5b7.crous
  artifacts/di.a3f9c2d1e5b7.crous
  artifacts/fingerprint.json

# Production serve
$ aq serve --workers=4
Starting Aquilia runtime (prod mode)...
✓ Loaded frozen artifacts (fingerprint: a3f9c2d1e5b7)
✓ Strict validation passed
✓ 4 workers spawned
✓ Listening on http://0.0.0.0:8000
```

---

**Aquilate: Manifest-driven, artifact-first orchestration for Aquilia.**

*No Django. No Flask. No FastAPI patterns. Pure Aquilia.*
