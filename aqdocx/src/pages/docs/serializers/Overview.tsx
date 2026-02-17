import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowRight, Database, Shield, Lock, Layers } from 'lucide-react'

export function SerializersOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Database className="w-4 h-4" />
          Data Layer / Serializers
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Serializers
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Serializers validate incoming data, transform outgoing data, and bridge the gap between raw HTTP payloads and typed Python objects. They support nested relationships, custom validators, and automatic OpenAPI schema generation.
        </p>
      </div>

      {/* Core Concepts */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Core Concepts</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { icon: <Layers className="w-5 h-5" />, title: 'Serializer', desc: 'Standalone serializer for arbitrary data validation and transformation' },
            { icon: <Database className="w-5 h-5" />, title: 'ModelSerializer', desc: 'Auto-generates fields from Aquilia model definitions' },
            { icon: <Shield className="w-5 h-5" />, title: 'Validators', desc: 'Field-level and object-level validation with custom rules' },
            { icon: <Lock className="w-5 h-5" />, title: 'ListSerializer', desc: 'Validates arrays of objects with per-item validation' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <div className="text-aquilia-500 mb-2">{item.icon}</div>
              <h3 className={`font-bold text-sm mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.title}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Basic Serializer */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Defining a Serializer</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A serializer declares fields as class attributes. Each field specifies its type, constraints, and validation rules.
        </p>
        <CodeBlock language="python" filename="serializers.py">{`from aquilia import (
    Serializer, CharField, IntegerField, FloatField,
    BooleanField, EmailField, DateTimeField, ListField,
    DictField, ChoiceField, SlugField, URLField, UUIDField,
)


class CreateProductSerializer(Serializer):
    """Validates product creation payloads."""

    name = CharField(max_length=200, required=True, help_text="Product name")
    price = FloatField(min_value=0, required=True)
    sku = CharField(max_length=50, required=True, pattern=r"^[A-Z0-9-]+$")
    description = CharField(max_length=2000, required=False, default="")
    category = ChoiceField(choices=["electronics", "clothing", "food"])
    is_active = BooleanField(default=True)
    tags = ListField(child=CharField(max_length=50), required=False)
    metadata = DictField(required=False)


class UpdateProductSerializer(Serializer):
    """Partial update — all fields optional."""

    name = CharField(max_length=200, required=False)
    price = FloatField(min_value=0, required=False)
    description = CharField(max_length=2000, required=False)
    is_active = BooleanField(required=False)`}</CodeBlock>
      </section>

      {/* Using in Controllers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using with Controllers</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Post, Put


class ProductController(Controller):
    prefix = "/api/products"

    @Post("/", request_serializer=CreateProductSerializer, status_code=201)
    async def create(self, ctx):
        # ctx.validated_data is populated after serializer validation
        data = ctx.validated_data
        product = await Product.objects.create(**data)
        return ctx.json(product.to_dict())

    @Put("/{id:int}", request_serializer=UpdateProductSerializer)
    async def update(self, ctx, id: int):
        data = ctx.validated_data
        product = await Product.objects.get(id=id)
        for key, value in data.items():
            setattr(product, key, value)
        await product.save()
        return ctx.json(product.to_dict())`}</CodeBlock>
      </section>

      {/* ModelSerializer */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ModelSerializer</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">ModelSerializer</code> auto-generates fields from an Aquilia model, reducing boilerplate significantly.
        </p>
        <CodeBlock language="python" filename="model_serializer.py">{`from aquilia import ModelSerializer


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "sku", "category", "is_active"]
        read_only_fields = ["id"]


class ProductDetailSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"          # Include all model fields
        exclude = ["internal_notes"]  # Except these
        read_only_fields = ["id", "created_at", "updated_at"]
        depth = 1                     # Include nested relations


# Usage
serializer = ProductSerializer(data={"name": "Widget", "price": 9.99})
if serializer.is_valid():
    product = await serializer.save()  # Creates the model instance
else:
    print(serializer.errors)  # {"sku": ["This field is required."]}`}</CodeBlock>
      </section>

      {/* Field Types */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Available Field Types</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Python Type</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Key Options</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { f: 'CharField', t: 'str', o: 'max_length, min_length, pattern, trim' },
                { f: 'IntegerField', t: 'int', o: 'min_value, max_value' },
                { f: 'FloatField', t: 'float', o: 'min_value, max_value' },
                { f: 'BooleanField', t: 'bool', o: 'default' },
                { f: 'DateTimeField', t: 'datetime', o: 'format, auto_now' },
                { f: 'DateField', t: 'date', o: 'format' },
                { f: 'TimeField', t: 'time', o: 'format' },
                { f: 'EmailField', t: 'str', o: 'max_length' },
                { f: 'URLField', t: 'str', o: 'max_length, schemes' },
                { f: 'UUIDField', t: 'UUID', o: 'format' },
                { f: 'SlugField', t: 'str', o: 'max_length' },
                { f: 'ChoiceField', t: 'Any', o: 'choices' },
                { f: 'ListField', t: 'list', o: 'child, min_length, max_length' },
                { f: 'DictField', t: 'dict', o: 'child' },
                { f: 'JSONField', t: 'Any', o: 'schema' },
                { f: 'FileField', t: 'UploadFile', o: 'max_size, allowed_types' },
                { f: 'ImageField', t: 'UploadFile', o: 'max_size, max_width, max_height' },
                { f: 'DecimalField', t: 'Decimal', o: 'max_digits, decimal_places' },
                { f: 'IPAddressField', t: 'str', o: 'protocol (ipv4/ipv6/both)' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-2 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.f}</code></td>
                  <td className={`py-2 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-2 px-4 text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{row.o}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Validation */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Validation</h2>
        <CodeBlock language="python" filename="validators.py">{`from aquilia import Serializer, CharField, IntegerField, ValidationFault


class RegisterSerializer(Serializer):
    username = CharField(min_length=3, max_length=30)
    email = EmailField(required=True)
    password = CharField(min_length=8)
    password_confirm = CharField(min_length=8)
    age = IntegerField(min_value=13)

    def validate_username(self, value):
        """Field-level validator — called for 'username' field."""
        if value.lower() in ["admin", "root", "system"]:
            raise ValidationFault("This username is reserved.")
        return value.lower()

    def validate(self, data):
        """Object-level validator — called after all fields pass."""
        if data["password"] != data["password_confirm"]:
            raise ValidationFault({"password_confirm": "Passwords do not match."})
        # Remove confirm field from validated data
        data.pop("password_confirm")
        return data`}</CodeBlock>
      </section>

      {/* Nested Serializers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Nested & Relational Serializers</h2>
        <CodeBlock language="python" filename="nested.py">{`from aquilia import Serializer, CharField, PrimaryKeyRelatedField, NestedSerializer


class AddressSerializer(Serializer):
    street = CharField(max_length=200)
    city = CharField(max_length=100)
    zip_code = CharField(max_length=20)


class OrderItemSerializer(Serializer):
    product_id = IntegerField()
    quantity = IntegerField(min_value=1)
    note = CharField(required=False)


class CreateOrderSerializer(Serializer):
    customer_id = PrimaryKeyRelatedField(queryset=Customer.objects)
    shipping_address = NestedSerializer(AddressSerializer)
    items = ListField(child=NestedSerializer(OrderItemSerializer), min_length=1)
    coupon_code = CharField(required=False)

    def validate(self, data):
        if len(data["items"]) > 50:
            raise ValidationFault("Maximum 50 items per order.")
        return data`}</CodeBlock>
      </section>

      {/* Sub-Pages */}
      <section>
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Deep Dives</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { title: 'Base Serializer', desc: 'Core Serializer class and its API', to: '/docs/serializers/base' },
            { title: 'ModelSerializer', desc: 'Auto-generated serializers from models', to: '/docs/serializers/model' },
            { title: 'Field Reference', desc: 'Complete field type reference', to: '/docs/serializers/fields' },
            { title: 'Validators', desc: 'Custom validation patterns', to: '/docs/serializers/validators' },
            { title: 'Relations', desc: 'Nested and relational fields', to: '/docs/serializers/relations' },
          ].map((item, i) => (
            <Link key={i} to={item.to} className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
              <h3 className={`font-bold text-sm mb-1 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {item.title}
                <ArrowRight className="w-3 h-3 text-aquilia-500 opacity-0 group-hover:opacity-100 transition" />
              </h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
