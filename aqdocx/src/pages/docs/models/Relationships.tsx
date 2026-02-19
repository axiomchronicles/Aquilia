import { useTheme } from '../../../context/ThemeContext';
import { CodeBlock } from '../../../components/CodeBlock';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { NextSteps } from '../../../components/NextSteps'

export function ModelsRelationships() {
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
          <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>Relationships</span>
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Relationships
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          ForeignKey, OneToOne, ManyToMany — how Aquilia maps database relationships to Python objects, with cascading deletes, eager loading, and through models.
        </p>
      </div>

      {/* ForeignKey */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>ForeignKey</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Creates a many-to-one relationship. Stores the related object's primary key in a <code>_id</code> column and provides lazy/eager access to the related instance.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>to</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str | type</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Target model class or string for lazy reference (e.g. "User")</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>on_delete</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Delete behavior: CASCADE, SET_NULL, PROTECT, etc.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>related_name</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str | None</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Name for reverse relation on the target model</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>to_field</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Target field to reference (default: "id")</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>db_constraint</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>bool</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Whether to create a FOREIGN KEY constraint (default: True)</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models import Model
from aquilia.models.fields_module import CharField, ForeignKey, IntegerField

class User(Model):
    table = "users"
    name = CharField(max_length=100)

class Post(Model):
    table = "posts"
    title = CharField(max_length=200)
    author = ForeignKey(to="User", on_delete="CASCADE", related_name="posts")

# The ForeignKey creates a column: author_id INTEGER REFERENCES users(id)

# Accessing the relationship
post = await Post.objects.first()
post.author_id          # → 1 (raw FK value, always available)
author = await post.related("author")  # → <User id=1> (loaded from DB)

# Eager loading via select_related (JOIN)
posts = await (
    Post.objects
    .select_related("author")
    .filter(author__name="Alice")
    .all()
)
posts[0].author  # already loaded, no extra query`}
        </CodeBlock>
      </section>

      {/* on_delete Behaviors */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>on_delete Behaviors</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>on_delete</code> parameter controls what happens to referencing rows when the referenced (parent) row is deleted.
          Aquilia implements these behaviors in the <code>OnDeleteHandler</code>.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Behavior</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>SQL</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>CASCADE</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ON DELETE CASCADE</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Delete referencing rows (most common)</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>SET_NULL</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ON DELETE SET NULL</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Set FK to NULL (requires <code>null=True</code>)</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>PROTECT</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>—</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Raise <code>ProtectedError</code> to prevent deletion</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>RESTRICT</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ON DELETE RESTRICT</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Raise <code>RestrictedError</code> (checked at DB level)</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>SET_DEFAULT</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ON DELETE SET DEFAULT</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Set FK to its default value</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>DO_NOTHING</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ON DELETE NO ACTION</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>No action. DB may raise IntegrityError.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>SET(value)</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>—</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Set FK to a fixed value or callable result</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models.deletion import CASCADE, SET_NULL, PROTECT, SET, RESTRICT
from aquilia.models.deletion import ProtectedError, RestrictedError

class Comment(Model):
    table = "comments"
    post = ForeignKey("Post", on_delete="CASCADE")        # delete with post
    author = ForeignKey("User", on_delete="SET_NULL", null=True)  # keep comment
    category = ForeignKey("Category", on_delete="PROTECT")  # block delete

# SET with a callable
def get_default_user():
    return 1  # fallback user ID

class AuditLog(Model):
    table = "audit_logs"
    user = ForeignKey("User", on_delete="SET", set_value=get_default_user)`}
        </CodeBlock>
      </section>

      {/* OneToOneField */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>OneToOneField</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          A <code>ForeignKey</code> with <code>unique=True</code>. Ensures each parent has at most one related child.
          Accessed via <code>.related()</code> — returns a single instance (not a queryset).
        </p>
        <CodeBlock language="python">
{`from aquilia.models.fields_module import OneToOneField

class Profile(Model):
    table = "profiles"
    user = OneToOneField("User", on_delete="CASCADE", related_name="profile")
    bio = TextField(blank=True)
    avatar_url = URLField(null=True)

# Access
profile = await Profile.objects.select_related("user").first()
profile.user  # → <User id=1>

# Reverse access
user = await User.objects.first()
profile = await user.related("profile")  # → <Profile> or None`}
        </CodeBlock>
      </section>

      {/* ManyToManyField */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>ManyToManyField</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Creates a many-to-many relationship with an auto-generated junction table. Supports custom junction tables via <code>through</code>.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>to</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str | type</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Target model</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>related_name</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str | None</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Reverse accessor name</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>through</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str | None</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Custom junction model class name</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>through_fields</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>tuple | None</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Tuple of (source_fk, target_fk) field names</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models.fields_module import ManyToManyField

class Article(Model):
    table = "articles"
    title = CharField(max_length=200)
    tags = ManyToManyField("Tag", related_name="articles")

class Tag(Model):
    table = "tags"
    name = CharField(max_length=50, unique=True)

# Auto-generated junction table:
# articles_tags (id, article_id, tag_id)
# with FOREIGN KEY constraints and ON DELETE CASCADE`}
        </CodeBlock>
      </section>

      {/* M2M Operations */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>M2M Operations: attach / detach</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Use <code>attach()</code> and <code>detach()</code> on model instances to manage many-to-many relationships.
          Both methods fire the <code>m2m_changed</code> signal.
        </p>
        <CodeBlock language="python">
{`article = await Article.objects.first()

# Attach — inserts junction rows
await article.attach(db, "tags", [tag1.id, tag2.id])
# INSERT INTO articles_tags (article_id, tag_id) VALUES (?, ?), (?, ?)

# Detach — removes junction rows
await article.detach(db, "tags", [tag1.id])
# DELETE FROM articles_tags WHERE article_id = ? AND tag_id = ?

# Read related
tags = await article.related("tags")  # → [<Tag>, <Tag>, ...]

# Reverse
articles = await tag.related("articles")  # → [<Article>, ...]`}
        </CodeBlock>
      </section>

      {/* Through Models */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Through Models</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Custom junction tables with extra columns. Use <code>through</code> and <code>through_fields</code> on ManyToManyField.
        </p>
        <CodeBlock language="python">
{`class Membership(Model):
    table = "memberships"
    user = ForeignKey("User", on_delete="CASCADE")
    group = ForeignKey("Group", on_delete="CASCADE")
    role = CharField(max_length=20, default="member")
    joined_at = DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "group"], name="uq_membership"),
        ]

class Group(Model):
    table = "groups"
    name = CharField(max_length=100)
    members = ManyToManyField(
        "User",
        through="Membership",
        through_fields=("group", "user"),
        related_name="groups",
    )

# Query through model directly for extra data
memberships = await (
    Membership.objects
    .select_related("user", "group")
    .filter(role="admin")
    .all()
)

# Or use M2M related access
group = await Group.objects.first()
members = await group.related("members")  # → [<User>, ...]`}
        </CodeBlock>
      </section>

      {/* Eager Loading */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Eager Loading</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia provides two strategies to avoid N+1 queries:
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Strategy</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>SQL</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Best For</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>select_related()</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>JOIN</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>ForeignKey, OneToOne — single objects</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>prefetch_related()</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Separate query + in-memory</td>
                <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>ManyToMany, reverse FK — collections</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models.query import Prefetch

# select_related — SQL JOIN (ForeignKey/OneToOne)
posts = await (
    Post.objects
    .select_related("author", "category")
    .all()
)
# One query: SELECT posts.*, users.*, categories.* FROM posts
#   JOIN users ON ... JOIN categories ON ...

# prefetch_related — separate queries (M2M, reverse FK)
users = await (
    User.objects
    .prefetch_related("posts", "groups")
    .all()
)
# Query 1: SELECT * FROM users
# Query 2: SELECT * FROM posts WHERE author_id IN (1, 2, 3, ...)
# Query 3: SELECT * FROM groups JOIN memberships ...

# Custom prefetch with filtered inner query
users = await (
    User.objects
    .prefetch_related(
        Prefetch(
            "posts",
            queryset=Post.objects.filter(status="published").order("-created_at").limit(5),
            to_attr="recent_posts",
        )
    )
    .all()
)
# user.recent_posts → last 5 published posts per user`}
        </CodeBlock>
      </section>

      {/* Forward References */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Forward References & Lazy Resolution</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Use string names for models that haven't been defined yet. The <code>ModelRegistry._resolve_relations()</code> method resolves these after all models are registered.
        </p>
        <CodeBlock language="python">
{`# Forward reference — "Comment" doesn't exist yet
class Post(Model):
    table = "posts"
    title = CharField(max_length=200)
    # Use string name for forward reference
    best_comment = ForeignKey("Comment", on_delete="SET_NULL", null=True)

# Defined later — registry resolves the reference
class Comment(Model):
    table = "comments"
    post = ForeignKey("Post", on_delete="CASCADE")
    text = TextField()

# Self-referential relationships
class Category(Model):
    table = "categories"
    name = CharField(max_length=100)
    parent = ForeignKey("self", on_delete="CASCADE", null=True, related_name="children")

# Resolution happens automatically during create_tables()
# or can be triggered manually:
from aquilia.models.registry import ModelRegistry
ModelRegistry._resolve_relations()`}
        </CodeBlock>
      </section>

      {/* Signals */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Relationship Signals</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>m2m_changed</code> signal fires when M2M relationships are modified via <code>attach()</code> / <code>detach()</code>.
        </p>
        <CodeBlock language="python">
{`from aquilia.models.signals import m2m_changed, receiver

@receiver(m2m_changed, sender=Article)
async def on_tags_changed(sender, instance, action, pk_set, **kwargs):
    """
    action: "pre_add", "post_add", "pre_remove", "post_remove", "pre_clear", "post_clear"
    pk_set: set of related PKs being added/removed
    """
    if action == "post_add":
        print(f"Tags added to {instance}: {pk_set}")
    elif action == "post_remove":
        print(f"Tags removed from {instance}: {pk_set}")`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex justify-between items-center pt-8 mt-8 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <Link
          to="/docs/models/queryset"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          <ArrowLeft className="w-4 h-4" /> QuerySet
        </Link>
        <Link
          to="/docs/models/migrations"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          Migrations <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  );
}