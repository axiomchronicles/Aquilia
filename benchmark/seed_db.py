"""
Database Seed Script
====================
Creates the bench_users table and seeds it with 1000 rows.
Used by all three frameworks identically.

Usage:
    python -m benchmark.seed_db
    # or: python benchmark/seed_db.py
"""
import asyncio
import os
import sys

import asyncpg

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@localhost:5432/bench")


async def seed():
    print(f"[seed] Connecting to {DB_DSN}")
    conn = await asyncpg.connect(DB_DSN)

    # Create table
    await conn.execute("""
        DROP TABLE IF EXISTS bench_users CASCADE;
        CREATE TABLE bench_users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            bio TEXT NOT NULL DEFAULT ''
        );
    """)
    print("[seed] Table bench_users created")

    # Seed 1000 rows
    values = []
    for i in range(1, 1001):
        values.append((f"user-{i}", f"user{i}@example.com", f"Bio for user {i}. " * 10))

    await conn.executemany(
        "INSERT INTO bench_users (name, email, bio) VALUES ($1, $2, $3)",
        values,
    )
    print(f"[seed] Inserted {len(values)} rows")

    # Create index
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_users_id ON bench_users(id);")
    print("[seed] Index created")

    count = await conn.fetchval("SELECT COUNT(*) FROM bench_users")
    print(f"[seed] Verification: {count} rows in bench_users")

    await conn.close()
    print("[seed] Done")


if __name__ == "__main__":
    asyncio.run(seed())
