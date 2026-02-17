import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowRight, Rocket, FileCode, Database, Shield, Globe } from 'lucide-react'

export function QuickStartPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Rocket className="w-4 h-4" />
          Getting Started
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Quick Start
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Build your first Aquilia application in under 5 minutes. This guide walks you through creating a REST API with a database model, controller, and dependency injection.
        </p>
      </div>

      {/* Step 1 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500 text-black font-bold text-sm">1</span>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Create a Project</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Create a new directory and set up your environment:
        </p>
        <CodeBlock language="bash" filename="Terminal">{`mkdir my-aquilia-app && cd my-aquilia-app
python -m venv env && source env/bin/activate
pip install aquilia`}</CodeBlock>
        <p className={`mt-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Create the following project structure:
        </p>
        <CodeBlock language="text" filename="Project Structure">{`my-aquilia-app/
├── starter.py          # Application entry point
├── config/
│   └── workspace.yaml  # Configuration
└── modules/
    └── products/
        ├── __init__.py
        ├── controller.py
        ├── model.py
        └── service.py`}</CodeBlock>
      </section>

      {/* Step 2 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500 text-black font-bold text-sm">2</span>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Define a Model</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia's ORM lets you define database models with declarative typed fields:
        </p>
        <CodeBlock language="python" filename="modules/products/model.py">{`from aquilia import Model, CharField, IntegerField, FloatField, BooleanField, DateTimeField


class Product(Model):
    """A product in the catalog."""
    name = CharField(max_length=200)
    description = CharField(max_length=1000, default="")
    price = FloatField()
    stock = IntegerField(default=0)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        table_name = "products"
        ordering = ["-created_at"]

    def __repr__(self):
        return f"<Product {self.name} ${"$"}{self.price}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "is_active": self.is_active,
        }`}</CodeBlock>
      </section>

      {/* Step 3 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500 text-black font-bold text-sm">3</span>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Create a Service</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Services contain your business logic. They're registered in the DI container and injected into controllers:
        </p>
        <CodeBlock language="python" filename="modules/products/service.py">{`from .model import Product


class ProductService:
    """Business logic for products."""

    async def list_products(self, active_only: bool = True):
        """List all products, optionally filtering by active status."""
        qs = Product.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return await qs

    async def get_product(self, product_id: int):
        """Get a single product by ID."""
        return await Product.objects.get(id=product_id)

    async def create_product(self, data: dict):
        """Create a new product."""
        return await Product.objects.create(**data)

    async def update_product(self, product_id: int, data: dict):
        """Update an existing product."""
        product = await Product.objects.get(id=product_id)
        for key, value in data.items():
            setattr(product, key, value)
        await product.save()
        return product

    async def delete_product(self, product_id: int):
        """Delete a product."""
        product = await Product.objects.get(id=product_id)
        await product.delete()`}</CodeBlock>
      </section>

      {/* Step 4 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500 text-black font-bold text-sm">4</span>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Build a Controller</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Controllers handle HTTP requests. Use decorators to define routes and inject dependencies:
        </p>
        <CodeBlock language="python" filename="modules/products/controller.py">{`from aquilia import Controller, Get, Post, Put, Delete, Inject
from .service import ProductService


class ProductController(Controller):
    prefix = "/api/products"

    @Inject()
    def __init__(self, service: ProductService):
        self.service = service

    @Get("/")
    async def list_products(self, ctx):
        """GET /api/products — List all active products."""
        products = await self.service.list_products()
        return ctx.json({
            "products": [p.to_dict() for p in products],
            "count": len(products)
        })

    @Get("/{product_id:int}")
    async def get_product(self, ctx, product_id: int):
        """GET /api/products/:id — Get a single product."""
        try:
            product = await self.service.get_product(product_id)
            return ctx.json({"product": product.to_dict()})
        except Exception:
            return ctx.json({"error": "Product not found"}, status=404)

    @Post("/")
    async def create_product(self, ctx):
        """POST /api/products — Create a new product."""
        body = await ctx.json_body()
        product = await self.service.create_product(body)
        return ctx.json({"product": product.to_dict()}, status=201)

    @Put("/{product_id:int}")
    async def update_product(self, ctx, product_id: int):
        """PUT /api/products/:id — Update a product."""
        body = await ctx.json_body()
        product = await self.service.update_product(product_id, body)
        return ctx.json({"product": product.to_dict()})

    @Delete("/{product_id:int}")
    async def delete_product(self, ctx, product_id: int):
        """DELETE /api/products/:id — Delete a product."""
        await self.service.delete_product(product_id)
        return ctx.json({"message": "Deleted"}, status=204)`}</CodeBlock>
      </section>

      {/* Step 5 */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500 text-black font-bold text-sm">5</span>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Wire It Up</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The starter file bootstraps the AquiliaServer, registers services and controllers, and starts the server:
        </p>
        <CodeBlock language="python" filename="starter.py">{`from aquilia import AquiliaServer
from aquilia.di import Singleton

from modules.products.controller import ProductController
from modules.products.service import ProductService
from modules.products.model import Product


# Create the server
app = AquiliaServer()

# Register the database
app.use_database("sqlite:///db.sqlite3")

# Register models
app.register_model(Product)

# Register services in the DI container
app.container.register(ProductService, lifetime=Singleton)

# Register controllers
app.register_controller(ProductController)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)`}</CodeBlock>
      </section>

      {/* Step 6: Run */}
      <section className="mb-12">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500 text-black font-bold text-sm">6</span>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Run the Server</h2>
        </div>
        <CodeBlock language="bash" filename="Terminal">{`python starter.py

# Output:
# 🦅 Aquilia v0.2.0
# ├─ Server running on http://0.0.0.0:8000
# ├─ Database: sqlite:///db.sqlite3
# ├─ Controllers: 1 registered
# └─ Ready in 0.12s`}</CodeBlock>
        <p className={`mt-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Test your API:
        </p>
        <CodeBlock language="bash" filename="Terminal">{`# Create a product
curl -X POST http://localhost:8000/api/products \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Laptop", "price": 999.99, "stock": 50}'

# List products
curl http://localhost:8000/api/products

# Get a single product
curl http://localhost:8000/api/products/1`}</CodeBlock>
      </section>

      {/* What's Next */}
      <section>
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>What's Next?</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { icon: <FileCode />, label: 'Controllers', to: '/docs/controllers', desc: 'Deep-dive into the controller architecture' },
            { icon: <Database />, label: 'Models & ORM', to: '/docs/models', desc: 'Learn about the full ORM system' },
            { icon: <Shield />, label: 'Authentication', to: '/docs/auth', desc: 'Add auth to your app' },
            { icon: <Globe />, label: 'Architecture', to: '/docs/architecture', desc: 'Understand the full framework architecture' },
          ].map((item, i) => (
            <Link key={i} to={item.to} className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
              <div className="text-aquilia-500 mb-2 w-5 h-5">{item.icon}</div>
              <h3 className={`font-bold text-sm mb-1 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {item.label}
                <ArrowRight className="w-3 h-3 text-aquilia-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              </h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
