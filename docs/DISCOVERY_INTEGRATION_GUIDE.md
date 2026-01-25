# Enhanced Auto-Discovery Integration Guide

## Quick Start

### 1. Generate Workspace with Auto-Discovery

```bash
python -c "
from aquilia.cli.generators.workspace import WorkspaceGenerator
from pathlib import Path

gen = WorkspaceGenerator('myapp', Path('myapp'))
gen.generate()
"
```

**What happens automatically:**
- ✅ Scans `modules/` directory
- ✅ Detects all modules with `manifest.py`
- ✅ Extracts metadata (version, description, tags, etc.)
- ✅ Resolves dependencies
- ✅ Validates configurations
- ✅ Generates ordered module registrations in `workspace.py`

### 2. Inspect Discovered Modules

```bash
# List all modules
python -m aquilia.cli.commands.discover myapp

# Verbose output with details
python -m aquilia.cli.commands.discover myapp --verbose
```

### 3. Run Analytics

```bash
# Get health score and recommendations
python -c "
from aquilia.cli.commands.analytics import DiscoveryAnalytics, print_analysis_report

analytics = DiscoveryAnalytics('myapp')
analysis = analytics.analyze()
print_analysis_report(analysis)
"
```

### 4. Validate Modules

```bash
python -c "
from aquilia.cli.discovery_cli import DiscoveryCLI

DiscoveryCLI.validate('myapp')
"
```

### 5. View Dependency Graph

```bash
python -c "
from aquilia.cli.discovery_cli import DiscoveryCLI

DiscoveryCLI.dependencies('myapp')
"
```

## Module Manifest Requirements

For auto-discovery to work, each module needs a `manifest.py`:

```python
# modules/mymodule/manifest.py
from aquilia import AppManifest

manifest = AppManifest(
    # Required - identity
    name="mymodule",
    version="1.0.0",
    description="My module",
    
    # Optional - metadata
    author="team@company.com",
    tags=["feature", "core"],
    
    # Required - routing
    route_prefix="/api/v1/mymodule",
    base_path="modules.mymodule",
    
    # Optional - structure
    services=["modules.mymodule.services:MyService"],
    controllers=["modules.mymodule.controllers:MyController"],
    
    # Optional - dependencies
    depends_on=["core", "auth"],
)
```

## Common Workflows

### Workflow 1: Create New Module with Auto-Detection

```bash
# 1. Create module directory
mkdir -p modules/newmodule/{services,controllers}

# 2. Create manifest
cat > modules/newmodule/manifest.py << 'EOF'
from aquilia import AppManifest

manifest = AppManifest(
    name="newmodule",
    version="0.1.0",
    description="New module",
    route_prefix="/newmodule",
    base_path="modules.newmodule",
    depends_on=["core"],
)
EOF

# 3. Regenerate workspace (auto-discovery runs)
python -c "
from aquilia.cli.generators.workspace import WorkspaceGenerator
from pathlib import Path
WorkspaceGenerator('myapp', Path('myapp')).generate()
"

# 4. Verify module was detected
python -m aquilia.cli.commands.discover myapp
```

### Workflow 2: Validate Dependencies

```python
from aquilia.cli.generators.workspace import WorkspaceGenerator
from pathlib import Path

gen = WorkspaceGenerator('myapp', Path('myapp'))
discovered = gen._discover_modules()
validation = gen._validate_modules(discovered)

if not validation['valid']:
    print("❌ Validation failed!")
    for error in validation['errors']:
        print(f"  - {error}")
else:
    print("✓ All modules valid")
```

### Workflow 3: Check Module Loading Order

```python
from aquilia.cli.generators.workspace import WorkspaceGenerator
from pathlib import Path

gen = WorkspaceGenerator('myapp', Path('myapp'))
discovered = gen._discover_modules()
sorted_mods = gen._resolve_dependencies(discovered)

print("Module loading order:")
for i, mod_name in enumerate(sorted_mods, 1):
    deps = discovered[mod_name].get('depends_on', [])
    if deps:
        print(f"  {i}. {mod_name} (requires: {', '.join(deps)})")
    else:
        print(f"  {i}. {mod_name}")
```

### Workflow 4: Generate Analytics Report

```python
from aquilia.cli.commands.analytics import DiscoveryAnalytics
import json

analytics = DiscoveryAnalytics('myapp')
analysis = analytics.analyze()

# Access detailed data
print(f"Health Score: {analysis['metrics']['health_score']}")
print(f"Total Modules: {analysis['summary']['total_modules']}")
print(f"Recommendations: {len(analysis['recommendations'])}")

# Save to file
with open('discovery_report.json', 'w') as f:
    json.dump(analysis, f, indent=2, default=str)
```

## CLI Commands Reference

### Discovery Commands

```bash
# List modules (basic)
python -m aquilia.cli.commands.discover WORKSPACE

# List modules (verbose)
python -m aquilia.cli.commands.discover WORKSPACE --verbose

# Custom workspace path
python -m aquilia.cli.commands.discover WORKSPACE --path /path/to/workspace
```

