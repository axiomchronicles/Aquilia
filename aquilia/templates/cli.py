"""
Template CLI - Command-line interface for template management.

Provides commands:
- aq templates compile: Compile templates to crous artifacts
- aq templates lint: Lint templates for errors
- aq templates inspect: Inspect template metadata
- aq templates clear-cache: Clear bytecode cache
"""

from typing import Optional
from pathlib import Path
import asyncio
import sys
import json

from .engine import TemplateEngine
from .loader import TemplateLoader
from .bytecode_cache import CrousBytecodeCache, InMemoryBytecodeCache
from .manager import TemplateManager
from .security import SandboxPolicy


def create_template_engine_from_config(
    template_dirs: list[str],
    cache_dir: str = "artifacts",
    sandbox: bool = True,
    mode: str = "prod"
) -> TemplateEngine:
    """
    Create template engine from configuration.
    
    Args:
        template_dirs: List of template directories
        cache_dir: Cache directory for bytecode
        sandbox: Enable sandbox
        mode: Mode (dev/prod)
    
    Returns:
        Configured TemplateEngine
    """
    # Create loader
    loader = TemplateLoader(search_paths=template_dirs)
    
    # Create bytecode cache
    if mode == "prod":
        bytecode_cache = CrousBytecodeCache(cache_dir=cache_dir)
    else:
        # Use in-memory cache for dev
        bytecode_cache = InMemoryBytecodeCache()
    
    # Create engine
    policy = SandboxPolicy.strict() if sandbox else None
    
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=bytecode_cache,
        sandbox=sandbox,
        sandbox_policy=policy
    )
    
    return engine


