import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, Activity, Globe } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../../components/NextSteps'

export function DecoratorWS() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-teal-500/10 text-teal-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @WS
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@WS</code> decorator creates <strong>WebSocket endpoints</strong> for real-time, bidirectional communication.
                    Unlike HTTP handlers, WebSocket handlers maintain a persistent connection.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, WS, RequestCtx, WebSocket

class ChatController(Controller):
    
    @WS("/chat/«room_id»")
    async def chat_endpoint(self, ctx: RequestCtx, room_id: str):
        ws: WebSocket = ctx.websocket
        await ws.accept()
        
        try:
            while True:
                data = await ws.receive_text()
                await ws.send_text(f"Echo from {room_id}: {data}")
        except Exception:
            print("Client disconnected")`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Lifecycle */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Activity className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Connection Lifecycle</h2>
                </div>
                <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    A WebSocket handler has a distinct lifecycle compared to HTTP handlers.
                </p>

                <div className="space-y-4">
                    <div className={`p-4 rounded border ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-white border-gray-200'}`}>
                        <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>1. Handshake</h3>
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            The connection starts as an HTTP Upgrade request. Aquilia routes this to your handler.
                            You <strong>must</strong> call <code>await ws.accept()</code> to complete the handshake, or the connection will close.
                        </p>
                    </div>
                    <div className={`p-4 rounded border ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-white border-gray-200'}`}>
                        <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>2. Message Loop</h3>
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Typically implemented as a <code>while True</code> loop. Use <code>receive_text()</code>, <code>receive_bytes()</code>, or <code>receive_json()</code> to wait for messages.
                        </p>
                    </div>
                    <div className={`p-4 rounded border ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-white border-gray-200'}`}>
                        <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>3. Disconnection</h3>
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            When the client disconnects, `receive_*` methods will raise a `WebSocketDisconnect` exception.
                            It is best practice to wrap your loop in a try/except block to handle cleanups.
                        </p>
                    </div>
                </div>
            </section>

            {/* Limitations */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Globe className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Differences from HTTP</h2>
                </div>
                <ul className={`list-disc pl-5 space-y-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    <li>
                        <strong>No Response Object:</strong> You do not return a `Response` object. You send data directly via `ws.send_*`.
                    </li>
                    <li>
                        <strong>Middleware Limitations:</strong> Some global middleware (like GZip or Content-Length helpers) may not apply to the WebSocket stream itself, only the initial handshake.
                    </li>
                    <li>
                        <strong>Pipelines:</strong> Route pipelines (`pipeline=[...]`) <strong>do not apply</strong> to WebSockets in the same way, as there isn't a single request/response cycle.
                        However, guards run <em>before</em> the handler is invoked, allowing you to reject the handshake (e.g., authentication).
                    </li>
                </ul>
            </section>

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/options" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @OPTIONS
                </Link>
                <Link to="/docs/controllers/decorators/route" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: @route <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        
      <NextSteps />
    </div>
    )
}