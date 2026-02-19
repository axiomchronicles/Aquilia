import { useTheme } from '../../../context/ThemeContext';
import { CodeBlock } from '../../../components/CodeBlock';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ModelsMigrations() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm mb-4">
          <Link to="/docs" className={isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}>Docs</Link>
          <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>/</span>
          <Link to="/docs/models/overview" className={isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}>Models</Link>
          <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>/</span>
          <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>Migrations</span>
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Migrations
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia's 4-layer migration system — from high-level DSL operations to raw DDL, with auto-generation, tracking, and rollback support.
        </p>
      </div>

      {/* Architecture */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The migration system is organized in four layers, from highest to lowest level:
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Layer</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Module</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Role</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>Auto-Generator</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>migration_gen.py</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Diff current models against DB schema → generate DSL migration files</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>DSL</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>migration_dsl.py</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>High-level operations: CreateModel, AddField, RunSQL, RunPython, etc.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>Runner</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>migration_runner.py</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Execute, track, rollback, plan, status. Manages <code>aquilia_migrations</code> table.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>DDL Ops</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>migrations.py</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Raw SQL builders: create/drop/rename tables, add/alter/drop columns, indexes, constraints</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Migration DSL */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Migration DSL</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Migrations are Python files in your <code>migrations/</code> directory. Each file defines a <code>Migration</code> class with a list of operations.
        </p>
        <CodeBlock language="python" filename="migrations/0001_initial.py">
{`from aquilia.models.migration_dsl import Migration, CreateModel, AddField, CreateIndex, C

class InitialMigration(Migration):
    """Create users and posts tables."""
    
    dependencies = []  # no prior migration

    operations = [
        CreateModel(
            name="users",
            columns=[
                C.bigserial("id").primary_key(),
                C.varchar("name", 150).not_null(),
                C.varchar("email", 254).not_null().unique(),
                C.boolean("active").default(True),
                C.timestamp("created_at").default("NOW()"),
            ],
        ),
        CreateModel(
            name="posts",
            columns=[
                C.bigserial("id").primary_key(),
                C.varchar("title", 200).not_null(),
                C.text("body"),
                C.bigint("author_id").not_null().references("users", "id", on_delete="CASCADE"),
                C.timestamp("published_at").nullable(),
            ],
        ),
        CreateIndex(
            table="posts",
            columns=["author_id"],
            name="idx_posts_author",
        ),
    ]`}
        </CodeBlock>
      </section>

      {/* DSL Operations */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>DSL Operations</h2>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Operation</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Reversible</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {[
                ['CreateModel', 'CREATE TABLE with columns', 'Yes → DROP TABLE'],
                ['DropModel', 'DROP TABLE', 'No'],
                ['RenameModel', 'ALTER TABLE RENAME', 'Yes → reverse rename'],
                ['AddField', 'ALTER TABLE ADD COLUMN', 'Yes → drop column'],
                ['RemoveField', 'ALTER TABLE DROP COLUMN', 'No'],
                ['AlterField', 'ALTER TABLE ALTER COLUMN (type, default, null)', 'Yes → reverse alter'],
                ['RenameField', 'ALTER TABLE RENAME COLUMN', 'Yes → reverse rename'],
                ['CreateIndex', 'CREATE INDEX', 'Yes → DROP INDEX'],
                ['DropIndex', 'DROP INDEX', 'No'],
                ['AddConstraint', 'ALTER TABLE ADD CONSTRAINT', 'Yes → drop constraint'],
                ['RemoveConstraint', 'ALTER TABLE DROP CONSTRAINT', 'No'],
                ['RunSQL', 'Execute raw SQL', 'Yes (if reverse_sql provided)'],
                ['RunPython', 'Execute Python callable', 'Yes (if reverse_func provided)'],
              ].map(([op, desc, rev]) => (
                <tr key={op}>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{op}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{desc}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{rev}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Column Definitions with C */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Column Definitions — C Namespace</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>C</code> class provides a fluent builder for column definitions used in CreateModel and AddField operations:
        </p>
        <CodeBlock language="python">
{`from aquilia.models.migration_dsl import C

# C.<type>(name, ...) returns a ColumnDef with chainable methods:
# .not_null()   — add NOT NULL constraint
# .nullable()   — explicitly allow NULL
# .primary_key() — mark as PRIMARY KEY
# .unique()      — add UNIQUE constraint
# .default(val)  — set DEFAULT value
# .references(table, column, on_delete=...) — add FOREIGN KEY
# .check(expr)   — add CHECK constraint

# Examples
C.bigserial("id").primary_key()
C.varchar("name", 150).not_null()
C.integer("age").nullable().default(0)
C.text("bio")
C.boolean("active").not_null().default(True)
C.timestamp("created_at").default("NOW()")
C.decimal("price", 10, 2).not_null().check("price > 0")
C.bigint("user_id").references("users", "id", on_delete="CASCADE")
C.jsonb("metadata").default("'{}'")
C.uuid("public_id").not_null().unique()

# Available types:
# C.integer, C.bigint, C.smallint, C.serial, C.bigserial
# C.varchar, C.text, C.char
# C.boolean
# C.real, C.double, C.decimal, C.numeric
# C.date, C.time, C.timestamp, C.interval
# C.blob, C.bytea
# C.json, C.jsonb
# C.uuid
# C.inet, C.cidr, C.macaddr
# C.array(base_type)
# C.custom(sql_type)`}
        </CodeBlock>
      </section>

      {/* Data Migrations */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Data Migrations</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Use <code>RunSQL</code> and <code>RunPython</code> for data transformations that go beyond schema changes.
        </p>
        <CodeBlock language="python" filename="migrations/0003_backfill_slugs.py">
{`from aquilia.models.migration_dsl import Migration, RunSQL, RunPython

async def backfill_slugs(db):
    """Generate slugs for existing articles."""
    rows = await db.fetch_all("SELECT id, title FROM articles WHERE slug IS NULL")
    for row in rows:
        slug = row["title"].lower().replace(" ", "-")[:50]
        await db.execute("UPDATE articles SET slug = ? WHERE id = ?", [slug, row["id"]])

async def reverse_slugs(db):
    """Clear all slugs."""
    await db.execute("UPDATE articles SET slug = NULL")

class BackfillSlugsMigration(Migration):
    dependencies = ["0002_add_slug"]

    operations = [
        # RunPython — callable with optional reverse
        RunPython(
            forward=backfill_slugs,
            reverse=reverse_slugs,
        ),

        # RunSQL — raw SQL with optional reverse SQL
        RunSQL(
            sql="UPDATE articles SET status = 'draft' WHERE status IS NULL",
            reverse_sql="UPDATE articles SET status = NULL WHERE status = 'draft'",
        ),
    ]`}
        </CodeBlock>
      </section>

      {/* Migration Runner */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Migration Runner</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>MigrationRunner</code> handles execution, tracking, and rollback of migrations. It uses an <code>aquilia_migrations</code> tracking table.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.migration_runner import MigrationRunner

# Initialize — auto-creates tracking table
runner = MigrationRunner(db, migrations_dir="migrations/")
await runner.init()

# Status — show all migrations and their state
status = await runner.status()
# [
#   {"name": "0001_initial", "applied": True, "applied_at": "2024-..."},
#   {"name": "0002_add_slug", "applied": False, "applied_at": None},
# ]

# Pending — only unapplied migrations
pending = await runner.get_pending()
# ["0002_add_slug", "0003_backfill_slugs"]

# Applied — already executed
applied = await runner.get_applied()
# ["0001_initial"]

# Plan — dry-run showing what would execute
plan = await runner.plan()
# [{"name": "0002_add_slug", "operations": [...]}, ...]

# sqlmigrate — view SQL without executing
sql = await runner.sqlmigrate("0002_add_slug")
# "ALTER TABLE articles ADD COLUMN slug VARCHAR(50);"

# Migrate — apply all pending migrations
await runner.migrate()

# Migrate to specific target
await runner.migrate(target="0002_add_slug")

# Rollback — reverse the last applied migration
await runner.rollback()

# Rollback to specific target
await runner.rollback(target="0001_initial")`}
        </CodeBlock>
      </section>

      {/* Auto-generation */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Auto-Generation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>generate_dsl_migration()</code> compares your current model definitions against the database schema and generates a migration file with the necessary operations.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.migration_gen import generate_dsl_migration

# Generate migration from schema diff
migration_code = await generate_dsl_migration(
    db=db,
    models=[User, Post, Comment],      # current model classes
    migrations_dir="migrations/",       # where to find existing migrations
    name="auto",                        # migration name (auto-numbered)
)

# The generated code is a valid Python file with:
# - CreateModel for new tables
# - AddField for new columns
# - AlterField for changed columns
# - RemoveField for deleted columns
# - CreateIndex / DropIndex for index changes

# Write to file
with open("migrations/0004_auto.py", "w") as f:
    f.write(migration_code)

# Review and apply
await runner.migrate()`}
        </CodeBlock>
      </section>

      {/* Low-level DDL */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Low-Level DDL — MigrationOps</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          For advanced or dynamic schema changes, use <code>MigrationOps</code> directly. This is the lowest-level API that DSL operations compile into.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.migrations import MigrationOps

ops = MigrationOps(db)

# Table operations
await ops.create_table("users", {
    "id": "BIGSERIAL PRIMARY KEY",
    "name": "VARCHAR(150) NOT NULL",
    "email": "VARCHAR(254) NOT NULL UNIQUE",
})
await ops.drop_table("old_table")
await ops.rename_table("users", "accounts")
await ops.table_exists("users")         # → True

# Column operations
await ops.add_column("users", "age", "INTEGER DEFAULT 0")
await ops.drop_column("users", "legacy_field")
await ops.rename_column("users", "name", "full_name")
await ops.alter_column("users", "email", "TEXT NOT NULL")
await ops.column_exists("users", "age")  # → True

# Index operations
await ops.create_index("users", ["email"], unique=True, name="idx_email")
await ops.drop_index("idx_email")

# Constraint operations
await ops.add_constraint("users", "ck_age", "CHECK (age >= 0)")
await ops.drop_constraint("users", "ck_age")

# Column type helpers
ops.integer()        # → "INTEGER"
ops.bigint()         # → "BIGINT"
ops.varchar(100)     # → "VARCHAR(100)"
ops.text()           # → "TEXT"
ops.boolean()        # → "BOOLEAN" / "INTEGER" (SQLite)
ops.timestamp()      # → "TIMESTAMP" / "TIMESTAMPTZ"
ops.decimal(10, 2)   # → "DECIMAL(10,2)"
ops.jsonb()          # → "JSONB" / "TEXT" (SQLite)
ops.uuid()           # → "UUID" / "VARCHAR(36)" (SQLite)
ops.serial()         # → "SERIAL" / "INTEGER" (SQLite)
ops.bigserial()      # → "BIGSERIAL" / "INTEGER" (SQLite)
ops.array("TEXT")    # → "TEXT[]" / "TEXT" (SQLite)

# Foreign key helper
await ops.add_foreign_key(
    table="posts",
    column="author_id",
    ref_table="users",
    ref_column="id",
    on_delete="CASCADE",
)`}
        </CodeBlock>
      </section>

      {/* Tracking Table */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Tracking Table</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The runner stores migration state in <code>aquilia_migrations</code>:
        </p>
        <CodeBlock language="sql">
{`CREATE TABLE IF NOT EXISTS aquilia_migrations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    NOT NULL UNIQUE,
    applied   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Each row = one applied migration
-- name: migration filename without .py extension
-- applied: ISO timestamp when it was applied`}
        </CodeBlock>
      </section>

      {/* Signals */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Migration Signals</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Hook into migration execution with the <code>pre_migrate</code> and <code>post_migrate</code> signals.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.signals import pre_migrate, post_migrate, receiver

@receiver(pre_migrate)
async def before_migration(sender, migration_name, **kwargs):
    print(f"About to apply: {migration_name}")

@receiver(post_migrate)
async def after_migration(sender, migration_name, **kwargs):
    print(f"Successfully applied: {migration_name}")
    # Good place to seed data, clear caches, etc.`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex justify-between items-center pt-8 mt-8 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <Link
          to="/docs/models/relationships"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          <ArrowLeft className="w-4 h-4" /> Relationships
        </Link>
        <Link
          to="/docs/models/advanced"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          Advanced <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
