# authentication

Aquilia workspace generated with `aq init workspace authentication`.

## Structure

```
authentication/
  aquilia.py          # Workspace configuration (Python)
  modules/            # Application modules
  config/             # Environment-specific configs
    base.yaml        # Base config
    dev.yaml         # Development config
    prod.yaml        # Production config
  artifacts/          # Compiled artifacts
  runtime/            # Runtime state
```

## Configuration Architecture

Aquilia uses a **professional separation of concerns**:

- **`aquilia.py`** - Workspace structure (modules, integrations)
  - Version-controlled and shared across team
  - Environment-agnostic
  - Type-safe Python API

- **`config/*.yaml`** - Runtime settings (host, port, workers)
  - Environment-specific (dev, prod, staging)
  - Can contain secrets (not committed)
  - Merged in order: base → environment → env vars

## Getting Started

### Add a module

```bash
aq add module users
```

This will update `aquilia.py`:

```python
workspace = (
    Workspace("authentication", version="0.1.0")
    .module(Module("users").route_prefix("/users"))
    ...
)
```

### Run development server

```bash
aq run
```

This loads: `aquilia.py` + `config/base.yaml` + `config/dev.yaml`

### Run production server

```bash
aq run --mode=prod
```

This loads: `aquilia.py` + `config/base.yaml` + `config/prod.yaml`

## Session Management

Enable sessions with unique Aquilia syntax in `aquilia.py`:

```python
workspace = (
    Workspace("authentication", version="0.1.0")
    .integrate(Integration.sessions(
        policy=SessionPolicy(ttl=timedelta(days=7)),
        store=MemoryStore(max_sessions=1000),
    ))
)
```

Then use in controllers:

```python
from aquilia import session, authenticated, stateful

@GET("/profile")
@authenticated
async def profile(ctx, user: SessionPrincipal):
    return {"user_id": user.id}

@POST("/cart")
@stateful
async def cart(ctx, state: SessionState):
    state._data['items'].append(item)
```

## Commands

- `aq add module <name>` - Add new module
- `aq validate` - Validate configuration
- `aq compile` - Compile to artifacts
- `aq run` - Development server
- `aq run --mode=prod` - Production server
- `aq serve` - Production server (frozen artifacts)
- `aq freeze` - Generate immutable artifacts
- `aq inspect routes` - Inspect compiled routes
- `aq sessions list` - List active sessions
- `aq doctor` - Diagnose issues
- `aq deploy all` - Generate all deployment files
- `aq deploy dockerfile` - Generate Dockerfiles
- `aq deploy compose` - Generate docker-compose.yml
- `aq deploy kubernetes` - Generate Kubernetes manifests

## Documentation

See Aquilia documentation for complete guides.