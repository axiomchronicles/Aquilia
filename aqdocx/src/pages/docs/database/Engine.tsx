import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Database } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function DatabaseEngine() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Database className="w-4 h-4" />
          Database / Engine
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Database Engine
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">AquiliaDatabase</code> is the central database manager. It handles connection pooling, adapter selection, migration state, and integrates with the DI container.
        </p>
      </div>

      {/* AquiliaDatabase */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>AquiliaDatabase</h2>
        <CodeBlock language="python" filename="db.py">{`from aquilia.db import AquiliaDatabase

db = AquiliaDatabase(
    url="sqlite:///db.sqlite3",
    # url="postgresql://user:pass@localhost:5432/mydb",
    # url="mysql://user:pass@localhost:3306/mydb",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    echo=False,        # SQL logging
)

# Lifecycle
await db.connect()
await db.disconnect()

# Raw queries
rows = await db.execute("SELECT * FROM users WHERE active = ?", [True])
row = await db.fetch_one("SELECT * FROM users WHERE id = ?", [42])
count = await db.execute("UPDATE users SET active = ? WHERE id = ?", [False, 42])`}</CodeBlock>
      </section>

      {/* Adapters */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Database Adapters</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { name: 'SQLiteAdapter', desc: 'File-based, zero config. WAL mode, foreign keys enabled. Great for development and small apps.', url: 'sqlite:///db.sqlite3' },
            { name: 'PostgresAdapter', desc: 'Full-featured with JSONB, arrays, full-text search. Connection pooling via asyncpg.', url: 'postgresql://user:pass@host/db' },
            { name: 'MySQLAdapter', desc: 'MySQL/MariaDB support with aiomysql. Charset and collation configuration.', url: 'mysql://user:pass@host/db' },
          ].map((a, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-sm mb-2 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{a.name}</h3>
              <p className={`text-xs mb-2 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{a.desc}</p>
              <code className={`text-xs font-mono ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>{a.url}</code>
            </div>
          ))}
        </div>
      </section>

      {/* Transactions */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Transactions</h2>
        <CodeBlock language="python" filename="transactions.py">{`# Context manager — auto commit/rollback
async with db.transaction() as tx:
    await tx.execute("INSERT INTO users (name) VALUES (?)", ["Asha"])
    await tx.execute("INSERT INTO profiles (user_id) VALUES (?)", [1])
    # Commits on exit, rolls back on exception

# Nested transactions (savepoints)
async with db.transaction() as tx:
    await tx.execute("INSERT INTO orders (user_id) VALUES (?)", [1])
    async with tx.savepoint() as sp:
        await sp.execute("INSERT INTO items (order_id) VALUES (?)", [1])
        # Can rollback just this savepoint
        await sp.rollback()
    # Outer transaction still active`}</CodeBlock>
      </section>

      {/* Connection Pool */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Connection Pool Config</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Option</th>
                <th className="py-3 px-4 text-left font-semibold">Default</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['pool_size', '5', 'Number of persistent connections'],
                ['max_overflow', '10', 'Extra connections above pool_size'],
                ['pool_timeout', '30', 'Seconds to wait for a connection'],
                ['pool_recycle', '3600', 'Recycle connections after N seconds'],
                ['echo', 'False', 'Log all SQL statements'],
              ].map(([opt, def_, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{opt}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{def_}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}