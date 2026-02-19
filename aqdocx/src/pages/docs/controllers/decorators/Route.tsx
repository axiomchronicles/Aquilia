import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, GitMerge, Layers } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../../components/NextSteps'

export function DecoratorRoute() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @route
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@route</code> decorator acts as a generic factory that can apply <strong>multiple HTTP methods</strong> to a single handler function.
                    It is useful for unifying logic or handling methods dynamically.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, route, RequestCtx, Response

class GeneralController(Controller):
    
    # Handle both GET and POST on the same endpoint
    @route(["GET", "POST"], "/submit")
    async def handle_submit(self, ctx: RequestCtx):
        if ctx.method == "GET":
            return Response.html("Form HTML...")
        
        # POST logic
        data = await ctx.json()
        return Response.json({"received": data})`}
                    language="python"
                />
            </section>

            {/* Deep Dive: How it works */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <GitMerge className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Method Multiplexing</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    Under the hood, <code>@route</code> iterates over the provided list of methods and applies the corresponding specific decorator (e.g., <code>GET</code>, <code>POST</code>) sequentially.
                </p>

                <div className={`p-4 rounded border ${isDark ? 'bg-purple-900/20 border-purple-500/30' : 'bg-purple-50 border-purple-200'}`}>
                    <div className="flex items-start gap-3">
                        <Layers className="w-5 h-5 text-purple-500 mt-0.5" />
                        <div>
                            <h4 className={`font-semibold ${isDark ? 'text-purple-200' : 'text-purple-800'}`}>Stacking Behavior</h4>
                            <p className={`text-sm ${isDark ? 'text-purple-300' : 'text-purple-700'}`}>
                                Calling <code>@route(["GET", "POST"])</code> is functionally equivalent to stacking:
                                <br /><code className="text-xs mt-2 block">@GET(...)<br />@POST(...)<br />def handler(...): ...</code>
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/ws" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @WS
                </Link>
                <Link to="/docs/controllers/request-ctx" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: RequestCtx <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        
      <NextSteps />
    </div>
    )
}