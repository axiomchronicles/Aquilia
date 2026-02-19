import { useTheme } from '../../../context/ThemeContext';
import { CodeBlock } from '../../../components/CodeBlock';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { NextSteps } from '../../../components/NextSteps'

export function ModelsAdvanced() {
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
          <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>Advanced</span>
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Advanced
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Transactions, expressions, database functions, SQL builders, constraints, and choices — the full power of Aquilia's ORM.
        </p>
      </div>

      {/* Transactions */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Transactions</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>atomic()</code> context manager wraps database operations in a transaction. It supports nesting via savepoints.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.transactions import atomic

# Basic transaction
async with atomic(db):
    user = User(name="Alice", email="alice@co.com")
    await user.save(db)
    profile = Profile(user_id=user.id, bio="Hello")
    await profile.save(db)
    # If either fails, both are rolled back

# Nested transactions — uses SAVEPOINTs
async with atomic(db):
    await user.save(db)

    async with atomic(db):
        # Creates SAVEPOINT
        await risky_operation(db)
        # If this fails, only the inner block rolls back

    # Outer transaction continues

# Durable mode — prevents nesting, always creates a real transaction
async with atomic(db, durable=True):
    await critical_operation(db)

# as decorator
@atomic(db)
async def transfer_funds(from_id, to_id, amount):
    await Account.objects.filter(id=from_id).update(balance=F("balance") - amount)
    await Account.objects.filter(id=to_id).update(balance=F("balance") + amount)`}
        </CodeBlock>
      </section>

      {/* on_commit / on_rollback */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>on_commit / on_rollback Hooks</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Register callbacks that fire after the transaction successfully commits or rolls back. Callbacks are FIFO-ordered and only fire once.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.transactions import atomic, on_commit, on_rollback

async with atomic(db) as txn:
    user = User(name="Bob")
    await user.save(db)

    # Runs only if the transaction commits
    on_commit(txn, lambda: send_welcome_email(user.id))
    on_commit(txn, lambda: invalidate_cache("users"))

    # Runs only if the transaction rolls back
    on_rollback(txn, lambda: log_failure("user_creation_failed"))

# Multiple callbacks execute in registration order
# on_commit hooks are suppressed if any exception occurs`}
        </CodeBlock>
      </section>

      {/* Isolation Levels */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Isolation Levels</h2>
        <CodeBlock language="python">
{`from aquilia.models.transactions import atomic, IsolationLevel

# Default isolation level (depends on DB engine)
async with atomic(db):
    ...

# Explicit isolation level (PostgreSQL)
async with atomic(db, isolation_level=IsolationLevel.SERIALIZABLE):
    ...

# Available levels:
# IsolationLevel.READ_UNCOMMITTED
# IsolationLevel.READ_COMMITTED     (PG default)
# IsolationLevel.REPEATABLE_READ    (MySQL default)
# IsolationLevel.SERIALIZABLE       (strictest)`}
        </CodeBlock>
      </section>

      {/* Expression System */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Expression System</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia's expression system lets you build complex SQL expressions in Python. All expressions implement <code>as_sql()</code> for SQL generation.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Expression</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Purpose</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Example SQL</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {[
                ['F("field")', 'Column reference', 'field'],
                ['Value(42)', 'Literal value', '42'],
                ['RawSQL("expr")', 'Raw SQL fragment', 'expr'],
                ['Col("table", "field")', 'Qualified column', 'table.field'],
                ['Star()', 'All columns', '*'],
                ['CombinedExpression', 'Arithmetic: F("a") + F("b")', 'a + b'],
              ].map(([expr, purpose, sql]) => (
                <tr key={expr}>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{expr}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{purpose}</td>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{sql}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* When / Case */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>When / Case Expressions</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Build SQL CASE WHEN expressions for conditional logic in queries.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.expression import When, Case, Value, F

# Simple CASE WHEN
users = await (
    User.objects
    .annotate(
        tier=Case(
            When(points__gte=1000, then=Value("gold")),
            When(points__gte=500, then=Value("silver")),
            When(points__gte=100, then=Value("bronze")),
            default=Value("basic"),
        )
    )
    .all()
)

# CASE with expressions
orders = await (
    Order.objects
    .annotate(
        discount_price=Case(
            When(quantity__gte=100, then=F("price") * Value(0.8)),
            When(quantity__gte=50, then=F("price") * Value(0.9)),
            default=F("price"),
        )
    )
    .all()
)

# Conditional update
await (
    Product.objects
    .update(
        status=Case(
            When(stock=0, then=Value("out_of_stock")),
            When(stock__lt=10, then=Value("low_stock")),
            default=Value("in_stock"),
        )
    )
)`}
        </CodeBlock>
      </section>

      {/* Subqueries */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Subqueries</h2>
        <CodeBlock language="python">
{`from aquilia.models.expression import Subquery, Exists, OuterRef

# Subquery — embed a QuerySet as a scalar subquery
latest_comment = (
    Comment.objects
    .filter(post_id=OuterRef("id"))
    .order("-created_at")
    .values("text")
    .limit(1)
)

posts = await (
    Post.objects
    .annotate(latest_comment=Subquery(latest_comment))
    .all()
)

# Exists — boolean subquery for filtering
has_comments = Exists(
    Comment.objects.filter(post_id=OuterRef("id"))
)

posts_with_comments = await (
    Post.objects
    .filter(has_comments)
    .all()
)

# OuterRef — reference a column from the outer query
# Used inside Subquery/Exists to correlate with the parent query`}
        </CodeBlock>
      </section>

      {/* Database Functions */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Database Functions</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Built-in SQL function wrappers for use in annotations, filters, and updates:
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Category</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Functions</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Comparison</td>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>Coalesce, Greatest, Least, NullIf</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>String</td>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>Length, Upper, Lower, Trim, LTrim, RTrim, Concat, Substr, Replace</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Math</td>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>Abs, Round, Power</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Date/Time</td>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>Now</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</td>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>Cast, Func (custom), ExpressionWrapper</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models.expression import (
    Coalesce, Greatest, Least, NullIf,
    Length, Upper, Lower, Trim, Concat, Substr, Replace,
    Abs, Round, Power,
    Now, Cast, Func, ExpressionWrapper,
    F, Value,
)

# Coalesce — first non-NULL value
users = await (
    User.objects
    .annotate(display_name=Coalesce(F("nickname"), F("name"), Value("Anonymous")))
    .all()
)

# String functions
users = await (
    User.objects
    .annotate(
        name_len=Length(F("name")),
        upper_name=Upper(F("name")),
        initials=Concat(Substr(F("first_name"), 1, 1), Substr(F("last_name"), 1, 1)),
    )
    .all()
)

# Math functions
products = await (
    Product.objects
    .annotate(
        rounded_price=Round(F("price"), 2),
        abs_diff=Abs(F("price") - F("cost")),
    )
    .all()
)

# Cast — type conversion
users = await (
    User.objects
    .annotate(age_text=Cast(F("age"), "TEXT"))
    .all()
)

# Now() — current timestamp
await User.objects.filter(id=1).update(last_seen=Now())

# Greatest / Least
await Product.objects.annotate(
    effective_price=Least(F("price"), F("sale_price")),
).all()

# NullIf — return NULL if equal
await User.objects.annotate(
    real_name=NullIf(F("name"), Value("")),
).all()`}
        </CodeBlock>
      </section>

      {/* SQL Builder */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>SQL Builder API</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Low-level fluent SQL builders for when you need full control over query construction. Used internally by the Q class.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.sql_builder import (
    SQLBuilder, InsertBuilder, UpdateBuilder,
    DeleteBuilder, CreateTableBuilder, AlterTableBuilder,
    UpsertBuilder,
)

# SELECT builder
sql, params = (
    SQLBuilder("users")
    .select("id", "name", "email")
    .where("active = ?", True)
    .where("age >= ?", 18)
    .order_by("name ASC")
    .limit(10)
    .offset(20)
    .build()
)
# → ("SELECT id, name, email FROM users WHERE active = ? AND age >= ?
#     ORDER BY name ASC LIMIT 10 OFFSET 20", [True, 18])

# INSERT builder
sql, params = (
    InsertBuilder("users")
    .columns("name", "email", "active")
    .values("Alice", "alice@co.com", True)
    .returning("id")
    .build()
)

# UPDATE builder
sql, params = (
    UpdateBuilder("users")
    .set(name="Bob", email="bob@co.com")
    .where("id = ?", 42)
    .build()
)

# DELETE builder
sql, params = (
    DeleteBuilder("users")
    .where("active = ?", False)
    .build()
)

# CREATE TABLE builder
sql = (
    CreateTableBuilder("products")
    .column("id", "BIGSERIAL PRIMARY KEY")
    .column("name", "VARCHAR(200) NOT NULL")
    .column("price", "DECIMAL(10,2)")
    .if_not_exists()
    .build()
)

# ALTER TABLE builder
sql = (
    AlterTableBuilder("users")
    .add_column("phone", "VARCHAR(20)")
    .build()
)

# UPSERT builder (INSERT ... ON CONFLICT)
sql, params = (
    UpsertBuilder("users")
    .columns("email", "name")
    .values("alice@co.com", "Alice Updated")
    .conflict_columns("email")
    .update_columns("name")
    .build()
)`}
        </CodeBlock>
      </section>

      {/* Constraints */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Constraints</h2>
        <CodeBlock language="python">
{`from aquilia.models.constraint import CheckConstraint, ExclusionConstraint, Deferrable

class Product(Model):
    table = "products"
    name = CharField(max_length=200)
    price = DecimalField(max_digits=10, decimal_places=2)
    sale_price = DecimalField(max_digits=10, decimal_places=2, null=True)

    class Meta:
        constraints = [
            # Check constraint — arbitrary SQL condition
            CheckConstraint(
                check="price > 0",
                name="positive_price",
            ),
            # Sale price must be less than regular price
            CheckConstraint(
                check="sale_price IS NULL OR sale_price < price",
                name="valid_sale_price",
            ),
        ]

# Exclusion constraint (PostgreSQL only)
class Booking(Model):
    table = "bookings"
    room_id = IntegerField()
    during = DateTimeRangeField()

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="no_overlapping_bookings",
                expressions=[
                    ("room_id", "="),
                    ("during", "&&"),   # range overlap
                ],
            ),
        ]

# Deferrable constraints
# Deferrable.DEFERRED — check at transaction commit
# Deferrable.IMMEDIATE — check at statement end (default)`}
        </CodeBlock>
      </section>

      {/* Choices */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Choices — TextChoices & IntegerChoices</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Enum-like classes that generate <code>(value, label)</code> pairs for field choices.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.enums import Choices, TextChoices, IntegerChoices

class Status(TextChoices):
    DRAFT = "draft", "Draft"
    REVIEW = "review", "In Review"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"

class Priority(IntegerChoices):
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    CRITICAL = 4, "Critical"

class Article(Model):
    table = "articles"
    title = CharField(max_length=200)
    status = CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority = IntegerField(choices=Priority.choices, default=Priority.MEDIUM)

# Usage
article = Article(title="Test", status=Status.PUBLISHED)

# Access choices
Status.choices   # → [("draft", "Draft"), ("review", "In Review"), ...]
Status.values    # → ["draft", "review", "published", "archived"]
Status.labels    # → ["Draft", "In Review", "Published", "Archived"]
Status.names     # → ["DRAFT", "REVIEW", "PUBLISHED", "ARCHIVED"]

# Membership testing
Status.DRAFT in Status.values  # → True

# Custom Choices base class
class Choices:
    """Base class providing .choices, .values, .labels, .names properties."""`}
        </CodeBlock>
      </section>

      {/* Custom DB Functions */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Database Functions</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Extend the expression system with your own SQL functions using the <code>Func</code> base class.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.expression import Func, F, Value

# Custom function — wraps any SQL function
class DateTrunc(Func):
    function = "DATE_TRUNC"

# Usage
users = await (
    User.objects
    .annotate(
        signup_month=DateTrunc(Value("month"), F("created_at"))
    )
    .group_by("signup_month")
    .annotate(count=Count("id"))
    .order("signup_month")
    .values("signup_month", "count")
    .all()
)

# Generic Func usage
class JSONExtract(Func):
    function = "JSON_EXTRACT"

data = await (
    Config.objects
    .annotate(theme=JSONExtract(F("settings"), Value("$.theme")))
    .values("id", "theme")
    .all()
)`}
        </CodeBlock>
      </section>

      {/* select_for_update */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Pessimistic Locking — select_for_update</h2>
        <CodeBlock language="python">
{`from aquilia.models.transactions import atomic

# SELECT ... FOR UPDATE locks the selected rows
async with atomic(db):
    account = await (
        Account.objects
        .select_for_update()   # basic row lock
        .filter(id=42)
        .first()
    )
    account.balance -= 100
    await account.save(db)

# Options:
# .select_for_update(nowait=True)       — raise error instead of waiting
# .select_for_update(skip_locked=True)  — skip locked rows
# .select_for_update(of=["self"])       — lock only this table (not JOINed)
# .select_for_update(no_key=True)       — FOR NO KEY UPDATE (PG: weaker lock)`}
        </CodeBlock>
      </section>

      {/* Signals */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Signals</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Hook into the model lifecycle at every stage:
        </p>
        <CodeBlock language="python">
{`from aquilia.models.signals import (
    pre_save, post_save, pre_delete, post_delete,
    pre_init, post_init, class_prepared,
    m2m_changed, receiver,
)

@receiver(pre_save, sender=User)
async def hash_password(sender, instance, **kwargs):
    if instance._state.get("password_changed"):
        instance.password = hash_fn(instance.password)

@receiver(post_save, sender=User)
async def send_notification(sender, instance, created, **kwargs):
    if created:
        await send_welcome_email(instance.email)

@receiver(pre_delete, sender=User)
async def check_can_delete(sender, instance, **kwargs):
    if instance.is_superuser:
        raise PermissionError("Cannot delete superuser")

@receiver(class_prepared)
async def on_model_registered(sender, **kwargs):
    print(f"Model registered: {sender.__name__}")

# Signal.connect() / Signal.disconnect() for manual management
from aquilia.models.signals import Signal

custom_signal = Signal()
custom_signal.connect(my_handler, sender=MyModel)
await custom_signal.send(sender=MyModel, instance=obj)
custom_signal.disconnect(my_handler, sender=MyModel)`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex justify-between items-center pt-8 mt-8 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <Link
          to="/docs/models/migrations"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          <ArrowLeft className="w-4 h-4" /> Migrations
        </Link>
        <Link
          to="/docs/serializers/overview"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          Serializers <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  );
}