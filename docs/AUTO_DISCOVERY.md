# Enhanced Module Auto-Discovery System

## Overview

The Aquilia framework now features an advanced module auto-discovery system that goes far beyond simple file detection. It provides intelligent module management with dependency resolution, validation, analytics, and optimization recommendations.

## Key Features

### 1. **Intelligent Module Detection**

The auto-discovery system automatically scans the `modules/` directory and identifies all modules that have a `manifest.py` file.

**What gets detected:**
- Module name (directory name)
- Version (from manifest)
- Description and author
- Route prefix and base path
- Tags for categorization
- Dependencies on other modules
- Available components (services, controllers, middleware)

### 2. **Dependency Resolution**

Modules can declare dependencies on other modules via the `depends_on` field in their manifest. The system uses **Kahn's topological sorting algorithm** to determine the optimal loading order.

```python
# Example manifest with dependencies
depends_on=["core", "auth"]  # This module depends on 'core' and 'auth'
```

**Benefits:**
- Automatic ordering ensures dependencies load before dependents
- Prevents "undefined dependency" errors
- Enables modular architecture patterns

### 3. **Comprehensive Validation**

The discovery system validates all discovered modules and detects:

- **Dependency conflicts**: Missing or circular dependencies
- **Route conflicts**: Duplicate route prefixes
- **Structural issues**: Missing or malformed manifests
- **Metadata completeness**: Missing author, tags, or version info

### 4. **Module Structure Analysis**

The system detects what components each module contains:

```
- Services: Business logic and DI services
- Controllers: HTTP endpoints and routing
- Middleware: Request/response processing
```

### 5. **Module Categorization**

Modules can be tagged for better organization and filtering:

```python
tags=["auth", "security", "core"]
```

### 6. **Automatic Workspace Generation**

When you generate a new workspace, the system automatically:

1. Discovers all modules
2. Validates them
3. Resolves dependencies
4. Generates properly ordered `.module()` registrations
5. Includes metadata (version, tags, dependencies)

**Generated output in workspace.py:**
```python
workspace = (
    Workspace(...)
    # Auto-detected modules
    .module(Module("core", version="1.0.0", description="Core module").route_prefix("/api").tags("core"))
    .module(Module("auth", version="0.5.0", description="Auth module").route_prefix("/auth").tags("security", "auth").depends_on("core"))
    .module(Module("users", version="0.2.0", description="Users module").route_prefix("/users").tags("users").depends_on("core", "auth"))
)
```

## Usage

### Inspect Discovered Modules

```bash
# Basic module list
python -m aquilia.cli.commands.discover myapp

# Verbose output with details
python -m aquilia.cli.commands.discover myapp --verbose

# Custom workspace path
python -m aquilia.cli.commands.discover myapp --path /path/to/myapp
```

**Output:**
```
📦 Module Discovery Report
============================================================
Workspace: myapp
Path: myapp
Modules Found: 3

Module               Version      Route               
-------------------- ------------ --------------------
core                 1.0.0        /api                
auth                 0.5.0        /auth               
users                0.2.0        /users              

✓ All modules valid - no issues detected
```

### Run Analytics

```python
from aquilia.cli.commands.analytics import DiscoveryAnalytics, print_analysis_report

analytics = DiscoveryAnalytics('myapp')
analysis = analytics.analyze()
print_analysis_report(analysis)
```

**Output includes:**
- Module summary statistics
- Health score (0-100)
- Dependency depth and cycles
- Validation issues
- Optimization recommendations

## API Reference

### WorkspaceGenerator Methods

#### `_discover_modules() -> dict`
Discovers all modules and returns detailed metadata for each.

```python
discovered = generator._discover_modules()
# Returns:
# {
#   'module_name': {
#     'name': str,
#     'path': Path,
#     'version': str,
#     'description': str,
#     'route_prefix': str,
#     'author': str,
#     'tags': List[str],
#     'base_path': str,
#     'depends_on': List[str],
#     'has_services': bool,
#     'has_controllers': bool,
#     'has_middleware': bool,
#   }
# }
```

