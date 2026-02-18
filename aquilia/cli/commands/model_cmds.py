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
                    click.style(f"  ! Failed to import {py_path}: {e}", fg="yellow")
                )
            continue

    return discovered


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_makemigrations(
    app: Optional[str] = None,
    migrations_dir: str = "migrations",
    verbose: bool = False,
    use_dsl: bool = True,
) -> List[Path]:
    """
    Generate migration files from Python Model definitions.

    If use_dsl=True (default), uses the new DSL system with schema
    snapshot diffing and rename detection. Otherwise, uses the legacy
    raw-SQL migration generator.

    Returns:
        List of generated migration file paths
    """
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

    if use_dsl:
        # New DSL migration generation with snapshot diffing
        from aquilia.models.migration_gen import generate_dsl_migration

        generated = generate_dsl_migration(
            model_classes=models,
            migrations_dir=migrations_dir,
        )

        if generated is None:
            click.echo(
                click.style("No model changes detected.", fg="yellow")
            )
            return []

        model_names = ", ".join(m.__name__ for m in models)
        click.echo(
            click.style(
                f"✓ Generated DSL migration: {generated.name} "
                f"({len(models)} model(s): {model_names})",
                fg="green",
            )
        )
        snap_path = Path(migrations_dir) / "schema_snapshot.json"
        click.echo(
            click.style(
                f"  Schema snapshot: {snap_path}",
                dim=True,
            )
        )
        return [generated]
    else:
        # Legacy raw-SQL migration generation
        from aquilia.models.migrations import generate_migration_from_models

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
    fake: bool = False,
    plan: bool = False,
    database: Optional[str] = None,
) -> List[str]:
    """
    Apply pending migrations to the database.

    Supports both DSL and legacy migrations. The runner auto-detects
    the migration format.

    Args:
        fake: Mark as applied without executing SQL
        plan: Preview SQL only (dry-run)
        database: Database alias for multi-db setups

    Returns:
        List of applied revision IDs
    """
    from aquilia.db import AquiliaDatabase
    from aquilia.models.migration_runner import MigrationRunner

    async def _run() -> List[str]:
        db = AquiliaDatabase(database_url)
        await db.connect()
        try:
            runner = MigrationRunner(db, migrations_dir, dialect=db.dialect)

            if plan:
                # Dry-run: just show SQL
                stmts = await runner.plan(target=target)
                if stmts:
                    click.echo(click.style("-- Migration Plan (dry-run):", fg="cyan"))
                    for sql in stmts:
                        click.echo(sql)
                else:
                    click.echo(click.style("No pending migrations.", fg="yellow"))
                return []

            if target:
                revs = await runner.migrate(target=target, fake=fake)
                action = "Faked rollback of" if fake else "Rolled back"
                if revs:
                    click.echo(
                        click.style(
                            f"✓ {action} {len(revs)} migration(s) to {target}",
                            fg="green",
                        )
                    )
                else:
                    click.echo(click.style("Nothing to rollback.", fg="yellow"))
            else:
                revs = await runner.migrate(fake=fake)
                action = "Faked" if fake else "Applied"
                if revs:
                    click.echo(
                        click.style(
                            f"✓ {action} {len(revs)} migration(s)",
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


# ── New Commands ──────────────────────────────────────────────────────────────


def cmd_inspectdb(
    database_url: str = "sqlite:///db.sqlite3",
    tables: Optional[List[str]] = None,
    verbose: bool = False,
) -> str:
    """
    Introspect an existing database and generate Model classes.

    Reads the database schema and emits Python Model definitions
    that can be pasted into a models.py file.

    Args:
        database_url: Database connection URL
        tables: Specific tables to inspect (None = all)
        verbose: Verbose output

    Returns:
        Generated Python source code
    """
    from aquilia.db import AquiliaDatabase

    async def _run() -> str:
        db = AquiliaDatabase(database_url)
        await db.connect()

        try:
            # Get table list
            if database_url.startswith("sqlite"):
                rows = await db.fetch_all(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
                all_tables = [row["name"] for row in rows]
            else:
                all_tables = []

            if tables:
                all_tables = [t for t in all_tables if t in tables]

            if not all_tables:
                return "# No tables found in database."

            lines = [
                '"""',
                "Auto-generated Model definitions from database introspection.",
                "",
                f"Database: {database_url}",
                '"""',
                "",
                "from aquilia.models import Model",
                "from aquilia.models.fields import (",
                "    CharField, IntegerField, FloatField, BooleanField,",
                "    TextField, DateTimeField, DecimalField, BigIntegerField,",
                "    BinaryField, JSONField,",
                ")",
                "",
                "",
            ]

            for table_name in all_tables:
                if verbose:
                    click.echo(click.style(f"  Inspecting: {table_name}", fg="blue"))

                # Get table schema
                if database_url.startswith("sqlite"):
                    col_rows = await db.fetch_all(f'PRAGMA table_info("{table_name}")')
                else:
                    col_rows = []

                class_name = _table_to_class_name(table_name)
                lines.append(f"class {class_name}(Model):")
                lines.append(f'    table = "{table_name}"')
                lines.append("")

                for col in col_rows:
                    col_name = col["name"]
                    col_type = col["type"].upper()
                    notnull = col["notnull"]
                    pk = col["pk"]
                    default_val = col["dflt_value"]

                    if pk:
                        # Skip auto-PK — Model adds it automatically
                        continue

                    field_type, field_args = _sql_type_to_field(col_type, notnull, default_val)
                    lines.append(f"    {col_name} = {field_type}({field_args})")

                lines.append("")
                lines.append(f"    class Meta:")
                lines.append(f'        verbose_name = "{class_name}"')
                lines.append("")
                lines.append("")

            return "\n".join(lines)
        finally:
            await db.disconnect()

    return asyncio.run(_run())


def cmd_showmigrations(
    migrations_dir: str = "migrations",
    database_url: str = "sqlite:///db.sqlite3",
    verbose: bool = False,
) -> List[dict]:
    """
    Show all migrations and their applied status against the database.

    Connects to the real database to check the aquilia_migrations tracking
    table.  Falls back to a file-only listing when the DB doesn't exist or
    the tracking table hasn't been created yet.

    Returns:
        List of dicts with keys: name, file, applied
    """
    from aquilia.db import AquiliaDatabase
    from aquilia.models.migration_runner import MigrationRunner

    migrations_path = Path(migrations_dir)

    if not migrations_path.is_dir():
        click.echo(click.style(f"No migrations directory: {migrations_dir}", fg="yellow"))
        return []

    # Collect on-disk migration files
    files = sorted(
        p for p in migrations_path.glob("*.py") if not p.name.startswith("_")
    )

    if not files:
        click.echo(click.style("  No migrations found.", fg="yellow"))
        return []

    # Try to get applied set from the database
    applied_set: set[str] = set()

    async def _fetch_applied() -> set[str]:
        db = AquiliaDatabase(database_url)
        try:
            await db.connect()
            runner = MigrationRunner(db, migrations_dir, dialect=db.dialect)
            return set(await runner.get_applied())
        except Exception:
            return set()
        finally:
            try:
                await db.disconnect()
            except Exception:
                pass

    try:
        applied_set = asyncio.run(_fetch_applied())
    except Exception:
        pass

    results: List[dict] = []
    for pyf in files:
        name = pyf.stem
        is_applied = name in applied_set
        info = {
            "name": name,
            "file": str(pyf),
            "applied": is_applied,
        }
        results.append(info)
        marker = (
            click.style("[X]", fg="green")
            if is_applied
            else click.style("[ ]", fg="yellow")
        )
        click.echo(f"  {marker} {name}")

    return results


def cmd_sqlmigrate(
    migration_name: str,
    migrations_dir: str = "migrations",
    verbose: bool = False,
    database: Optional[str] = None,
) -> Optional[str]:
    """
    Display the SQL statements for a specific migration.

    For DSL migrations the operations are compiled to SQL for the
    current dialect (defaults to ``sqlite``).  For legacy migrations,
    SQL is extracted from the source via regex or the raw source is
    displayed.

    Args:
        migration_name: Name of the migration file (without .py)
        migrations_dir: Directory containing migration files
        database: Database alias — unused today, reserved for multi-db

    Returns:
        SQL string or None
    """
    from aquilia.models.migration_runner import MigrationRunner

    migrations_path = Path(migrations_dir)
    target = migrations_path / f"{migration_name}.py"

    if not target.is_file():
        # Try partial match
        candidates = list(migrations_path.glob(f"*{migration_name}*.py"))
        if len(candidates) == 1:
            target = candidates[0]
        elif len(candidates) > 1:
            click.echo(
                click.style(
                    f"Ambiguous: {[c.stem for c in candidates]}", fg="yellow"
                )
            )
            return None
        else:
            click.echo(
                click.style(f"Migration not found: {migration_name}", fg="red")
            )
            return None

    # Try DSL compilation first
    try:
        from aquilia.models.migration_runner import (
            _load_migration_module,
            _build_migration_from_module,
            _extract_revision,
        )

        rev = _extract_revision(target) or target.stem
        module = _load_migration_module(target, rev)
        if hasattr(module, "operations"):
            migration_obj = _build_migration_from_module(module)
            stmts = migration_obj.compile_upgrade("sqlite")
            if stmts:
                output = f"-- SQL for migration: {target.stem}\n\n"
                output += "\n".join(stmts)
                click.echo(output)
                return output
    except Exception:
        pass

    # Fallback: extract SQL from legacy migration source via regex
    source = target.read_text(encoding="utf-8")

    import re

    sql_statements = re.findall(
        r'(?:execute|executescript)\s*\(\s*["\']+(.*?)["\']+\s*\)',
        source,
        re.DOTALL,
    )
    sql_statements += re.findall(
        r'(?:execute|executescript)\s*\(\s*"""(.*?)"""\s*\)',
        source,
        re.DOTALL,
    )
    sql_statements += re.findall(
        r"(?:execute|executescript)\s*\(\s*'''(.*?)'''\s*\)",
        source,
        re.DOTALL,
    )

    if sql_statements:
        output = f"-- SQL for migration: {target.stem}\n"
        for sql in sql_statements:
            output += f"\n{sql.strip()};\n"
        click.echo(output)
        return output
    else:
        click.echo(click.style(f"-- Migration: {target.stem}", fg="cyan"))
        click.echo(source)
        return source


def cmd_db_status(
    database_url: str = "sqlite:///db.sqlite3",
    verbose: bool = False,
) -> dict:
    """
    Show database status — tables, row counts, schema details.

    Returns:
        Dict with database status information
    """
    from aquilia.db import AquiliaDatabase

    async def _run() -> dict:
        db = AquiliaDatabase(database_url)
        await db.connect()

        try:
            status = {
                "url": database_url,
                "tables": [],
                "total_tables": 0,
            }

            if database_url.startswith("sqlite"):
                rows = await db.fetch_all(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
                for row in rows:
                    table_name = row["name"]
                    count_row = await db.fetch_one(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
                    count = count_row["cnt"] if count_row else 0

                    col_rows = await db.fetch_all(f'PRAGMA table_info("{table_name}")')
                    col_count = len(col_rows)

                    table_info = {
                        "name": table_name,
                        "rows": count,
                        "columns": col_count,
                    }
                    status["tables"].append(table_info)

                    # Display
                    row_str = click.style(f"{count:>8} rows", fg="cyan")
                    col_str = click.style(f"{col_count} columns", dim=True)
                    click.echo(f"  {table_name:<30} {row_str}  ({col_str})")

                status["total_tables"] = len(status["tables"])

            click.echo(
                click.style(
                    f"\n  Total: {status['total_tables']} table(s), "
                    f"{sum(t['rows'] for t in status['tables'])} row(s)",
                    fg="green",
                    bold=True,
                )
            )

            return status
        finally:
            await db.disconnect()

    return asyncio.run(_run())


# ── Internal Helpers ──────────────────────────────────────────────────────────


def _table_to_class_name(table_name: str) -> str:
    """Convert a table name to a PascalCase class name."""
    # users → User, order_items → OrderItem
    parts = table_name.replace("-", "_").split("_")
    return "".join(part.capitalize() for part in parts if part)


def _sql_type_to_field(
    col_type: str, notnull: int, default_val: Optional[str]
) -> tuple:
    """Map an SQL column type to an Aquilia field type + args."""
    args: List[str] = []

    if not notnull:
        args.append("null=True")
    if default_val is not None and default_val not in ("NULL", ""):
        args.append(f"default={default_val}")

    col_upper = col_type.upper()

    if "INT" in col_upper:
        if "BIGINT" in col_upper:
            return "BigIntegerField", ", ".join(args)
        return "IntegerField", ", ".join(args)
    elif "CHAR" in col_upper or "VARCHAR" in col_upper:
        # Extract max_length from VARCHAR(N)
        import re
        m = re.search(r'\((\d+)\)', col_type)
        if m:
            args.insert(0, f"max_length={m.group(1)}")
        else:
            args.insert(0, "max_length=255")
        return "CharField", ", ".join(args)
    elif "TEXT" in col_upper or "CLOB" in col_upper:
        return "TextField", ", ".join(args)
    elif "REAL" in col_upper or "FLOAT" in col_upper or "DOUBLE" in col_upper:
        return "FloatField", ", ".join(args)
    elif "DECIMAL" in col_upper or "NUMERIC" in col_upper:
        return "DecimalField", ", ".join(args)
    elif "BOOL" in col_upper:
        return "BooleanField", ", ".join(args)
    elif "BLOB" in col_upper:
        return "BinaryField", ", ".join(args)
    elif "DATETIME" in col_upper or "TIMESTAMP" in col_upper:
        return "DateTimeField", ", ".join(args)
    elif "JSON" in col_upper:
        return "JSONField", ", ".join(args)
    else:
        return "CharField", "max_length=255" + (", " + ", ".join(args) if args else "")
