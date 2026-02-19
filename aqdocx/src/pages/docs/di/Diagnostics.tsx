import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

export function DIDiagnostics() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Box className="w-4 h-4" />Dependency Injection</div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Diagnostics
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The diagnostics module in <code className="text-aquilia-500">aquilia/di/diagnostics.py</code> provides observability into the DI container — event tracking, resolution timing, error reporting, and pluggable listeners. It also covers the <code className="text-aquilia-500">DependencyGraph</code> analysis tools, testing utilities, legacy compatibility, and CLI commands.
        </p>
      </div>

      {/* DIEventType */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DIEventType</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Every observable action in the DI container emits a typed event:
        </p>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Event</th>
              <th className="text-left py-3 pr-4">Emitted When</th>
              <th className="text-left py-3">Metadata</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['REGISTRATION', 'container.register() is called', 'token, tag, provider_name'],
                ['RESOLUTION_START', 'resolve_async() begins for a token', 'token, tag'],
                ['RESOLUTION_SUCCESS', 'resolve_async() completes successfully', 'token, tag, duration'],
                ['RESOLUTION_FAILURE', 'resolve_async() raises an error', 'token, tag, duration, error'],
                ['LIFECYCLE_STARTUP', 'Container startup begins', 'app_name (via metadata)'],
                ['LIFECYCLE_SHUTDOWN', 'Container shutdown begins', 'app_name (via metadata)'],
                ['PROVIDER_INSTANTIATION', 'A provider creates a new instance', 'token, provider_name, duration'],
              ].map(([event, when, meta], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{event}</code></td>
                  <td className={`py-3 pr-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{when}</td>
                  <td className={`py-3 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{meta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* DIEvent */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DIEvent</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A dataclass carrying all the data for a diagnostic event:
        </p>
        <CodeBlock language="python" filename="DIEvent Dataclass">{`from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time

@dataclass
class DIEvent:
    type: DIEventType                                # Event category
    timestamp: float = field(default_factory=time.time)  # When it occurred
    token: Optional[Any] = None                      # Resolution token
    tag: Optional[str] = None                        # Provider tag
    provider_name: Optional[str] = None              # Provider human name
    duration: Optional[float] = None                 # Operation duration (seconds)
    error: Optional[Exception] = None                # Error if failed
    metadata: Dict[str, Any] = field(default_factory=dict)  # Extra data`}</CodeBlock>
      </section>

      {/* DiagnosticListener Protocol */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DiagnosticListener Protocol</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Implement this protocol to receive DI events. The <code className="text-aquilia-500">on_event</code> method is called for every emitted event.
        </p>
        <CodeBlock language="python" filename="DiagnosticListener Protocol">{`from typing import Protocol

class DiagnosticListener(Protocol):
    def on_event(self, event: DIEvent) -> None:
        """Called when a DI event occurs."""
        ...`}</CodeBlock>
      </section>

      {/* ConsoleDiagnosticListener */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ConsoleDiagnosticListener</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A built-in listener that logs events to Python's <code className="text-aquilia-500">logging</code> system under the <code className="text-aquilia-500">aquilia.di.diagnostics</code> logger:
        </p>
        <CodeBlock language="python" filename="ConsoleDiagnosticListener">{`from aquilia.di.diagnostics import ConsoleDiagnosticListener

listener = ConsoleDiagnosticListener(log_level=logging.DEBUG)

# Output examples:
# DEBUG - Registered provider 'UserService' for token=UserService (tag=None)
# DEBUG - Resolving token=UserService (tag=None)...
# DEBUG - Resolved token=UserService in 0.0012s
# ERROR - Failed to resolve token=MissingService: ProviderNotFoundError(...)
# INFO  - Container startup: users_app`}</CodeBlock>
      </section>

      {/* DIDiagnostics Coordinator */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DIDiagnostics</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">DIDiagnostics</code> class coordinates event emission to multiple listeners. The Container holds a <code className="text-aquilia-500">_diagnostics</code> instance and calls <code className="text-aquilia-500">emit()</code> at key points.
        </p>
        <CodeBlock language="python" filename="DIDiagnostics API">{`from aquilia.di.diagnostics import DIDiagnostics, DIEventType

diagnostics = DIDiagnostics()

# Add listeners
diagnostics.add_listener(ConsoleDiagnosticListener())
diagnostics.add_listener(my_custom_listener)

# Emit events (called internally by Container)
diagnostics.emit(
    DIEventType.REGISTRATION,
    token=UserService,
    provider_name="UserService",
    tag=None,
)

# Measure duration with context manager
with diagnostics.measure(DIEventType.RESOLUTION_START, token=UserService):
    instance = await provider.instantiate(ctx)
# → Automatically emits RESOLUTION_SUCCESS or RESOLUTION_FAILURE with duration`}</CodeBlock>
      </section>

      {/* Custom Listener Example */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Listener Example</h2>
        <CodeBlock language="python" filename="Metrics Listener">{`class PrometheusListener:
    """Export DI metrics to Prometheus."""
    
    def __init__(self):
        from prometheus_client import Counter, Histogram
        
        self.resolutions = Counter(
            "di_resolutions_total",
            "Total DI resolutions",
            ["token", "status"],
        )
        self.resolution_duration = Histogram(
            "di_resolution_duration_seconds",
            "DI resolution latency",
            ["token"],
        )
    
    def on_event(self, event: DIEvent) -> None:
        if event.type == DIEventType.RESOLUTION_SUCCESS:
            self.resolutions.labels(
                token=str(event.token), status="success"
            ).inc()
            self.resolution_duration.labels(
                token=str(event.token)
            ).observe(event.duration)
        
        elif event.type == DIEventType.RESOLUTION_FAILURE:
            self.resolutions.labels(
                token=str(event.token), status="failure"
            ).inc()

# Register:
diagnostics.add_listener(PrometheusListener())`}</CodeBlock>
      </section>

      {/* _DiagnosticMeasure */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Duration Measurement</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">measure()</code> method returns a <code className="text-aquilia-500">_DiagnosticMeasure</code> context manager that automatically tracks operation duration:
        </p>
        <CodeBlock language="python" filename="_DiagnosticMeasure">{`class _DiagnosticMeasure:
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type:
            # On error → emit RESOLUTION_FAILURE with duration + error
            self.diagnostics.emit(
                DIEventType.RESOLUTION_FAILURE,
                duration=duration,
                error=exc_val,
                **self.kwargs,
            )
        else:
            # On success → emit RESOLUTION_SUCCESS with duration
            self.diagnostics.emit(
                DIEventType.RESOLUTION_SUCCESS,
                duration=duration,
                **self.kwargs,
            )`}</CodeBlock>
      </section>

      {/* DependencyGraph */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DependencyGraph</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">DependencyGraph</code> class in <code className="text-aquilia-500">aquilia/di/graph.py</code> provides graph analysis for the DI system. It builds an adjacency list from providers and their dependencies, then offers three key operations:
        </p>

        <div className="overflow-x-auto mb-6">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Method</th>
              <th className="text-left py-3 pr-4">Algorithm</th>
              <th className="text-left py-3">Returns</th>
            </tr></thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['detect_cycles()', 'Tarjan\'s SCC algorithm', 'List of strongly-connected components (cycles). Filters trivial SCCs.'],
                ['get_resolution_order()', 'Kahn\'s topological sort', 'List of tokens in dependency order. Raises DependencyCycleError if cycle found.'],
                ['export_dot()', 'Graph traversal', 'Graphviz DOT string. Color-codes nodes by scope.'],
                ['get_tree_view(root?)', 'Recursive DFS', 'Text tree view of dependencies. Marks circular and missing nodes.'],
              ].map(([method, algo, returns], i) => (
                <tr key={i}>
                  <td className="py-3 pr-4"><code className="text-aquilia-500 text-xs">{method}</code></td>
                  <td className={`py-3 pr-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{algo}</td>
                  <td className={`py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{returns}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" filename="DependencyGraph Usage">{`from aquilia.di.graph import DependencyGraph

graph = DependencyGraph()

# Add providers with their dependencies
graph.add_provider(user_service_provider, dependencies=["UserRepository", "CacheBackend"])
graph.add_provider(user_repo_provider, dependencies=["DatabasePool"])
graph.add_provider(cache_provider, dependencies=[])
graph.add_provider(pool_provider, dependencies=["AppConfig"])

# Detect cycles
cycles = graph.detect_cycles()
if cycles:
    print(f"Found {len(cycles)} cycle(s):")
    for cycle in cycles:
        print(f"  {' → '.join(cycle)}")

# Get resolution order (topological sort)
order = graph.get_resolution_order()
# → ["AppConfig", "DatabasePool", "CacheBackend", "UserRepository", "UserService"]

# Export as Graphviz DOT
dot = graph.export_dot()
Path("di_graph.dot").write_text(dot)
# → dot -Tpng di_graph.dot -o di_graph.png

# Text tree view
tree = graph.get_tree_view()
print(tree)
# ├── UserService (request)
# │   ├── UserRepository (app)
# │   │   └── DatabasePool (singleton)
# │   │       └── AppConfig (singleton)
# │   └── CacheBackend (singleton)
# ├── DatabasePool (singleton)
# │   └── AppConfig (singleton)`}</CodeBlock>
      </section>

      {/* Tarjan's Algorithm */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Tarjan's Algorithm Internals</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The cycle detection uses Tarjan's strongly-connected-component (SCC) algorithm — a single-pass DFS with O(V+E) complexity:
        </p>
        <CodeBlock language="python" filename="Tarjan's SCC">{`# Internal state:
_index_counter: int              # Global DFS counter
_stack: list[str]                # DFS stack
_lowlinks: dict[str, int]        # Lowest reachable index per node
_index: dict[str, int]           # Discovery index per node
_on_stack: set[str]              # Nodes currently on stack
_sccs: list[list[str]]           # All discovered SCCs

def _strongconnect(self, token: str):
    # 1. Assign index and lowlink
    self._index[token] = self._index_counter
    self._lowlinks[token] = self._index_counter
    self._index_counter += 1
    self._stack.append(token)
    self._on_stack.add(token)
    
    # 2. Visit successors (dependencies)
    for dep in self.adj_list.get(token, []):
        if dep not in self._index:
            self._strongconnect(dep)
            self._lowlinks[token] = min(self._lowlinks[token], self._lowlinks[dep])
        elif dep in self._on_stack:
            self._lowlinks[token] = min(self._lowlinks[token], self._index[dep])
    
    # 3. If token is a root, pop SCC from stack
    if self._lowlinks[token] == self._index[token]:
        scc = []
        while True:
            w = self._stack.pop()
            self._on_stack.remove(w)
            scc.append(w)
            if w == token:
                break
        self._sccs.append(scc)

# After detection, trivial SCCs (single node, no self-loop) are filtered out`}</CodeBlock>
      </section>

      {/* Testing Utilities */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Testing Utilities</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">aquilia/di/testing.py</code> provides mock providers, test registries, and pytest fixtures for DI testing.
        </p>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>MockProvider</h3>
        <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Extends <code className="text-aquilia-500">ValueProvider</code> with access tracking for test assertions:
        </p>
        <CodeBlock language="python" filename="MockProvider">{`from aquilia.di.testing import MockProvider

mock = MockProvider(
    value=FakeUserRepo(),
    token=UserRepository,
    name="mock_user_repo",
)

# After resolution:
assert mock.access_count == 1
assert len(mock.instantiate_calls) == 1  # Each call's trace

# Reset tracking:
mock.reset()
assert mock.access_count == 0`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>TestRegistry</h3>
        <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Extends <code className="text-aquilia-500">Registry</code> with override support. Relaxes cross-app validation and allows cycle tolerance:
        </p>
        <CodeBlock language="python" filename="TestRegistry">{`from aquilia.di.testing import TestRegistry, MockProvider

# Build test registry with overrides
registry = TestRegistry.from_manifests(
    manifests=[users_manifest],
    config=test_config,
    overrides={
        "UserRepository": MockProvider(FakeRepo(), UserRepository),
        "CacheBackend": MockProvider(FakeCache(), CacheBackend),
    },
    enforce_cross_app=False,  # Relaxed for tests
)

container = registry.build_container()
# Container has real services except overridden ones`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>override_container()</h3>
        <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Async context manager for temporary provider overrides — restores the original on exit:
        </p>
        <CodeBlock language="python" filename="override_container">{`from aquilia.di.testing import override_container

async def test_order_processing():
    container = build_test_container()
    
    mock_repo = MockOrderRepo()
    async with override_container(container, OrderRepository, mock_repo) as mock:
        # Inside: OrderRepository resolves to mock_repo
        result = await process_order(container, order_id=1)
        assert mock.access_count >= 1
    
    # Outside: original OrderRepository restored`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Pytest Fixtures</h3>
        <p className={`mb-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Automatically available when pytest is installed:
        </p>
        <CodeBlock language="python" filename="Pytest Fixtures">{`import pytest

# Clean app container per test
@pytest.fixture
def di_container():
    container = Container(scope="app")
    yield container

# Request-scoped container per test
@pytest.fixture
async def request_container(di_container):
    container = di_container.create_request_scope()
    yield container
    await container.shutdown()

# MockProvider factory
@pytest.fixture
def mock_provider():
    def _create_mock(value, token, **kwargs):
        return MockProvider(value, token, **kwargs)
    return _create_mock

# Usage in tests:
async def test_user_service(request_container, mock_provider):
    mock = mock_provider(FakeRepo(), UserRepository)
    request_container.register(mock)
    
    user_svc = await request_container.resolve_async(UserService)
    assert user_svc is not None`}</CodeBlock>
      </section>

      {/* Legacy Compatibility */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Legacy Compatibility (RequestCtx)</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">aquilia/di/compat.py</code> provides a compatibility layer for code written against the legacy <code className="text-aquilia-500">RequestCtx</code> API. It wraps the new <code className="text-aquilia-500">Container</code> system and uses <code className="text-aquilia-500">contextvars.ContextVar</code> for implicit request container access.
        </p>
        <CodeBlock language="python" filename="Legacy Compatibility">{`from aquilia.di.compat import RequestCtx, get_request_container, set_request_container

# RequestCtx wraps a Container with the legacy API:
class RequestCtx:
    def __init__(self, container: Container): ...
    
    def get(self, token, *, tag=None, default=None):
        """Sync get with default fallback."""
        try:
            return self._container.resolve(token, tag=tag)
        except Exception:
            return default
    
    async def get_async(self, token, *, tag=None, default=None):
        """Async get with default fallback."""
        try:
            return await self._container.resolve_async(token, tag=tag)
        except Exception:
            return default

# ContextVar-based access (thread/task safe):
set_request_container(container)      # Set per-request
container = get_request_container()   # Get current (or None)
clear_request_container()             # Clear on request end

# Migration guide:
# Old:  ctx = RequestCtx.get_current(); svc = ctx.get(UserService)
# New:  svc = await request.container.resolve_async(UserService)`}</CodeBlock>
      </section>

      {/* CLI Commands */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CLI Commands</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">aquilia/di/cli.py</code> exposes 5 CLI commands for DI validation, visualization, and benchmarking:
        </p>

        {/* di-check */}
        <div className="mb-6">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500 text-lg">aq di-check</code></h3>
          <p className={`mb-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Static DI validation. Loads manifests, builds the registry with full validation, and reports:
          </p>
          <ul className={`list-disc pl-6 mb-3 space-y-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <li>All providers are resolvable</li>
            <li>No dependency cycles (unless <code className="text-aquilia-500">allow_lazy</code>)</li>
            <li>No scope violations</li>
            <li>Cross-app dependencies properly declared</li>
          </ul>
          <CodeBlock language="bash">{`aq di-check --settings settings.py
# DI configuration is valid!
# Summary:
#   - Providers: 42
#   - singleton: 8
#   - app: 12
#   - request: 22

aq di-check --settings settings.py --no-cross-app-check
# Skip cross-app validation`}</CodeBlock>
        </div>

        {/* di-tree */}
        <div className="mb-6">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500 text-lg">aq di-tree</code></h3>
          <p className={`mb-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Renders the dependency tree as text. Optionally start from a specific root token:
          </p>
          <CodeBlock language="bash">{`aq di-tree --settings settings.py
# Dependency Tree
# ├── UserService (request)
# │   ├── UserRepository (app)
# │   │   └── DatabasePool (singleton)
# │   └── CacheBackend (singleton)

aq di-tree --settings settings.py --root UserService --out tree.txt`}</CodeBlock>
        </div>

        {/* di-graph */}
        <div className="mb-6">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500 text-lg">aq di-graph</code></h3>
          <p className={`mb-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Exports the dependency graph as Graphviz DOT format. Nodes are color-coded by scope:
          </p>
          <CodeBlock language="bash">{`aq di-graph --settings settings.py --out graph.dot
# Graph exported to graph.dot
# Visualize with: dot -Tpng graph.dot -o graph.png

# Scope colors:
# singleton/app → lightblue
# request → lightgreen
# transient → lightyellow
# pooled → lightcoral
# ephemeral → lightgray`}</CodeBlock>
        </div>

        {/* di-profile */}
        <div className="mb-6">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500 text-lg">aq di-profile</code></h3>
          <p className={`mb-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Benchmarks DI performance — registry build, container build, and cached resolution latency:
          </p>
          <CodeBlock language="bash">{`aq di-profile --settings settings.py --bench resolve --runs 1000
# Profiling DI performance...
#
# 1. Registry build (cold):
#    12.34ms
#
# 2. Container build:
#    0.45ms
#
# 3. Cached resolution (1000 iterations):
#    Average: 1.82µs
#    Median:  1.65µs
#    P95:     2.41µs
#    Target <3µs: PASSED`}</CodeBlock>
        </div>

        {/* di-manifest */}
        <div className="mb-6">
          <h3 className={`text-lg font-mono font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}><code className="text-aquilia-500 text-lg">aq di-manifest</code></h3>
          <p className={`mb-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Generates a JSON manifest for LSP/IDE integration — hover info, autocomplete for <code className="text-aquilia-500">Inject(tag="...")</code>, and "find provider" navigation:
          </p>
          <CodeBlock language="bash">{`aq di-manifest --settings settings.py --out di_manifest.json
# Manifest exported to di_manifest.json
#    42 providers

# Output format:
# {
#   "version": "1.0",
#   "providers": [
#     {"name": "UserService", "token": "app.services.UserService",
#      "scope": "request", "module": "app.services", "line": 42, ...}
#   ],
#   "graph": {"app.services.UserService": ["app.repos.UserRepository", ...]}
# }`}</CodeBlock>
        </div>
      </section>

      {/* Navigation */}
      <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/di/lifecycle" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
          <ArrowLeft className="w-4 h-4" /> Lifecycle
        </Link>
        <span />
      </div>
    </div>
  )
}