#### `_resolve_dependencies(modules: dict) -> list`
Returns modules in correct load order based on dependencies.

```python
sorted_modules = generator._resolve_dependencies(discovered)
# Returns: ['core', 'auth', 'users']  # Correctly ordered
```

#### `_validate_modules(modules: dict) -> dict`
Validates modules and returns issues.

```python
validation = generator._validate_modules(discovered)
# Returns:
# {
#   'valid': bool,
#   'warnings': List[str],
#   'errors': List[str],
# }
```

### DiscoveryAnalytics Methods

#### `analyze() -> dict`
Runs comprehensive analysis on all discovered modules.

Returns analysis including:
- Summary statistics
- Module-level analysis
- Dependency graph
- Health metrics
- Recommendations

#### `get_cached_analysis(max_age_seconds: int = 3600) -> Optional[dict]`
Retrieves cached analysis if fresh (faster than re-running).

## Module Manifest Structure

Create a `manifest.py` in each module directory:

```python
from aquilia import AppManifest

manifest = AppManifest(
    # Identity
    name="mymodule",
    version="1.0.0",
    description="My awesome module",
    author="team@company.com",
    tags=["feature", "core"],
    
    # Services and controllers
    services=["modules.mymodule.services:MyService"],
    controllers=["modules.mymodule.controllers:MyController"],
    
    # Routing
    route_prefix="/api/v1/mymodule",
    base_path="modules.mymodule",
    
    # Dependencies on other modules
    depends_on=["core", "auth"],
)
```

## Advanced Features

### Topological Sorting

Modules are automatically ordered based on dependencies using Kahn's algorithm:

```
Input: Module A depends on B, B depends on C
Output: [C, B, A]  # Correct load order
```

### Cycle Detection

The system detects circular dependencies:

```
A -> B -> C -> A  # Detected! ⚠️
```

### Health Scoring

Modules receive a health score (0-100) based on:
- Validation errors/warnings
- Metadata completeness
- Documentation
- Version maturity

### Caching

Analysis results are cached in `.aquilia/discovery/analysis.json` for performance.

## Common Patterns

### Pattern 1: Core + Feature Modules

```
modules/
├── core/               # Base functionality
│   └── manifest.py
├── auth/              # Depends on core
│   └── manifest.py    # depends_on=["core"]
└── users/             # Depends on auth, core
    └── manifest.py    # depends_on=["core", "auth"]
```

**Auto-generated order:** core → auth → users ✓

### Pattern 2: Plugin System

```
modules/
├── base/              # Core plugin interface
│   └── manifest.py
├── plugin_a/          # Depends on base
│   └── manifest.py
└── plugin_b/          # Depends on base
    └── manifest.py
```

**Auto-generated order:** base → plugin_a, plugin_b ✓

### Pattern 3: Layered Architecture

```
modules/
├── data/              # Data layer
│   └── manifest.py
├── business/          # Business logic (depends on data)
│   └── manifest.py    # depends_on=["data"]
└── api/               # API layer (depends on business)
    └── manifest.py    # depends_on=["business", "data"]
```

**Auto-generated order:** data → business → api ✓

## Troubleshooting

### "Module X depends on Y which is not installed"

**Issue:** Module declares dependency on non-existent module.

**Solution:**
1. Create the dependency module
2. Or remove the dependency from `depends_on`

### "Route prefix conflict: '/api' used by both X and Y"

**Issue:** Multiple modules using same route prefix.

**Solution:** Update route_prefix in one of the manifests to be unique.

### Modules not loading in correct order

**Issue:** Topological sort found circular dependencies.

**Solution:** 
1. Check for circular dependencies: A → B → C → A
2. Break the cycle by removing one dependency

## Performance Considerations

- Discovery runs once at workspace generation
- Results are cached for 1 hour
- Caching can be disabled or refreshed manually
- Suitable for 100+ modules

## Future Enhancements

- [ ] Module version constraints (e.g., "core>=1.0.0")
- [ ] Module health checks and linting
- [ ] Automatic module generation based on templates
- [ ] Module dependency visualization (graph export)
- [ ] Module usage analytics
- [ ] Auto-wiring module dependencies
