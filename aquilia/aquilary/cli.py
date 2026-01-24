"""
Aquilary CLI commands for manifest validation, inspection, and deployment.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional, Any
import importlib.util


def load_config(config_path: Optional[str]) -> Any:
    """
    Load config from Python file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Config object
    """
    if not config_path:
        return None
    
    path = Path(config_path)
    if not path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    # Import config module
    spec = importlib.util.spec_from_file_location("config", path)
    if spec is None or spec.loader is None:
        print(f"❌ Cannot load config from {config_path}")
        sys.exit(1)
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Find Config class
    for name, obj in vars(module).items():
        if isinstance(obj, type) and name == "Config":
            return obj()
    
    print(f"❌ No Config class found in {config_path}")
    sys.exit(1)


def cmd_validate(args: argparse.Namespace) -> None:
    """
    Validate manifests.
    
    Usage:
        aquilary validate apps/*/manifest.py --config config.py --mode prod
    """
    from aquilia.aquilary import Aquilary, ManifestValidationError
    
    print(f"🔍 Validating manifests in mode: {args.mode}")
    print(f"   Manifests: {', '.join(args.manifests)}")
    
    # Load config
    config = load_config(args.config)
    
    try:
        # Build registry (validation happens automatically)
        registry = Aquilary.from_manifests(
            manifests=args.manifests,
            config=config,
            mode=args.mode,
            allow_fs_autodiscovery=args.autodiscover,
        )
        
        print(f"\n✅ Validation passed!")
        print(f"   Apps: {len(registry.app_contexts)}")
        print(f"   Fingerprint: {registry.fingerprint[:16]}...")
        
        # Show load order
        print(f"\n📦 Load Order:")
        for ctx in registry.app_contexts:
            deps = f" (→ {', '.join(ctx.depends_on)})" if ctx.depends_on else ""
            print(f"   {ctx.load_order + 1}. {ctx.name} v{ctx.version}{deps}")
        
        # Show warnings if any
        if registry._validation_report.get('warning_count', 0) > 0:
            print(f"\n⚠️  Warnings:")
            for warning in registry._validation_report.get('warnings', []):
                print(f"   - {warning}")
        
        sys.exit(0)
        
    except ManifestValidationError as e:
        print(f"\n❌ Validation failed!")
        print(f"\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_inspect(args: argparse.Namespace) -> None:
    """
    Inspect registry and show diagnostics.
    
    Usage:
        aquilary inspect --manifests apps/*/manifest.py --config config.py
    """
    from aquilia.aquilary import Aquilary
    
    print(f"🔍 Inspecting registry...")
    
    # Load config
    config = load_config(args.config)
    
    # Build registry
    registry = Aquilary.from_manifests(
        manifests=args.manifests,
        config=config,
        mode=args.mode,
        allow_fs_autodiscovery=args.autodiscover,
    )
    
    # Get diagnostics
    diagnostics = registry.inspect()
    
    # Display
    print(f"\n{'='*70}")
    print(f"Registry Diagnostics")
    print(f"{'='*70}")
    
    print(f"\n📊 Summary:")
    print(f"   Fingerprint: {diagnostics['fingerprint']}")
    print(f"   Mode: {diagnostics['mode']}")
    print(f"   App Count: {diagnostics['app_count']}")
    
    print(f"\n📦 Applications:")
    for app in diagnostics['apps']:
        print(f"\n   {app['name']} v{app['version']}")
        print(f"      Load Order: {app['load_order']}")
        print(f"      Controllers: {app['controllers']}")
        print(f"      Services: {app['services']}")
        print(f"      Dependencies: {', '.join(app['depends_on']) if app['depends_on'] else 'none'}")
    
    print(f"\n🔗 Dependency Graph:")
    for app_name, deps in diagnostics['dependency_graph'].items():
        deps_str = ', '.join(deps) if deps else 'none'
        print(f"   {app_name}: {deps_str}")
    
    if args.json:
        # Export as JSON
        output_path = args.json
        Path(output_path).write_text(json.dumps(diagnostics, indent=2))
        print(f"\n💾 Diagnostics exported to: {output_path}")


def cmd_freeze(args: argparse.Namespace) -> None:
    """
    Freeze manifest for reproducible deploys.
    
    Usage:
        aquilary freeze --manifests apps/*/manifest.py --config config.py --output frozen.json
    """
    from aquilia.aquilary import Aquilary
    
    print(f"🧊 Freezing manifest...")
    
    # Load config
    config = load_config(args.config)
    
    # Build registry
    registry = Aquilary.from_manifests(
        manifests=args.manifests,
        config=config,
        mode="prod",  # Always freeze in prod mode
        allow_fs_autodiscovery=args.autodiscover,
    )
    
    # Export frozen manifest
    output_path = args.output or "frozen_manifest.json"
    registry.export_manifest(output_path)
    
    print(f"\n✅ Frozen manifest exported!")
    print(f"   Path: {output_path}")
    print(f"   Fingerprint: {registry.fingerprint}")
    print(f"   Apps: {len(registry.app_contexts)}")
    
    print(f"\n📋 Apps included:")
    for ctx in registry.app_contexts:
        print(f"   - {ctx.name} v{ctx.version}")
    
    print(f"\n💡 Usage in production:")
    print(f"   1. Commit {output_path} to version control")
    print(f"   2. Deploy with: aquilary run --frozen {output_path}")
    print(f"   3. Verify fingerprint matches: {registry.fingerprint}")


def cmd_graph(args: argparse.Namespace) -> None:
    """
    Visualize dependency graph.
    
    Usage:
        aquilary graph --manifests apps/*/manifest.py --output graph.dot
    """
    from aquilia.aquilary import Aquilary
    
    print(f"📊 Generating dependency graph...")
    
    # Load config
    config = load_config(args.config)
    
    # Build registry
    registry = Aquilary.from_manifests(
        manifests=args.manifests,
        config=config,
        mode=args.mode,
        allow_fs_autodiscovery=args.autodiscover,
    )
    
    # Build dependency graph
    from aquilia.aquilary import DependencyGraph
    
    graph = DependencyGraph()
    for ctx in registry.app_contexts:
        graph.add_node(ctx.name, ctx.depends_on)
    
    # Export as DOT
    dot = graph.to_dot()
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(dot)
        print(f"\n✅ Graph exported to: {output_path}")
        print(f"\n💡 Visualize with:")
        print(f"   dot -Tpng {output_path} -o {output_path.stem}.png")
        print(f"   Or view at: https://dreampuf.github.io/GraphvizOnline/")
    else:
        print(f"\n{dot}")
    
    # Show layers
    layers = graph.get_layers()
    print(f"\n⚡ Parallel Loading Layers:")
    for i, layer in enumerate(layers, 1):
        print(f"   Layer {i}: {', '.join(layer)}")


def cmd_run(args: argparse.Namespace) -> None:
    """
    Run application with registry.
    
    Usage:
        aquilary run --frozen frozen.json --config config.py
    """
    from aquilia.aquilary import Aquilary
    
    print(f"🚀 Starting application...")
    
    # Load config
    config = load_config(args.config)
    
    # Build registry
    if args.frozen:
        print(f"   Loading from frozen manifest: {args.frozen}")
        registry = Aquilary.from_manifests(
            manifests=[],
            config=config,
            mode="prod",
            freeze_manifest_path=args.frozen,
        )
    else:
        print(f"   Loading from manifests...")
        registry = Aquilary.from_manifests(
            manifests=args.manifests,
            config=config,
            mode=args.mode,
            allow_fs_autodiscovery=args.autodiscover,
        )
    
    print(f"\n✅ Registry loaded:")
    print(f"   Fingerprint: {registry.fingerprint}")
    print(f"   Apps: {len(registry.app_contexts)}")
    
    # Build runtime
    print(f"\n🔨 Building runtime...")
    runtime = registry.build_runtime()
    
    # Compile routes
    print(f"   Compiling routes...")
    runtime.compile_routes()
    
    print(f"\n✅ Runtime ready!")
    print(f"\n💡 Next: Start server with runtime instance")
    
    # In real implementation, this would start the server
    # For now, just show what would happen
    print(f"\n📦 Startup sequence:")
    for ctx in registry.app_contexts:
        print(f"   {ctx.load_order + 1}. Starting {ctx.name}...")
        if ctx.on_startup:
            ctx.on_startup()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="aquilary",
        description="Aquilary - Manifest-driven App Registry for Aquilia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate manifests
  aquilary validate apps/*/manifest.py --config config.py --mode prod
  
  # Inspect registry
  aquilary inspect --manifests apps/*/manifest.py --json diagnostics.json
  
  # Freeze for deploy
  aquilary freeze --manifests apps/*/manifest.py --output frozen.json
  
  # Visualize graph
  aquilary graph --manifests apps/*/manifest.py --output graph.dot
  
  # Run with frozen manifest
  aquilary run --frozen frozen.json --config config.py
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate manifests",
    )
    validate_parser.add_argument(
        "manifests",
        nargs="+",
        help="Manifest files or directories",
    )
    validate_parser.add_argument(
        "--config",
        help="Config file path",
    )
    validate_parser.add_argument(
        "--mode",
        choices=["dev", "prod", "test"],
        default="prod",
        help="Registry mode",
    )
    validate_parser.add_argument(
        "--autodiscover",
        action="store_true",
        help="Auto-discover manifests in apps/",
    )
    
    # Inspect command
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect registry diagnostics",
    )
    inspect_parser.add_argument(
        "--manifests",
        nargs="+",
        default=[],
        help="Manifest files or directories",
    )
    inspect_parser.add_argument(
        "--config",
        help="Config file path",
    )
    inspect_parser.add_argument(
        "--mode",
        choices=["dev", "prod", "test"],
        default="dev",
        help="Registry mode",
    )
    inspect_parser.add_argument(
        "--autodiscover",
        action="store_true",
        help="Auto-discover manifests in apps/",
    )
    inspect_parser.add_argument(
        "--json",
        help="Export diagnostics to JSON file",
    )
    
    # Freeze command
    freeze_parser = subparsers.add_parser(
        "freeze",
        help="Freeze manifest for deployment",
    )
    freeze_parser.add_argument(
        "--manifests",
        nargs="+",
        default=[],
        help="Manifest files or directories",
    )
    freeze_parser.add_argument(
        "--config",
        help="Config file path",
    )
    freeze_parser.add_argument(
        "--output",
        help="Output file path (default: frozen_manifest.json)",
    )
    freeze_parser.add_argument(
        "--autodiscover",
        action="store_true",
        help="Auto-discover manifests in apps/",
    )
    
    # Graph command
    graph_parser = subparsers.add_parser(
        "graph",
        help="Visualize dependency graph",
    )
    graph_parser.add_argument(
        "--manifests",
        nargs="+",
        default=[],
        help="Manifest files or directories",
    )
    graph_parser.add_argument(
        "--config",
        help="Config file path",
    )
    graph_parser.add_argument(
        "--mode",
        choices=["dev", "prod", "test"],
        default="dev",
        help="Registry mode",
    )
    graph_parser.add_argument(
        "--output",
        help="Output DOT file path",
    )
    graph_parser.add_argument(
        "--autodiscover",
        action="store_true",
        help="Auto-discover manifests in apps/",
    )
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run application with registry",
    )
    run_parser.add_argument(
        "--frozen",
        help="Frozen manifest file path",
    )
    run_parser.add_argument(
        "--manifests",
        nargs="*",
        default=[],
        help="Manifest files (if not using frozen)",
    )
    run_parser.add_argument(
        "--config",
        required=True,
        help="Config file path",
    )
    run_parser.add_argument(
        "--mode",
        choices=["dev", "prod", "test"],
        default="prod",
        help="Registry mode",
    )
    run_parser.add_argument(
        "--autodiscover",
        action="store_true",
        help="Auto-discover manifests in apps/",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to command handler
    commands = {
        "validate": cmd_validate,
        "inspect": cmd_inspect,
        "freeze": cmd_freeze,
        "graph": cmd_graph,
        "run": cmd_run,
    }
    
    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
