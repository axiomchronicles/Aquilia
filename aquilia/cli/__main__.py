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
def add():
    """Add module to workspace."""
    pass


@add.command('module')
@click.argument('name')
@click.option('--depends-on', multiple=True, help='Module dependencies')
@click.option('--fault-domain', type=str, help='Custom fault domain')
@click.option('--route-prefix', type=str, help='Route prefix (default: /name)')
@click.option('--with-tests', is_flag=True, help='Generate test routes')
@click.pass_context
def add_module(ctx, name: str, depends_on: tuple, fault_domain: Optional[str], route_prefix: Optional[str], with_tests: bool):
    """
    Add a new module to the workspace.
    
    Examples:
      aq add module users
      aq add module products --depends-on=users
      aq add module admin --fault-domain=ADMIN --route-prefix=/api/admin
      aq add module test --with-tests
    """
    from .commands.add import add_module as _add_module
    
    try:
        module_path = _add_module(
            name=name,
            depends_on=list(depends_on),
            fault_domain=fault_domain,
            route_prefix=route_prefix,
            with_tests=with_tests,
            verbose=ctx.obj['verbose'],
        )
        
        if not ctx.obj['quiet']:
            success(f"✓ Added module '{name}'")
            info(f"  Location: {module_path}")
            if depends_on:
                info(f"  Dependencies: {', '.join(depends_on)}")
            info(f"\nNext steps:")
            info(f"  1. Implement controllers in modules/{name}/controllers.py")
            info(f"  2. Implement services in modules/{name}/services.py")
            info(f"  3. Run: aq run")
    
    except Exception as e:
        error(f"✗ Failed to add module: {e}")
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


@cli.group()
def manifest():
    """Manage module manifests."""
    pass


@manifest.command('update')
@click.argument('module')
@click.option('--check', is_flag=True, help='Fail if manifest is out of sync (CI mode)')
@click.option('--freeze', is_flag=True, help='Disable auto-discovery after Sync (Strict mode)')
@click.pass_context
def manifest_update(ctx, module: str, check: bool, freeze: bool):
    """
    Update manifest with auto-discovered resources.
    
    Scans the module for controllers and services, then explicitly
    writes them into manifest.py.
    
    Examples:
      aq manifest update mymod
      aq manifest update mymod --check   # For CI
      aq manifest update mymod --freeze  # For Prod
    """
    from .commands.manifest import update_manifest
    
    try:
        # Resolve workspace root (assume cwd)
        workspace_root = Path.cwd()
        
        update_manifest(
            module_name=module,
            workspace_root=workspace_root,
            check=check,
            freeze=freeze,
            verbose=ctx.obj['verbose'],
        )
        
    except Exception as e:
        error(f"✗ Manifest update failed: {e}")
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


# ============================================================================
# WebSocket management
# ============================================================================

@cli.group()
def ws():
    """WebSocket management commands."""
    pass


@ws.command('inspect')
@click.option('--artifacts-dir', type=click.Path(), default='artifacts', help='Artifacts directory')
@click.pass_context
def ws_inspect(ctx, artifacts_dir: str):
    """Inspect compiled WebSocket namespaces."""
    from .commands.ws import cmd_ws_inspect
    try:
        cmd_ws_inspect({'artifacts_dir': artifacts_dir})
    except Exception as e:
        error(f"✗ WS inspect failed: {e}")
        sys.exit(1)


@ws.command('broadcast')
@click.option('--namespace', required=True, help='Namespace')
@click.option('--room', default=None, help='Room (optional)')
@click.option('--event', required=True, help='Event name')
@click.option('--payload', default='{}', help='JSON payload')
@click.pass_context
def ws_broadcast(ctx, namespace: str, room: Optional[str], event: str, payload: str):
    """Broadcast message to namespace or room."""
    from .commands.ws import cmd_ws_broadcast
    try:
        cmd_ws_broadcast({'namespace': namespace, 'room': room, 'event': event, 'payload': payload})
    except Exception as e:
        error(f"✗ WS broadcast failed: {e}")
        sys.exit(1)


@ws.command('gen-client')
@click.option('--lang', default='ts', help='Language (ts)')
@click.option('--out', required=True, help='Output file')
@click.option('--artifacts-dir', type=click.Path(), default='artifacts', help='Artifacts directory')
@click.pass_context
def ws_gen_client(ctx, lang: str, out: str, artifacts_dir: str):
    """Generate TypeScript client SDK from compiled WebSocket artifacts."""
    from .commands.ws import cmd_ws_gen_client
    try:
        cmd_ws_gen_client({'lang': lang, 'out': out, 'artifacts_dir': artifacts_dir})
    except Exception as e:
        error(f"✗ WS gen-client failed: {e}")
        sys.exit(1)


