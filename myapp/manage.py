#!/usr/bin/env python3
"""
Aquilia CRM — Database Management Script
=========================================
Run: python manage.py setup   — Create tables and seed data
Run: python manage.py reset   — Drop and recreate everything
"""

import asyncio
import sys
import os

# Ensure myapp directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def setup():
    """Create all CRM tables and seed initial data."""
    import aiosqlite

    db_path = os.path.join(os.path.dirname(__file__), "crm.db")
    print(f"📂 Database: {db_path}")

    # Simple wrapper that matches AquiliaDatabase interface
    class SimpleDB:
        def __init__(self, conn):
            self._conn = conn

        async def execute(self, sql, params=None):
            await self._conn.execute(sql, params or [])
            await self._conn.commit()

        async def fetch_one(self, sql, params=None):
            cursor = await self._conn.execute(sql, params or [])
            row = await cursor.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

        async def fetch_all(self, sql, params=None):
            cursor = await self._conn.execute(sql, params or [])
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]

    async with aiosqlite.connect(db_path) as conn:
        db = SimpleDB(conn)

        from modules.shared.db_setup import setup_database
        await setup_database(db)

    print("\n✅ Database setup complete!")
    print(f"   → Tables created and data seeded in {db_path}")
    print(f"   → Run the app: aquilia serve --host 0.0.0.0 --port 8000")


async def reset():
    """Drop and recreate the database."""
    db_path = os.path.join(os.path.dirname(__file__), "crm.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑  Removed existing database: {db_path}")
    else:
        print(f"ℹ  No existing database found at {db_path}")

    await setup()


def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print()
        print("Commands:")
        print("  setup   Create tables and seed initial data")
        print("  reset   Drop database and recreate from scratch")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "setup":
        asyncio.run(setup())
    elif command == "reset":
        asyncio.run(reset())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
