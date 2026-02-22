import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, GitBranch, ArrowLeft, ArrowRight, Zap, RefreshCw, Layers } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../components/NextSteps'

export function DIRequestDAG() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-12">
                <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
                    <Box className="w-4 h-4" />Dependency Injection
                </div>
                <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                        RequestDAG
                        <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
                    </span>
                </h1>
                <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    The <code className="text-aquilia-500">RequestDAG</code> is Aquilia's high-performance per-request dependency resolver. While the <code className="text-aquilia-500">Container</code> handles application-wide lifecycle and scope resolution, the <code className="text-aquilia-500">RequestDAG</code> dynamically parses, deduplicates, and resolves graph nodes declared via <code className="text-aquilia-500">Dep()</code> within route handlers.
                </p>
            </div>

            {/* Core Concepts */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Core Execution Mechanics</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                        { icon: <Layers className="w-5 h-5" />, title: 'Graph Deduplication', desc: 'If multiple dependencies inside your handler require the same sub-dependency (like a DB connection), the RequestDAG calculates a deduplicated graph. The shared sub-dependency executes exactly once.' },
                        { icon: <Zap className="w-5 h-5" />, title: 'Parallel Resolution', desc: 'Independent branches of the dependency graph are resolved concurrently using asyncio.gather. The engine maximizes throughput for async I/O bounded dependencies.' },
                        { icon: <RefreshCw className="w-5 h-5" />, title: 'LIFO Generator Teardown', desc: 'If a dependency yields a value, execution pauses. After the HTTP response is sent, the code following the yield block executes in strict Last-In-First-Out (LIFO) order to guarantee safe resource release.' },
                        { icon: <GitBranch className="w-5 h-5" />, title: 'Container Fallback', desc: 'If a Dep() annotation targets an interface or type natively bound in the application Container (via @service), the RequestDAG seamlessly falls back to container.resolve_async().' },
                    ].map((card, i) => (
                        <div key={i} className={`p-5 rounded-xl border ${isDark ? 'bg-[#111] border-white/10' : 'bg-white border-gray-200'}`}>
                            <div className="flex items-center gap-3 mb-3">
                                <div className="text-aquilia-500">{card.icon}</div>
                                <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{card.title}</h3>
                            </div>
                            <p className={`text-sm leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{card.desc}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Resolution Flow Example */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Resolution Flow</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Consider a route handler with deeply nested dependencies:
                </p>

                <CodeBlock language="python" filename="Nested Dependencies">{`from typing import Annotated
from aquilia.di import Dep

async def get_db():
    print("Opening DB")
    yield "DB_SESSION"
    print("Closing DB")

async def get_user_repo(db: Annotated[str, Dep(get_db)]):
    print("Creating UserRepo")
    return {"name": "UserRepository", "db": db}

async def get_auth_service(db: Annotated[str, Dep(get_db)]):
    print("Creating AuthService")
    return {"name": "AuthService", "db": db}

@get("/dashboard")
async def dashboard_view(
    repo: Annotated[dict, Dep(get_user_repo)],
    auth: Annotated[dict, Dep(get_auth_service)],
):
    return {"repo": repo, "auth": auth}`}</CodeBlock>

                <div className={`mt-6 p-6 rounded-xl border ${isDark ? 'bg-gray-900/50 border-gray-800' : 'bg-gray-50 border-gray-200'}`}>
                    <h4 className={`font-mono text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Execution Output Trace:</h4>
                    <ol className={`space-y-2 list-decimal list-inside font-mono text-sm ${isDark ? 'text-green-400' : 'text-green-700'}`}>
                        <li><span className={isDark ? 'text-gray-300' : 'text-gray-800'}>Opening DB</span> <span className="text-gray-500 text-xs italic">// Executed only once due to deduplication!</span></li>
                        <li><span className={isDark ? 'text-gray-300' : 'text-gray-800'}>Creating UserRepo</span> <span className="text-gray-500 text-xs italic">// Parallel with AuthService</span></li>
                        <li><span className={isDark ? 'text-gray-300' : 'text-gray-800'}>Creating AuthService</span></li>
                        <li><span className="text-blue-400">HTTP Response sent to client</span></li>
                        <li><span className={isDark ? 'text-gray-300' : 'text-gray-800'}>Closing DB</span> <span className="text-gray-500 text-xs italic">// Teardown executed in LIFO order</span></li>
                    </ol>
                </div>
            </section>

            {/* Skipping Deduplication */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Disabling Cache (Deduplication)</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    By default, all <code className="text-aquilia-500">Dep()</code> nodes are cached within a single request, meaning multiple branches requiring the same dependency receive the exact same instance. You can force the <code className="text-aquilia-500">RequestDAG</code> to re-evaluate the dependency by setting <code className="text-aquilia-500">cached=False</code>.
                </p>
                <CodeBlock language="python" filename="Uncached Dependencies">{`import uuid

def generate_tx_id():
    return str(uuid.uuid4())

@get("/process")
async def process_item(
    # These will receive the exact SAME uuid
    tx1: Annotated[str, Dep(generate_tx_id)],
    tx2: Annotated[str, Dep(generate_tx_id)],
    
    # These will receive DIFFERENT uuids
    id1: Annotated[str, Dep(generate_tx_id, cached=False)],
    id2: Annotated[str, Dep(generate_tx_id, cached=False)],
):
    assert tx1 == tx2
    assert id1 != id2`}</CodeBlock>
            </section>

            {/* Internal Architecture */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How It Works Internally</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    The RequestDAG is fundamentally bound to the <code className="text-aquilia-500">ControllerEngine</code>. During <code className="text-aquilia-500">_bind_parameters</code> (which maps parsed HTTP request data to handler signature parameters), Aquilia processes route annotations.
                </p>

                <ul className={`text-sm space-y-4 list-none pl-0 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    {[
                        { step: '1', title: 'Inspection', desc: 'The ControllerEngine identifies any parameter annotated with a Dep descriptor, or a callable with a defined __di_requires_coercion__ signature.' },
                        { step: '2', title: 'DAG Construction', desc: 'A new RequestDAG instance is spun up. It inspects signatures recursively, caching callable identities (hashes/refs) to detect diamond-shaped dependencies.' },
                        { step: '3', title: 'Execution', desc: 'Dependencies are batched layer by layer. The root nodes (those without dependencies themselves) are resolved concurrently via asyncio.gather(). Their results are injected into the next layer of nodes.' },
                        { step: '4', title: 'Teardown Queueing', desc: 'Any resolved dependency that returned an AsyncGenerator or Generator is intercepted. The engine loops the generator once (extracting the yielded value), and pushes the generator itself into a request-local teardown stack.' },
                        { step: '5', title: 'Cleanup', desc: 'The ControllerEngine wraps the request handler in a try...finally block. Once the HTTP response is complete, the finally block pops from the teardown stack (LIFO) and executes the remaining generator blocks (generators are driven to StopIteration).' }
                    ].map((item, i) => (
                        <li key={i} className="flex gap-4">
                            <div className="flex-shrink-0">
                                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-aquilia-500/20 text-aquilia-500 text-xs font-bold">{item.step}</span>
                            </div>
                            <div>
                                <strong className={isDark ? 'text-white' : 'text-gray-900'}>{item.title}</strong>
                                <p className="mt-1">{item.desc}</p>
                            </div>
                        </li>
                    ))}
                </ul>
            </section>


            {/* Navigation */}
            <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
                <Link to="/docs/di/decorators" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
                    <ArrowLeft className="w-4 h-4" /> Decorators
                </Link>
                <Link to="/docs/di/extractors" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
                    HTTP Extractors <ArrowRight className="w-4 h-4" />
                </Link>
            </div>

            <NextSteps />
        </div>
    )
}
