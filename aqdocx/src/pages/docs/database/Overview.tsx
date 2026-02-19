import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Database } from 'lucide-react'

export function DatabaseOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Database className="w-4 h-4" />
          Data Layer / Database
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Database Engine
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">AquiliaDatabase</code> engine manages database connections, query execution, and transaction management with async-first design and pluggable backends for SQLite, PostgreSQL, and MySQL.
        </p>
      </div>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Integration

workspace = Workspace(
    integrations=[
        # SQLite (default — zero-config)
        Integration.database(
            engine="sqlite",
            name="db.sqlite3",
        ),

        # PostgreSQL
        Integration.database(
            engine="postgresql",
            host="localhost",
            port=5432,
            name="myapp",
            user="postgres",
            password="secret",
            pool_size=10,
            max_overflow=20,
        ),

        # MySQL
        Integration.database(
            engine="mysql",
            host="localhost",
            port=3306,
            name="myapp",
            user="root",
            password="secret",
        ),
    ],
)`}</CodeBlock>
      </section>

      {/* Backends */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Database Backends</h2>
        <div className="space-y-3">
          {[
            { name: 'SQLite', desc: 'File-based, zero-config database. Ideal for development, testing, and small deployments. Uses aiosqlite for async.', feat: 'WAL mode, connection pooling, auto-vacuum' },
            { name: 'PostgreSQL', desc: 'Production-grade relational database with full async support via asyncpg. Supports JSONB, arrays, CTEs, and window functions.', feat: 'Connection pooling, prepared statements, LISTEN/NOTIFY' },
            { name: 'MySQL', desc: 'MySQL/MariaDB support via aiomysql. Full compatibility with InnoDB storage engine.', feat: 'Connection pooling, SSL, charset configuration' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
              <p className={`text-xs mt-2 font-mono ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>{item.feat}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Using with Models */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using with Models</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The database engine is used internally by the ORM. You rarely interact with it directly — models handle all queries:
        </p>
        <CodeBlock language="python" filename="models.py">{`from aquilia.models import Model, CharField, IntegerField, ForeignKey


class Category(Model):
    name = CharField(max_length=100)

    class Meta:
        table = "categories"


class Product(Model):
    name = CharField(max_length=200)
    price = IntegerField()
    category = ForeignKey(Category, on_delete="CASCADE")

    class Meta:
        table = "products"
        ordering = ["-id"]


# All queries are async
products = await Product.objects.filter(
    category__name="Electronics",
    price__gte=100,
).order_by("-price").limit(10).to_list()`}</CodeBlock>
      </section>

      {/* Raw Queries */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Raw Queries</h2>
        <CodeBlock language="python" filename="raw.py">{`from aquilia.db import AquiliaDatabase

# Inject the database engine
class ReportController(Controller):
    prefix = "/api/reports"

    @Inject()
    def __init__(self, db: AquiliaDatabase):
        self.db = db

    @Get("/revenue")
    async def revenue_report(self, ctx):
        rows = await self.db.fetch_all(
            "SELECT category, SUM(price) as total "
            "FROM products GROUP BY category ORDER BY total DESC"
        )
        return ctx.json({"report": [dict(r) for r in rows]})

    @Get("/product/{id:int}")
    async def product_detail(self, ctx, id: int):
        row = await self.db.fetch_one(
            "SELECT * FROM products WHERE id = ?", [id]
        )
        if not row:
            return ctx.json({"error": "Not found"}, status=404)
        return ctx.json(dict(row))`}</CodeBlock>
      </section>

      {/* Transactions */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Transactions</h2>
        <CodeBlock language="python" filename="transactions.py">{`from aquilia.db import AquiliaDatabase


async def transfer_funds(db: AquiliaDatabase, from_id: int, to_id: int, amount: int):
    async with db.transaction() as tx:
        # All queries within this block run in a single transaction
        await tx.execute(
            "UPDATE accounts SET balance = balance - ? WHERE id = ?",
            [amount, from_id],
        )
        await tx.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            [amount, to_id],
        )
        # Transaction commits automatically on success
        # Rolls back on exception`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/serializers" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Serializers
        </Link>
        <Link to="/docs/auth" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Auth <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
