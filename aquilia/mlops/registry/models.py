"""
Registry data models — SQLite backend (default).

Uses ``aiosqlite`` which is already an Aquilia dependency.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aquilia.mlops.registry.models")


class RegistryDB:
    """
    Async SQLite backend for registry metadata.

    Tables:
    - ``packs``: immutable manifest records keyed by digest
    - ``tags``: mutable name:tag → digest pointers
    """

    def __init__(self, db_path: str = "registry.db"):
        self.db_path = db_path
        self._conn = None

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        import aiosqlite

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS packs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                tag         TEXT    NOT NULL,
                digest      TEXT    NOT NULL UNIQUE,
                manifest_json TEXT  NOT NULL,
                signed_by   TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_packs_name ON packs(name);
            CREATE INDEX IF NOT EXISTS idx_packs_digest ON packs(digest);

            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                tag         TEXT    NOT NULL,
                digest      TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(name, tag)
            );

            CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);

            CREATE TABLE IF NOT EXISTS blobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                digest      TEXT    NOT NULL UNIQUE,
                size        INTEGER NOT NULL DEFAULT 0,
                storage_path TEXT   DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_blobs_digest ON blobs(digest);
            """
        )
        await self._conn.commit()
        logger.info("Registry DB initialized: %s", self.db_path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ── Packs ────────────────────────────────────────────────────────

    async def insert_pack(
        self,
        name: str,
        tag: str,
        digest: str,
        manifest_json: str,
        signed_by: str = "",
    ) -> None:
        """Insert a pack record. Ignores if digest already exists."""
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO packs (name, tag, digest, manifest_json, signed_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, tag, digest, manifest_json, signed_by),
        )
        await self._conn.commit()

    async def get_pack(self, name: str, tag: str) -> Optional[Dict[str, Any]]:
        """Get pack by name:tag via the tags table."""
        assert self._conn is not None
        cursor = await self._conn.execute(
            """
            SELECT p.* FROM packs p
            INNER JOIN tags t ON p.digest = t.digest
            WHERE t.name = ? AND t.tag = ?
            """,
            (name, tag),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_pack_by_digest(self, digest: str) -> Optional[Dict[str, Any]]:
        """Get pack by content digest."""
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT * FROM packs WHERE digest = ?", (digest,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_versions(self, name: str) -> List[Dict[str, Any]]:
        """List all versions (tags) of a named pack."""
        assert self._conn is not None
        cursor = await self._conn.execute(
            """
            SELECT t.tag, t.digest, t.updated_at, p.signed_by
            FROM tags t
            LEFT JOIN packs p ON t.digest = p.digest
            WHERE t.name = ?
            ORDER BY t.updated_at DESC
            """,
            (name,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def list_packs(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List distinct pack names with latest tag info."""
        assert self._conn is not None
        cursor = await self._conn.execute(
            """
            SELECT DISTINCT p.name, t.tag, p.digest, p.created_at, p.signed_by
            FROM packs p
            LEFT JOIN tags t ON p.digest = t.digest AND t.tag = 'latest'
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Tags ─────────────────────────────────────────────────────────

    async def upsert_tag(self, name: str, tag: str, digest: str) -> None:
        """Insert or update a tag pointer."""
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT INTO tags (name, tag, digest, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(name, tag)
            DO UPDATE SET digest = excluded.digest, updated_at = excluded.updated_at
            """,
            (name, tag, digest),
        )
        await self._conn.commit()

    async def delete_tag(self, name: str, tag: str) -> None:
        """Delete a tag."""
        assert self._conn is not None
        await self._conn.execute(
            "DELETE FROM tags WHERE name = ? AND tag = ?", (name, tag)
        )
        await self._conn.commit()

    # ── Blobs ────────────────────────────────────────────────────────

    async def insert_blob(
        self, digest: str, size: int, storage_path: str = ""
    ) -> None:
        """Track a blob in the registry."""
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO blobs (digest, size, storage_path)
            VALUES (?, ?, ?)
            """,
            (digest, size, storage_path),
        )
        await self._conn.commit()
