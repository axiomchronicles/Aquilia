"""
CLI command for module discovery inspection and validation.
Shows detailed information about auto-discovered modules including:
- Module metadata (version, description, tags, author)
- Dependencies and dependency ordering
- Module structure (services, controllers, middleware)
- Route conflicts and validation warnings
"""

import sys
from pathlib import Path
from typing import Optional
from aquilia.cli.generators.workspace import WorkspaceGenerator


class DiscoveryInspector:
    """Inspect and display auto-discovered modules."""
    
    def __init__(self, workspace_name: str, workspace_path: Optional[str] = None):
        self.workspace_name = workspace_name
        self.workspace_path = Path(workspace_path or workspace_name)
        self.generator = WorkspaceGenerator(workspace_name, self.workspace_path)
    
    def inspect(self, verbose: bool = False) -> None:
        """Run discovery inspection and display results."""
        discovered = self.generator._discover_modules()
        
        if not discovered:
            print(f"No modules discovered in {self.workspace_path}/modules")
            return
        
        # Validate modules
        validation = self.generator._validate_modules(discovered)
        
        # Resolve dependencies
        sorted_names = self.generator._resolve_dependencies(discovered)
        
        # Display summary
        self._print_summary(discovered, validation, sorted_names)
        
        if verbose:
            self._print_detailed_info(discovered, sorted_names)
    
    def _print_summary(self, discovered: dict, validation: dict, sorted_names: list) -> None:
        """Print summary of discovered modules."""
        print(f"\n📦 Module Discovery Report")
        print(f"{'='*60}")
        print(f"Workspace: {self.workspace_name}")
        print(f"Path: {self.workspace_path}")
        print(f"Modules Found: {len(discovered)}")
        print()
        
        # Module list
        print(f"{'Module':<20} {'Version':<12} {'Route':<20}")
        print(f"{'-'*20} {'-'*12} {'-'*20}")
        
        for mod_name in sorted_names:
            mod = discovered[mod_name]
            version = mod['version']
            route = mod['route_prefix']
            print(f"{mod_name:<20} {version:<12} {route:<20}")
        
        print()
        
        # Validation results
        if validation['warnings']:
            print(f"⚠️  Warnings ({len(validation['warnings'])}):")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        if validation['errors']:
            print(f"❌ Errors ({len(validation['errors'])}):")
            for error in validation['errors']:
                print(f"  - {error}")
        elif not validation['warnings']:
            print(f"✓ All modules valid - no issues detected")
        
        print()
    
    def _print_detailed_info(self, discovered: dict, sorted_names: list) -> None:
        """Print detailed information about each module."""
        print(f"\n{'='*60}")
        print(f"Detailed Module Information")
        print(f"{'='*60}\n")
        
        for mod_name in sorted_names:
            mod = discovered[mod_name]
            self._print_module_details(mod)
    
    def _print_module_details(self, mod: dict) -> None:
        """Print detailed information about a single module."""
        print(f"📌 {mod['name']}")
        print(f"   Version: {mod['version']}")
        print(f"   Description: {mod['description']}")
        print(f"   Route Prefix: {mod['route_prefix']}")
        print(f"   Base Path: {mod['base_path']}")
        
        if mod.get('author'):
            print(f"   Author: {mod['author']}")
        
        if mod.get('tags'):
            tags = ", ".join(mod['tags'])
            print(f"   Tags: {tags}")
        
        if mod.get('depends_on'):
            deps = ", ".join(mod['depends_on'])
            print(f"   Dependencies: {deps}")
        
        # Module structure
        structure = []
        if mod['has_services']:
            structure.append("services")
        if mod['has_controllers']:
            structure.append("controllers")
        if mod['has_middleware']:
            structure.append("middleware")
        
        if structure:
            print(f"   Components: {', '.join(structure)}")
        
        print()


def main():
    """CLI entry point for discovery command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Inspect auto-discovered modules in workspace"
    )
    parser.add_argument(
        "workspace",
        help="Workspace name or path"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed module information"
    )
    parser.add_argument(
        "--path",
        help="Workspace path (defaults to workspace name)"
    )
    
    args = parser.parse_args()
    
    try:
        inspector = DiscoveryInspector(args.workspace, args.path)
        inspector.inspect(verbose=args.verbose)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
