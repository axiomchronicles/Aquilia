"""
Aquilia CLI integration for enhanced auto-discovery commands.
Provides convenient shortcuts for module discovery, inspection, and analytics.
"""

import sys
from pathlib import Path
from typing import Optional
from aquilia.cli.commands.discover import DiscoveryInspector
from aquilia.cli.commands.analytics import DiscoveryAnalytics, print_analysis_report


class DiscoveryCLI:
    """CLI interface for discovery operations."""
    
    @staticmethod
    def discover(workspace: str, path: Optional[str] = None, verbose: bool = False) -> None:
        """Discover and list all modules."""
        try:
            inspector = DiscoveryInspector(workspace, path or workspace)
            inspector.inspect(verbose=verbose)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    @staticmethod
    def analyze(workspace: str, path: Optional[str] = None) -> None:
        """Run analytics on discovered modules."""
        try:
            analytics = DiscoveryAnalytics(workspace, path or workspace)
            analysis = analytics.analyze()
            print_analysis_report(analysis)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    @staticmethod
    def validate(workspace: str, path: Optional[str] = None) -> None:
        """Validate all discovered modules."""
        try:
            inspector = DiscoveryInspector(workspace, path or workspace)
            generator = inspector.generator
            discovered = generator._discover_modules()
            validation = generator._validate_modules(discovered)
            
            print(f"\n✓ Module Validation Report")
            print(f"{'='*60}")
            print(f"Workspace: {workspace}")
            print(f"Modules Checked: {len(discovered)}")
            print()
            
            if validation['errors']:
                print(f"❌ Errors ({len(validation['errors'])}):")
                for error in validation['errors']:
                    print(f"  - {error}")
                print()
            
            if validation['warnings']:
                print(f"⚠️  Warnings ({len(validation['warnings'])}):")
                for warning in validation['warnings']:
                    print(f"  - {warning}")
                print()
            
            if validation['valid']:
                print(f"✓ All modules valid!")
            else:
                print(f"✗ Validation failed!")
                sys.exit(1)
        
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    @staticmethod
    def dependencies(workspace: str, path: Optional[str] = None) -> None:
        """Show module dependency graph."""
        try:
            inspector = DiscoveryInspector(workspace, path or workspace)
            generator = inspector.generator
            discovered = generator._discover_modules()
            sorted_mods = generator._resolve_dependencies(discovered)
            
            print(f"\n📊 Module Dependency Graph")
            print(f"{'='*60}")
            print(f"Workspace: {workspace}")
            print(f"Load Order:")
            print()
            
            for i, mod_name in enumerate(sorted_mods, 1):
                mod = discovered[mod_name]
                deps = mod.get('depends_on', [])
                
                if deps:
                    deps_str = " → ".join(deps)
                    print(f"  {i}. {mod_name} (depends on: {deps_str})")
                else:
                    print(f"  {i}. {mod_name} (no dependencies)")
            
            print()
            print(f"{'='*60}\n")
        
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Aquilia module auto-discovery CLI"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Discovery commands')
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='List discovered modules')
    discover_parser.add_argument('workspace', help='Workspace name')
    discover_parser.add_argument('--path', help='Workspace path')
    discover_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    discover_parser.set_defaults(func=lambda args: DiscoveryCLI.discover(
        args.workspace, args.path, args.verbose
    ))
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze modules')
    analyze_parser.add_argument('workspace', help='Workspace name')
    analyze_parser.add_argument('--path', help='Workspace path')
    analyze_parser.set_defaults(func=lambda args: DiscoveryCLI.analyze(
        args.workspace, args.path
    ))
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate modules')
    validate_parser.add_argument('workspace', help='Workspace name')
    validate_parser.add_argument('--path', help='Workspace path')
    validate_parser.set_defaults(func=lambda args: DiscoveryCLI.validate(
        args.workspace, args.path
    ))
    
    # Dependencies command
    deps_parser = subparsers.add_parser('deps', help='Show dependency graph')
    deps_parser.add_argument('workspace', help='Workspace name')
    deps_parser.add_argument('--path', help='Workspace path')
    deps_parser.set_defaults(func=lambda args: DiscoveryCLI.dependencies(
        args.workspace, args.path
    ))
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
