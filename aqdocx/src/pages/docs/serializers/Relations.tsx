import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Binary } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function SerializerRelations() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Binary className="w-4 h-4" />
          Serializers / Relations
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Relational Fields
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Relational fields represent model relationships (foreign keys, many-to-many) in serialized output. Aquilia provides four relational field types, each controlling how related objects are represented.
        </p>
      </div>

      {/* Field Reference */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Relational Field Types</h2>
        <div className="space-y-4">
          {[
            { name: 'RelatedField', desc: 'Base class for all relational fields. Not used directly — subclass it to define custom relationship representations.', output: 'Custom' },
            { name: 'PrimaryKeyRelatedField', desc: 'Represents the relationship using the related object\'s primary key. Most common for write operations.', output: 'int / UUID' },
            { name: 'SlugRelatedField', desc: 'Uses a slug or unique attribute of the related object instead of the PK.', output: 'str' },
            { name: 'StringRelatedField', desc: 'Uses the __str__() representation of the related object. Read-only by default.', output: '__str__()' },
          ].map((f, i) => (
            <div key={i} className={box}>
              <div className="flex items-start justify-between mb-2">
                <h3 className={`font-mono font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{f.name}</h3>
                <span className={`text-xs font-mono px-2 py-0.5 rounded ${isDark ? 'bg-aquilia-500/10 text-aquilia-400' : 'bg-aquilia-50 text-aquilia-700'}`}>→ {f.output}</span>
              </div>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* PrimaryKeyRelatedField */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>PrimaryKeyRelatedField</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The most common relational field. On <strong>read</strong> it outputs the PK; on <strong>write</strong> it looks up the related object by PK.
        </p>
        <CodeBlock language="python" filename="pk_relation.py">{`from aquilia.serializers import ModelSerializer, PrimaryKeyRelatedField
from myapp.models import Order, Product

class OrderSerializer(ModelSerializer):
    # many=True for one-to-many / many-to-many
    products = PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        many=True,
    )
    # Single FK
    customer = PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
    )

    class Meta:
        model = Order
        fields = ["id", "customer", "products", "total", "created_at"]

# Input:  {"customer": 42, "products": [1, 2, 3]}
# Output: {"id": 1, "customer": 42, "products": [1, 2, 3], ...}`}</CodeBlock>
      </section>

      {/* SlugRelatedField */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SlugRelatedField</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Uses a human-readable attribute (slug, username, SKU) instead of the numeric primary key.
        </p>
        <CodeBlock language="python" filename="slug_relation.py">{`from aquilia.serializers import ModelSerializer, SlugRelatedField
from myapp.models import Article, Category

class ArticleSerializer(ModelSerializer):
    category = SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.all(),
    )

    class Meta:
        model = Article
        fields = ["title", "category", "content"]

# Input:  {"title": "Hello", "category": "tech"}
# Output: {"title": "Hello", "category": "tech", ...}
# The serializer resolves Category.objects.get(slug="tech")`}</CodeBlock>
      </section>

      {/* StringRelatedField */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>StringRelatedField</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Outputs the <code className="text-aquilia-400">__str__()</code> of related objects. Always read-only — useful for display purposes.
        </p>
        <CodeBlock language="python" filename="str_relation.py">{`from aquilia.serializers import ModelSerializer, StringRelatedField
from myapp.models import Order

class OrderSummarySerializer(ModelSerializer):
    customer = StringRelatedField()    # → "John Doe"
    products = StringRelatedField(many=True)  # → ["Widget A", "Widget B"]

    class Meta:
        model = Order
        fields = ["id", "customer", "products", "total"]`}</CodeBlock>
      </section>

      {/* Nested Serializers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Nested Serializers as Relations</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          For richer output, use another serializer as a field to embed the full related object.
        </p>
        <CodeBlock language="python" filename="nested.py">{`from aquilia.serializers import ModelSerializer

class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

class ArticleSerializer(ModelSerializer):
    # Full nested object in output
    category = CategorySerializer(read_only=True)
    # PK for writes
    category_id = PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Article
        fields = ["id", "title", "category", "category_id"]`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}