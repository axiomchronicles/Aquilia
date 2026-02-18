"""
Aquilia Safe DB Startup — guards against implicit database creation.

Prevents the database file and tables from being auto-created when
models change at server startup. If the DB file does not exist or
there are unapplied migrations, the server must fail-start with a
yellow warning instructing the developer to run:

    aquilia makemigrations && aquilia migrate

Behavior can be overridden with the environment variable:
    AQUILIA_AUTO_MIGRATE=1

Configuration:
    db.sqlite.journal_mode  — "wal" (default for runtime), "delete" for
                              schema-check/dry-run operations to avoid
                              creating -wal/-shm sidecar files.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aquilia.db.startup")

# ANSI yellow for terminal warning
_YELLOW = "\033[93m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


class DatabaseNotReadyError(SystemExit):
    """
    Raised when the database is not ready at server startup.

    This is a SystemExit subclass so the process exits with a
    non-zero code and a human-readable message.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(1)


def check_db_ready(
    db_url: str = "sqlite:///db.sqlite3",
    migrations_dir: str | Path = "migrations",
    *,
    auto_migrate: Optional[bool] = None,
) -> bool:
    """
    Check if the database is ready for the application to start.

    This function MUST be called during server startup (before
    any ModelRegistry.create_tables() call).

    Rules:
    1. If AQUILIA_AUTO_MIGRATE=1 (or auto_migrate=True), skip checks.
    2. For SQLite: if the DB file does not exist, warn and return False.
    3. If there are unapplied migrations, warn and return False.

    Args:
        db_url: Database connection URL
        migrations_dir: Path to migrations directory
        auto_migrate: Override for AQUILIA_AUTO_MIGRATE env var

    Returns:
        True if the database is ready, False otherwise.
    """
    from .migration_runner import check_db_exists, check_migrations_applied

    # Check auto-migrate override
    if auto_migrate is None:
        auto_migrate = os.environ.get("AQUILIA_AUTO_MIGRATE", "").strip() in ("1", "true", "yes")

    if auto_migrate:
        logger.info("AQUILIA_AUTO_MIGRATE=1: skipping migration checks")
        return True

    # Check 1: Does the database file exist?
    if not check_db_exists(db_url):
        _warn_not_ready(
            "Database file does not exist",
            db_url=db_url,
            hint="Run the following commands to create and initialize the database:",
        )
        return False

    # Check 2: Are all migrations applied?
    mdir = Path(migrations_dir)
    if mdir.exists() and any(mdir.glob("*.py")):
        if not check_migrations_applied(db_url, migrations_dir):
            _warn_not_ready(
                "Unapplied migrations detected",
                db_url=db_url,
                hint="Run the following commands to apply pending migrations:",
            )
            return False

    logger.info("Database ready — all migrations applied")
    return True


def _warn_not_ready(reason: str, *, db_url: str, hint: str) -> None:
    """Print a yellow warning banner (non-fatal)."""
    msg = f"""
{_YELLOW}{_BOLD}╔══════════════════════════════════════════════════════════════╗
║                   DATABASE NOT READY                         ║
╠══════════════════════════════════════════════════════════════╣{_RESET}
{_YELLOW}║  {reason:<60}║
║                                                              ║
║  Database: {db_url:<49}║
║                                                              ║
║  {hint:<60}║
║                                                              ║
║    $ aq db makemigrations                                    ║
║    $ aq db migrate                                           ║
║                                                              ║
║  Or set AQUILIA_AUTO_MIGRATE=1 to auto-create on startup.    ║
╚══════════════════════════════════════════════════════════════╝{_RESET}
"""
    print(msg, file=sys.stderr)


def _fail_start(reason: str, *, db_url: str, hint: str) -> None:
    """Print a yellow warning and raise DatabaseNotReadyError (legacy)."""
    _warn_not_ready(reason, db_url=db_url, hint=hint)
    raise DatabaseNotReadyError(reason)
