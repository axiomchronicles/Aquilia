"""
DB Integration Tests — AquiliaDatabase with in-memory SQLite.

Tests connection, transactions, queries, and error handling.
"""

import pytest
from aquilia.db.engine import AquiliaDatabase, DatabaseError


@pytest.fixture
async def db():
    database = AquiliaDatabase("sqlite:///:memory:")
    await database.connect()
    yield database
    await database.disconnect()


class TestDatabaseConnection:
    """Test database connection management."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Connect and disconnect cleanly."""
        db = AquiliaDatabase("sqlite:///:memory:")
        assert db.is_connected is False

        await db.connect()
        assert db.is_connected is True

        await db.disconnect()
        assert db.is_connected is False

    @pytest.mark.asyncio
    async def test_double_connect_safe(self):
        """Double connect is safe."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        await db.connect()  # Should not raise
        assert db.is_connected is True
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_double_disconnect_safe(self):
        """Double disconnect is safe."""
        db = AquiliaDatabase("sqlite:///:memory:")
        await db.connect()
        await db.disconnect()
        await db.disconnect()  # Should not raise

    def test_detect_driver(self):
        """Detect driver from URL."""
        db = AquiliaDatabase("sqlite:///test.db")
        assert db.driver == "sqlite"

    def test_unsupported_driver(self):
        """Reject unsupported URL scheme."""
        with pytest.raises(DatabaseError, match="Unsupported"):
            AquiliaDatabase("oracle://host/db")

    @pytest.mark.asyncio
    async def test_properties(self):
        """Test URL and driver properties."""
        db = AquiliaDatabase("sqlite:///:memory:")
        assert db.url == "sqlite:///:memory:"
        assert db.driver == "sqlite"
        await db.connect()
        await db.disconnect()


class TestDatabaseExecute:
    """Test SQL execution."""

    @pytest.mark.asyncio
    async def test_execute_create(self, db):
        """Execute CREATE TABLE."""
        await db.execute(
            'CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)'
        )
        exists = await db.table_exists("test")
        assert exists is True

    @pytest.mark.asyncio
    async def test_execute_insert(self, db):
        """Execute INSERT."""
        await db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        cursor = await db.execute(
            'INSERT INTO test (name) VALUES (?)', ['hello']
        )
        assert cursor.lastrowid == 1

    @pytest.mark.asyncio
    async def test_fetch_all(self, db):
        """Fetch all rows."""
        await db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        await db.execute('INSERT INTO test (name) VALUES (?)', ['a'])
        await db.execute('INSERT INTO test (name) VALUES (?)', ['b'])

        rows = await db.fetch_all('SELECT * FROM test ORDER BY id')
        assert len(rows) == 2
        assert rows[0]['name'] == 'a'
        assert rows[1]['name'] == 'b'

    @pytest.mark.asyncio
    async def test_fetch_one(self, db):
        """Fetch one row."""
        await db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        await db.execute('INSERT INTO test (name) VALUES (?)', ['only'])

        row = await db.fetch_one('SELECT * FROM test WHERE name = ?', ['only'])
        assert row is not None
        assert row['name'] == 'only'

    @pytest.mark.asyncio
    async def test_fetch_one_none(self, db):
        """Fetch one returns None for no match."""
        await db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')

        row = await db.fetch_one('SELECT * FROM test WHERE id = ?', [999])
        assert row is None

    @pytest.mark.asyncio
    async def test_fetch_val(self, db):
        """Fetch scalar value."""
        await db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        await db.execute('INSERT INTO test (name) VALUES (?)', ['a'])
        await db.execute('INSERT INTO test (name) VALUES (?)', ['b'])

        count = await db.fetch_val('SELECT COUNT(*) FROM test')
        assert count == 2

    @pytest.mark.asyncio
    async def test_table_exists_false(self, db):
        """table_exists returns False for missing table."""
        exists = await db.table_exists("nonexistent")
        assert exists is False


class TestDatabaseTransactions:
    """Test transaction support."""

    @pytest.mark.asyncio
    async def test_transaction_commit(self, db):
        """Transaction commits on success."""
        await db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')

        async with db.transaction():
            await db.execute('INSERT INTO test (name) VALUES (?)', ['tx1'])
            await db.execute('INSERT INTO test (name) VALUES (?)', ['tx2'])

        rows = await db.fetch_all('SELECT * FROM test')
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db):
        """Transaction rolls back on exception."""
        await db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        await db.execute('INSERT INTO test (name) VALUES (?)', ['existing'])

        try:
            async with db.transaction():
                await db.execute('INSERT INTO test (name) VALUES (?)', ['new'])
                raise ValueError("Intentional error")
        except ValueError:
            pass

        rows = await db.fetch_all('SELECT * FROM test')
        # Should only have the pre-transaction row
        assert len(rows) == 1
        assert rows[0]['name'] == 'existing'
