import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Boxes } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function AquilaryRuntime() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Boxes className="w-4 h-4" />
          Aquilary / RuntimeRegistry
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            RuntimeRegistry
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">RuntimeRegistry</code> is the live, scoped registry used at runtime. It's built from validated manifests and provides module lookup, context scoping, and hot-reload support.
        </p>
      </div>

      {/* Core Classes */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registry Hierarchy</h2>
        <CodeBlock language="python" filename="registry.py">{`from aquilia.aquilary import Aquilary, AquilaryRegistry, RuntimeRegistry

# Aquilary — top-level entry point
aquilary = Aquilary()

# AquilaryRegistry — static registry (manifests, validation)
static_registry = AquilaryRegistry()
static_registry.register(users_manifest)
static_registry.register(products_manifest)

# RuntimeRegistry — live runtime (after validation + compilation)
runtime = RuntimeRegistry(static_registry)
await runtime.initialize()`}</CodeBlock>
      </section>

      {/* AppContext */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>AppContext</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Each module gets an <code className="text-aquilia-400">AppContext</code> providing scoped access to DI, config, and effects.
        </p>
        <CodeBlock language="python" filename="context.py">{`from aquilia.aquilary import AppContext

# Get context for a module
ctx = runtime.get_context("users")

print(ctx.name)           # "users"
print(ctx.version)        # "1.0.0"
print(ctx.controllers)    # [UserController, ProfileController]
print(ctx.models)         # [User, Profile]
print(ctx.config)         # Module-specific config`}</CodeBlock>
      </section>

      {/* RegistryMode */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registry Modes</h2>
        <CodeBlock language="python" filename="modes.py">{`from aquilia.aquilary import RegistryMode

# DEVELOPMENT — hot-reload enabled, verbose logging
# PRODUCTION — frozen manifest, optimized paths
# TESTING — isolated, mock-friendly

registry = AquilaryRegistry(mode=RegistryMode.DEVELOPMENT)

# In production, freeze the manifest for immutability
# aq freeze → generates frozen manifest
registry = AquilaryRegistry(mode=RegistryMode.PRODUCTION)`}</CodeBlock>
      </section>

      {/* RegistryFingerprint */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Registry Fingerprint</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A deterministic hash of the entire registry state, used for cache invalidation and deployment verification.
        </p>
        <CodeBlock language="python" filename="fingerprint.py">{`from aquilia.aquilary import FingerprintGenerator, RegistryFingerprint

gen = FingerprintGenerator()
fingerprint: RegistryFingerprint = gen.generate(registry)

print(fingerprint.hash)       # "sha256:a1b2c3d4..."
print(fingerprint.modules)    # {"users": "sha256:...", ...}
print(fingerprint.timestamp)  # datetime

# Compare with frozen manifest
if fingerprint != frozen_fingerprint:
    raise FrozenManifestMismatchError(...)`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}