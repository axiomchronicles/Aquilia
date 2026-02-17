import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Database } from 'lucide-react'

export function ModelsRelationships() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Database className="w-4 h-4" />Data Layer</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Relationships</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia supports <code className="text-aquilia-500">ForeignKey</code>, <code className="text-aquilia-500">OneToOneField</code>, and <code className="text-aquilia-500">ManyToManyField</code> with configurable on_delete behavior — CASCADE, SET_NULL, PROTECT, SET_DEFAULT, DO_NOTHING, RESTRICT.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ForeignKey</h2>
        <CodeBlock language="python" filename="ForeignKey">{`from aquilia.models import Model
from aquilia.models.fields_module import (
    CharField, ForeignKey, CASCADE, SET_NULL
)

class Author(Model):
    table = "authors"
    name = CharField(max_length=200)

class Post(Model):
    table = "posts"
    title = CharField(max_length=300)
    author = ForeignKey(Author, on_delete=CASCADE, related_name="posts")

# Traverse forward
post = await Post.get(pk=1)
author = await post.related("author")       # → Author instance

# Traverse reverse
author = await Author.get(pk=1)
posts = await author.related("posts")       # → List[Post]`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>OneToOneField</h2>
        <CodeBlock language="python" filename="OneToOne">{`from aquilia.models.fields_module import OneToOneField

class UserProfile(Model):
    table = "profiles"
    bio = TextField(blank=True)
    user = OneToOneField(User, on_delete=CASCADE, related_name="profile")

# Access
profile = await user.related("profile")     # → UserProfile (single)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ManyToManyField</h2>
        <CodeBlock language="python" filename="ManyToMany">{`from aquilia.models.fields_module import ManyToManyField

class Tag(Model):
    table = "tags"
    name = CharField(max_length=50, unique=True)

class Article(Model):
    table = "articles"
    title = CharField(max_length=300)
    tags = ManyToManyField(Tag, related_name="articles")

# Access M2M
article = await Article.get(pk=1)
tags = await article.related("tags")         # → List[Tag]

# Reverse
tag = await Tag.get(pk=1)
articles = await tag.related("articles")     # → List[Article]`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>on_delete Behaviors</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Handler</th>
              <th className="text-left py-3">Behavior</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['CASCADE', 'Delete related objects when the referenced object is deleted.'],
                ['SET_NULL', 'Set the FK column to NULL (field must have null=True).'],
                ['PROTECT', 'Raise ProtectedError — prevent deletion if references exist.'],
                ['RESTRICT', 'Raise RestrictedError — like PROTECT but at a higher semantic level.'],
                ['SET_DEFAULT', 'Set the FK to the field\'s default value.'],
                ['DO_NOTHING', 'Take no action — relies on DB-level constraints.'],
              ].map(([handler, desc], i) => (
                <tr key={i}>
                  <td className="py-2.5 pr-4 font-mono text-xs text-aquilia-400">{handler}</td>
                  <td className={`py-2.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Eager Loading</h2>
        <CodeBlock language="python" filename="Eager Loading">{`# select_related — JOIN-based (single query)
posts = await Post.objects.select_related("author").all()
# Each post.author is already loaded — no extra query

# prefetch_related — separate queries
users = await User.objects.prefetch_related("posts").all()
# Executes: SELECT * FROM users; SELECT * FROM posts WHERE author_id IN (...)

# Prefetch with custom queryset
from aquilia.models.query import Prefetch

users = await User.objects.prefetch_related(
    Prefetch("posts", queryset=Post.objects.filter(published=True).order("-date"))
).all()`}</CodeBlock>
      </section>
    </div>
  )
}
