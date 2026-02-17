import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Boxes } from 'lucide-react'

export function AquilaryFingerprint() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Boxes className="w-4 h-4" />
          Aquilary / Fingerprinting
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Fingerprinting
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Fingerprinting produces a deterministic hash of the entire module registry. Used for deployment verification, cache invalidation, and ensuring frozen manifests match the live state.
        </p>
      </div>

      {/* FingerprintGenerator */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FingerprintGenerator</h2>
        <CodeBlock language="python" filename="fingerprint.py">{`from aquilia.aquilary import FingerprintGenerator

gen = FingerprintGenerator()

# Generate fingerprint from registry
fingerprint = gen.generate(registry)

# The fingerprint includes:
# - Module names, versions, and dependencies
# - Controller routes and method signatures
# - Model schemas and field definitions
# - Config schemas
# - Effect declarations`}</CodeBlock>
      </section>

      {/* RegistryFingerprint */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RegistryFingerprint</h2>
        <CodeBlock language="python" filename="usage.py">{`from aquilia.aquilary import RegistryFingerprint

# Fingerprint data structure
fingerprint = RegistryFingerprint(
    hash="sha256:a1b2c3d4e5f6...",
    modules={
        "users": "sha256:111...",
        "products": "sha256:222...",
    },
    timestamp=datetime.now(),
    registry_mode="production",
)

# Compare fingerprints
if current_fingerprint.hash != deployed_fingerprint.hash:
    print("Registry has changed since last deployment!")
    
    # Find which modules changed
    for name, hash in current_fingerprint.modules.items():
        if hash != deployed_fingerprint.modules.get(name):
            print(f"  Changed: {name}")`}</CodeBlock>
      </section>

      {/* Freeze & Verify */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Freeze & Verify</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Use <code className="text-aquilia-400">aq freeze</code> to lock the manifest, then verify at startup in production mode.
        </p>
        <CodeBlock language="bash" filename="terminal">{`# Freeze the current manifest
aq freeze

# This generates .aquilia/frozen_manifest.json
# containing the full registry fingerprint

# At startup in PRODUCTION mode, Aquilia verifies
# the live registry matches the frozen manifest.
# Any mismatch raises FrozenManifestMismatchError.`}</CodeBlock>
      </section>
    </div>
  )
}
