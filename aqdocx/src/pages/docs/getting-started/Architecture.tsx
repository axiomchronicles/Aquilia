import { useTheme } from '../../../context/ThemeContext'
import { Link } from 'react-router-dom'
import { Layers, ArrowRight } from 'lucide-react'

export function ArchitecturePage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Layers className="w-4 h-4" />
          Getting Started
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Architecture
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia is built as a layered, async-native framework. Each layer has a clear responsibility, and they compose together through well-defined interfaces.
        </p>
      </div>

      {/* Animated Architecture Diagram */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Layered Architecture</h2>
        <div className={boxClass}>
          <svg viewBox="0 0 900 600" className="w-full" fill="none">
            <defs>
              <linearGradient id="green-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#22c55e" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#4ade80" stopOpacity="0.2" />
              </linearGradient>
              <marker id="arrow" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                <polygon points="0 0,10 3.5,0 7" className="fill-aquilia-500/60" />
              </marker>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            {/* Transport Layer */}
            <g>
              <rect x="50" y="20" width="800" height="65" rx="14" className={`${isDark ? 'fill-zinc-900' : 'fill-gray-50'}`} stroke="url(#green-grad)" strokeWidth="1.5">
                <animate attributeName="stroke-opacity" values="0.4;1;0.4" dur="3s" repeatCount="indefinite" />
              </rect>
              <text x="90" y="50" className="fill-aquilia-500 text-xs font-bold tracking-wider">TRANSPORT LAYER</text>
              <text x="90" y="68" className={`text-[11px] ${isDark ? 'fill-gray-500' : 'fill-gray-500'}`}>ASGI Adapter • HTTP/1.1, HTTP/2, WebSocket • Lifespan Protocol</text>

              {/* Animated data packet */}
              <circle r="4" fill="#22c55e" filter="url(#glow)">
                <animateMotion dur="2s" repeatCount="indefinite" path="M100,40 L800,40" />
                <animate attributeName="opacity" values="0;1;1;0" dur="2s" repeatCount="indefinite" />
              </circle>
            </g>

            <line x1="450" y1="85" x2="450" y2="110" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Middleware Layer */}
            <g>
              <rect x="50" y="110" width="800" height="65" rx="14" className={`${isDark ? 'fill-zinc-900' : 'fill-gray-50'}`} stroke="url(#green-grad)" strokeWidth="1.5" strokeOpacity="0.6" />
              <text x="90" y="140" className="fill-aquilia-500 text-xs font-bold tracking-wider">MIDDLEWARE STACK</text>
              <text x="90" y="158" className={`text-[11px] ${isDark ? 'fill-gray-500' : 'fill-gray-500'}`}>Exception • RequestID • CORS • RateLimit • Security Headers • Static Files • Auth • Session</text>

              {/* Pipeline flow arrows */}
              {[200, 320, 440, 560, 680].map((x, i) => (
                <g key={i}>
                  <line x1={x} y1="142" x2={x + 40} y2="142" stroke="#22c55e" strokeOpacity="0.2" strokeWidth="1" markerEnd="url(#arrow)" />
                </g>
              ))}
            </g>

            <line x1="450" y1="175" x2="450" y2="200" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Controller Layer */}
            <g>
              <rect x="50" y="200" width="800" height="80" rx="14" className="fill-aquilia-500/5" stroke="#22c55e" strokeWidth="2" strokeOpacity="0.5">
                <animate attributeName="stroke-opacity" values="0.3;0.8;0.3" dur="4s" repeatCount="indefinite" />
              </rect>
              <text x="90" y="230" className="fill-aquilia-500 text-xs font-bold tracking-wider">CONTROLLER ENGINE</text>
              <text x="90" y="248" className={`text-[11px] ${isDark ? 'fill-gray-500' : 'fill-gray-500'}`}>ControllerCompiler → Route Tree → Pattern Match → Handler Dispatch</text>
              <text x="90" y="266" className={`text-[11px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>RequestCtx wraps scope, request, response for each handler invocation</text>

              {/* Pulsing core */}
              <circle cx="800" cy="240" r="15" fill="#22c55e" fillOpacity="0.1" stroke="#22c55e" strokeWidth="1" strokeOpacity="0.3">
                <animate attributeName="r" values="12;18;12" dur="2s" repeatCount="indefinite" />
                <animate attributeName="fill-opacity" values="0.05;0.15;0.05" dur="2s" repeatCount="indefinite" />
              </circle>
              <text x="800" y="244" textAnchor="middle" className="fill-aquilia-400 text-[9px] font-bold">CTX</text>
            </g>

            <line x1="450" y1="280" x2="450" y2="305" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* DI Container */}
            <g>
              <rect x="50" y="305" width="800" height="65" rx="14" className={`${isDark ? 'fill-zinc-900' : 'fill-gray-50'}`} stroke="url(#green-grad)" strokeWidth="1.5" strokeOpacity="0.4" />
              <text x="90" y="335" className="fill-aquilia-500 text-xs font-bold tracking-wider">DEPENDENCY INJECTION</text>
              <text x="90" y="353" className={`text-[11px] ${isDark ? 'fill-gray-500' : 'fill-gray-500'}`}>Container → Provider Resolution → Scoped Lifetimes (Singleton, App, Request, Transient, Pooled, Ephemeral)</text>
            </g>

            <line x1="450" y1="370" x2="450" y2="395" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Services Layer */}
            <g>
              <rect x="50" y="395" width="800" height="65" rx="14" className={`${isDark ? 'fill-zinc-900' : 'fill-gray-50'}`} stroke="url(#green-grad)" strokeWidth="1.5" strokeOpacity="0.3" />
              <text x="90" y="425" className="fill-aquilia-500 text-xs font-bold tracking-wider">SERVICES & EFFECTS</text>
              <text x="90" y="443" className={`text-[11px] ${isDark ? 'fill-gray-500' : 'fill-gray-500'}`}>Business Logic • Effect System (DBTx, Cache, Queue) • Guards • Serializers • Validators</text>
            </g>

            <line x1="450" y1="460" x2="450" y2="485" stroke="#22c55e" strokeOpacity="0.3" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Data Layer */}
            <g>
              <rect x="50" y="485" width="800" height="65" rx="14" className={`${isDark ? 'fill-zinc-900' : 'fill-gray-50'}`} stroke="url(#green-grad)" strokeWidth="1.5" strokeOpacity="0.2" />
              <text x="90" y="515" className="fill-aquilia-500 text-xs font-bold tracking-wider">DATA & INFRASTRUCTURE</text>
              <text x="90" y="533" className={`text-[11px] ${isDark ? 'fill-gray-500' : 'fill-gray-500'}`}>ORM Models • Database Engine • Cache Service • Sessions • Templates • Mail • MLOps • Sockets</text>
            </g>

            {/* Side annotations */}
            <g className={isDark ? 'fill-zinc-600' : 'fill-gray-400'}>
              <text x="870" y="55" textAnchor="end" className="text-[9px] font-mono" transform="rotate(-90, 870, 55)">lifecycle</text>
              <line x1="862" y1="20" x2="862" y2="550" strokeDasharray="4 4" className={isDark ? 'stroke-zinc-800' : 'stroke-gray-200'} strokeWidth="1" />
            </g>
          </svg>
        </div>
      </section>

      {/* Layer Descriptions */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Layer Breakdown</h2>
        <div className="space-y-6">
          {[
            {
              title: 'Transport Layer — ASGI Adapter',
              desc: 'The ASGIAdapter translates raw ASGI scope/receive/send into Aquilia\'s Request and Response objects. It handles HTTP/1.1, HTTP/2, WebSocket connections, and the lifespan protocol for startup/shutdown events.',
              link: '/docs/server/asgi',
            },
            {
              title: 'Middleware Stack',
              desc: 'An ordered pipeline of middleware classes. Each middleware can inspect/modify requests and responses. Built-in middleware includes exception handling, request IDs, CORS, rate limiting, security headers, static files, authentication, and sessions.',
              link: '/docs/middleware',
            },
            {
              title: 'Controller Engine',
              desc: 'The ControllerCompiler compiles controller classes into a radix-tree router at startup. At runtime, the ControllerEngine dispatches requests by matching URL patterns, extracting path parameters, and calling the appropriate handler with a RequestCtx instance.',
              link: '/docs/controllers',
            },
            {
              title: 'Dependency Injection',
              desc: 'A hierarchical, scoped DI container that resolves services with different lifetimes: Singleton (process-wide), App (per-app), Request (per-HTTP-request), Transient (new each time), Pooled (from a pool), and Ephemeral (disposed immediately).',
              link: '/docs/di',
            },
            {
              title: 'Services & Effects',
              desc: 'Business logic lives in service classes injected by the DI container. The Effect system provides typed side-effect declarations (DBTx, Cache, Queue) that the framework manages automatically.',
              link: '/docs/effects',
            },
            {
              title: 'Data & Infrastructure',
              desc: 'The data layer includes the async ORM with models, fields, queries, and migrations; the multi-backend database engine; cache service with stampede prevention; cryptographic sessions; Jinja2 templates; mail service; MLOps platform; and WebSocket runtime.',
              link: '/docs/models',
            },
          ].map((layer, i) => (
            <div key={i} className={boxClass}>
              <h3 className={`text-lg font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{layer.title}</h3>
              <p className={`text-sm mb-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{layer.desc}</p>
              <Link to={layer.link} className="inline-flex items-center gap-1 text-sm text-aquilia-500 hover:underline font-medium">
                Learn more <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Request Lifecycle */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request Lifecycle</h2>
        <div className={boxClass}>
          <svg viewBox="0 0 800 200" className="w-full" fill="none">
            {/* Flow boxes */}
            {[
              { x: 10, label: 'ASGI', sub: 'scope' },
              { x: 140, label: 'Request', sub: 'parse' },
              { x: 270, label: 'Middleware', sub: 'pipeline' },
              { x: 410, label: 'Router', sub: 'match' },
              { x: 540, label: 'Handler', sub: 'execute' },
              { x: 670, label: 'Response', sub: 'send' },
            ].map((box, i) => (
              <g key={i}>
                <rect x={box.x} y="40" width="110" height="60" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5">
                  <animate attributeName="stroke-opacity" values="0.2;0.6;0.2" dur="3s" begin={`${i * 0.5}s`} repeatCount="indefinite" />
                </rect>
                <text x={box.x + 55} y="66" textAnchor="middle" className="fill-aquilia-500 text-[11px] font-bold">{box.label}</text>
                <text x={box.x + 55} y="84" textAnchor="middle" className={`text-[9px] ${isDark ? 'fill-gray-500' : 'fill-gray-400'}`}>{box.sub}</text>
                {i < 5 && (
                  <line x1={box.x + 115} y1="70" x2={box.x + 135} y2="70" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#arrow)" />
                )}
              </g>
            ))}
            {/* Flow indicator */}
            <circle r="5" fill="#22c55e" filter="url(#glow)">
              <animateMotion dur="4s" repeatCount="indefinite" path="M15,70 L145,70 L275,70 L415,70 L545,70 L675,70 L780,70" />
              <animate attributeName="opacity" values="0.8;1;0.8" dur="1s" repeatCount="indefinite" />
            </circle>

            <text x="400" y="140" textAnchor="middle" className={`text-[11px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>
              Every request flows through this pipeline. Middleware can short-circuit at any point.
            </text>
            <text x="400" y="160" textAnchor="middle" className={`text-[11px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>
              The DI Container resolves all dependencies for the handler before invocation.
            </text>
          </svg>
        </div>
      </section>

      {/* Next */}
      <section>
        <div className="flex gap-4">
          <Link to="/docs/project-structure" className={`flex-1 group p-6 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold mb-2 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Project Structure <ArrowRight className="w-4 h-4 text-aquilia-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Learn how to organize an Aquilia project</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
