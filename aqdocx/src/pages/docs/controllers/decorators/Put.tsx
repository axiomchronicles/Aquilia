import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, RefreshCw, FileWarning } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../../components/NextSteps'

export function DecoratorPut() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-orange-500/10 text-orange-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @PUT
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@PUT</code> decorator handles HTTP PUT requests for <strong>full resource replacement</strong>.
                    It enforces idempotency, meaning multiple identical requests should have the same effect as a single one.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, PUT, RequestCtx, Response

class UsersController(Controller):
    prefix = "/users"

    @PUT("/«id:int»")
    async def update_user(self, ctx: RequestCtx, id: int):
        """Fully replace the user resource."""
        data = await ctx.json()
        user = await self.service.replace(id, data)
        return Response.json(user)`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Idempotency & Validation */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <RefreshCw className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Replacement Semantics</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Unlike <code>@PATCH</code>, <code>@PUT</code> expects a complete representation of the resource.
                    Accessing <code>ctx.data</code> via a serializer will typically enforce that all required fields are present.
                </p>

                <div className={`p-4 mb-6 rounded-lg border ${isDark ? 'bg-orange-900/20 border-orange-500/30' : 'bg-orange-50 border-orange-200'}`}>
                    <div className="flex items-start gap-3">
                        <FileWarning className="w-5 h-5 text-orange-500 mt-0.5" />
                        <div>
                            <h4 className={`font-semibold ${isDark ? 'text-orange-200' : 'text-orange-800'}`}>Validation Behavior</h4>
                            <p className={`text-sm ${isDark ? 'text-orange-300' : 'text-orange-700'}`}>
                                When using <code>request_serializer</code> with PUT, partial updates (missing required fields) will strictly fail validation.
                                Use <code>@PATCH</code> if you want to allow partial data.
                            </p>
                        </div>
                    </div>
                </div>

                <CodeBlock
                    code={`@PUT(
    "/«id:int»",
    request_serializer=UserSerializer,  # Strict: Requires all fields
    response_serializer=UserSerializer
)
async def update(self, ctx: RequestCtx, id: int):
    # ctx.data contains the full object
    user = await self.repo.update(id, ctx.data)
    return user`}
                    language="python"
                />
            </section>

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/post" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @POST
                </Link>
                <Link to="/docs/controllers/decorators/patch" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: @PATCH <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        
      <NextSteps />
    </div>
    )
}