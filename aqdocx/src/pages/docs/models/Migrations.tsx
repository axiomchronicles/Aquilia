import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Database } from 'lucide-react'

export function ModelsMigrations() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Database className="w-4 h-4" />Data Layer</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Migrations</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia's migration system generates and applies schema changes, tracks applied migrations in a dedicated table, and provides DDL operations for tables, columns, indexes, and constraints.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CLI Commands</h2>
        <CodeBlock language="bash" filename="Terminal">{`# Generate a migration from model changes
aquilia makemigrations --name add_user_table

# Apply all pending migrations
aquilia migrate

# Show migration status
aquilia showmigrations

# Rollback the last migration
aquilia migrate --rollback`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Migration File Structure</h2>
        <CodeBlock language="python" filename="migrations/0001_add_user_table.py">{`"""
Migration: 0001_add_user_table
Generated: 2025-01-15 10:30:00
"""
from aquilia.models.migrations import op

async def upgrade(conn):
    op.create_table("users", [
        '"id" INTEGER PRIMARY KEY AUTOINCREMENT',
        '"name" VARCHAR(150) NOT NULL',
        '"email" VARCHAR(255) NOT NULL UNIQUE',
        '"age" INTEGER',
        '"active" BOOLEAN DEFAULT 1',
        '"created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    ])
    op.create_index("users", "ix_users_email", ["email"])

    for sql in op.get_statements():
        await conn.execute(sql)
    op.clear()

async def downgrade(conn):
    op.drop_table("users")
    for sql in op.get_statements():
        await conn.execute(sql)
    op.clear()`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Migration Operations</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Operation</th>
              <th className="text-left py-3 text-aquilia-500">Description</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['op.create_table(name, columns)', 'CREATE TABLE IF NOT EXISTS'],
                ['op.drop_table(name, cascade?)', 'DROP TABLE IF EXISTS'],
                ['op.rename_table(old, new)', 'ALTER TABLE RENAME TO (dialect-aware)'],
                ['op.add_column(table, col_def)', 'ALTER TABLE ADD COLUMN'],
                ['op.drop_column(table, col)', 'ALTER TABLE DROP COLUMN'],
                ['op.rename_column(table, old, new)', 'RENAME COLUMN (dialect-aware)'],
                ['op.alter_column(table, col, type)', 'ALTER COLUMN TYPE'],
                ['op.create_index(table, name, cols)', 'CREATE INDEX'],
                ['op.drop_index(name)', 'DROP INDEX'],
                ['op.add_unique(table, name, cols)', 'ADD UNIQUE constraint'],
                ['op.add_check(table, name, expr)', 'ADD CHECK constraint'],
                ['op.add_fk(table, name, col, ref)', 'ADD FOREIGN KEY'],
                ['op.raw_sql(sql)', 'Execute raw SQL statement'],
              ].map(([op, desc], i) => (
                <tr key={i}>
                  <td className="py-2 pr-4 font-mono text-xs text-aquilia-400 whitespace-nowrap">{op}</td>
                  <td className={`py-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SQL Type Helpers</h2>
        <CodeBlock language="python" filename="Type Helpers">{`# Column type helpers generate dialect-aware SQL
op.varchar("name", 150, nullable=False)
# → '"name" VARCHAR(150) NOT NULL'

op.integer("age", nullable=True)
# → '"age" INTEGER'

op.boolean("active", default=True)
# → '"active" BOOLEAN DEFAULT 1'

op.timestamp("created_at", default="CURRENT_TIMESTAMP")
# → '"created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP'`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Migration Tracking</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <p className={`${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Aquilia tracks applied migrations in the <code className="text-aquilia-500">aquilia_migrations</code> table with columns:
          </p>
          <ul className={`mt-3 space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>• <code className="text-aquilia-400">id</code> — Auto-increment primary key</li>
            <li>• <code className="text-aquilia-400">name</code> — Migration filename</li>
            <li>• <code className="text-aquilia-400">app</code> — Application module name</li>
            <li>• <code className="text-aquilia-400">applied_at</code> — Timestamp of application</li>
            <li>• <code className="text-aquilia-400">checksum</code> — SHA-256 hash for integrity</li>
          </ul>
          <p className={`mt-3 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
            Signals: <code>pre_migrate</code> and <code>post_migrate</code> are fired before and after each migration runs.
          </p>
        </div>
      </section>
    </div>
  )
}