### Analytics Commands

```bash
python -c "
from aquilia.cli.discovery_cli import DiscoveryCLI
DiscoveryCLI.analyze('myapp')
"
```

### Validation Commands

```bash
python -c "
from aquilia.cli.discovery_cli import DiscoveryCLI
DiscoveryCLI.validate('myapp')
"
```

### Dependency Commands

```bash
python -c "
from aquilia.cli.discovery_cli import DiscoveryCLI
DiscoveryCLI.dependencies('myapp')
"
```

## Advanced Usage

### Custom Discovery Logic

```python
from aquilia.cli.generators.workspace import WorkspaceGenerator
from pathlib import Path

class CustomDiscovery(WorkspaceGenerator):
    def _discover_modules(self):
        discovered = super()._discover_modules()
        
        # Add custom filtering
        filtered = {
            name: mod for name, mod in discovered.items()
            if not name.startswith('_')  # Skip private modules
        }
        
        return filtered

gen = CustomDiscovery('myapp', Path('myapp'))
discovered = gen._discover_modules()
```

### Custom Validation

```python
from aquilia.cli.generators.workspace import WorkspaceGenerator

gen = WorkspaceGenerator('myapp', Path('myapp'))
discovered = gen._discover_modules()
validation = gen._validate_modules(discovered)

# Add custom checks
for name, mod in discovered.items():
    if not mod['has_controllers']:
        validation['warnings'].append(
            f"Module '{name}' has no controllers"
        )
```

### Caching Management

```python
from aquilia.cli.commands.analytics import DiscoveryAnalytics

analytics = DiscoveryAnalytics('myapp')

# Get cached results (if fresh)
cached = analytics.get_cached_analysis(max_age_seconds=3600)
if cached:
    print("Using cached analysis")
else:
    # Run fresh analysis
    analysis = analytics.analyze()
```

## Troubleshooting

### Issue: "Module not appearing in workspace.py"

**Solution:**
1. Ensure module directory has `manifest.py`
2. Check manifest is valid Python
3. Regenerate workspace: `WorkspaceGenerator().generate()`

### Issue: "Dependency errors reported"

**Solution:**
1. Verify dependencies exist: `python -m aquilia.cli.commands.discover myapp --verbose`
2. Check `depends_on` list in manifest
3. Run validation: `python -c "from aquilia.cli.discovery_cli import DiscoveryCLI; DiscoveryCLI.validate('myapp')"`

### Issue: "Route prefix conflicts"

**Solution:**
1. List all modules: `python -m aquilia.cli.commands.discover myapp --verbose`
2. Find duplicate `route_prefix` values
3. Update manifest to use unique prefix

### Issue: "Circular dependencies detected"

**Solution:**
1. Check dependency graph: `python -c "from aquilia.cli.discovery_cli import DiscoveryCLI; DiscoveryCLI.dependencies('myapp')"`
2. Look for cycles (A→B→C→A)
3. Break cycle by removing one dependency

## Performance Tips

1. **Cache Results**
   - Use `get_cached_analysis()` for repeated checks
   - Default cache TTL: 3600 seconds

2. **Batch Operations**
   - Run discovery once, reuse results
   - Avoid repeated `_discover_modules()` calls

3. **Filter Early**
   - Skip validation for known-good modules
   - Custom filtering in `_discover_modules()`

4. **Async Operations**
   - Run analytics in background
   - Cache results for UI display

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Validate Module Discovery
  run: |
    python -c "
    from aquilia.cli.discovery_cli import DiscoveryCLI
    DiscoveryCLI.validate('myapp')
    "
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

python -c "
from aquilia.cli.discovery_cli import DiscoveryCLI
try:
    DiscoveryCLI.validate('myapp')
except SystemExit:
    exit 1
"
```

### Docker Build

```dockerfile
FROM python:3.11

WORKDIR /app
COPY . .

# Validate module discovery
RUN python -c "
from aquilia.cli.discovery_cli import DiscoveryCLI
DiscoveryCLI.validate('myapp')
"

RUN python main.py
```

## Best Practices

✅ **DO:**
- Include `author` in manifests
- Add descriptive `tags`
- Use semantic versioning
- Declare all dependencies
- Keep manifests up-to-date

❌ **DON'T:**
- Create circular dependencies
- Use duplicate route prefixes
- Leave manifests at `version="0.1.0"`
- Omit module metadata
- Create unused modules

## Summary

The enhanced auto-discovery system provides:

1. **Automatic Detection** - Finds all modules automatically
2. **Intelligent Ordering** - Resolves dependencies correctly
3. **Validation** - Detects conflicts and issues
4. **Analytics** - Health scoring and recommendations
5. **CLI Tools** - Easy command-line access
6. **Caching** - Performance optimization
7. **Integration** - Works with existing systems

Use these tools to build scalable, modular Aquilia applications with confidence!
