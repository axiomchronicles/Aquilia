import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, Shield, Globe } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../../components/NextSteps'

export function DecoratorOptions() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @OPTIONS
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@OPTIONS</code> decorator handles HTTP OPTIONS requests, primarily used for <strong>Cross-Origin Resource Sharing (CORS) preflight checks</strong> and discovering allowed methods on a resource.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Implicit vs Explicit</h2>
                <div className={`p-4 mb-6 rounded border ${isDark ? 'bg-indigo-900/20 border-indigo-500/30' : 'bg-indigo-50 border-indigo-200'}`}>
                    <div className="flex items-start gap-3">
                        <Globe className="w-5 h-5 text-indigo-500 mt-0.5" />
                        <div>
                            <h4 className={`font-semibold ${isDark ? 'text-indigo-200' : 'text-indigo-800'}`}>Automatic Handling</h4>
                            <p className={`text-sm ${isDark ? 'text-indigo-300' : 'text-indigo-700'}`}>
                                Aquilia's router automatically handles OPTIONS requests for CORS preflight if you have the <strong>CORS Middleware</strong> enabled.
                                You rarely need to define <code>@OPTIONS</code> handlers manually.
                            </p>
                        </div>
                    </div>
                </div>

                <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Manual Definition</h3>
                <p className={`mb-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    If you need custom logic for an OPTIONS request (e.g., dynamic capability advertising), you can define it explicitly.
                </p>
                <CodeBlock
                    code={`from aquilia import Controller, OPTIONS, RequestCtx, Response

class ApiController(Controller):
    
    @OPTIONS("/")
    async def options(self, ctx: RequestCtx):
        return Response(
            status=204,
            headers={
                "Allow": "GET, POST, OPTIONS",
                "X-Api-Version": "2.0",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
            }
        )`}
                    language="python"
                />
            </section>

            {/* Deep Dive: CORS */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Shield className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>CORS Preflight</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Browsers send an OPTIONS request before making complex cross-origin requests (e.g., checks for headers like <code>Authorization</code> or <code>Content-Type: application/json</code>).
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    The manual handler allows you to inspect <code>Access-Control-Request-Method</code> and <code>Access-Control-Request-Headers</code> to implement fine-grained security policies beyond global middleware settings.
                </p>
            </section>

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/head" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @HEAD
                </Link>
                <Link to="/docs/controllers/decorators/ws" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: @WS <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        
      <NextSteps />
    </div>
    )
}