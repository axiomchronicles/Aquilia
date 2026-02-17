import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Cpu } from 'lucide-react'

export function MLOpsOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Cpu className="w-4 h-4" />
          Advanced / MLOps
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          MLOps Platform
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia's MLOps module provides production-ready model packaging (Modelpack), a content-addressable registry, dynamic serving with batching, observability with drift detection, and rollout management — fully integrated with the framework's DI, fault, and lifecycle systems.
        </p>
      </div>

      {/* Architecture */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { name: 'ModelpackBuilder', desc: 'Packages models, dependencies, and metadata into a portable .modelpack archive with content-addressable storage.' },
            { name: 'RegistryService', desc: 'Centralized model registry with versioning, immutability enforcement, and push/pull semantics.' },
            { name: 'PythonRuntime', desc: 'Loads and executes models in an isolated Python runtime. Supports PyTorch, TensorFlow, ONNX, and scikit-learn.' },
            { name: 'ModelServingServer', desc: 'HTTP/gRPC serving layer with warmup strategies, health checks, and graceful draining.' },
            { name: 'DynamicBatcher', desc: 'Groups inference requests into micro-batches for GPU throughput optimization.' },
            { name: 'MetricsCollector', desc: 'Collects latency, throughput, error rate, and custom metrics. Exports to Prometheus/OpenTelemetry.' },
            { name: 'DriftDetector', desc: 'Monitors prediction distributions for data/concept drift using KS-test, PSI, and custom methods.' },
            { name: 'PluginHost', desc: 'Extension system for custom hooks: pre/post-inference, model loading, metrics export.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Modelpack */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Building a Modelpack</h2>
        <CodeBlock language="python" filename="build_pack.py">{`from aquilia.mlops import ModelpackBuilder, Framework

builder = ModelpackBuilder(
    name="sentiment-classifier",
    version="v1.2.0",
    description="BERT-based sentiment analysis model",
)

# Add the model file
builder.add_model(
    "model.pt",
    framework=Framework.PYTORCH,
    input_spec={"text": {"type": "string", "max_length": 512}},
    output_spec={"label": {"type": "string"}, "score": {"type": "number"}},
)

# Add preprocessing artifacts
builder.add_artifact("tokenizer/", "tokenizer")
builder.add_artifact("config.json", "config")

# Add dependencies
builder.add_requirements(["torch>=2.0", "transformers>=4.30"])

# Set provenance
builder.set_provenance(
    training_data="s3://data/sentiment-v3",
    training_commit="abc123",
    metrics={"accuracy": 0.945, "f1": 0.932},
)

# Build the pack
pack_path = await builder.save("./modelpacks/")
print(f"Modelpack saved to {pack_path}")
# → ./modelpacks/sentiment-classifier-v1.2.0.modelpack`}</CodeBlock>
      </section>

      {/* Registry */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Registry</h2>
        <CodeBlock language="python" filename="registry.py">{`from aquilia.mlops import RegistryService

registry = RegistryService(storage_path="./model-registry/")

# Push a modelpack to the registry
await registry.push("./modelpacks/sentiment-classifier-v1.2.0.modelpack")

# List available models
models = await registry.list_models()
for model in models:
    print(f"{model.name}:{model.version} — {model.framework}")

# Pull a specific version
pack = await registry.pull("sentiment-classifier", version="v1.2.0")

# Immutability — pushing the same version again raises an error
# ImmutabilityViolationFault: Version v1.2.0 already exists`}</CodeBlock>
      </section>

      {/* Serving */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Serving</h2>
        <CodeBlock language="python" filename="serve.py">{`from aquilia.mlops import (
    ModelServingServer, PythonRuntime,
    DynamicBatcher, WarmupStrategy,
)

# Create runtime
runtime = PythonRuntime()
await runtime.prepare(manifest, model_dir="./models/sentiment/")
await runtime.load()

# Create serving server
server = ModelServingServer(
    runtime=runtime,
    batcher=DynamicBatcher(
        max_batch_size=32,
        max_wait_ms=50,
        strategy="adaptive",
    ),
    warmup=WarmupStrategy.EAGER,  # Pre-warm on startup
    max_concurrent=100,
)

# Inference
result = await server.predict({
    "text": "This product is amazing!",
})
print(result)  # {"label": "positive", "score": 0.987}`}</CodeBlock>
      </section>

      {/* Drift Detection */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Drift Detection</h2>
        <CodeBlock language="python" filename="drift.py">{`from aquilia.mlops import DriftDetector, DriftMethod

detector = DriftDetector(
    method=DriftMethod.KS_TEST,  # Kolmogorov-Smirnov test
    window_size=1000,
    threshold=0.05,
    features=["text_length", "vocab_coverage"],
)

# Feed predictions for monitoring
detector.observe(predictions)

# Check for drift
report = detector.report()
if report.is_drifted:
    print(f"Drift detected: {report.drifted_features}")
    print(f"P-value: {report.p_value}")
    # Trigger alert or auto-retrain`}</CodeBlock>
      </section>

      {/* Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Framework Integration</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Integration

workspace = Workspace(
    integrations=[
        Integration.mlops(
            registry_path="./model-registry/",
            serving_port=8081,
            metrics_export="prometheus",
            drift_detection=True,
            drift_method="ks_test",
            drift_window=1000,
        ),
    ],
)

# MLOps controller is auto-registered at /mlops/*
# GET  /mlops/models          → List models
# GET  /mlops/models/{name}   → Model details
# POST /mlops/predict/{name}  → Inference
# GET  /mlops/health          → Health check
# GET  /mlops/metrics         → Prometheus metrics`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/mail" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Mail
        </Link>
        <Link to="/docs/cli" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          CLI <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
