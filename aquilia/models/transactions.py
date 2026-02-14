"""
Aquilia Transactions — atomic() context manager with savepoint support.

Provides safe transaction handling with nested savepoint support
and automatic rollback on exception.

Usage:
    from aquilia.models.transactions import atomic

    async with atomic():
        user = await User.create(name="Alice")
        await Profile.create(user=user.id)
        # Both committed together

    async with atomic() as sp1:
        await User.create(name="Bob")
        async with atomic() as sp2:
            await Post.create(title="Hello")
            raise ValueError("oops")  # sp2 rolled back
        # sp1 still active — Bob is saved, Post is not

    # Explicit savepoint control:
    async with atomic(savepoint=True) as txn:
        await txn.savepoint()
        ...
        await txn.rollback_to_savepoint()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..db.engine import AquiliaDatabase

logger = logging.getLogger("aquilia.models.transactions")

__all__ = [
    "atomic",
    "TransactionManager",
    "Atomic",
]

# Track nested transaction depth per-task
_task_transaction_depth: dict = {}


def _get_task_id() -> int:
    """Get current asyncio task ID for nesting tracking."""
    try:
        task = asyncio.current_task()
        return id(task) if task else 0
    except RuntimeError:
        return 0


class Atomic:
    """
    Async context manager for database transactions.

    Supports nested savepoints:
    - First atomic() opens a transaction (BEGIN)
    - Nested atomic() creates a SAVEPOINT
    - Exception causes rollback of the innermost savepoint/transaction
    - Successful exit commits or releases the savepoint
    """

    def __init__(
        self,
        db: Optional[AquiliaDatabase] = None,
        *,
        savepoint: bool = True,
        durable: bool = False,
    ):
        """
        Args:
            db: Database instance. If None, uses the default database.
            savepoint: Whether to use savepoints for nesting (default True)
            durable: If True, raises error when used inside another atomic block
        """
        self._db = db
        self._use_savepoint = savepoint
        self._durable = durable
        self._savepoint_id: Optional[str] = None
        self._is_outermost = False

    def _get_db(self) -> AquiliaDatabase:
        if self._db is not None:
            return self._db
        from ..db.engine import get_database
        return get_database()

    async def __aenter__(self) -> Atomic:
        db = self._get_db()
        if not db.is_connected:
            await db.connect()

        task_id = _get_task_id()
        depth = _task_transaction_depth.get(task_id, 0)

        if depth == 0:
            # Outermost: start transaction
            self._is_outermost = True
            await db.execute("BEGIN")
            _task_transaction_depth[task_id] = 1
        else:
            if self._durable:
                raise RuntimeError(
                    "atomic(durable=True) cannot be nested inside another atomic block"
                )
            if self._use_savepoint:
                # Nested: create savepoint
                self._savepoint_id = f"sp_{uuid.uuid4().hex[:8]}"
                await db.execute(f"SAVEPOINT {self._savepoint_id}")
            _task_transaction_depth[task_id] = depth + 1

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        db = self._get_db()
        task_id = _get_task_id()
        depth = _task_transaction_depth.get(task_id, 1)

        try:
            if exc_type is not None:
                # Exception occurred — rollback
                if self._savepoint_id:
                    await db.execute(f"ROLLBACK TO SAVEPOINT {self._savepoint_id}")
                    logger.debug(f"Rolled back savepoint {self._savepoint_id}")
                elif self._is_outermost:
                    await db.execute("ROLLBACK")
                    logger.debug("Rolled back transaction")
            else:
                # Success — commit or release savepoint
                if self._savepoint_id:
                    await db.execute(f"RELEASE SAVEPOINT {self._savepoint_id}")
                    logger.debug(f"Released savepoint {self._savepoint_id}")
                elif self._is_outermost:
                    await db.execute("COMMIT")
                    logger.debug("Committed transaction")
        finally:
            # Decrement depth
            new_depth = depth - 1
            if new_depth <= 0:
                _task_transaction_depth.pop(task_id, None)
            else:
                _task_transaction_depth[task_id] = new_depth

        return False  # Don't suppress exceptions

    async def savepoint(self) -> str:
        """Create an explicit savepoint within this atomic block."""
        db = self._get_db()
        sp_id = f"sp_{uuid.uuid4().hex[:8]}"
        await db.execute(f"SAVEPOINT {sp_id}")
        return sp_id

    async def rollback_to_savepoint(self, savepoint_id: str) -> None:
        """Roll back to a specific savepoint."""
        db = self._get_db()
        await db.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id}")

    async def release_savepoint(self, savepoint_id: str) -> None:
        """Release (commit) a savepoint."""
        db = self._get_db()
        await db.execute(f"RELEASE SAVEPOINT {savepoint_id}")


def atomic(
    db: Optional[AquiliaDatabase] = None,
    *,
    savepoint: bool = True,
    durable: bool = False,
) -> Atomic:
    """
    Create an atomic transaction context manager.

    Can be used as a context manager:
        async with atomic():
            ...

    Or with a specific database:
        async with atomic(db=my_db):
            ...

    Args:
        db: Database instance. If None, uses the default.
        savepoint: Use savepoints for nesting (default True)
        durable: Disallow nesting inside another atomic block
    """
    return Atomic(db, savepoint=savepoint, durable=durable)


class TransactionManager:
    """
    Higher-level transaction manager that integrates with Model.

    Provides on_commit hooks and rollback tracking.
    """

    def __init__(self, db: Optional[AquiliaDatabase] = None):
        self._db = db
        self._on_commit_hooks: list = []

    def on_commit(self, func):
        """Register a function to be called after successful commit."""
        self._on_commit_hooks.append(func)

    @asynccontextmanager
    async def atomic(self, **kwargs) -> AsyncIterator[Atomic]:
        """Use as: async with manager.atomic() as txn: ..."""
        txn = Atomic(self._db, **kwargs)
        async with txn:
            yield txn
        # If we get here, commit was successful
        for hook in self._on_commit_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as exc:
                logger.error(f"on_commit hook failed: {exc}")
        self._on_commit_hooks.clear()
