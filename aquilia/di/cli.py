"""
CLI commands for DI system.

Commands:
- aq di-check: Validate DI configuration
- aq di-tree: Show dependency tree
- aq di-graph: Export dependency graph
- aq di-profile: Benchmark DI performance
"""

import sys
import argparse
import asyncio
import time
from pathlib import Path
from typing import List, Any, Optional
import json


def load_manifests_from_settings(settings_path: str) -> tuple[List[Any], Any]:
    """
    Load manifests and config from settings file.
    
    Returns:
        Tuple of (manifests, config)
    """
    sys.path.insert(0, str(Path(settings_path).parent))
    
    # Import settings
    module_name = Path(settings_path).stem
    settings = __import__(module_name)
    
    manifests = getattr(settings, "AQ_APPS", [])
    
    # Load config
    from aquilia.config import ConfigLoader
    config = ConfigLoader.load(
        paths=[str(Path(settings_path).parent / "config" / "*.py")],
        env_file=str(Path(settings_path).parent / ".env"),
    )
    
    return manifests, config


def cmd_di_check(args):
    """
    Validate DI configuration (static analysis).
    
    Checks:
    - All providers resolvable
    - No cycles (unless allow_lazy)
    - No scope violations
    - Cross-app dependencies declared
    """
    print("🔍 Checking DI configuration...")
    
    try:
        manifests, config = load_manifests_from_settings(args.settings)
        
        from aquilia.di import Registry
        from aquilia.di.errors import DIError, DependencyCycleError, ScopeViolationError
        
        # Build registry with validation
        try:
            registry = Registry.from_manifests(
                manifests,
                config=config,
                enforce_cross_app=not args.no_cross_app_check,
            )
            
            print("✅ DI configuration is valid!")
            
            # Show summary
            provider_count = len(registry._providers)
            print(f"\n📊 Summary:")
            print(f"  - Providers: {provider_count}")
            
            # Count by scope
            from collections import Counter
            scopes = Counter(p.meta.scope for p in registry._providers)
            for scope, count in scopes.items():
                print(f"  - {scope}: {count}")
            
            return 0
            
        except DependencyCycleError as e:
            print(f"❌ Dependency cycle detected:")
            print(f"   {e}")
            if not args.quiet:
                print(f"\n💡 Suggestion: Use allow_lazy=True in manifest to break cycle")
            return 1
            
        except ScopeViolationError as e:
            print(f"❌ Scope violation:")
            print(f"   {e}")
            return 1
            
        except DIError as e:
            print(f"❌ DI error:")
            print(f"   {e}")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_di_tree(args):
    """
    Show dependency tree.
    
    Displays provider dependencies as a tree.
    """
    print("🌳 Dependency Tree\n")
    
    try:
        manifests, config = load_manifests_from_settings(args.settings)
        
        from aquilia.di import Registry
        from aquilia.di.graph import DependencyGraph
        
        registry = Registry.from_manifests(manifests, config=config)
        
        # Build graph
        graph = DependencyGraph()
        for provider in registry._providers:
            deps = registry._graph.get(provider.meta.token, [])
            graph.add_provider(provider, deps)
        
        # Get tree view
        if args.root:
            tree = graph.get_tree_view(root=args.root)
        else:
            tree = graph.get_tree_view()
        
        print(tree)
        
        # Save to file if requested
        if args.out:
            Path(args.out).write_text(tree)
            print(f"\n💾 Saved to {args.out}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_di_graph(args):
    """
    Export dependency graph as Graphviz DOT.
    
    Useful for visualization with `dot -Tpng graph.dot -o graph.png`.
    """
    print("📊 Exporting dependency graph...")
    
    try:
        manifests, config = load_manifests_from_settings(args.settings)
        
        from aquilia.di import Registry
        from aquilia.di.graph import DependencyGraph
        
        registry = Registry.from_manifests(manifests, config=config)
        
        # Build graph
        graph = DependencyGraph()
        for provider in registry._providers:
            deps = registry._graph.get(provider.meta.token, [])
            graph.add_provider(provider, deps)
        
        # Export DOT
        dot = graph.export_dot()
        
        # Save to file
        out_path = Path(args.out)
        out_path.write_text(dot)
        
        print(f"✅ Graph exported to {args.out}")
        print(f"\n💡 Visualize with: dot -Tpng {args.out} -o graph.png")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_di_profile(args):
    """
    Benchmark DI performance.
    
    Measures:
    - Cold container build time
    - Hot path resolve latency (cached)
    - New instance creation time
    - Pool acquire/release latency
    """
    print("⚡ Profiling DI performance...\n")
    
    async def run_benchmarks():
        try:
            manifests, config = load_manifests_from_settings(args.settings)
            
            from aquilia.di import Registry
            
            # Benchmark 1: Registry build
            print("1️⃣  Registry build (cold):")
            start = time.perf_counter()
            registry = Registry.from_manifests(manifests, config=config)
            build_time = time.perf_counter() - start
            print(f"   ⏱️  {build_time*1000:.2f}ms")
            
            # Benchmark 2: Container build
            print("\n2️⃣  Container build:")
            start = time.perf_counter()
            container = registry.build_container()
            container_time = time.perf_counter() - start
            print(f"   ⏱️  {container_time*1000:.2f}ms")
            
            # Benchmark 3: Cached resolution
            if args.bench:
                print(f"\n3️⃣  Cached resolution ({args.runs} iterations):")
                
                # Resolve once to populate cache
                if registry._providers:
                    first_token = list(registry._providers)[0]
                    await container.resolve_async(first_token.meta.token)
                    
                    # Benchmark cached lookups
                    times = []
                    for _ in range(args.runs):
                        start = time.perf_counter()
                        await container.resolve_async(first_token.meta.token)
                        times.append(time.perf_counter() - start)
                    
                    # Statistics
                    avg_time = sum(times) / len(times)
                    median_time = sorted(times)[len(times)//2]
                    p95_time = sorted(times)[int(len(times)*0.95)]
                    
                    print(f"   ⏱️  Average: {avg_time*1_000_000:.2f}µs")
                    print(f"   ⏱️  Median:  {median_time*1_000_000:.2f}µs")
                    print(f"   ⏱️  P95:     {p95_time*1_000_000:.2f}µs")
                    
                    # Check against target (<3µs)
                    if median_time * 1_000_000 < 3:
                        print(f"   ✅ Target <3µs: PASSED")
                    else:
                        print(f"   ⚠️  Target <3µs: FAILED")
            
            print("\n✅ Profiling complete!")
            
            # Summary
            print(f"\n📊 Summary:")
            print(f"  - Registry build: {build_time*1000:.2f}ms")
            print(f"  - Container build: {container_time*1000:.2f}ms")
            print(f"  - Providers: {len(registry._providers)}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    return asyncio.run(run_benchmarks())


def cmd_di_manifest(args):
    """
    Generate di_manifest.json for LSP integration.
    
    Contains provider metadata for IDE features:
    - Hover information
    - Autocomplete for Inject tags
    - "Find provider" navigation
    """
    print("📄 Generating di_manifest.json...")
    
    try:
        manifests, config = load_manifests_from_settings(args.settings)
        
        from aquilia.di import Registry
        
        registry = Registry.from_manifests(manifests, config=config)
        
        # Build manifest
        manifest_data = {
            "version": "1.0",
            "providers": [
                provider.meta.to_dict()
                for provider in registry._providers
            ],
            "graph": {
                token: deps
                for token, deps in registry._graph.items()
            },
        }
        
        # Save to file
        out_path = Path(args.out)
        out_path.write_text(json.dumps(manifest_data, indent=2))
        
        print(f"✅ Manifest exported to {args.out}")
        print(f"   {len(manifest_data['providers'])} providers")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def setup_di_commands(subparsers):
    """
    Setup DI subcommands.
    
    Args:
        subparsers: ArgumentParser subparsers object
    """
    # di-check command
    parser_check = subparsers.add_parser(
        "di-check",
        help="Validate DI configuration",
    )
    parser_check.add_argument(
        "--settings",
        required=True,
        help="Path to settings file",
    )
    parser_check.add_argument(
        "--no-cross-app-check",
        action="store_true",
        help="Skip cross-app dependency validation",
    )
    parser_check.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress suggestions",
    )
    parser_check.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed errors",
    )
    parser_check.set_defaults(func=cmd_di_check)
    
    # di-tree command
    parser_tree = subparsers.add_parser(
        "di-tree",
        help="Show dependency tree",
    )
    parser_tree.add_argument(
        "--settings",
        required=True,
        help="Path to settings file",
    )
    parser_tree.add_argument(
        "--root",
        help="Root provider token to start tree from",
    )
    parser_tree.add_argument(
        "--out",
        help="Output file path",
    )
    parser_tree.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed errors",
    )
    parser_tree.set_defaults(func=cmd_di_tree)
    
    # di-graph command
    parser_graph = subparsers.add_parser(
        "di-graph",
        help="Export dependency graph as DOT",
    )
    parser_graph.add_argument(
        "--settings",
        required=True,
        help="Path to settings file",
    )
    parser_graph.add_argument(
        "--out",
        required=True,
        help="Output DOT file path",
    )
    parser_graph.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed errors",
    )
    parser_graph.set_defaults(func=cmd_di_graph)
    
    # di-profile command
    parser_profile = subparsers.add_parser(
        "di-profile",
        help="Benchmark DI performance",
    )
    parser_profile.add_argument(
        "--settings",
        required=True,
        help="Path to settings file",
    )
    parser_profile.add_argument(
        "--bench",
        default="resolve",
        help="Benchmark to run (resolve, pool_acquire)",
    )
    parser_profile.add_argument(
        "--runs",
        type=int,
        default=1000,
        help="Number of iterations",
    )
    parser_profile.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed errors",
    )
    parser_profile.set_defaults(func=cmd_di_profile)
    
    # di-manifest command
    parser_manifest = subparsers.add_parser(
        "di-manifest",
        help="Generate di_manifest.json for LSP",
    )
    parser_manifest.add_argument(
        "--settings",
        required=True,
        help="Path to settings file",
    )
    parser_manifest.add_argument(
        "--out",
        default="di_manifest.json",
        help="Output manifest file path",
    )
    parser_manifest.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed errors",
    )
    parser_manifest.set_defaults(func=cmd_di_manifest)