async def cmd_compile(
    template_dirs: Optional[list[str]] = None,
    output: str = "artifacts/templates.crous",
    mode: str = "prod",
    verbose: bool = False
):
    """
    Compile all templates to crous artifact.
    
    Args:
        template_dirs: Template directories to compile
        output: Output file path
        mode: Compilation mode (dev/prod)
        verbose: Verbose output
    """
    if not template_dirs:
        # Auto-discover template directories
        template_dirs = _discover_template_dirs()
    
    if not template_dirs:
        print("Error: No template directories found")
        print("Specify directories with --dirs or create templates/ directories")
        sys.exit(1)
    
    if verbose:
        print(f"Compiling templates from:")
        for dir in template_dirs:
            print(f"  - {dir}")
        print()
    
    # Create engine
    engine = create_template_engine_from_config(
        template_dirs=template_dirs,
        cache_dir=Path(output).parent,
        sandbox=True,
        mode=mode
    )
    
    # Create manager
    manager = TemplateManager(engine, engine.loader)
    
    # Compile
    try:
        result = await manager.compile_all(output_path=output)
        
        print(f"✓ Compiled {result['count']} templates")
        print(f"  Fingerprint: {result['fingerprint']}")
        print(f"  Output: {result['output']}")
        
        if verbose:
            print("\nCompiled templates:")
            for name in sorted(result['templates']):
                print(f"  - {name}")
        
        return 0
    
    except Exception as e:
        print(f"✗ Compilation failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


async def cmd_lint(
    template_dirs: Optional[list[str]] = None,
    strict: bool = True,
    json_output: bool = False,
    verbose: bool = False
):
    """
    Lint all templates.
    
    Args:
        template_dirs: Template directories to lint
        strict: Strict mode (treat warnings as errors)
        json_output: Output JSON format
        verbose: Verbose output
    """
    if not template_dirs:
        template_dirs = _discover_template_dirs()
    
    if not template_dirs:
        print("Error: No template directories found")
        sys.exit(1)
    
    # Create engine
    engine = create_template_engine_from_config(
        template_dirs=template_dirs,
        sandbox=True,
        mode="dev"
    )
    
    # Create manager
    manager = TemplateManager(engine, engine.loader)
    
    # Lint
    try:
        issues = await manager.lint_all(strict_undefined=strict)
        
        if json_output:
            # Output as JSON for LSP integration
            print(json.dumps([issue.to_dict() for issue in issues], indent=2))
            return 0 if not issues else 1
        
        # Human-readable output
        if not issues:
            print("✓ No issues found")
            return 0
        
        # Group by severity
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        info = [i for i in issues if i.severity == "info"]
        
        for issue in issues:
            print(issue)
        
        print()
        print(f"Found {len(issues)} issues:")
        print(f"  Errors: {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        print(f"  Info: {len(info)}")
        
        return 1 if errors or (strict and warnings) else 0
    
    except Exception as e:
        print(f"✗ Lint failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


async def cmd_inspect(
    template_name: str,
    template_dirs: Optional[list[str]] = None,
    verbose: bool = False
):
    """
    Inspect template metadata.
    
    Args:
        template_name: Template name to inspect
        template_dirs: Template directories
        verbose: Verbose output
    """
    if not template_dirs:
        template_dirs = _discover_template_dirs()
    
    if not template_dirs:
        print("Error: No template directories found")
        sys.exit(1)
    
    # Create engine
    engine = create_template_engine_from_config(
        template_dirs=template_dirs,
        mode="dev"
    )
    
    # Create manager
    manager = TemplateManager(engine, engine.loader)
    
    # Inspect
    try:
        info = await manager.inspect(template_name)
        
        if "error" in info:
            print(f"✗ {info['error']}")
            return 1
        
        print(f"Template: {info['name']}")
        print(f"  Path: {info['path']}")
        print(f"  Hash: {info['hash']}")
        print(f"  Size: {info['size']} bytes")
        print(f"  Modified: {info['mtime']}")
        print(f"  Compiled: {'yes' if info['compiled'] else 'no'}")
        print(f"  Cached: {'yes' if info['cached'] else 'no'}")
        
        return 0
    
    except Exception as e:
        print(f"✗ Inspect failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


async def cmd_clear_cache(
    template_name: Optional[str] = None,
    cache_dir: str = "artifacts",
    all_caches: bool = False,
    verbose: bool = False
):
    """
    Clear template cache.
    
    Args:
        template_name: Specific template to clear (None = all)
        cache_dir: Cache directory
        all_caches: Clear all cache types
        verbose: Verbose output
    """
    try:
        # Clear bytecode cache
        bytecode_cache = CrousBytecodeCache(cache_dir=cache_dir)
        
        if template_name:
            bytecode_cache.invalidate(template_name)
            print(f"✓ Cleared cache for {template_name}")
        else:
            bytecode_cache.clear()
            print("✓ Cleared all bytecode caches")
        
        bytecode_cache.save()
        
        return 0
    
    except Exception as e:
        print(f"✗ Clear cache failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def _discover_template_dirs() -> list[str]:
    """
    Auto-discover template directories.
    
    Looks for:
    - ./templates
    - ./modules/*/templates
    - ./myapp/modules/*/templates
    """
    dirs = []
    
    # Check common locations
    candidates = [
        Path("templates"),
        Path("myapp/templates"),
    ]
    
    # Check module directories
    for modules_dir in [Path("modules"), Path("myapp/modules")]:
        if modules_dir.exists():
            for module_dir in modules_dir.iterdir():
                if module_dir.is_dir():
                    templates_dir = module_dir / "templates"
                    if templates_dir.exists():
                        candidates.append(templates_dir)
    
    # Filter existing directories
    for path in candidates:
        if path.exists() and path.is_dir():
            dirs.append(str(path.absolute()))
    
    return dirs


# CLI entry points (for integration with aq command)

def compile_command(args):
    """Entry point for `aq templates compile`."""
    template_dirs = args.get("dirs")
    output = args.get("output", "artifacts/templates.crous")
    mode = args.get("mode", "prod")
    verbose = args.get("verbose", False)
    
    return asyncio.run(cmd_compile(
        template_dirs=template_dirs,
        output=output,
        mode=mode,
        verbose=verbose
    ))


def lint_command(args):
    """Entry point for `aq templates lint`."""
    template_dirs = args.get("dirs")
    strict = args.get("strict", True)
    json_output = args.get("json", False)
    verbose = args.get("verbose", False)
    
    return asyncio.run(cmd_lint(
        template_dirs=template_dirs,
        strict=strict,
        json_output=json_output,
        verbose=verbose
    ))


def inspect_command(args):
    """Entry point for `aq templates inspect`."""
    template_name = args.get("name")
    if not template_name:
        print("Error: Template name required")
        return 1
    
    template_dirs = args.get("dirs")
    verbose = args.get("verbose", False)
    
    return asyncio.run(cmd_inspect(
        template_name=template_name,
        template_dirs=template_dirs,
        verbose=verbose
    ))


def clear_cache_command(args):
    """Entry point for `aq templates clear-cache`."""
    template_name = args.get("template")
    cache_dir = args.get("cache_dir", "artifacts")
    all_caches = args.get("all", False)
    verbose = args.get("verbose", False)
    
    return asyncio.run(cmd_clear_cache(
        template_name=template_name,
        cache_dir=cache_dir,
        all_caches=all_caches,
        verbose=verbose
    ))


# Command registry for aq CLI
TEMPLATE_COMMANDS = {
    "compile": compile_command,
    "lint": lint_command,
    "inspect": inspect_command,
    "clear-cache": clear_cache_command,
}
