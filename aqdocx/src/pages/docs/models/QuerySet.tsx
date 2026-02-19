import { useTheme } from '../../../context/ThemeContext';
import { CodeBlock } from '../../../components/CodeBlock';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { NextSteps } from '../../../components/NextSteps'

export function ModelsQuerySet() {
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
          <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>QuerySet</span>
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            QuerySet
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia's query engine: an immutable, clone-on-write async query builder with 20+ chain methods and 15+ terminal methods.
        </p>
      </div>

      {/* Obtaining a QuerySet */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Obtaining a QuerySet</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Every model class has a <code>Manager</code> descriptor injected by the metaclass. Calling any method on it returns a new <code>Q</code> instance — Aquilia's immutable QuerySet.
        </p>
        <CodeBlock language="python">
{`# Access the manager — returns Q instances
User.objects.filter(active=True)      # Q clone
User.objects.all()                    # Q clone
User.query()                          # shortcut → Q clone

# The Q class is immutable: every chain call returns a NEW copy
q1 = User.objects.filter(active=True)
q2 = q1.filter(age__gt=18)  # q1 is NOT modified
q3 = q2.order("-created_at")  # q2 is NOT modified`}
        </CodeBlock>
      </section>

      {/* Chain Methods */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Chain Methods</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Chain methods return a new <code>Q</code> clone with the modification applied. They can be composed in any order.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {[
                ['filter(**kw)', 'AND conditions to WHERE clause'],
                ['exclude(**kw)', 'AND NOT conditions to WHERE'],
                ['where(*raw)', 'Raw SQL WHERE fragment'],
                ['order(*fields)', 'ORDER BY. Prefix "-" for DESC'],
                ['limit(n)', 'LIMIT n rows'],
                ['offset(n)', 'OFFSET n rows'],
                ['distinct()', 'SELECT DISTINCT'],
                ['only(*fields)', 'SELECT only these columns'],
                ['defer(*fields)', 'Exclude columns from SELECT'],
                ['annotate(**kw)', 'Add computed expressions to SELECT'],
                ['group_by(*fields)', 'GROUP BY clause'],
                ['having(**kw)', 'HAVING clause (requires group_by)'],
                ['select_related(*fk)', 'JOIN and load FK relations in one query'],
                ['prefetch_related(*rel)', 'Separate query + in-memory join'],
                ['select_for_update()', 'SELECT ... FOR UPDATE (row locking)'],
                ['union(other)', 'UNION of two QuerySets'],
                ['intersection(other)', 'INTERSECT of two QuerySets'],
                ['difference(other)', 'EXCEPT of two QuerySets'],
                ['none()', 'Returns empty Q (no SQL executed)'],
                ['apply_q(qnode)', 'Apply a QNode (AND/OR/NOT composition)'],
              ].map(([method, desc]) => (
                <tr key={method}>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{method}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`# Complex chained query
users = await (
    User.objects
    .filter(active=True, role="admin")
    .exclude(email__endswith="@test.com")
    .annotate(post_count=Count("posts"))
    .order("-post_count", "name")
    .only("id", "name", "email")
    .limit(20)
    .offset(40)
    .all()
)

# select_related — eager load via JOIN
orders = await (
    Order.objects
    .select_related("user", "product")
    .filter(status="pending")
    .all()
)
# Each order.user and order.product is already loaded

# select_for_update — row locking within a transaction
async with atomic(db):
    account = await (
        Account.objects
        .select_for_update(nowait=True, of=["self"])
        .filter(id=42)
        .first()
    )
    account.balance -= 100
    await account.save(db)`}
        </CodeBlock>
      </section>

      {/* Terminal Methods */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Terminal Methods (async)</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Terminal methods execute SQL and return results. All are <code>async</code>.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {[
                ['all()', 'list[Model]', 'Execute query, return all rows as model instances'],
                ['first()', 'Model | None', 'First row or None (adds LIMIT 1)'],
                ['last()', 'Model | None', 'Last row or None (reverses order, LIMIT 1)'],
                ['one()', 'Model', 'Exactly one row or raises ValueError'],
                ['count()', 'int', 'SELECT COUNT(*) — no rows fetched'],
                ['exists()', 'bool', 'SELECT EXISTS — no rows fetched'],
                ['update(**kw)', 'int', 'Bulk UPDATE, returns affected rows count'],
                ['delete()', 'int', 'Bulk DELETE, returns affected rows count'],
                ['values(*fields)', 'list[dict]', 'Return dicts instead of model instances'],
                ['values_list(*fields)', 'list[tuple]', 'Return tuples. flat=True for single-field'],
                ['in_bulk(ids)', 'dict', 'Map of id → model for given IDs'],
                ['aggregate(**kw)', 'dict', 'Compute aggregates (Sum, Avg, etc.)'],
                ['explain()', 'str', 'EXPLAIN query plan'],
                ['latest(field)', 'Model', 'Most recent row by field'],
                ['earliest(field)', 'Model', 'Oldest row by field'],
              ].map(([method, ret, desc]) => (
                <tr key={method}>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{method}</td>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{ret}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`# Basic terminal methods
count = await User.objects.filter(active=True).count()
exists = await User.objects.filter(email="admin@co.com").exists()
admin = await User.objects.filter(role="admin").first()

# values / values_list
emails = await User.objects.filter(active=True).values_list("email", flat=True)
# → ["alice@co.com", "bob@co.com", ...]

user_data = await User.objects.values("id", "name", "email").all()
# → [{"id": 1, "name": "Alice", "email": "..."}, ...]

# in_bulk
users_map = await User.objects.in_bulk([1, 2, 3])
# → {1: <User id=1>, 2: <User id=2>, 3: <User id=3>}

# Bulk operations
updated = await User.objects.filter(role="guest").update(active=False)
deleted = await User.objects.filter(active=False).delete()

# latest / earliest
newest = await Post.objects.latest("published_at")
oldest = await Post.objects.earliest("created_at")`}
        </CodeBlock>
      </section>

      {/* Lookups */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lookups</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Use double-underscore suffixes in <code>filter()</code> / <code>exclude()</code> for rich comparisons. Lookups are resolved
          by the <code>LookupRegistry</code> and compiled to SQL.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Lookup</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>SQL Equivalent</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Example</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {[
                ['exact', '= value', 'filter(name__exact="Alice")'],
                ['iexact', 'LOWER(col) = LOWER(val)', 'filter(name__iexact="alice")'],
                ['contains', "LIKE '%val%'", 'filter(name__contains="li")'],
                ['icontains', "ILIKE '%val%'", 'filter(name__icontains="LI")'],
                ['startswith', "LIKE 'val%'", 'filter(name__startswith="Al")'],
                ['endswith', "LIKE '%ce'", 'filter(name__endswith="ce")'],
                ['in', 'IN (a, b, c)', 'filter(id__in=[1, 2, 3])'],
                ['gt / gte / lt / lte', '> / >= / < / <=', 'filter(age__gte=18)'],
                ['range', 'BETWEEN a AND b', 'filter(age__range=(18, 65))'],
                ['isnull', 'IS NULL / IS NOT NULL', 'filter(email__isnull=False)'],
              ].map(([lookup, sql, example]) => (
                <tr key={lookup}>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{lookup}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{sql}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{example}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* QNode Composition */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>QNode — AND / OR / NOT Composition</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>QNode</code> lets you build complex boolean expressions using Python operators: <code>&amp;</code> (AND), <code>|</code> (OR), <code>~</code> (NOT).
        </p>
        <CodeBlock language="python">
{`from aquilia.models.query import QNode

# OR condition
active_admins = QNode(active=True) & QNode(role="admin")
suspended_or_guest = QNode(status="suspended") | QNode(role="guest")

# NOT condition
not_staff = ~QNode(is_staff=True)

# Complex composition
q = (QNode(active=True) & QNode(age__gte=18)) | ~QNode(role="guest")

# Apply to QuerySet
users = await User.objects.apply_q(q).order("name").all()

# Nested composition
complex_q = (
    (QNode(country="US") | QNode(country="CA"))
    & QNode(age__gte=21)
    & ~QNode(banned=True)
)
results = await User.objects.apply_q(complex_q).all()`}
        </CodeBlock>
      </section>

      {/* Aggregation */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Aggregation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aggregate functions compute summary values. Use <code>.aggregate()</code> for whole-table aggregates or <code>.annotate()</code> with <code>.group_by()</code> for per-group.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Function</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>SQL</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Notes</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {[
                ['Sum("field")', 'SUM(field)', 'Numeric sum'],
                ['Avg("field")', 'AVG(field)', 'Average'],
                ['Count("field")', 'COUNT(field)', 'Count. distinct=True for COUNT(DISTINCT)'],
                ['Max("field")', 'MAX(field)', 'Maximum value'],
                ['Min("field")', 'MIN(field)', 'Minimum value'],
                ['StdDev("field")', 'STDDEV(field)', 'Standard deviation. sample=True for STDDEV_SAMP'],
                ['Variance("field")', 'VARIANCE(field)', 'Variance. sample=True for VAR_SAMP'],
              ].map(([func, sql, notes]) => (
                <tr key={func}>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{func}</td>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{sql}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models.aggregate import Sum, Avg, Count, Max, Min

# Whole-table aggregate
stats = await Order.objects.aggregate(
    total=Sum("amount"),
    avg_amount=Avg("amount"),
    order_count=Count("id"),
    max_amount=Max("amount"),
)
# → {"total": 50000, "avg_amount": 250.0, "order_count": 200, "max_amount": 999}

# Per-group annotation
by_category = await (
    Product.objects
    .annotate(total_sales=Sum("sales"))
    .group_by("category")
    .order("-total_sales")
    .values("category", "total_sales")
    .all()
)
# → [{"category": "Electronics", "total_sales": 50000}, ...]

# PostgreSQL-specific aggregates
from aquilia.models.aggregate import ArrayAgg, StringAgg

grouped = await (
    Tag.objects
    .annotate(
        names=ArrayAgg("name"),
        csv=StringAgg("name", delimiter=", "),
    )
    .group_by("category")
    .values("category", "names", "csv")
    .all()
)`}
        </CodeBlock>
      </section>

      {/* F() Expressions */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>F() Expressions</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>F()</code> references a database column by name, enabling field-to-field comparisons and in-place updates without loading data into Python.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.expression import F

# Field-to-field comparison
users = await User.objects.filter(login_count__gt=F("post_count")).all()

# Arithmetic on F expressions
await Product.objects.filter(id=42).update(stock=F("stock") - 1)
await Product.objects.filter(id=42).update(price=F("price") * 1.1)

# F in annotations
users = await (
    User.objects
    .annotate(activity_ratio=F("login_count") / F("post_count"))
    .order("-activity_ratio")
    .all()
)

# Combine F with values
from aquilia.models.expression import Value
await Product.objects.update(name=F("name") + Value(" (archived)"))`}
        </CodeBlock>
      </section>

      {/* Managers & Custom QuerySets */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Managers & Custom QuerySets</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Every model gets a <code>Manager</code> as <code>objects</code>. You can customize the manager or attach a custom QuerySet class.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.manager import Manager, BaseManager, QuerySet

# Custom QuerySet with reusable methods
class ArticleQuerySet(QuerySet):
    def published(self):
        return self.filter(status="published")
    
    def by_author(self, author_id):
        return self.filter(author_id=author_id)
    
    def recent(self, days=7):
        cutoff = datetime.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff)

# Attach to model via Manager.from_queryset()
class Article(Model):
    table = "articles"
    title = CharField(max_length=200)
    status = CharField(max_length=20)
    author_id = IntegerField()
    created_at = DateTimeField(auto_now_add=True)

    # Manager forwards all QuerySet methods
    objects = Manager.from_queryset(ArticleQuerySet)()

# Usage — methods chain naturally
recent_posts = await (
    Article.objects
    .published()
    .by_author(42)
    .recent(days=30)
    .order("-created_at")
    .all()
)

# BaseManager — the underlying class
# Forwards 30+ methods to Q: filter, exclude, all, first, count, etc.
# Manager is a descriptor — returns a BoundManager per model class`}
        </CodeBlock>
      </section>

      {/* Prefetch Objects */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Prefetch Objects</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>Prefetch</code> objects let you customize the query used for prefetch_related lookups.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.query import Prefetch

# Simple prefetch — separate query, in-memory join
users = await (
    User.objects
    .prefetch_related("posts", "comments")
    .all()
)

# Custom Prefetch — control the inner query
users = await (
    User.objects
    .prefetch_related(
        Prefetch(
            "posts",
            queryset=Post.objects.filter(status="published").order("-created_at"),
            to_attr="recent_posts",  # store in custom attribute
        )
    )
    .all()
)
# user.recent_posts → only published posts, sorted`}
        </CodeBlock>
      </section>

      {/* Set Operations */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Set Operations</h2>
        <CodeBlock language="python">
{`# UNION — combine results from two queries
admins = User.objects.filter(role="admin")
mods = User.objects.filter(role="moderator")
staff = admins.union(mods)  # UNION (removes duplicates)

# INTERSECT — rows in both queries
active = User.objects.filter(active=True)
premium = User.objects.filter(plan="premium")
active_premium = active.intersection(premium)

# EXCEPT — rows in first but not second
all_users = User.objects.all()
banned = User.objects.filter(banned=True)
good_users = all_users.difference(banned)`}
        </CodeBlock>
      </section>

      {/* Slicing */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Slicing</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          QuerySets support Python slice syntax, which translates to <code>LIMIT</code> and <code>OFFSET</code>.
        </p>
        <CodeBlock language="python">
{`# Slice via Python syntax
q = User.objects.order("name")
page = q[20:40]  # OFFSET 20 LIMIT 20

# Single index
first = q[0]     # LIMIT 1
tenth = q[9]     # OFFSET 9 LIMIT 1

# Step is NOT supported (raises TypeError)`}
        </CodeBlock>
      </section>

      {/* SQL Introspection */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>SQL Introspection</h2>
        <CodeBlock language="python">
{`# View the generated SQL without executing
q = User.objects.filter(active=True).order("name").limit(10)
sql, params = q.build_select()
print(sql)
# → SELECT * FROM users WHERE active = ? ORDER BY name LIMIT 10
print(params)
# → [True]

# EXPLAIN — view query execution plan
plan = await User.objects.filter(active=True).explain()
print(plan)
# → QUERY PLAN: Seq Scan on users ...`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex justify-between items-center pt-8 mt-8 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <Link
          to="/docs/models/fields"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          <ArrowLeft className="w-4 h-4" /> Fields
        </Link>
        <Link
          to="/docs/models/relationships"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          Relationships <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  );
}