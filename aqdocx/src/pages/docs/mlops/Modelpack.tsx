import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Brain } from 'lucide-react'

export function MLOpsModelpack() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Brain className="w-4 h-4" />
          MLOps / Modelpack
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Modelpack
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-400">Modelpack</code> is a self-contained bundle of a trained model, its metadata, preprocessing artifacts, and versioning information. <code className="text-aquilia-400">ModelpackBuilder</code> provides a fluent API for assembling modelpacks.
        </p>
      </div>

      {/* ModelpackBuilder */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ModelpackBuilder</h2>
        <CodeBlock language="python" filename="builder.py">{`from aquilia.mlops import ModelpackBuilder

pack = (
    ModelpackBuilder("sentiment-classifier")
    .version("1.2.0")
    .framework("sklearn")
    .model(trained_model)                    # The trained model object
    .preprocessor(tfidf_vectorizer)          # Preprocessing pipeline
    .metadata({
        "accuracy": 0.94,
        "f1_score": 0.92,
        "training_date": "2024-01-15",
        "dataset": "imdb_reviews",
    })
    .input_schema({"text": "string"})
    .output_schema({"label": "string", "confidence": "float"})
    .tags(["nlp", "sentiment", "production"])
    .build()
)

# Save to disk
pack.save("./models/sentiment-v1.2.0.aqpack")

# Load from disk
loaded = Modelpack.load("./models/sentiment-v1.2.0.aqpack")`}</CodeBlock>
      </section>

      {/* ContentStore */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ContentStore</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">ContentStore</code> handles serialization and storage of model artifacts.
        </p>
        <CodeBlock language="python" filename="store.py">{`from aquilia.mlops import ContentStore

# Built-in stores
store = ContentStore.local("./model_store/")    # Local filesystem
store = ContentStore.s3("my-bucket", prefix="models/")  # S3

# Store a modelpack
content_id = await store.put(pack)

# Retrieve a modelpack
loaded_pack = await store.get(content_id)

# List stored modelpacks
packs = await store.list()
for p in packs:
    print(f"{p.name} v{p.version} ({p.content_id})")`}</CodeBlock>
      </section>

      {/* Modelpack Metadata */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Modelpack Properties</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Property</th>
                <th className="py-3 px-4 text-left font-semibold">Type</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['name', 'str', 'Modelpack name (unique identifier)'],
                ['version', 'str', 'Semantic version string'],
                ['framework', 'str', 'ML framework (sklearn, torch, tf, onnx)'],
                ['model', 'Any', 'The trained model object'],
                ['preprocessor', 'Any | None', 'Optional preprocessing pipeline'],
                ['metadata', 'dict', 'Arbitrary key-value metadata'],
                ['input_schema', 'dict', 'JSON Schema for input validation'],
                ['output_schema', 'dict', 'JSON Schema for output format'],
                ['tags', 'list[str]', 'Searchable tags'],
                ['created_at', 'datetime', 'Pack creation timestamp'],
                ['content_id', 'str', 'Content-addressable hash'],
              ].map(([prop, type, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{prop}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{type}</td>
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
