import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Database } from 'lucide-react'

export function ModelsQuerySet() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Database className="w-4 h-4" />Data Layer</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>QuerySet API</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Q</code> class provides a chainable, immutable, async-terminal query builder. Every chain method returns a <em>new</em> Q instance — terminal methods like <code>.all()</code> are async and actually execute the query.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Chain Methods (return Q)</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Method</th>
              <th className="text-left py-3 text-aquilia-500">Description</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['filter(*q_nodes, **kwargs)', 'WHERE conditions with field lookups'],
                ['exclude(**kwargs)', 'Negated filter (WHERE NOT)'],
                ['where(clause, *args)', 'Raw parameterized WHERE (Aquilia-only)'],
                ['order(*fields)', 'ORDER BY — prefix with "-" for DESC'],
                ['limit(n)', 'LIMIT n'],
                ['offset(n)', 'OFFSET n'],
                ['distinct()', 'SELECT DISTINCT'],
                ['only(*fields)', 'Load only specified columns'],
                ['defer(*fields)', 'Defer loading of columns'],
                ['annotate(**exprs)', 'Add computed annotations'],
                ['group_by(*fields)', 'GROUP BY'],
                ['having(clause, *args)', 'HAVING (use after group_by)'],
                ['select_related(*fields)', 'JOIN-based eager loading'],
                ['prefetch_related(*lookups)', 'Separate-query prefetching'],
                ['select_for_update()', 'SELECT ... FOR UPDATE (locking)'],
                ['using(db_alias)', 'Target a specific database'],
                ['union(*qs, all=False)', 'UNION set operation'],
                ['intersection(*qs)', 'INTERSECT'],
                ['difference(*qs)', 'EXCEPT'],
              ].map(([method, desc], i) => (
                <tr key={i}>
                  <td className="py-2 pr-4 font-mono text-xs text-aquilia-400 whitespace-nowrap">{method}</td>
                  <td className={`py-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Terminal Methods (async)</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Method</th>
              <th className="text-left py-3 text-aquilia-500">Returns</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['await qs.all()', 'List[Model] — all matching records'],
                ['await qs.first()', 'Model | None — first record'],
                ['await qs.last()', 'Model | None — last record'],
                ['await qs.one()', 'Model — raises if != 1 result (Aquilia-only)'],
                ['await qs.get(**kw)', 'Model | None — single record by filters'],
                ['await qs.count()', 'int — count of matching records'],
                ['await qs.exists()', 'bool — True if any matching records'],
                ['await qs.update(**kw)', 'int — number of rows updated'],
                ['await qs.delete()', 'int — number of rows deleted'],
                ['await qs.aggregate(**exprs)', 'dict — aggregation results'],
                ['await qs.values(*fields)', 'List[dict] — raw dicts'],
                ['await qs.values_list(*f, flat=False)', 'List[tuple] or List[val]'],
              ].map(([method, ret], i) => (
                <tr key={i}>
                  <td className="py-2 pr-4 font-mono text-xs text-aquilia-400 whitespace-nowrap">{method}</td>
                  <td className={`py-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{ret}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Field Lookups</h2>
        <CodeBlock language="python" filename="Lookup Examples">{`# Exact (default)
await User.objects.filter(name="Alice").all()

# Comparison
await User.objects.filter(age__gt=18).all()       # >
await User.objects.filter(age__gte=18).all()      # >=
await User.objects.filter(age__lt=65).all()       # <
await User.objects.filter(age__lte=65).all()      # <=

# String lookups
await User.objects.filter(name__contains="ali").all()
await User.objects.filter(name__icontains="ali").all()    # case-insensitive
await User.objects.filter(name__startswith="A").all()
await User.objects.filter(name__endswith="ce").all()

# IN
await User.objects.filter(id__in=[1, 2, 3]).all()

# NULL
await User.objects.filter(age__isnull=True).all()

# Range
await User.objects.filter(age__range=(18, 65)).all()`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>QNode — Complex Queries</h2>
        <CodeBlock language="python" filename="QNode Composition">{`from aquilia.models.query import QNode as QF

# OR
q = QF(name="Alice") | QF(name="Bob")
users = await User.objects.filter(q).all()

# AND + OR
q = (QF(active=True) & QF(role="admin")) | QF(is_superuser=True)

# Negation
q = ~QF(banned=True)  # WHERE NOT banned = True

# Nest freely
q = QF(active=True) & (QF(age__gt=18) | QF(verified=True))`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom QuerySets</h2>
        <CodeBlock language="python" filename="Custom Manager">{`from aquilia.models.manager import QuerySet, Manager

class UserQuerySet(QuerySet):
    def active(self):
        return self.get_queryset().filter(active=True)

    def adults(self):
        return self.get_queryset().filter(age__gte=18)

UserManager = Manager.from_queryset(UserQuerySet)

class User(Model):
    table = "users"
    objects = UserManager()

# Chain custom + built-in:
users = await User.objects.active().adults().order("-name").limit(10).all()`}</CodeBlock>
      </section>
    </div>
  )
}
