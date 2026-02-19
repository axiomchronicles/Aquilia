import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, Edit, AlertCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DecoratorPatch() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-yellow-500/10 text-yellow-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @PATCH
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@PATCH</code> decorator handles HTTP PATCH requests, used for <strong>partial modifications</strong> of a resource.
                    Clients only need to send the fields they wish to change.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, PATCH, RequestCtx, Response, exceptions

class UsersController(Controller):
    prefix = "/users"

    @PATCH("/«id:int»")
    async def partial_update(self, ctx: RequestCtx, id: int):
        user = await self.repo.get_or_404(id)
        
        # Merge changes from request body
        payload = await ctx.json()
        updated_user = await self.repo.update(user, payload)
        
        return Response.json(updated_user)`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Partial Validation */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Edit className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Partial Updates</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    When using <code>request_serializer</code> with <code>@PATCH</code>, the framework automatically treats the serializer logic as <strong>partial</strong>.
                    Required fields that are missing from the payload are ignored, while present fields are validated as usual.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>With Serializer</h3>
                        <CodeBlock
                            code={`@PATCH(
    "/«id:int»",
    request_serializer=UserSerializer,
    response_serializer=UserSerializer
)
async def update(self, ctx, id):
    # ctx.data only contains validated fields usually
    # sent by the client. Missing fields don't cause errors.
    user = await self.repo.patch(id, ctx.data)
    return user`}
                            language="python"
                        />
                    </div>
                    <div>
                        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>With Blueprint</h3>
                        <div className={`p-4 rounded border text-sm ${isDark ? 'bg-yellow-900/10 border-yellow-500/20 text-yellow-200' : 'bg-yellow-50 border-yellow-200 text-yellow-800'}`}>
                            <AlertCircle className="w-4 h-4 mb-2" />
                            Requests using Blueprints with PATCH must use <code>Optional</code> types for all fields in the blueprint definition if you want them to be optional at the schema level.
                        </div>
                    </div>
                </div>
            </section>

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/put" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @PUT
                </Link>
                <Link to="/docs/controllers/decorators/delete" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: @DELETE <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        </div>
    )
}
