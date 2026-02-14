#!/usr/bin/env bash
# verify_models_changes.sh — Smoke-test the AMDL model system.
#
# Usage:
#   chmod +x verify_models_changes.sh && ./verify_models_changes.sh
#
# What it does:
#   1. Installs the package in editable mode (with dev extras)
#   2. Runs makemigrations against examples/blog/models.amdl → tmpdir
#   3. Runs migrate on an in-memory SQLite (actually a tmp file)
#   4. Runs the AMDL-related pytest suites
#   5. Cleans up temp artefacts

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

TMPDIR=$(mktemp -d)
DB_FILE="${TMPDIR}/test_blog.sqlite3"
MIGRATIONS_DIR="${TMPDIR}/migrations"

cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo -e "${YELLOW}── Step 1: pip install -e '.[dev]' ──${NC}"
pip install -e ".[dev]" --quiet 2>&1 | tail -3
echo -e "${GREEN}✓ Install OK${NC}"

echo ""
echo -e "${YELLOW}── Step 2: aq db makemigrations ──${NC}"
python -c "
import sys, pathlib, asyncio
from aquilia.models.parser import parse_amdl_file
from aquilia.models.migrations import generate_migration_file

amdl = parse_amdl_file('examples/blog/models.amdl')
outdir = pathlib.Path('${MIGRATIONS_DIR}')
outdir.mkdir(parents=True, exist_ok=True)
path = generate_migration_file(amdl.models, str(outdir), slug='blog_initial')
print(f'Generated: {path}')
"
echo -e "${GREEN}✓ makemigrations OK${NC}"

echo ""
echo -e "${YELLOW}── Step 3: aq db migrate (SQLite in tmpdir) ──${NC}"
python -c "
import asyncio
from aquilia.db.engine import AquiliaDatabase
from aquilia.models.migrations import MigrationRunner

async def main():
    db = AquiliaDatabase('sqlite:///${DB_FILE}')
    await db.connect()
    runner = MigrationRunner(db, '${MIGRATIONS_DIR}')
    await runner.migrate()
    print(f'Applied: {await runner.get_applied()}')

    # Quick CRUD sanity check
    await db.execute(
        'INSERT INTO \"aq_user\" (\"username\", \"email\", \"bio\", \"active\") VALUES (?, ?, ?, ?)',
        ['tester', 'tester@example.com', 'hello', 1]
    )
    row = await db.fetch_one('SELECT * FROM \"aq_user\" WHERE \"username\" = ?', ['tester'])
    assert row is not None and row['email'] == 'tester@example.com', 'CRUD check failed'
    print('CRUD check passed')

    await db.disconnect()

asyncio.run(main())
"
echo -e "${GREEN}✓ migrate + CRUD OK${NC}"

echo ""
echo -e "${YELLOW}── Step 4: pytest (AMDL suites) ──${NC}"
python -m pytest \
    tests/test_models_parser.py \
    tests/test_models_runtime.py \
    tests/test_models_relations.py \
    tests/test_models_migrations.py \
    tests/test_db_integration.py \
    -v --tb=short \
    2>&1

echo ""
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  All AMDL model checks passed  ✓${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