# ============================================================================
# Discovery
# ============================================================================

@cli.command('discover')
@click.option('--path', type=click.Path(), default=None, help='Workspace path')
@click.pass_context
def discover(ctx, path: Optional[str]):
    """Inspect auto-discovered modules in workspace."""
    from .commands.discover import DiscoveryInspector

    try:
        workspace_root = Path(path) if path else Path.cwd()
        inspector = DiscoveryInspector(workspace_root.name, str(workspace_root))
        inspector.inspect(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ Discovery failed: {e}")
        sys.exit(1)


# ============================================================================
# Analytics
# ============================================================================

@cli.command('analytics')
@click.option('--path', type=click.Path(), default=None, help='Workspace path')
@click.pass_context
def analytics(ctx, path: Optional[str]):
    """Run discovery analytics and show health report."""
    from .commands.analytics import DiscoveryAnalytics, print_analysis_report

    try:
        workspace_root = Path(path) if path else Path.cwd()
        analyser = DiscoveryAnalytics(workspace_root.name, str(workspace_root))
        analysis = analyser.analyze()
        print_analysis_report(analysis)
    except Exception as e:
        error(f"✗ Analytics failed: {e}")
        sys.exit(1)


# ============================================================================
# Mail
# ============================================================================

@cli.group()
def mail():
    """AquilaMail commands — test, inspect, and validate mail configuration."""
    pass


@mail.command('check')
@click.pass_context
def mail_check(ctx):
    """
    Validate mail configuration and report issues.

    Examples:
      aq mail check
    """
    from .commands.mail import cmd_mail_check

    try:
        cmd_mail_check(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ mail check failed: {e}")
        sys.exit(1)


@mail.command('send-test')
@click.argument('to')
@click.option('--subject', type=str, default=None, help='Email subject')
@click.option('--body', type=str, default=None, help='Email body')
@click.pass_context
def mail_send_test(ctx, to: str, subject: Optional[str], body: Optional[str]):
    """
    Send a test email to verify mail provider configuration.

    Examples:
      aq mail send-test user@example.com
      aq mail send-test user@example.com --subject="Hello"
    """
    from .commands.mail import cmd_mail_send_test

    try:
        cmd_mail_send_test(
            to=to,
            subject=subject,
            body=body,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ mail send-test failed: {e}")
        sys.exit(1)


@mail.command('inspect')
@click.pass_context
def mail_inspect(ctx):
    """
    Display current mail configuration as JSON.

    Examples:
      aq mail inspect
    """
    from .commands.mail import cmd_mail_inspect

    try:
        cmd_mail_inspect(verbose=ctx.obj['verbose'])
    except Exception as e:
        error(f"✗ mail inspect failed: {e}")
        sys.exit(1)


# ============================================================================
# Database / Models
# ============================================================================

@cli.group()
def db():
    """Database and model ORM commands."""
    pass


@db.command('makemigrations')
@click.option('--app', type=str, default=None, help='Restrict to specific module/app')
@click.option('--migrations-dir', type=click.Path(), default='migrations', help='Migrations directory')
@click.pass_context
def db_makemigrations(ctx, app: Optional[str], migrations_dir: str):
    """
    Generate migration files from Python Model definitions.

    Discovers Model subclasses in modules/*/models/, generates
    CREATE TABLE SQL, and writes a migration script.

    Examples:
      aq db makemigrations
      aq db makemigrations --app=products
      aq db makemigrations --migrations-dir=db/migrations
    """
    from .commands.model_cmds import cmd_makemigrations

    try:
        cmd_makemigrations(
            app=app,
            migrations_dir=migrations_dir,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ makemigrations failed: {e}")
        sys.exit(1)


@db.command('migrate')
@click.option('--migrations-dir', type=click.Path(), default='migrations', help='Migrations directory')
@click.option('--database-url', type=str, default='sqlite:///db.sqlite3', help='Database URL')
@click.option('--target', type=str, default=None, help='Target revision (or "zero" to rollback all)')
@click.pass_context
def db_migrate(ctx, migrations_dir: str, database_url: str, target: Optional[str]):
    """
    Apply pending migrations to the database.

    Examples:
      aq db migrate
      aq db migrate --database-url=sqlite:///prod.db
      aq db migrate --target=zero
    """
    from .commands.model_cmds import cmd_migrate

    try:
        cmd_migrate(
            migrations_dir=migrations_dir,
            database_url=database_url,
            target=target,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ migrate failed: {e}")
        sys.exit(1)


@db.command('dump')
@click.option('--emit', type=click.Choice(['python', 'sql']), default='python', help='Output format')
@click.option('--output-dir', type=click.Path(), default=None, help='Output directory')
@click.pass_context
def db_dump(ctx, emit: str, output_dir: Optional[str]):
    """
    Dump model schema — annotated Python overview or raw SQL DDL.

    Examples:
      aq db dump
      aq db dump --emit=sql
      aq db dump --output-dir=generated/
    """
    from .commands.model_cmds import cmd_model_dump

    try:
        cmd_model_dump(
            emit=emit,
            output_dir=output_dir,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ dump failed: {e}")
        sys.exit(1)


@db.command('shell')
@click.option('--database-url', type=str, default='sqlite:///db.sqlite3', help='Database URL')
@click.pass_context
def db_shell(ctx, database_url: str):
    """
    Open an async REPL with models pre-loaded.

    All discovered Model classes, Q query builder, and ModelRegistry
    are available in the shell namespace.

    Examples:
      aq db shell
      aq db shell --database-url=sqlite:///prod.db
    """
    from .commands.model_cmds import cmd_shell

    try:
        cmd_shell(
            database_url=database_url,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ shell failed: {e}")
        sys.exit(1)


@db.command('inspectdb')
@click.option('--database-url', type=str, default='sqlite:///db.sqlite3', help='Database URL')
@click.option('--table', type=str, multiple=True, help='Specific tables to inspect')
@click.option('--output', type=click.Path(), default=None, help='Output file path')
@click.pass_context
def db_inspectdb(ctx, database_url: str, table: tuple, output: Optional[str]):
    """
    Introspect database and generate Model definitions.

    Reads the database schema and emits Python Model class
    definitions that mirror the existing tables.

    Examples:
      aq db inspectdb
      aq db inspectdb --table=users --table=orders
      aq db inspectdb --output=models/generated.py
    """
    from .commands.model_cmds import cmd_inspectdb

    try:
        tables = list(table) if table else None
        result = cmd_inspectdb(
            database_url=database_url,
            tables=tables,
            verbose=ctx.obj['verbose'],
        )
        if output and result:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(result, encoding="utf-8")
            click.echo(click.style(f"✓ Models written to {output}", fg="green"))
    except Exception as e:
        error(f"✗ inspectdb failed: {e}")
        sys.exit(1)


@db.command('showmigrations')
@click.option('--migrations-dir', type=click.Path(), default='migrations', help='Migrations directory')
@click.pass_context
def db_showmigrations(ctx, migrations_dir: str):
    """
    Show all migrations and their applied/pending status.

    Examples:
      aq db showmigrations
      aq db showmigrations --migrations-dir=db/migrations
    """
    from .commands.model_cmds import cmd_showmigrations

    try:
        cmd_showmigrations(
            migrations_dir=migrations_dir,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ showmigrations failed: {e}")
        sys.exit(1)


@db.command('sqlmigrate')
@click.argument('migration_name')
@click.option('--migrations-dir', type=click.Path(), default='migrations', help='Migrations directory')
@click.pass_context
def db_sqlmigrate(ctx, migration_name: str, migrations_dir: str):
    """
    Display SQL statements for a specific migration.

    Examples:
      aq db sqlmigrate 0001_initial
      aq db sqlmigrate 0002 --migrations-dir=db/migrations
    """
    from .commands.model_cmds import cmd_sqlmigrate

    try:
        cmd_sqlmigrate(
            migration_name=migration_name,
            migrations_dir=migrations_dir,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ sqlmigrate failed: {e}")
        sys.exit(1)


@db.command('status')
@click.option('--database-url', type=str, default='sqlite:///db.sqlite3', help='Database URL')
@click.pass_context
def db_status(ctx, database_url: str):
    """
    Show database status — tables, row counts, columns.

    Examples:
      aq db status
      aq db status --database-url=sqlite:///prod.db
    """
    from .commands.model_cmds import cmd_db_status

    try:
        cmd_db_status(
            database_url=database_url,
            verbose=ctx.obj['verbose'],
        )
    except Exception as e:
        error(f"✗ status failed: {e}")
        sys.exit(1)


def main():
    """Entry point for `aq` command."""
    cli(obj={})


if __name__ == '__main__':
    main()
