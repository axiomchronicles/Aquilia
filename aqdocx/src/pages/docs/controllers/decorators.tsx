import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Tag } from 'lucide-react'

export function ControllersDecorators() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Tag className="w-4 h-4" />
          Controllers
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Route Decorators
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides HTTP method decorators that attach route metadata to controller methods. Routes are compiled at startup — no import-time side effects.
        </p>
      </div>

      {/* Available Decorators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>HTTP Method Decorators</h2>
        <p className={`mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          All decorators extend the <code className="text-aquilia-500">RouteDecorator</code> base class and accept the same keyword arguments:
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Decorator</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>HTTP Method</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Usage</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { dec: '@Get(path)', method: 'GET', usage: 'Retrieve resources' },
                { dec: '@Post(path)', method: 'POST', usage: 'Create resources' },
                { dec: '@Put(path)', method: 'PUT', usage: 'Full update resources' },
                { dec: '@Patch(path)', method: 'PATCH', usage: 'Partial update resources' },
                { dec: '@Delete(path)', method: 'DELETE', usage: 'Delete resources' },
                { dec: '@Head(path)', method: 'HEAD', usage: 'Headers only (no body)' },
                { dec: '@Options(path)', method: 'OPTIONS', usage: 'CORS preflight / capabilities' },
                { dec: '@WS(path)', method: 'WebSocket', usage: 'WebSocket upgrade endpoints' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.dec}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.method}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.usage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* RouteDecorator Parameters */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Decorator Parameters</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Every decorator accepts these keyword arguments via the <code className="text-aquilia-500">RouteDecorator</code> base:
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { p: 'path', t: 'str | None', d: 'URL path template. Supports dynamic segments like /{id:int}. If None, derived from method name.' },
                { p: 'pipeline', t: 'List[Any]', d: 'Method-level pipeline nodes (guards, interceptors). Overrides class-level pipeline.' },
                { p: 'summary', t: 'str | None', d: 'OpenAPI summary. Defaults to method name titleized.' },
                { p: 'description', t: 'str | None', d: 'OpenAPI description. Defaults to method docstring.' },
                { p: 'tags', t: 'List[str]', d: 'OpenAPI tags. Extends class-level tags.' },
                { p: 'deprecated', t: 'bool', d: 'Mark as deprecated in OpenAPI spec.' },
                { p: 'response_model', t: 'type | None', d: 'Response type for OpenAPI schema generation.' },
                { p: 'status_code', t: 'int', d: 'Default HTTP status code (200).' },
                { p: 'request_serializer', t: 'type | None', d: 'Aquilia Serializer class for request body validation.' },
                { p: 'response_serializer', t: 'type | None', d: 'Aquilia Serializer class for response serialization.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.p}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Path Parameters */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Path Parameters</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Use curly braces to define dynamic path segments. The framework extracts them and passes as handler arguments:
        </p>
        <CodeBlock language="python" filename="Path Parameters">{`class ProductController(Controller):
    prefix = "/products"

    @Get("/{product_id:int}")
    async def get_product(self, ctx, product_id: int):
        """Path parameter is automatically parsed as int."""
        product = await Product.objects.get(id=product_id)
        return ctx.json({"product": product.to_dict()})

    @Get("/{category:str}/{slug:str}")
    async def get_by_slug(self, ctx, category: str, slug: str):
        """Multiple path parameters."""
        product = await Product.objects.get(
            category=category, slug=slug
        )
        return ctx.json({"product": product.to_dict()})

    @Get("/search/{query:path}")
    async def search(self, ctx, query: str):
        """The :path converter matches everything including slashes."""
        results = await Product.objects.filter(name__contains=query)
        return ctx.json({"results": [r.to_dict() for r in results]})`}</CodeBlock>

        <div className={`mt-6 ${boxClass}`}>
          <h3 className={`font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Supported Type Converters</h3>
          <ul className={`space-y-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <li><code className="text-aquilia-500">{'{id:int}'}</code> — Integer parameter</li>
            <li><code className="text-aquilia-500">{'{name:str}'}</code> — String parameter (default)</li>
            <li><code className="text-aquilia-500">{'{slug:path}'}</code> — Matches everything including slashes</li>
            <li><code className="text-aquilia-500">{'{uuid:uuid}'}</code> — UUID parameter</li>
          </ul>
        </div>
      </section>

      {/* Serializer Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Serializer Integration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Decorators can specify serializers for automatic request validation and response formatting:
        </p>
        <CodeBlock language="python" filename="Serializer Integration">{`from aquilia import Serializer, CharField, IntegerField


class CreateProductSerializer(Serializer):
    name = CharField(max_length=200, required=True)
    price = IntegerField(min_value=0, required=True)
    description = CharField(max_length=1000, required=False)


class ProductResponseSerializer(Serializer):
    id = IntegerField()
    name = CharField()
    price = IntegerField()


class ProductController(Controller):
    prefix = "/products"

    @Post(
        "/",
        request_serializer=CreateProductSerializer,
        response_serializer=ProductResponseSerializer,
        status_code=201,
        summary="Create a new product",
        tags=["Products", "Admin"],
    )
    async def create(self, ctx):
        # ctx.validated_data is populated by the request_serializer
        data = ctx.validated_data
        product = await Product.objects.create(**data)
        return ctx.json(product.to_dict())`}</CodeBlock>
      </section>

      {/* Pipeline per Method */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Method-Level Pipelines</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Override or extend the class-level pipeline for individual methods:
        </p>
        <CodeBlock language="python" filename="Method Pipelines">{`class AdminController(Controller):
    prefix = "/admin"
    pipeline = [Auth.guard()]  # Requires auth for all routes

    @Get("/dashboard")
    async def dashboard(self, ctx):
        """Uses class-level pipeline (Auth guard)."""
        return ctx.json({"page": "dashboard"})

    @Post(
        "/users",
        pipeline=[Auth.guard(), RoleGuard("admin")]
    )
    async def create_admin_user(self, ctx):
        """Overrides with stricter pipeline: auth + admin role."""
        body = await ctx.json()
        user = await self.service.create_admin(body)
        return ctx.json({"user": user.to_dict()})`}</CodeBlock>
      </section>

      {/* Generic Route */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>The Generic route() Decorator</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          For handling multiple HTTP methods on the same handler, use the generic <code className="text-aquilia-500">route()</code> function:
        </p>
        <CodeBlock language="python" filename="Generic Route">{`from aquilia import route


class ItemController(Controller):
    prefix = "/items"

    @route("GET", "/")
    async def list_items(self, ctx):
        return ctx.json({"items": []})

    @route(["GET", "POST"], "/bulk")
    async def bulk_handler(self, ctx):
        """Handles both GET and POST on /items/bulk."""
        if ctx.method == "GET":
            return ctx.json({"items": await self.service.bulk_list()})
        else:
            body = await ctx.json()
            created = await self.service.bulk_create(body["items"])
            return ctx.json({"created": len(created)}, status=201)`}</CodeBlock>
      </section>

      {/* How Metadata Works */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How Route Metadata Works</h2>
        <div className={boxClass}>
          <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            When a decorator is applied, it attaches a <code className="text-aquilia-500">__route_metadata__</code> list to the function. The <code className="text-aquilia-500">ControllerCompiler</code> inspects this metadata at startup to build the route tree. This means:
          </p>
          <ul className={`space-y-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>No code runs at import time — decorators only attach data</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>Routes are compiled once at startup for maximum performance</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>A single function can have multiple route decorators (multiple methods/paths)</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>The metadata includes function signature for automatic parameter extraction</li>
          </ul>
        </div>
      </section>
    </div>
  )
}
