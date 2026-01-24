# myapp

Aquilia workspace generated with `aq init workspace myapp`.

## Structure

```
myapp/
  aquilia.aq          # Workspace manifest
  modules/            # Application modules
  config/             # Configuration files
    base.aq          # Base config
    dev.aq           # Development config
    prod.aq          # Production config
  artifacts/          # Compiled artifacts
  runtime/            # Runtime state
```

## Getting Started

### Add a module

```bash
aq add module users
```

### Validate manifests

```bash
aq validate
```

### Compile artifacts

```bash
aq compile
```

### Run development server

```bash
aq run
```

## Commands

- `aq add module <name>` - Add new module
- `aq validate` - Validate manifests
- `aq compile` - Compile to artifacts
- `aq run` - Development server
- `aq serve` - Production server
- `aq freeze` - Generate immutable artifacts
- `aq inspect routes` - Inspect compiled routes
- `aq doctor` - Diagnose issues

## Documentation

See `docs/AQUILATE_DESIGN.md` for complete design documentation.