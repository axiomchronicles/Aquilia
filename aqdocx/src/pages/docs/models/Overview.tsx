import { useTheme } from '../../../context/ThemeContext';
import { CodeBlock } from '../../../components/CodeBlock';
import { Database, ArrowRight, Box, Layers, Zap, Shield, GitBranch } from 'lucide-react';
import { Link } from 'react-router-dom';
import { NextSteps } from '../../../components/NextSteps'

export function ModelsOverview() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm mb-4">
          <Link to="/docs" className={isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}>Docs</Link>
          <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>/</span>
          <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>Models</span>
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Models
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Pure Python, Django-grade, async-first ORM — define your schema as Python classes with full validation, relationships, signals, and migration support.
        </p>
      </div>

      {/* Architecture callout */}
      <div className={`rounded-lg p-6 mb-8 ${isDark ? 'bg-aquilia-500/5 border border-aquilia-500/20' : 'bg-blue-50/50 border border-blue-200/50'}`}>
        <div className="flex items-start gap-3">
          <Database className={`w-6 h-6 mt-0.5 ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`} />
          <div>
            <h3 className={`font-semibold mb-2 ${isDark ? 'text-aquilia-300' : 'text-blue-700'}`}>Architecture</h3>
            <p className={isDark ? 'text-aquilia-200' : 'text-blue-700'}>
              Aquilia's model system uses a metaclass-driven architecture inspired by Django. Models are plain Python classes with field descriptors.
              A <code>ModelMeta</code> metaclass collects fields, injects auto-PKs, parses the inner <code>Meta</code> class, registers models in a global
              registry, and attaches a default <code>Manager</code>. All terminal query methods are async — every database access returns an awaitable.
            </p>
          </div>
        </div>
      </div>

      {/* Quick start */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Quick Start</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Define a model by subclassing <code>Model</code> and declaring field attributes. Set the <code>table</code> attribute to name the
          database table, or let Aquilia generate one from the class name (lowercased).
        </p>
        <CodeBlock language="python" filename="models.py">
{`from aquilia.models import Model
from aquilia.models.fields_module import (
    CharField, EmailField, BooleanField, DateTimeField,
    IntegerField, ForeignKey, Index,
)

class User(Model):
    table = "users"

    name = CharField(max_length=150)
    email = EmailField(unique=True)
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [Index(fields=["email"])]

class Post(Model):
    table = "posts"

    title = CharField(max_length=200)
    body = CharField(max_length=None, blank=True)  # TextField
    author = ForeignKey("User", on_delete="CASCADE", related_name="posts")
    views = IntegerField(default=0)
    published_at = DateTimeField(null=True)`}
        </CodeBlock>
      </section>

      {/* CRUD */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>CRUD Operations</h2>
        <CodeBlock language="python">
{`# CREATE — two ways
user = User(name="Alice", email="alice@co.com")
await user.save(db)          # INSERT — assigns user.id

user = await User.objects.create(db, name="Bob", email="bob@co.com")

# READ
users = await User.objects.filter(active=True).order("-created_at").all()
user  = await User.objects.get(pk=1)           # raises if missing
user  = await User.objects.filter(id=1).first()  # None if missing

# UPDATE — instance
user.name = "Bob Smith"
await user.save(db)          # UPDATE

# UPDATE — bulk (does not fire signals)
await User.objects.filter(active=False).update(active=True)

# DELETE — instance
await user.delete_instance(db)   # DELETE WHERE id = ?

# DELETE — bulk
await User.objects.filter(created_at__lt=cutoff).delete()`}
        </CodeBlock>
      </section>

      {/* Model instance methods */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Instance Methods</h2>
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
                ['save(db, update_fields=None)', 'INSERT or UPDATE. Fires pre_save / post_save signals.'],
                ['delete_instance(db)', 'DELETE this row. Fires pre_delete / post_delete signals.'],
                ['full_clean()', 'Run all field-level validators. Raises ValidationError if invalid.'],
                ['to_dict(fields=None, exclude=None)', 'Serialize instance to a plain dict. Optional field filtering.'],
                ['from_row(row)', 'Class method. Construct a model instance from a DB row dict.'],
                ['related(name)', 'Async. Load a related object (FK, O2O, M2M) by relation name.'],
                ['attach(db, rel, ids)', 'Async. Add M2M relationships by target PKs.'],
                ['detach(db, rel, ids)', 'Async. Remove M2M relationships by target PKs.'],
                ['query()', 'Class method shortcut → Q (QuerySet) instance.'],
                ['generate_create_table_sql()', 'Returns CREATE TABLE SQL for this model.'],
                ['fingerprint()', 'SHA-256 hash of the model schema for migration diffing.'],
              ].map(([method, desc]) => (
                <tr key={method}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{method}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`# Validation before save
user = User(name="", email="bad-email")
try:
    user.full_clean()
except ValidationError as e:
    print(e.errors)  # {"name": ["This field cannot be blank"], ...}

# to_dict
user.to_dict()
# → {"id": 1, "name": "Alice", "email": "alice@co.com", "active": True, ...}

user.to_dict(fields=["id", "name"])
# → {"id": 1, "name": "Alice"}

user.to_dict(exclude=["created_at"])
# → {"id": 1, "name": "Alice", "email": "...", "active": True}

# update_fields — only update specific columns
user.name = "New Name"
await user.save(db, update_fields=["name"])
# → UPDATE users SET name = ? WHERE id = ?`}
        </CodeBlock>
      </section>

      {/* Meta class */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Meta Class Options</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The inner <code>Meta</code> class on a model controls table-level behavior. It is parsed by <code>ModelMeta</code> into an <code>Options</code> instance stored as <code>Model._meta</code>.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Option</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {[
                ['ordering', 'list[str]', 'Default ORDER BY. Prefix "-" for DESC.'],
                ['indexes', 'list[Index]', 'Database indexes to create.'],
                ['constraints', 'list', 'CheckConstraint, UniqueConstraint, etc.'],
                ['abstract', 'bool', 'If True, no table created. Fields are inherited.'],
                ['db_table', 'str', 'Override table name (alternative to class-level table attr).'],
                ['unique_together', 'list[tuple]', 'Multi-column UNIQUE constraints.'],
                ['verbose_name', 'str', 'Human-readable model name.'],
                ['verbose_name_plural', 'str', 'Plural human-readable model name.'],
                ['managed', 'bool', 'If False, Aquilia will not create/migrate this table.'],
                ['primary_key', 'CompositePrimaryKey', 'Composite PK spanning multiple columns.'],
              ].map(([opt, type_, desc]) => (
                <tr key={opt}>
                  <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{opt}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type_}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models.fields_module import Index, UniqueConstraint
from aquilia.models.constraint import CheckConstraint

class Article(Model):
    table = "articles"
    title = CharField(max_length=200)
    status = CharField(max_length=20, default="draft")
    price = DecimalField(max_digits=10, decimal_places=2, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["title"]),
            Index(fields=["status", "created_at"]),
        ]
        constraints = [
            UniqueConstraint(fields=["title"], name="uq_title"),
            CheckConstraint(check="price IS NULL OR price >= 0", name="ck_price"),
        ]
        verbose_name = "article"
        verbose_name_plural = "articles"`}
        </CodeBlock>
      </section>

      {/* Model Registry */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Registry</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Every model is automatically registered in a global <code>ModelRegistry</code> by the metaclass. The registry handles
          table creation order (topological sort for FK dependencies) and lazy relation resolution.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.registry import ModelRegistry

# Get a registered model by name
UserModel = ModelRegistry.get("User")

# List all registered models
all_models = ModelRegistry.all_models()

# Create all tables (respects FK ordering)
await ModelRegistry.create_tables(db)

# Drop all tables (reverse order)
await ModelRegistry.drop_tables(db)

# Set a database connection for a specific model
ModelRegistry.set_database(User, db)

# Resolve forward reference strings → actual model classes
ModelRegistry._resolve_relations()`}
        </CodeBlock>
      </section>

      {/* Abstract models */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Abstract Models</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Mark a model with <code>abstract = True</code> in its Meta class. Abstract models share fields with subclasses but have no database table themselves.
        </p>
        <CodeBlock language="python">
{`class TimestampedModel(Model):
    """Shared base with created_at/updated_at for all models."""
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # no table created

class User(TimestampedModel):
    table = "users"
    name = CharField(max_length=150)
    # Inherits: created_at, updated_at

class Post(TimestampedModel):
    table = "posts"
    title = CharField(max_length=200)
    # Inherits: created_at, updated_at`}
        </CodeBlock>
      </section>

      {/* Features grid */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>What's Included</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { icon: Box, title: 'Fields', desc: '40+ field types: numeric, text, date/time, JSON, UUID, PostgreSQL-specific (Array, HStore, Range, CI), and composite fields.' },
            { icon: Layers, title: 'QuerySet', desc: 'Immutable clone-on-write async query builder: 20+ chain methods, 15+ async terminal methods, lookups, QNode composition.' },
            { icon: GitBranch, title: 'Relationships', desc: 'ForeignKey, OneToOneField, ManyToManyField with through models. select_related (JOIN) and prefetch_related (separate query).' },
            { icon: Zap, title: 'Migrations', desc: '4-layer system: auto-generation, DSL operations, runner with rollback, and low-level DDL ops.' },
            { icon: Shield, title: 'Signals', desc: 'pre_save, post_save, pre_delete, post_delete, m2m_changed, class_prepared, pre/post_migrate and more.' },
            { icon: Database, title: 'Transactions', desc: 'atomic() context manager with nested savepoints, on_commit/on_rollback hooks, isolation levels, and row-locking.' },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className={`p-4 rounded-lg border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-5 h-5 ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`} />
                <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</h3>
              </div>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Navigation */}
      <div className={`flex justify-end items-center pt-8 mt-8 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <Link
          to="/docs/models/fields"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          Fields <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  );
}