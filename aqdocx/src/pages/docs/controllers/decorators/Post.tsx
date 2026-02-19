import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, Box, FileJson } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DecoratorPost() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @POST
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@POST</code> decorator handles HTTP POST requests, typically used for creating resources.
                    It provides robust mechanisms for <strong>request body validation</strong>, <strong>serialization</strong>, and <strong>response formatting</strong>.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, POST, RequestCtx, Response

class UsersController(Controller):
    prefix = "/users"

    @POST("/", status_code=201)
    async def create_user(self, ctx: RequestCtx):
        data = await ctx.json()
        user = await self.service.create(data)
        return Response.json(user, status=201)`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Input Validation */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <FileJson className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Input Validation & Serialization</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Aquilia offers two powerful ways to handle request bodies: <strong>Serializers</strong> (Django REST Framework style) and <strong>Blueprints</strong> (Pydantic/Type-safe style).
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>1. Using Serializers</h3>
                        <p className={`mb-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Ideal for complex validation rules and ORM integration. The validated data is available in <code>ctx.data</code>.
                        </p>
                        <CodeBlock
                            code={`@POST(
    "/",
    request_serializer=CreateUserSerializer
)
async def create(self, ctx: RequestCtx):
    # ctx.data is already validated
    user = await self.service.create(ctx.data)
    return Response.json(user)`}
                            language="python"
                        />
                    </div>
                    <div>
                        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>2. Using Blueprints</h3>
                        <p className={`mb-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Perfect for modern, type-hinted codebases. Request body is cast to the Blueprint type.
                        </p>
                        <CodeBlock
                            code={`@POST(
    "/",
    request_blueprint=UserBlueprint
)
async def create(self, ctx: RequestCtx):
    # ctx.blueprint is a UserBlueprint instance
    payload: UserBlueprint = ctx.blueprint
    return ...`}
                            language="python"
                        />
                    </div>
                </div>
            </section>

            {/* Deep Dive: Response Handling */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Box className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Response Formatting</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Control how your data is sent back to the client using <code>response_serializer</code> or <code>response_blueprint</code>.
                </p>

                <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Key Parameters</h3>
                <ul className={`list-disc pl-5 space-y-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    <li>
                        <strong>response_serializer</strong>: Automatically serializes the return value of the handler.
                        If set, you can return ORM objects directly instead of <code>Response</code> objects.
                    </li>
                    <li>
                        <strong>response_model</strong>: Used primarily for OpenAPI documentation to describe the success response schema.
                    </li>
                    <li>
                        <strong>status_code</strong>: Sets the default HTTP status code (default: 200, typically 201 for POST).
                    </li>
                </ul>

                <div className="mt-4">
                    <CodeBlock
                        code={`@POST(
    "/",
    status_code=201,
    response_serializer=UserSerializer
)
async def create(self, ctx: RequestCtx):
    user = await self.repo.create(...)
    # Framework automatically serializes 'user'
    # and wraps it in Response(..., status=201)
    return user`}
                        language="python"
                    />
                </div>
            </section>

            {/* API Reference Table */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>API Reference</h2>
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
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">request_serializer</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">Type[Serializer]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Serializer for request body validation.</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">request_blueprint</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">Type[Blueprint]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Blueprint for strictly typed request bodies.</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">response_serializer</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">Type[Serializer]</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Serializer for outgoing response data.</td>
                            </tr>
                            <tr>
                                <td className="px-4 py-3 text-sm font-mono text-aquilia-500">status_code</td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-500">int</td>
                                <td className="px-4 py-3 text-sm text-gray-500">Default HTTP status code (e.g., 201).</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/get" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @GET
                </Link>
                <Link to="/docs/controllers/decorators/put" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: @PUT <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        </div>
    )
}
