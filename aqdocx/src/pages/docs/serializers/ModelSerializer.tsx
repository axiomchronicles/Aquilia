import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Database } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function SerializerModel() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Database className="w-4 h-4" />
          Serializers / ModelSerializer
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            ModelSerializer
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">ModelSerializer</code> automatically generates serializer fields from your Aquilia model definitions. It handles field inference, creates/updates model instances, and supports relational fields out of the box.
        </p>
      </div>

      {/* Basic Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
        <CodeBlock language="python" filename="model_serializer.py">{`from aquilia.serializers import ModelSerializer
from myapp.models import Product

class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"                    # All model fields
        # OR explicit list:
        # fields = ["id", "name", "price", "category"]
        exclude = ["internal_notes"]          # Exclude specific fields
        read_only_fields = ["id", "created_at", "updated_at"]`}</CodeBlock>
      </section>

      {/* Meta Options */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Meta Options Reference</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Option</th>
                  <th className="text-left pb-3 font-semibold">Type</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['model', 'Model class', 'The Aquilia model to serialize'],
                  ['fields', '"__all__" | list', 'Which model fields to include'],
                  ['exclude', 'list', 'Fields to omit from the serializer'],
                  ['read_only_fields', 'list', 'Fields that appear in output only'],
                  ['extra_kwargs', 'dict', 'Override field arguments per-field'],
                  ['validators', 'list', 'Object-level validators'],
                  ['depth', 'int', 'Auto-nest related objects to this depth (0 = PK only)'],
                ].map(([opt, type, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{opt}</td>
                    <td className="py-2 text-xs">{type}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Create and Update */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Create & Update</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          ModelSerializer provides <code className="text-aquilia-400">create()</code> and <code className="text-aquilia-400">update()</code> methods that handle model instance persistence.
        </p>
        <CodeBlock language="python" filename="crud.py">{`class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ["name", "price", "category"]

    def create(self, validated_data):
        """Called when serializer.save() is called without instance."""
        return Product.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Called when serializer.save() is called with an existing instance."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

# Usage in a controller
@POST("/products")
async def create_product(self, ctx):
    serializer = ProductSerializer(data=ctx.json)
    if serializer.is_valid():
        product = serializer.save()  # calls create()
        return Response.created(serializer.data)
    return Response.bad_request(serializer.errors)

@PUT("/products/{id}")
async def update_product(self, ctx, id: int):
    product = await Product.objects.get(id=id)
    serializer = ProductSerializer(instance=product, data=ctx.json)
    if serializer.is_valid():
        serializer.save()  # calls update()
        return Response.ok(serializer.data)`}</CodeBlock>
      </section>

      {/* Extra Kwargs */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Extra Kwargs</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Override auto-generated field arguments without declaring the field explicitly.
        </p>
        <CodeBlock language="python" filename="extra_kwargs.py">{`class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "bio", "avatar"]
        extra_kwargs = {
            "email": {"required": True, "allow_blank": False},
            "bio": {"max_length": 500, "required": False},
            "avatar": {"read_only": True},
        }`}</CodeBlock>
      </section>

      {/* ListSerializer */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ListSerializer</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">ListSerializer</code> handles validation and serialization of lists of objects. It's automatically used when you pass <code className="text-aquilia-400">many=True</code>.
        </p>
        <CodeBlock language="python" filename="list.py">{`# Implicit — pass many=True to any serializer
serializer = ProductSerializer(data=products_list, many=True)
if serializer.is_valid():
    products = serializer.save()  # creates all

# Explicit — for custom list behavior
from aquilia.serializers import ListSerializer

class BulkProductSerializer(ListSerializer):
    child = ProductSerializer()
    max_length = 100  # limit bulk operations

    def create(self, validated_data):
        return Product.objects.bulk_create(
            [Product(**item) for item in validated_data]
        )`}</CodeBlock>
      </section>

      {/* Controller Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Full Controller Example</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, GET, POST, PUT, DELETE
from aquilia.response import Response
from aquilia.serializers import ModelSerializer
from myapp.models import Product

class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

class ProductController(Controller):
    prefix = "/products"

    @GET("/")
    async def list(self, ctx):
        products = await Product.objects.all()
        return Response.ok(
            ProductSerializer(products, many=True).data
        )

    @GET("/{id}")
    async def detail(self, ctx, id: int):
        product = await Product.objects.get(id=id)
        return Response.ok(ProductSerializer(product).data)

    @POST("/")
    async def create(self, ctx):
        s = ProductSerializer(data=ctx.json)
        if s.is_valid():
            s.save()
            return Response.created(s.data)
        return Response.bad_request(s.errors)

    @DELETE("/{id}")
    async def remove(self, ctx, id: int):
        await Product.objects.filter(id=id).delete()
        return Response.no_content()`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}