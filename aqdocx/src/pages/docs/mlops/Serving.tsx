import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Brain } from 'lucide-react'

export function MLOpsServing() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Brain className="w-4 h-4" />
          MLOps / Serving
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Model Serving
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">ModelServingServer</code> turns a modelpack into an HTTP prediction endpoint with dynamic batching, warmup strategies, and health checks.
        </p>
      </div>

      {/* ModelServingServer */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ModelServingServer</h2>
        <CodeBlock language="python" filename="serving.py">{`from aquilia.mlops import ModelServingServer, RegistryService

registry = RegistryService(store=store)
server = ModelServingServer(
    registry=registry,
    model_name="sentiment-classifier",
    host="0.0.0.0",
    port=8501,
)

# Start serving
await server.start()

# Prediction endpoint: POST /predict
# Health endpoint:     GET  /health
# Metrics endpoint:    GET  /metrics`}</CodeBlock>
      </section>

      {/* DynamicBatcher */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DynamicBatcher</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Batches incoming requests to maximize GPU/CPU throughput. Accumulates predictions until a batch size or timeout is reached, then runs a single forward pass.
        </p>
        <CodeBlock language="python" filename="batcher.py">{`from aquilia.mlops import DynamicBatcher

batcher = DynamicBatcher(
    max_batch_size=32,     # Max requests per batch
    max_wait_ms=50,        # Max wait time before flushing
    adaptive=True,         # Adjust batch size based on load
)

server = ModelServingServer(
    registry=registry,
    model_name="sentiment-classifier",
    batcher=batcher,
)`}</CodeBlock>
      </section>

      {/* WarmupStrategy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>WarmupStrategy</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Runs sample predictions on startup to warm up JIT compilers, GPU memory, and caches.
        </p>
        <CodeBlock language="python" filename="warmup.py">{`from aquilia.mlops import WarmupStrategy

warmup = WarmupStrategy(
    samples=[
        {"text": "This product is great!"},
        {"text": "Terrible experience."},
    ],
    rounds=3,      # Run each sample 3 times
    validate=True,  # Verify output matches expected schema
)

server = ModelServingServer(
    registry=registry,
    model_name="sentiment-classifier",
    warmup=warmup,
)`}</CodeBlock>
      </section>

      {/* Serving API */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Endpoints</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Endpoint</th>
                <th className="py-3 px-4 text-left font-semibold">Method</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['/predict', 'POST', 'Run inference on input data'],
                ['/predict/batch', 'POST', 'Run batch inference'],
                ['/health', 'GET', 'Server health check'],
                ['/health/ready', 'GET', 'Readiness probe (model loaded)'],
                ['/health/live', 'GET', 'Liveness probe (server running)'],
                ['/metrics', 'GET', 'Prometheus-format metrics'],
                ['/model/info', 'GET', 'Current model metadata'],
                ['/model/reload', 'POST', 'Hot-reload production model'],
              ].map(([ep, method, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{ep}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{method}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
