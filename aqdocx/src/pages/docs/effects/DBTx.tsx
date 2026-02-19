import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Workflow } from 'lucide-react'

export function EffectsDBTx() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Workflow className="w-4 h-4" />
          Effects / DBTx
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Database Transaction Effect
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">DBTx</code> is a typed effect that represents a database transaction capability. Handlers declare whether they need read or write access, and the <code className="text-aquilia-400">DBTxProvider</code> manages connection pool acquisition, commits, and rollbacks automatically.
        </p>
      </div>

      {/* DBTx Effect */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Effect Token</h2>
        <CodeBlock language="python" filename="dbtx.py">{`from aquilia.effects import DBTx, EffectKind

# DBTx is a typed effect with mode support
read_tx = DBTx(mode="read")    # Read-only transaction
write_tx = DBTx(mode="write")  # Read-write transaction

# Bracket syntax
DBTx["read"]    # Read-only
DBTx["write"]   # Read-write

# Properties
print(read_tx.name)    # "DBTx"
print(read_tx.kind)    # EffectKind.DB
print(read_tx.mode)    # "read"`}</CodeBlock>
      </section>

      {/* DBTxProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DBTxProvider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The provider manages the full lifecycle of database transactions: pool initialization, connection acquisition per-request, and commit/rollback on release.
        </p>
        <CodeBlock language="python" filename="provider.py">{`from aquilia.effects import DBTxProvider, EffectRegistry

# Create provider with connection string
provider = DBTxProvider(connection_string="sqlite:///db.sqlite3")

# Register with effect registry
registry = EffectRegistry()
registry.register("DBTx", provider)

# Lifecycle
await registry.initialize_all()  # Creates connection pool

# Per-request usage (handled automatically by the framework)
resource = await provider.acquire(mode="read")
# resource = {"connection": ..., "mode": "read", "transaction": ...}

# On success → commit
await provider.release(resource, success=True)

# On failure → rollback
await provider.release(resource, success=False)`}</CodeBlock>
      </section>

      {/* EffectRegistry */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>EffectRegistry</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Central registry for all effect providers. Integrates with DI for lifecycle management.
        </p>
        <CodeBlock language="python" filename="registry.py">{`from aquilia.effects import EffectRegistry, DBTxProvider, CacheProvider

registry = EffectRegistry()
registry.register("DBTx", DBTxProvider("sqlite:///db.sqlite3"))
registry.register("Cache", CacheProvider("memory"))

# Check availability
registry.has_effect("DBTx")       # True
registry.has_effect("Queue")      # False

# Get provider
provider = registry.get_provider("DBTx")

# DI integration
registry.register_with_container(container)

# Lifecycle hooks (called by server)
await registry.startup()     # initialize_all
await registry.shutdown()    # finalize_all`}</CodeBlock>
      </section>

      {/* Effect Base Class */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Effects</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Extend <code className="text-aquilia-400">Effect</code> and <code className="text-aquilia-400">EffectProvider</code> to create custom effects.
        </p>
        <CodeBlock language="python" filename="custom.py">{`from aquilia.effects import Effect, EffectProvider, EffectKind

class StorageEffect(Effect):
    """Object storage effect."""
    def __init__(self, bucket: str = "default"):
        super().__init__("Storage", mode=bucket, kind=EffectKind.STORAGE)

class S3StorageProvider(EffectProvider):
    def __init__(self, bucket: str, region: str):
        self.bucket = bucket
        self.region = region

    async def initialize(self):
        # Create S3 client
        ...

    async def acquire(self, mode=None):
        # Return S3 handle for the bucket
        return S3Handle(self.client, mode or self.bucket)

    async def release(self, resource, success=True):
        # Nothing to release for S3
        pass`}</CodeBlock>
      </section>
    </div>
  )
}
