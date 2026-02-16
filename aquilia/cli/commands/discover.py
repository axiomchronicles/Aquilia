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
from ..utils.colors import (
    success, error, info, warning, dim, bold,
    section, kv, rule, table, banner, _CHECK, _CROSS,
)


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
        banner("Module Discovery Report")
        kv("Workspace", self.workspace_name)
        kv("Path", str(self.workspace_path))
        kv("Modules Found", str(len(discovered)))

        import click
        click.echo()
        table(
            headers=["Module", "Version", "Route"],
            rows=[
                (mod_name, discovered[mod_name]['version'], discovered[mod_name]['route_prefix'])
                for mod_name in sorted_names
            ],
            col_widths=[20, 12, 20],
        )
        click.echo()

        # Validation results
        if validation['warnings']:
            warning(f"  Warnings ({len(validation['warnings'])}):") 
            for w in validation['warnings']:
                dim(f"    - {w}")
        
        if validation['errors']:
            error(f"  {_CROSS} Errors ({len(validation['errors'])}):") 
            for e in validation['errors']:
                dim(f"    - {e}")
        elif not validation['warnings']:
            success(f"  {_CHECK} All modules valid - no issues detected")

        import click
        click.echo()

    def _print_detailed_info(self, discovered: dict, sorted_names: list) -> None:
        """Print detailed information about each module."""
        import click
        click.echo()
        section("Detailed Module Information")
        click.echo()

        for mod_name in sorted_names:
            mod = discovered[mod_name]
            self._print_module_details(mod)

    def _print_module_details(self, mod: dict) -> None:
        """Print detailed information about a single module."""
        import click
        bold(f"  {mod['name']}")
        kv("Version", mod['version'], key_width=16)
        kv("Description", mod['description'], key_width=16)
        kv("Route Prefix", mod['route_prefix'], key_width=16)
        kv("Base Path", str(mod['base_path']), key_width=16)

        if mod.get('author'):
            kv("Author", mod['author'], key_width=16)

        if mod.get('tags'):
            kv("Tags", ", ".join(mod['tags']), key_width=16)

        if mod.get('depends_on'):
            kv("Dependencies", ", ".join(mod['depends_on']), key_width=16)

        # Module structure
        structure = []
        if mod['has_services']:
            structure.append("services")
        if mod['has_controllers']:
            structure.append("controllers")
        if mod['has_middleware']:
            structure.append("middleware")

        if structure:
            kv("Components", ", ".join(structure), key_width=16)

        click.echo()


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
