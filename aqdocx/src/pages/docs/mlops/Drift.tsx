import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Brain } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function MLOpsDrift() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Brain className="w-4 h-4" />
          MLOps / Drift Detection
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Drift Detection
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">DriftDetector</code> monitors prediction distributions over time to detect data drift, concept drift, and model degradation. <code className="text-aquilia-400">MetricsCollector</code> gathers latency, throughput, and error-rate metrics.
        </p>
      </div>

      {/* DriftDetector */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DriftDetector</h2>
        <CodeBlock language="python" filename="drift.py">{`from aquilia.mlops import DriftDetector

detector = DriftDetector(
    reference_data=training_distribution,
    method="ks",               # Kolmogorov-Smirnov test
    threshold=0.05,            # p-value threshold
    window_size=1000,          # Sliding window of predictions
    alert_callback=on_drift,   # Called when drift detected
)

# Feed predictions
detector.observe(input_features, prediction)

# Check drift status
report = detector.report()
print(report.is_drifted)     # True/False
print(report.p_value)        # 0.03
print(report.feature_scores) # {"text_length": 0.02, ...}
print(report.observations)   # 1247`}</CodeBlock>
      </section>

      {/* Drift Methods */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Detection Methods</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { name: 'ks', title: 'Kolmogorov-Smirnov', desc: 'Non-parametric test comparing two distributions. Good for continuous features.' },
            { name: 'psi', title: 'Population Stability Index', desc: 'Measures shift in population distributions. Widely used in credit scoring.' },
            { name: 'wasserstein', title: 'Wasserstein Distance', desc: 'Earth Mover\'s Distance between distributions. Sensitive to subtle shifts.' },
            { name: 'chi2', title: 'Chi-Squared', desc: 'For categorical features. Tests independence of observed vs expected frequencies.' },
          ].map((m, i) => (
            <div key={i} className={box}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`font-mono text-xs px-2 py-0.5 rounded ${isDark ? 'bg-aquilia-500/20 text-aquilia-400' : 'bg-aquilia-50 text-aquilia-600'}`}>{m.name}</span>
                <h3 className={`font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{m.title}</h3>
              </div>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* MetricsCollector */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>MetricsCollector</h2>
        <CodeBlock language="python" filename="metrics.py">{`from aquilia.mlops import MetricsCollector

collector = MetricsCollector()

# Automatic collection via serving server
server = ModelServingServer(
    registry=registry,
    model_name="sentiment-classifier",
    metrics_collector=collector,
)

# Manual observation
collector.observe_latency(duration_ms=12.5)
collector.observe_prediction(input_data, output_data)
collector.observe_error(error)

# Get metrics snapshot
metrics = collector.snapshot()
print(metrics.avg_latency_ms)      # 14.2
print(metrics.p99_latency_ms)      # 45.8
print(metrics.predictions_total)   # 50432
print(metrics.errors_total)        # 12
print(metrics.error_rate)          # 0.00024
print(metrics.throughput_rps)      # 125.3`}</CodeBlock>
      </section>

      {/* PredictionLogger */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>PredictionLogger</h2>
        <CodeBlock language="python" filename="logger.py">{`from aquilia.mlops import PredictionLogger

logger = PredictionLogger(
    store="prediction_logs/",  # Write predictions to disk
    sample_rate=0.1,           # Log 10% of predictions
    include_input=True,
    include_output=True,
)

server = ModelServingServer(
    registry=registry,
    model_name="sentiment-classifier",
    prediction_logger=logger,
)`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}