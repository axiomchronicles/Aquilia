"""
Model CLI Commands — aq makemigrations, aq migrate, aq model dump, aq shell.

Integrates AMDL parsing, migration generation/execution, and model inspection
with the Aquilia CLI system.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import click


def _find_amdl_files(search_dirs: Optional[List[str]] = None) -> List[Path]:
    """
    Find all .amdl files in the workspace.

    Searches:
    1. Explicit directories if provided
    2. modules/*/models/ convention
    3. models/ at workspace root
    4. examples/*/  for demo files
    """
    found: List[Path] = []
    cwd = Path.cwd()

    if search_dirs:
        for d in search_dirs:
            p = Path(d)
            if p.is_dir():
                found.extend(sorted(p.glob("**/*.amdl")))
    else:
        # Convention: modules/*/models/*.amdl
        found.extend(sorted(cwd.glob("modules/*/models/*.amdl")))
        # Root models/
        found.extend(sorted(cwd.glob("models/*.amdl")))
        # Examples
        found.extend(sorted(cwd.glob("examples/*/models.amdl")))
        found.extend(sorted(cwd.glob("examples/*/*.amdl")))

    return list(dict.fromkeys(found))  # dedupe preserving order


def cmd_makemigrations(
    app: Optional[str] = None,
    migrations_dir: str = "migrations",
    verbose: bool = False,
) -> List[Path]:
    """
    Generate migration files from AMDL models.

    Parses .amdl files, diffs against existing migrations,
    and generates new migration scripts.

    Returns:
        List of generated migration file paths
    """
    from aquilia.models.parser import parse_amdl_file, AMDLParseError
    from aquilia.models.migrations import generate_migration_file
    from aquilia.models.ast_nodes import ModelNode

    amdl_files = _find_amdl_files()
    if not amdl_files:
        click.echo(click.style("No .amdl files found in workspace.", fg="yellow"))
        return []

    all_models: List[ModelNode] = []
    for amdl_path in amdl_files:
        try:
            result = parse_amdl_file(amdl_path)
            all_models.extend(result.models)
            if verbose:
                click.echo(
                    click.style(f"  Parsed {amdl_path}: {len(result.models)} model(s)", fg="blue")
                )
        except AMDLParseError as e:
            click.echo(click.style(f"  ✗ {e}", fg="red"))
            return []

    if not all_models:
        click.echo(click.style("No MODEL stanzas found in .amdl files.", fg="yellow"))
        return []

    # Filter by app if specified
    if app:
        all_models = [m for m in all_models if app.lower() in m.source_file.lower()]

    if not all_models:
        click.echo(click.style(f"No models found for app '{app}'.", fg="yellow"))
        return []

    # Generate migration
    generated = generate_migration_file(all_models, migrations_dir)
    click.echo(
        click.style(
            f"✓ Generated migration: {generated.name} "
            f"({len(all_models)} model(s))",
            fg="green",
        )
    )
    return [generated]


def cmd_migrate(
    migrations_dir: str = "migrations",
    database_url: str = "sqlite:///db.sqlite3",
    target: Optional[str] = None,
    verbose: bool = False,
) -> List[str]:
    """
    Apply pending migrations.

    Returns:
        List of applied revision IDs
    """
    from aquilia.db import AquiliaDatabase
    from aquilia.models.migrations import MigrationRunner

    async def _run() -> List[str]:
        db = AquiliaDatabase(database_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, migrations_dir)
            if target:
                revs = await runner.migrate(target=target)
                if revs:
                    click.echo(
                        click.style(
                            f"✓ Rolled back {len(revs)} migration(s) to {target}",
                            fg="green",
                        )
                    )
                else:
                    click.echo(click.style("Nothing to rollback.", fg="yellow"))
            else:
                revs = await runner.migrate()
                if revs:
                    click.echo(
                        click.style(
                            f"✓ Applied {len(revs)} migration(s)",
                            fg="green",
                        )
                    )
                else:
                    click.echo(click.style("No pending migrations.", fg="yellow"))
            return revs
        finally:
            await db.disconnect()

    return asyncio.run(_run())


def cmd_model_dump(
    emit: bool = False,
    output_dir: str = "models_gen",
    verbose: bool = False,
) -> Optional[str]:
    """
    Dump generated Python model proxies.

    Args:
        emit: If True, write to files. If False, print to stdout.
        output_dir: Directory for emitted files.
        verbose: Verbose output.

    Returns:
        Generated Python source or None.
    """
    from aquilia.models.parser import parse_amdl_file, AMDLParseError
    from aquilia.models.runtime import ModelRegistry

    amdl_files = _find_amdl_files()
    if not amdl_files:
        click.echo(click.style("No .amdl files found.", fg="yellow"))
        return None

    registry = ModelRegistry()
    for path in amdl_files:
        try:
            result = parse_amdl_file(path)
            for model in result.models:
                registry.register_model(model)
        except AMDLParseError as e:
            click.echo(click.style(f"✗ {e}", fg="red"))
            return None

    source = registry.emit_python()

    if emit:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        outfile = out / "models.py"
        outfile.write_text(source, encoding="utf-8")
        click.echo(click.style(f"✓ Emitted model proxies to {outfile}", fg="green"))
    else:
        click.echo(source)

    return source


def cmd_shell(
    database_url: str = "sqlite:///db.sqlite3",
    verbose: bool = False,
) -> None:
    """
    Launch async REPL with models and DB preloaded.
    """
    click.echo(click.style("Aquilia Model Shell", fg="cyan", bold=True))
    click.echo(click.style("Type 'exit()' or Ctrl+D to quit.\n", dim=True))

    from aquilia.db import AquiliaDatabase, set_database
    from aquilia.models.parser import parse_amdl_file
    from aquilia.models.runtime import ModelRegistry

    async def _setup():
        db = AquiliaDatabase(database_url)
        await db.connect()
        set_database(db)

        registry = ModelRegistry(db)
        amdl_files = _find_amdl_files()
        for path in amdl_files:
            try:
                result = parse_amdl_file(path)
                for model in result.models:
                    registry.register_model(model)
            except Exception as e:
                click.echo(click.style(f"Warning: {e}", fg="yellow"))

        return db, registry

    try:
        import code

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db, registry = loop.run_until_complete(_setup())

        # Build namespace with all model proxies
        ns = {
            "db": db,
            "registry": registry,
            "asyncio": asyncio,
            "loop": loop,
        }
        for name, proxy_cls in registry.all_proxies().items():
            ns[name] = proxy_cls

        model_names = ", ".join(registry.all_proxies().keys()) or "(none)"
        click.echo(f"Models loaded: {model_names}")
        click.echo(f"Database: {database_url}")
        click.echo(
            click.style(
                "Tip: Use loop.run_until_complete(User.$get(pk=1)) for async ops\n",
                dim=True,
            )
        )

        code.interact(local=ns, banner="")

        loop.run_until_complete(db.disconnect())
        loop.close()
    except (ImportError, Exception) as e:
        click.echo(click.style(f"Shell error: {e}", fg="red"))
