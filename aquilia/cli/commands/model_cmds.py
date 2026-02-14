"""
Model CLI Commands — aq db makemigrations, aq db migrate, aq db dump, aq db shell.

Integrates model discovery, migration generation/execution, schema inspection,
and interactive REPL with the Aquilia CLI system.

Discovers pure-Python Model subclasses from:
  - modules/*/models/ packages
  - modules/*/models.py files
  - models/ at workspace root
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import List, Optional

import click


# ── Discovery Helpers ─────────────────────────────────────────────────────────


def _find_model_files(search_dirs: Optional[List[str]] = None) -> List[Path]:
    """
    Find all Python model files in the workspace.

    Searches (in order):
    1. Explicit directories if provided
    2. modules/*/models/ packages (__init__.py + siblings)
    3. modules/*/models.py single-file models
    4. models/ at workspace root
    """
    found: List[Path] = []
    cwd = Path.cwd()

    if search_dirs:
        for d in search_dirs:
            p = Path(d)
            if p.is_dir():
                for pyf in sorted(p.glob("**/*.py")):
                    if not pyf.name.startswith("_"):
                        found.append(pyf)
                # Also include __init__.py in model packages
                for init in sorted(p.glob("**/__init__.py")):
                    if init not in found:
                        found.append(init)
    else:
        # modules/*/models/ packages — prefer __init__.py as entry point
        for init in sorted(cwd.glob("modules/*/models/__init__.py")):
            found.append(init)
        # Non-init siblings inside model packages (additional model files)
        for pyf in sorted(cwd.glob("modules/*/models/*.py")):
            if pyf.name.startswith("_"):
                continue
            if pyf not in found:
                found.append(pyf)
        # modules/*/models.py single-file modules
        for pyf in sorted(cwd.glob("modules/*/models.py")):
            if pyf not in found:
                found.append(pyf)
        # Root models/ directory
        for init in sorted(cwd.glob("models/__init__.py")):
            if init not in found:
                found.append(init)
        for pyf in sorted(cwd.glob("models/*.py")):
            if pyf.name.startswith("_"):
                continue
            if pyf not in found:
                found.append(pyf)

    return list(dict.fromkeys(found))  # dedupe preserving order


def _import_model_module(py_path: Path) -> Optional[types.ModuleType]:
    """
    Import a Python model file using proper package-aware imports.

    Computes a dotted module path relative to cwd so that relative
    imports within model packages work correctly.
    """
    cwd = Path.cwd()

    try:
        rel = py_path.relative_to(cwd)
    except ValueError:
        rel = None

    if rel is not None:
        # Build dotted module name:
        # modules/products/models/__init__.py → modules.products.models
        parts = list(rel.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        dotted = ".".join(parts)

        # Ensure cwd is on sys.path
        cwd_str = str(cwd)
        if cwd_str not in sys.path:
            sys.path.insert(0, cwd_str)

        # Bootstrap parent packages in sys.modules so relative imports resolve
        for i in range(1, len(parts)):
            parent_dotted = ".".join(parts[:i])
            if parent_dotted not in sys.modules:
                parent_path = cwd / Path(*parts[:i])
                init_file = parent_path / "__init__.py"
                if init_file.is_file():
                    parent_spec = importlib.util.spec_from_file_location(
                        parent_dotted,
                        str(init_file),
                        submodule_search_locations=[str(parent_path)],
                    )
                    if parent_spec and parent_spec.loader:
                        parent_mod = importlib.util.module_from_spec(parent_spec)
                        sys.modules[parent_dotted] = parent_mod
                        try:
                            parent_spec.loader.exec_module(parent_mod)
                        except Exception:
                            pass
                else:
                    # Create a namespace package stub
                    ns_mod = types.ModuleType(parent_dotted)
                    ns_mod.__path__ = [str(parent_path)]
                    ns_mod.__package__ = parent_dotted
                    sys.modules[parent_dotted] = ns_mod

        # Import the actual module
        if dotted in sys.modules:
            return sys.modules[dotted]
        return importlib.import_module(dotted)
    else:
        # Fallback for files outside workspace
        module_name = f"_aquilia_cli_models_{py_path.stem}_{id(py_path)}"
        spec = importlib.util.spec_from_file_location(module_name, str(py_path))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


def _discover_models(
    search_dirs: Optional[List[str]] = None,
    app: Optional[str] = None,
    verbose: bool = False,
) -> list:
    """
    Discover all Model subclasses in the workspace.

    Args:
        search_dirs: Explicit directories to search
        app: Filter to a specific module/app name
        verbose: Print discovery details

    Returns:
        List of Model subclass classes
    """
    try:
        from aquilia.models.base import Model
    except ImportError:
        click.echo(click.style("Model system not available.", fg="red"))
        return []

    py_files = _find_model_files(search_dirs)

    # Filter by app if specified
    if app:
        py_files = [
            f for f in py_files
            if f"modules/{app}/" in str(f) or f"modules/{app}\\" in str(f)
        ]

    discovered = []
    seen_names: set = set()

    for py_path in py_files:
        try:
            mod = _import_model_module(py_path)
            if mod is None:
                continue

            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Model)
                    and attr is not Model
                    and not getattr(getattr(attr, "_meta", None), "abstract", False)
                    and attr.__name__ not in seen_names
                ):
                    discovered.append(attr)
                    seen_names.add(attr.__name__)
                    if verbose:
                        click.echo(
                            click.style(
                                f"  Found model: {attr.__name__} "
                                f"(table={attr._meta.table_name})",
                                fg="blue",
                            )
                        )
        except Exception as e:
            if verbose:
                click.echo(
                    click.style(f"  ⚠ Failed to import {py_path}: {e}", fg="yellow")
                )
            continue

    return discovered


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_makemigrations(
    app: Optional[str] = None,
    migrations_dir: str = "migrations",
    verbose: bool = False,
) -> List[Path]:
    """
    Generate migration files from Python Model definitions.

    Discovers Model subclasses, generates CREATE TABLE SQL,
    and writes a migration script into the migrations directory.

    Returns:
        List of generated migration file paths
    """
    from aquilia.models.migrations import generate_migration_from_models

    if verbose:
        click.echo(click.style("Scanning for models...", fg="cyan"))

    models = _discover_models(app=app, verbose=verbose)

    if not models:
        click.echo(
            click.style(
                f"No models found{f' for app {app!r}' if app else ''}. "
                "Define Model subclasses in modules/*/models/.",
                fg="yellow",
            )
        )
        return []

    # Generate migration
    generated = generate_migration_from_models(
        model_classes=models,
        migrations_dir=migrations_dir,
    )

    model_names = ", ".join(m.__name__ for m in models)
    click.echo(
        click.style(
            f"✓ Generated migration: {generated.name} "
            f"({len(models)} model(s): {model_names})",
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
    Apply pending migrations to the database.

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
    emit: str = "python",
    output_dir: Optional[str] = None,
    verbose: bool = False,
) -> Optional[str]:
    """
    Dump model schema information.

    Generates DDL (CREATE TABLE, indexes, constraints) for all
    discovered Model subclasses.

    Args:
        emit: Output format — 'python' for annotated schema, 'sql' for raw DDL.
        output_dir: Directory to write output files (if set).
        verbose: Verbose output.

    Returns:
        Generated source string or None.
    """
    models = _discover_models(verbose=verbose)

    if not models:
        click.echo(click.style("No models found in workspace.", fg="yellow"))
        return None

    parts: List[str] = []

    if emit == "sql":
        # Raw SQL DDL
        sql_lines = ["-- Aquilia Model Schema", "--"]
        for model_cls in models:
            sql_lines.append(f"\n-- Model: {model_cls.__name__}")
            sql_lines.append(f"-- Table: {model_cls._meta.table_name}")
            try:
                sql_lines.append(model_cls.generate_create_table_sql() + ";")
                for idx_sql in model_cls.generate_index_sql():
                    sql_lines.append(idx_sql + ";")
                for m2m_sql in model_cls.generate_m2m_sql():
                    sql_lines.append(m2m_sql + ";")
            except Exception as e:
                sql_lines.append(f"-- Error generating DDL: {e}")
        parts.append("\n".join(sql_lines))
    else:
        # Annotated Python-style schema overview
        py_lines = ['"""Aquilia Model Schema — auto-generated."""', ""]
        for model_cls in models:
            py_lines.append(f"# ── {model_cls.__name__} ──")
            py_lines.append(f"# Table: {model_cls._meta.table_name}")
            meta = model_cls._meta
            if hasattr(meta, "ordering") and meta.ordering:
                py_lines.append(f"# Ordering: {meta.ordering}")

            # Fields
            py_lines.append("# Fields:")
            for name, field in model_cls._meta.fields.items():
                col = getattr(field, "column_name", name)
                ftype = type(field).__name__
                extras = []
                if getattr(field, "primary_key", False):
                    extras.append("PK")
                if getattr(field, "unique", False):
                    extras.append("UNIQUE")
                if getattr(field, "null", False):
                    extras.append("NULL")
                if getattr(field, "default", None) is not None:
                    extras.append(f"default={field.default!r}")
                extra_str = f" [{', '.join(extras)}]" if extras else ""
                py_lines.append(f"#   {name} ({col}): {ftype}{extra_str}")

            # DDL
            try:
                ddl = model_cls.generate_create_table_sql()
                py_lines.append("\n# DDL:")
                for line in ddl.split("\n"):
                    py_lines.append(f"# {line}")
            except Exception as e:
                py_lines.append(f"# DDL Error: {e}")

            py_lines.append("")
        parts.append("\n".join(py_lines))

    source = "\n\n".join(parts)

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        ext = ".sql" if emit == "sql" else ".py"
        outfile = out / f"schema{ext}"
        outfile.write_text(source, encoding="utf-8")
        click.echo(click.style(f"✓ Schema written to {outfile}", fg="green"))
    else:
        click.echo(source)

    return source


def cmd_shell(
    database_url: str = "sqlite:///db.sqlite3",
    verbose: bool = False,
) -> None:
    """
    Launch an async REPL with models and database pre-loaded.

    All discovered Model subclasses, Q query builder, and ModelRegistry
    are available in the shell namespace.
    """
    click.echo(click.style("Aquilia Model Shell", fg="cyan", bold=True))
    click.echo(click.style("Type 'exit()' or Ctrl+D to quit.\n", dim=True))

    from aquilia.db import AquiliaDatabase, set_database

    async def _setup():
        db = AquiliaDatabase(database_url)
        await db.connect()
        set_database(db)

        # Wire models to database
        try:
            from aquilia.models.base import ModelRegistry
            ModelRegistry.set_database(db)
        except ImportError:
            pass

        models = _discover_models(verbose=verbose)
        return db, models

    try:
        import code

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db, models = loop.run_until_complete(_setup())

        # Build namespace
        ns = {
            "db": db,
            "asyncio": asyncio,
            "loop": loop,
        }

        # Add Model classes
        model_names = []
        for model_cls in models:
            ns[model_cls.__name__] = model_cls
            model_names.append(model_cls.__name__)

        # Add Q and ModelRegistry
        try:
            from aquilia.models.base import Q, ModelRegistry
            ns["Q"] = Q
            ns["ModelRegistry"] = ModelRegistry
        except ImportError:
            pass

        model_display = ", ".join(model_names) or "(none)"
        click.echo(f"Models loaded: {model_display}")
        click.echo(f"Database: {database_url}")
        click.echo(
            click.style(
                "Tip: Use loop.run_until_complete(Product.get(pk=1)) for async ops\n",
                dim=True,
            )
        )

        code.interact(local=ns, banner="")

        loop.run_until_complete(db.disconnect())
        loop.close()
    except (ImportError, Exception) as e:
        click.echo(click.style(f"Shell error: {e}", fg="red"))
