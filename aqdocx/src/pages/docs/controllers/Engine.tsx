import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Cpu } from 'lucide-react'

export function ControllersEngine() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Cpu className="w-4 h-4" />Controllers</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Controller Engine</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ControllerEngine</code> is the runtime dispatcher that receives incoming HTTP requests, matches them against the compiled route tree, and invokes the appropriate controller handler.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request Dispatch Flow</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 700 260" className="w-full" fill="none">
            <defs><marker id="eng-a" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" className="fill-aquilia-500/50" /></marker></defs>
            {/* Step boxes */}
            {[
              { x: 10, y: 20, label: '1. Receive', sub: 'ASGI scope' },
              { x: 160, y: 20, label: '2. Match', sub: 'radix tree lookup' },
              { x: 310, y: 20, label: '3. Extract', sub: 'path params' },
              { x: 460, y: 20, label: '4. Pipeline', sub: 'guards/interceptors' },
            ].map((b, i) => (
              <g key={i}>
                <rect x={b.x} y={b.y} width="135" height="55" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5" />
                <text x={b.x+67} y={b.y+24} textAnchor="middle" className="fill-aquilia-500 text-[11px] font-bold">{b.label}</text>
                <text x={b.x+67} y={b.y+42} textAnchor="middle" className={`text-[9px] ${isDark ? 'fill-gray-500' : 'fill-gray-400'}`}>{b.sub}</text>
                {i < 3 && <line x1={b.x+140} y1={b.y+28} x2={b.x+155} y2={b.y+28} stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#eng-a)" />}
              </g>
            ))}
            {/* Arrow down */}
            <line x1="527" y1="75" x2="527" y2="100" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#eng-a)" />
            {[
              { x: 460, y: 105, label: '5. Instantiate', sub: 'factory creates ctrl' },
              { x: 310, y: 105, label: '6. Build Ctx', sub: 'RequestCtx' },
              { x: 160, y: 105, label: '7. Invoke', sub: 'handler method' },
              { x: 10, y: 105, label: '8. Response', sub: 'send back' },
            ].map((b, i) => (
              <g key={i}>
                <rect x={b.x} y={b.y} width="135" height="55" rx="10" className={`${isDark ? 'fill-zinc-900 stroke-zinc-700' : 'fill-gray-50 stroke-gray-300'}`} strokeWidth="1.5" />
                <text x={b.x+67} y={b.y+24} textAnchor="middle" className={`text-[11px] font-bold ${isDark ? 'fill-gray-300' : 'fill-gray-700'}`}>{b.label}</text>
                <text x={b.x+67} y={b.y+42} textAnchor="middle" className={`text-[9px] ${isDark ? 'fill-gray-500' : 'fill-gray-400'}`}>{b.sub}</text>
                {i < 3 && <line x1={b.x-5} y1={b.y+28} x2={b.x+(-15)} y2={b.y+28} stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#eng-a)" transform="rotate(180)" />}
              </g>
            ))}
            <line x1="455" y1="133" x2="450" y2="133" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#eng-a)" />
            <line x1="305" y1="133" x2="300" y2="133" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#eng-a)" />
            <line x1="155" y1="133" x2="150" y2="133" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#eng-a)" />

            <text x="350" y="200" textAnchor="middle" className={`text-[10px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>The Engine handles the entire request lifecycle from ASGI scope to response bytes.</text>
            <text x="350" y="218" textAnchor="middle" className={`text-[10px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>If no route matches, a 404 response is returned. Exceptions trigger the fault system.</text>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Route Matching</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The engine uses a radix tree (compiled at startup by the ControllerCompiler) for O(log n) route matching. It supports:
        </p>
        <ul className={`space-y-2 mb-6 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>Static segments: <code className="text-aquilia-500">/users/list</code></li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>Dynamic segments: <code className="text-aquilia-500">{'/users/{id:int}'}</code></li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>Catch-all segments: <code className="text-aquilia-500">{'/files/{path:path}'}</code></li>
          <li className="flex gap-2"><span className="text-aquilia-500">•</span>Method-based matching: different handlers for GET vs POST on the same path</li>
        </ul>
        <CodeBlock language="python" filename="Route Matching Examples">{`# These routes are compiled into a radix tree:
#   /api/users          → UserController.list_users (GET)
#   /api/users          → UserController.create_user (POST)
#   /api/users/{id:int} → UserController.get_user (GET)
#   /api/users/{id:int} → UserController.update_user (PUT)
#   /api/users/{id:int} → UserController.delete_user (DELETE)

# At runtime, GET /api/users/42 resolves to:
#   handler: UserController.get_user
#   path_params: {"id": 42}  (already parsed as int)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Error Handling</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When a handler raises an exception, the Engine catches it and delegates to the Fault system:
        </p>
        <CodeBlock language="python" filename="Engine Error Flow">{`# If a handler raises an exception:
#   1. The Engine catches it
#   2. It wraps it in an AquiliaFault with the appropriate domain
#   3. The ExceptionMiddleware formats it into a proper HTTP response
#   4. In debug mode, a rich error page is shown
#   5. In production, a sanitized JSON/HTML error response is sent

# Handlers can also return error responses directly:
@Get("/{id:int}")
async def get(self, ctx, id: int):
    try:
        item = await self.service.get(id)
        return ctx.json({"item": item.to_dict()})
    except NotFoundError:
        return ctx.json({"error": "Not found"}, status=404)`}</CodeBlock>
      </section>
    </div>
  )
}
