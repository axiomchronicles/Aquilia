import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, Trash2, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DecoratorDelete() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-red-500/10 text-red-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @DELETE
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@DELETE</code> decorator handles HTTP DELETE requests, used to remove resources.
                    Successful operations typically return an empty body with a <strong>204 No Content</strong> status code.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, DELETE, RequestCtx, Response

class UsersController(Controller):
    prefix = "/users"

    @DELETE("/«id:int»")
    async def delete_user(self, ctx: RequestCtx, id: int):
        """Delete a user by ID."""
        success = await self.service.delete(id)
        if not success:
            return Response.status(404)
        
        # Return 204 No Content for successful deletion
        return Response.status(204)`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Status Codes */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Trash2 className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Response Semantics</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    A DELETE operation is typically idempotent. If the resource is already gone, repeated calls should explicitly or implicitly succeed.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className={`p-4 rounded border ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-white border-gray-200'}`}>
                        <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>204 No Content</h3>
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            The standard response for success. The client should not expect any content in the body.
                        </p>
                    </div>
                    <div className={`p-4 rounded border ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-white border-gray-200'}`}>
                        <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>202 Accepted</h3>
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Use this if the deletion is queued for background processing (soft delete, heavy cleanup).
                        </p>
                    </div>
                </div>

                <div className={`mt-6 p-4 rounded-lg flex items-start gap-3 border ${isDark ? 'bg-red-900/20 border-red-500/30' : 'bg-red-50 border-red-200'}`}>
                    <ShieldAlert className="w-5 h-5 text-red-500 mt-0.5" />
                    <div>
                        <h4 className={`font-semibold mb-1 ${isDark ? 'text-red-200' : 'text-red-800'}`}>Warning: Body Content</h4>
                        <p className={`text-sm ${isDark ? 'text-red-300' : 'text-red-700'}`}>
                            While HTTP specific allows a body in DELETE requests, many clients, proxies, and caches discard it.
                            Avoid relying on request bodies for DELETE operations; use path parameters or query strings instead.
                        </p>
                    </div>
                </div>
            </section>

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/patch" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @PATCH
                </Link>
                <Link to="/docs/controllers/decorators/head" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: @HEAD <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        </div>
    )
}
