import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Settings } from 'lucide-react'

export function ControllersFactory() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Settings className="w-4 h-4" />Controllers</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Controller Factory</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ControllerFactory</code> is responsible for instantiating controller classes. It manages the lifecycle of controller instances based on the <code className="text-aquilia-500">instantiation_mode</code>.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Instantiation Modes</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {[
            { mode: 'per_request', desc: 'A new controller instance is created for every HTTP request. Constructor dependencies are resolved from the request-scoped DI container. This is the default and recommended for stateful controllers.' },
            { mode: 'singleton', desc: 'A single controller instance is created at startup and reused for all requests. The constructor is called once with app-scoped dependencies. Best for stateless controllers.' },
          ].map((m, i) => (
            <div key={i} className={`p-6 rounded-xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
              <code className="text-aquilia-500 font-mono font-bold text-sm">{m.mode}</code>
              <p className={`text-sm mt-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{m.desc}</p>
            </div>
          ))}
        </div>
        <CodeBlock language="python" filename="Instantiation Modes">{`# Per-request (default): new instance per request
class UserController(Controller):
    prefix = "/users"
    instantiation_mode = "per_request"

    @Inject()
    def __init__(self, service: UserService):
        self.service = service  # Resolved per-request


# Singleton: one instance for the entire app lifetime
class HealthController(Controller):
    prefix = "/health"
    instantiation_mode = "singleton"

    @Inject()
    def __init__(self, metrics: MetricsService):
        self.metrics = metrics  # Resolved once at startup

    async def on_startup(self, ctx):
        await self.metrics.init()

    async def on_shutdown(self, ctx):
        await self.metrics.close()`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How the Factory Works</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <svg viewBox="0 0 700 200" className="w-full" fill="none">
            <defs><marker id="fa" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" className="fill-aquilia-500/50" /></marker></defs>
            {[
              { x: 10, label: 'Engine', sub: 'receives request' },
              { x: 155, label: 'Factory', sub: 'check mode' },
              { x: 310, label: 'DI Resolve', sub: 'constructor args' },
              { x: 465, label: 'Instance', sub: 'controller ready' },
              { x: 580, label: 'Handler', sub: 'invoke method' },
            ].map((b, i) => (
              <g key={i}>
                <rect x={b.x} y="50" width="130" height="55" rx="10" className="fill-aquilia-500/10 stroke-aquilia-500/30" strokeWidth="1.5" />
                <text x={b.x+65} y="75" textAnchor="middle" className="fill-aquilia-500 text-[11px] font-bold">{b.label}</text>
                <text x={b.x+65} y="92" textAnchor="middle" className={`text-[9px] ${isDark ? 'fill-gray-500' : 'fill-gray-400'}`}>{b.sub}</text>
                {i < 4 && <line x1={b.x+135} y1="78" x2={b.x+150} y2="78" stroke="#22c55e" strokeOpacity="0.4" strokeWidth="1.5" markerEnd="url(#fa)" />}
              </g>
            ))}
            <text x="350" y="140" textAnchor="middle" className={`text-[10px] ${isDark ? 'fill-gray-600' : 'fill-gray-400'}`}>For singleton mode, step 2-4 happen once at startup. For per_request, they happen every request.</text>
          </svg>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Dependency Injection in Controllers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">@Inject()</code> decorator tells the factory to resolve constructor parameters from the DI container. Type annotations are used to match providers:
        </p>
        <CodeBlock language="python" filename="Constructor DI">{`from aquilia import Controller, Inject, Get
from aquilia.di import Singleton


class OrderController(Controller):
    prefix = "/orders"

    @Inject()
    def __init__(
        self,
        order_service: OrderService,      # Resolved from DI
        payment_gateway: PaymentGateway,  # Resolved from DI
        notifier: NotificationService,    # Resolved from DI
    ):
        self.orders = order_service
        self.payments = payment_gateway
        self.notifier = notifier

    @Post("/")
    async def create_order(self, ctx):
        body = await ctx.json()
        order = await self.orders.create(body)
        await self.payments.charge(order)
        await self.notifier.send(order.user, "Order created!")
        return ctx.json({"order": order.to_dict()}, status=201)`}</CodeBlock>
      </section>
    </div>
  )
}
