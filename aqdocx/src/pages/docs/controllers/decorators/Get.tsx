import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, Filter, Search, List as ListIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../../components/NextSteps'

export function DecoratorGet() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @GET
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@GET</code> decorator handles HTTP GET requests. It is the workhorse for retrieving resources
                    and listing collections, with built-in support for filtering, searching, sorting, and pagination.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, GET, RequestCtx, Response

class UsersController(Controller):
    prefix = "/users"

    @GET("/")
    async def list_users(self, ctx: RequestCtx) -> Response:
        """List all users."""
        users = await self.repo.all()
        return Response.json(users)

    @GET("/«id:int»")
    async def get_user(self, ctx: RequestCtx, id: int) -> Response:
        """Get a single user by ID."""
        user = await self.repo.get(id)
        return Response.json(user)`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Filtering */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Filter className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Advanced Filtering</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Aquilia's <code>@GET</code> decorator integrates directly with the <code>FilterSet</code> system.
                    You can enable declarative filtering without writing any boilerplate query parsing logic.
                </p>

                <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>1. Simple Field Filtering</h3>
                <p className={`mb-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Use <code>filterset_fields</code> to allow exact matching on specific fields.
                </p>
                <CodeBlock
                    code={`@GET("/", filterset_fields=["status", "role"])
# Enable ?status=active&role=admin automatically`}
                    language="python"
                />

                <h3 className={`text-lg font-semibold mt-4 mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>2. Custom FilterSets</h3>
                <p className={`mb-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    For complex logic (ranges, multiple values, related fields), define a <code>FilterSet</code> class.
                </p>
                <CodeBlock
                    code={`class ProductFilter(FilterSet):
    min_price = NumberFilter(field_name="price", lookup_expr="gte")
    max_price = NumberFilter(field_name="price", lookup_expr="lte")
    category = CharFilter(lookup_expr="iexact")

class ProductController(Controller):
    @GET("/", filterset_class=ProductFilter)
    async def list_products(self, ctx: RequestCtx):
        # Filters are applied automatically to the queryset in ctx
        ...`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Searching & Sorting */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Search className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Search & Ordering</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Full-Text Search</h3>
                        <p className={`mb-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Enable the <code>?search=</code> query parameter by defining searchable fields.
                        </p>
                        <CodeBlock
                            code={`@GET(
    "/",
    search_fields=["title", "content", "author.name"]
)`}
                            language="python"
                        />
                    </div>
                    <div>
                        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Dynamic Ordering</h3>
                        <p className={`mb-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Allow clients to sort results using <code>?ordering=field</code> (or <code>-field</code> for descending).
                        </p>
                        <CodeBlock
                            code={`@GET(
    "/",
    ordering_fields=["created_at", "username", "score"]
)`}
                            language="python"
                        />
                    </div>
                </div>
            </section>

            {/* Deep Dive: Pagination */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <ListIcon className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Pagination</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Pagination is handled by the <code>pagination_class</code> argument. The framework provides standard implementations,
                    but you can also supply your own.
                </p>
                <CodeBlock
                    code={`from aquilia.pagination import PageNumberPagination, LimitOffsetPagination

class LargeSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'

class DataController(Controller):
    # Standard page-based pagination
    @GET("/items", pagination_class=PageNumberPagination)
    async def list_items(self, ctx: RequestCtx):
        return await self.repo.active_items()

    # Limit/Offset for infinite scroll APIs
    @GET("/feed", pagination_class=LimitOffsetPagination)
    async def feed(self, ctx: RequestCtx):
        return await self.repo.get_feed()`}
                    language="python"
                />
            </section>

            {/* Validation */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Complete API Reference</h2>
                <div className={`overflow-x-auto rounded-lg border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-white/10">
                        <thead className={isDark ? 'bg-zinc-800' : 'bg-gray-50'}>
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Argument</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Type</th>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Description</th>
                            </tr>
                        </thead>
                        <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">path</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">str</td>
                                <td className="px-4 py-3 text-sm text-gray-500">URL path pattern (e.g., <code>/users/«id:int»</code>). Defaults to method name if None.</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">filterset_fields</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">list[str]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">List of fields to enable simple exact-match filtering on.</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">search_fields</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">list[str]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Fields to search against when the <code>search</code> query param is present.</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">ordering_fields</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">list[str]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Fields allowed in the <code>ordering</code> query param.</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">pagination_class</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">Type[Pagination]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Class to handle pagination logic (PageNumber, LimitOffset, Cursor).</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">renderer_classes</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">list[Type[Renderer]]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Renderers to use for Content-Type negotiation.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>
        
      <NextSteps />
    </div>
    )
}