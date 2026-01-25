"""Aquilate CLI - Main Entry Point.

The `aq` command provides manifest-driven project orchestration.

Commands:
    init     - Create new workspace or module
    add      - Add module to workspace
    generate - Generate controllers and services
    validate - Static validation of manifests
    compile  - Compile manifests to artifacts
    run      - Development server with hot-reload
    serve    - Production server (immutable)
    freeze   - Generate immutable artifacts
    inspect  - Query compiled artifacts
    migrate  - Convert legacy Django-style projects
    doctor   - Diagnose workspace issues
    version  - Show version information
"""

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__, __cli_name__
from .utils.colors import success, error, info, warning


@click.group()
@click.version_option(version=__version__, prog_name=__cli_name__)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.pass_context
def cli(ctx, verbose: bool, quiet: bool):
    """
    Aquilate - Aquilia Native CLI.
    
    Manifest-driven, artifact-first project orchestration.
    
    Examples:
      aq init workspace my-api
      aq add module users
      aq validate
      aq compile
      aq run
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet


# ============================================================================
# Commands
# ============================================================================

@cli.group()
def init():
    """Initialize new workspace or module."""
    pass


@init.command('workspace')
@click.argument('name')
@click.option('--minimal', is_flag=True, help='Minimal setup (no examples)')
@click.option('--template', type=str, help='Use template (api, service, monolith)')
@click.pass_context
def init_workspace(ctx, name: str, minimal: bool, template: Optional[str]):
    """
    Create a new Aquilia workspace.
    
    Examples:
      aq init workspace my-api
      aq init workspace my-api --minimal
      aq init workspace my-api --template=api
    """
    from .commands.init import create_workspace
    
    try:
        workspace_path = create_workspace(
            name=name,
            minimal=minimal,
            template=template,
            verbose=ctx.obj['verbose'],
        )
        
        if not ctx.obj['quiet']:
            success(f"✓ Created workspace '{name}'")
            info(f"  Location: {workspace_path}")
            info(f"\nNext steps:")
            info(f"  cd {name}")
            info(f"  aq add module <module_name>")
            info(f"  aq run")
    
    except Exception as e:
        error(f"✗ Failed to create workspace: {e}")
        sys.exit(1)




@cli.group()
def generate():
    """Generate code from templates."""
    pass


@generate.command('controller')
@click.argument('name')
@click.option('--prefix', type=str, help='Route prefix (default: /name)')
@click.option('--resource', type=str, help='Resource name (default: name)')
@click.option('--simple', is_flag=True, help='Generate simple controller')
@click.option('--with-lifecycle', is_flag=True, help='Include lifecycle hooks')
@click.option('--test', is_flag=True, help='Generate test/demo controller')
@click.option('--output', type=click.Path(), help='Output directory')
@click.pass_context
def generate_controller(ctx, name: str, prefix: Optional[str], resource: Optional[str], simple: bool, with_lifecycle: bool, test: bool, output: Optional[str]):
    """
    Generate a new controller.
    
    Examples:
      aq generate controller Users
      aq generate controller Products --prefix=/api/products
      aq generate controller Health --simple
      aq generate controller Admin --with-lifecycle
      aq generate controller Test --test
      aq generate controller Admin --output=apps/admin/
    """
    from .generators.controller import generate_controller as _generate_controller
    
    try:
        file_path = _generate_controller(
            name=name,
            output_dir=output or 'controllers',
            prefix=prefix,
            resource=resource,
            simple=simple,
            with_lifecycle=with_lifecycle,
            test=test,
        )
        
        if not ctx.obj['quiet']:
            success(f"✓ Generated controller '{name}'")
            info(f"  Location: {file_path}")
            if with_lifecycle:
                info(f"  Includes: Lifecycle hooks (on_startup, on_request, on_response)")
            if test:
                info(f"  Type: Test/Demo controller")
            info(f"\nNext steps:")
            info(f"  1. Add to manifest: controllers = ['{file_path.parent.name}.{file_path.stem}:{name}Controller']")
            info(f"  2. Implement your business logic")
            info(f"  3. Run: aq run")
    
    except Exception as e:
        error(f"✗ Failed to generate controller: {e}")
        sys.exit(1)


@cli.command('validate')
@click.option('--strict', is_flag=True, help='Strict validation (prod-level)')
@click.option('--module', type=str, help='Validate single module')
@click.pass_context
def validate(ctx, strict: bool, module: Optional[str]):
    """
    Validate workspace manifests.
    
    Examples:
      aq validate
      aq validate --strict
      aq validate --module=users
    """
    from .commands.validate import validate_workspace
    
    try:
        result = validate_workspace(
            strict=strict,
            module_filter=module,
            verbose=ctx.obj['verbose'],
        )
        
        if not ctx.obj['quiet']:
            if result.is_valid:
                success(f"✓ Validation passed")
                info(f"  Modules: {result.module_count}")
                info(f"  Routes: {result.route_count}")
                info(f"  DI providers: {result.provider_count}")
            else:
                error(f"✗ Validation failed")
                for fault in result.faults:
                    error(f"  - {fault}")
                sys.exit(1)
    
    except Exception as e:
        error(f"✗ Validation error: {e}")
        sys.exit(1)


@cli.command('compile')
@click.option('--watch', is_flag=True, help='Watch for changes')
@click.option('--output', type=click.Path(), help='Output directory')
@click.pass_context
def compile(ctx, watch: bool, output: Optional[str]):
    """
    Compile manifests to artifacts.
    
    Examples:
      aq compile
      aq compile --watch
      aq compile --output=dist/
    """
    from .commands.compile import compile_workspace
    
    try:
        artifacts = compile_workspace(
            output_dir=output,
            watch=watch,
            verbose=ctx.obj['verbose'],
        )
        
        if not ctx.obj['quiet']:
            success(f"✓ Compilation complete")
            info(f"  Artifacts: {len(artifacts)}")
            for artifact in artifacts:
                info(f"    - {artifact}")
    
    except Exception as e:
        error(f"✗ Compilation failed: {e}")
        sys.exit(1)


@cli.command('run')
@click.option('--mode', type=click.Choice(['dev', 'test']), default='dev', help='Runtime mode')
@click.option('--port', type=int, default=8000, help='Server port')
@click.option('--host', type=str, default='127.0.0.1', help='Server host')
@click.option('--reload/--no-reload', default=True, help='Enable hot-reload')
@click.pass_context
def run(ctx, mode: str, port: int, host: str, reload: bool):
    """
    Start development server.
    
    Examples:
      aq run
      aq run --port=3000
      aq run --mode=test --no-reload
    """
    from .commands.run import run_dev_server
    
    try:
        run_dev_server(
            mode=mode,
            host=host,
            port=port,
            reload=reload,
            verbose=ctx.obj['verbose'],
        )
    
    except KeyboardInterrupt:
        if not ctx.obj['quiet']:
            info("\n✓ Server stopped")
    except Exception as e:
        error(f"✗ Server error: {e}")
        sys.exit(1)


@cli.command('serve')
@click.option('--workers', type=int, default=1, help='Number of workers')
@click.option('--bind', type=str, default='0.0.0.0:8000', help='Bind address')
@click.pass_context
def serve(ctx, workers: int, bind: str):
    """
    Start production server (requires frozen artifacts).
    
    Examples:
      aq serve
      aq serve --workers=4
      aq serve --bind=0.0.0.0:8080
    """
    from .commands.serve import serve_production
    
    try:
        serve_production(
            workers=workers,
            bind=bind,
            verbose=ctx.obj['verbose'],
        )
    
    except KeyboardInterrupt:
        if not ctx.obj['quiet']:
            info("\n✓ Server stopped")
    except Exception as e:
        error(f"✗ Server error: {e}")
        sys.exit(1)


@cli.command('freeze')
@click.option('--output', type=click.Path(), help='Output directory')
@click.option('--sign', is_flag=True, help='Sign artifacts')
@click.pass_context
def freeze(ctx, output: Optional[str], sign: bool):
    """
    Generate immutable artifacts for production.
    
    Examples:
      aq freeze
      aq freeze --output=dist/
      aq freeze --sign
    """
    from .commands.freeze import freeze_artifacts
    
    try:
        fingerprint = freeze_artifacts(
            output_dir=output,
            sign=sign,
            verbose=ctx.obj['verbose'],
        )
        
        if not ctx.obj['quiet']:
            success(f"✓ Artifacts frozen")
            info(f"  Fingerprint: {fingerprint}")
    
    except Exception as e:
        error(f"✗ Freeze failed: {e}")
        sys.exit(1)


# Import and register add command group


@cli.group()
def inspect():
    """Inspect compiled artifacts."""
    pass


@inspect.command('routes')
@click.pass_context
def inspect_routes(ctx):
    """Show compiled routes."""
    from .commands.inspect import inspect_routes as _inspect_routes
    
    try:
        _inspect_routes(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ Inspection failed: {e}")
        sys.exit(1)


@inspect.command('di')
@click.pass_context
def inspect_di(ctx):
    """Show DI graph."""
    from .commands.inspect import inspect_di as _inspect_di
    
    try:
        _inspect_di(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ Inspection failed: {e}")
        sys.exit(1)


@inspect.command('modules')
@click.pass_context
def inspect_modules(ctx):
    """List all modules."""
    from .commands.inspect import inspect_modules as _inspect_modules
    
    try:
        _inspect_modules(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ Inspection failed: {e}")
        sys.exit(1)


@inspect.command('faults')
@click.pass_context
def inspect_faults(ctx):
    """Show fault domains."""
    from .commands.inspect import inspect_faults as _inspect_faults
    
    try:
        _inspect_faults(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ Inspection failed: {e}")
        sys.exit(1)


@inspect.command('config')
@click.pass_context
def inspect_config(ctx):
    """Show resolved configuration."""
    from .commands.inspect import inspect_config as _inspect_config
    
    try:
        _inspect_config(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ Inspection failed: {e}")
        sys.exit(1)


@cli.command('migrate')
@click.argument('source', type=click.Choice(['legacy']))
@click.option('--dry-run', is_flag=True, help='Preview migration')
@click.pass_context
def migrate(ctx, source: str, dry_run: bool):
    """
    Migrate from Django-style layout.
    
    Examples:
      aq migrate legacy --dry-run
      aq migrate legacy
    """
    from .commands.migrate import migrate_legacy
    
    try:
        result = migrate_legacy(
            dry_run=dry_run,
            verbose=ctx.obj['verbose'],
        )
        
        if not ctx.obj['quiet']:
            if dry_run:
                warning("✓ Migration preview:")
            else:
                success("✓ Migration complete:")
            
            for item in result.changes:
                info(f"  {item}")
    
    except Exception as e:
        error(f"✗ Migration failed: {e}")
        sys.exit(1)


@cli.command('doctor')
@click.pass_context
def doctor(ctx):
    """Diagnose workspace issues."""
    from .commands.doctor import diagnose_workspace
    
    try:
        issues = diagnose_workspace(verbose=ctx.obj['verbose'])
        
        if not issues:
            success("✓ No issues found")
        else:
            warning(f"Found {len(issues)} issue(s):")
            for issue in issues:
                warning(f"  - {issue}")
    
    except Exception as e:
        error(f"✗ Diagnosis failed: {e}")
        sys.exit(1)


def main():
    """Entry point for `aq` command."""
    cli(obj={})


if __name__ == '__main__':
    main()
