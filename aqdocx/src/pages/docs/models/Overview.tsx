import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Database } from 'lucide-react'

export function ModelsOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Database className="w-4 h-4" />Data Layer</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Models &amp; ORM</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia includes a pure-Python, metaclass-driven, async-first ORM. Define models with declarative fields, use the chainable <code className="text-aquilia-500">QuerySet</code> API, and let the migration system manage your schema.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Defining a Model</h2>
        <CodeBlock language="python" filename="models.py">{`from aquilia.models import Model
from aquilia.models.fields_module import (
    CharField, IntegerField, DateTimeField,
    BooleanField, EmailField, TextField,
)

class User(Model):
    table = "users"

    name = CharField(max_length=150)
    email = EmailField(max_length=255, unique=True)
    age = IntegerField(null=True)
    bio = TextField(blank=True)
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        get_latest_by = "created_at"
        indexes = [
            Index(fields=["email", "name"]),
        ]`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CRUD API</h2>
        <CodeBlock language="python" filename="CRUD Operations">{`# Create
user = await User.create(name="Alice", email="alice@test.com")

# Read
user = await User.get(pk=1)
user = await User.get(email="alice@test.com")

# Update (via instance)
user.name = "Alice Smith"
await user.save()

# Update (via QuerySet)
await User.objects.filter(pk=1).update(name="Alice Smith")

# Delete
await user.delete()

# Bulk operations
await User.bulk_create([
    {"name": "Bob", "email": "bob@test.com"},
    {"name": "Eve", "email": "eve@test.com"},
], batch_size=100)

# Get or Create
user, created = await User.get_or_create(
    email="alice@test.com",
    defaults={"name": "Alice", "age": 30}
)

# Update or Create
user, created = await User.update_or_create(
    email="alice@test.com",
    defaults={"name": "Alice Updated"}
)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>QuerySet API</h2>
        <CodeBlock language="python" filename="QuerySet Chaining">{`# All terminal methods are async
users = await User.objects.filter(active=True).order("-created_at").all()
count = await User.objects.filter(age__gt=18).count()
exists = await User.objects.filter(email="test@test.com").exists()
first = await User.objects.filter(active=True).first()

# Q objects for complex queries
from aquilia.models.query import QNode as QF

q = (QF(active=True) & QF(role="admin")) | QF(is_superuser=True)
admins = await User.objects.filter(q).all()

# Aggregation
from aquilia.models.aggregate import Avg, Count, Max
result = await User.objects.aggregate(avg_age=Avg("age"), total=Count("id"))

# Select related (JOIN eager loading)
posts = await Post.objects.select_related("author").all()

# Prefetch related (separate query)
users = await User.objects.prefetch_related("posts").all()`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 700 260" className="w-full h-auto">
            <rect width="700" height="260" rx="16" fill={isDark ? '#0A0A0A' : '#f8fafc'} />

            {[
              { x: 30, y: 30, w: 140, label: 'Model', sub: 'metaclass + fields', color: '#22c55e' },
              { x: 190, y: 30, w: 140, label: 'Manager', sub: 'objects descriptor', color: '#3b82f6' },
              { x: 350, y: 30, w: 140, label: 'Q (QuerySet)', sub: 'chainable builder', color: '#f59e0b' },
              { x: 510, y: 30, w: 160, label: 'AquiliaDatabase', sub: 'async execute', color: '#ef4444' },
            ].map((b, i) => (
              <g key={i}>
                <rect x={b.x} y={b.y} width={b.w} height="55" rx="10" fill={b.color + '15'} stroke={b.color} strokeWidth="1.5" />
                <text x={b.x + b.w / 2} y={b.y + 25} textAnchor="middle" fill={b.color} fontSize="13" fontWeight="700">{b.label}</text>
                <text x={b.x + b.w / 2} y={b.y + 43} textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="10">{b.sub}</text>
                {i < 3 && <line x1={b.x + b.w} y1={b.y + 27} x2={b.x + b.w + 20} y2={b.y + 27} stroke={isDark ? '#333' : '#cbd5e1'} strokeWidth="1.5" markerEnd="url(#modelArrow)" />}
              </g>
            ))}

            {/* Second row */}
            {[
              { x: 30, y: 120, w: 130, label: 'ModelRegistry', sub: 'global model map' },
              { x: 180, y: 120, w: 130, label: 'Signals', sub: 'pre_save, post_save' },
              { x: 330, y: 120, w: 130, label: 'SQL Builder', sub: 'INSERT / UPDATE / ...' },
              { x: 480, y: 120, w: 130, label: 'Migrations', sub: 'schema versioning' },
            ].map((b, i) => (
              <g key={i}>
                <rect x={b.x} y={b.y} width={b.w} height="50" rx="10" fill={isDark ? '#111' : '#f1f5f9'} stroke={isDark ? '#333' : '#cbd5e1'} strokeWidth="1" />
                <text x={b.x + b.w / 2} y={b.y + 22} textAnchor="middle" fill={isDark ? '#ccc' : '#334155'} fontSize="12" fontWeight="600">{b.label}</text>
                <text x={b.x + b.w / 2} y={b.y + 38} textAnchor="middle" fill={isDark ? '#666' : '#94a3b8'} fontSize="10">{b.sub}</text>
              </g>
            ))}

            {/* Relationships row */}
            <rect x="100" y="200" width="500" height="40" rx="10" fill={isDark ? '#1a1a2e' : '#e0f2fe'} stroke="#8b5cf6" strokeWidth="1.5" />
            <text x="350" y="225" textAnchor="middle" fill="#8b5cf6" fontSize="12" fontWeight="600">ForeignKey • OneToOne • ManyToMany • CASCADE / SET_NULL / PROTECT / RESTRICT</text>

            <defs>
              <marker id="modelArrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill={isDark ? '#333' : '#cbd5e1'} /></marker>
            </defs>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Signals</h2>
        <CodeBlock language="python" filename="Model Signals">{`from aquilia.models.signals import pre_save, post_save, pre_delete, post_delete

@pre_save.connect
async def hash_password(sender, instance, created, **kwargs):
    if created and hasattr(instance, 'password'):
        instance.password = hash_pw(instance.password)

@post_save.connect
async def send_welcome(sender, instance, created, **kwargs):
    if created and sender.__name__ == "User":
        await send_welcome_email(instance.email)

# Available signals:
# pre_init, post_init, pre_save, post_save,
# pre_delete, post_delete, class_prepared,
# m2m_changed, pre_migrate, post_migrate`}</CodeBlock>
      </section>
    </div>
  )
}
