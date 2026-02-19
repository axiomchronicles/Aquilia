import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Settings, Layers, FileText, Zap, ArrowRight, AlertCircle, Database, Shield } from 'lucide-react'

export function ConfigOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Settings className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Configuration System
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.config &amp; aquilia.config_builders — Layered typed configuration</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia's configuration system is a <strong>layered, typed, merge-based</strong> architecture
          that supports Python-first fluent builders, YAML fallback, environment variables, <code>.env</code> files,
          and manual overrides — all merged with deterministic precedence ordering.
        </p>
      </div>

      {/* Two Approaches */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Two Configuration Approaches
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia supports two config formats. Python is recommended for IDE support, type-safety,
          and fluent builder syntax. YAML is supported for simpler projects or CI-driven environments.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className={`p-5 rounded-xl border ${isDark ? 'bg-aquilia-500/5 border-aquilia-500/20' : 'bg-blue-50/50 border-blue-200/50'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-aquilia-300' : 'text-blue-700'}`}>
              <FileText className="w-4 h-4 inline mr-1" /> Python — <code>aquilia.py</code>
            </h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              <li>• Full IDE autocompletion &amp; type checking</li>
              <li>• Fluent builder API (<code>Workspace</code>, <code>Module</code>, <code>Integration</code>)</li>
              <li>• Conditional logic, variables, imports</li>
              <li>• <strong>Takes precedence</strong> when both exist</li>
            </ul>
          </div>

          <div className={`p-5 rounded-xl border ${isDark ? 'bg-gray-800/50 border-gray-700/50' : 'bg-gray-50/50 border-gray-200/50'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              <FileText className="w-4 h-4 inline mr-1" /> YAML — <code>aquilia.yaml</code>
            </h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              <li>• Simple declarative syntax</li>
              <li>• Easy CI/CD integration</li>
              <li>• No code execution at config time</li>
              <li>• Fallback when no <code>aquilia.py</code> found</li>
            </ul>
          </div>
        </div>

        <CodeBlock language="python" title="aquilia.py — Python Config (Recommended)">
{`from aquilia.config_builders import Workspace, Module, Integration

workspace = (
    Workspace("myapp", version="1.0.0", description="My Application")
    .runtime(mode="dev", host="127.0.0.1", port=8000, reload=True)
    .module(
        Module("users")
        .route_prefix("/users")
        .auto_discover("apps/users")
        .register_controllers("UserController", "ProfileController")
    )
    .module(
        Module("blog")
        .route_prefix("/blog")
        .auto_discover("apps/blog")
    )
    .integrate(Integration.database(
        url="sqlite:///app.db",
        auto_create=True,
    ))
    .integrate(Integration.auth(
        secret_key="my-secret-key",
        store_type="memory",
    ))
    .integrate(Integration.openapi(
        title="My App API",
        version="1.0.0",
    ))
)`}
        </CodeBlock>

        <CodeBlock language="yaml" title="aquilia.yaml — YAML Config (Alternative)">
{`workspace:
  name: myapp
  version: "1.0.0"
  description: My Application

runtime:
  mode: dev
  host: 127.0.0.1
  port: 8000
  reload: true

modules:
  - name: users
    route_prefix: /users
    auto_discover: apps/users
    controllers:
      - UserController
      - ProfileController
  - name: blog
    route_prefix: /blog
    auto_discover: apps/blog

integrations:
  database:
    enabled: true
    url: sqlite:///app.db
    auto_create: true
  auth:
    enabled: true
    tokens:
      secret_key: my-secret-key
    store:
      type: memory
  openapi:
    enabled: true
    title: My App API
    version: "1.0.0"`}
        </CodeBlock>
      </section>

      {/* ConfigLoader */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 inline mr-2 text-aquilia-400" />
          ConfigLoader
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>ConfigLoader</code> is the core engine that loads, merges, and serves configuration.
          It implements a 6-step merge pipeline with deterministic precedence.
        </p>

        <CodeBlock language="python" title="aquilia/config.py — ConfigLoader">
{`class ConfigLoader:
    """
    Loads and merges configuration from multiple sources with precedence:
    CLI args > Environment variables > .env files > config files > defaults
    """
    
    def __init__(self, env_prefix: str = "AQ_"):
        self.env_prefix = env_prefix
        self.config_data: Dict[str, Any] = {}
        self.apps = NestedNamespace()  # Dot-access namespace for app configs
    
    @classmethod
    def load(
        cls,
        paths: Optional[list[str]] = None,
        env_prefix: str = "AQ_",
        env_file: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> "ConfigLoader":
        """Load configuration from multiple sources with proper merge strategy."""
        ...`}
        </CodeBlock>

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          6-Step Merge Pipeline
        </h3>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Each step <strong>deep-merges</strong> into the existing config. Later steps override earlier
          ones at the leaf-key level. Nested dicts are merged recursively, not replaced wholesale.
        </p>

        <div className={`overflow-x-auto mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Step</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Source</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Precedence</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['1', 'aquilia.py / aquilia.yaml', 'Workspace structure — modules, integrations, runtime', 'Lowest'],
                ['2', 'config/base.yaml', 'Shared defaults across all environments', '↓'],
                ['3', 'config/{mode}.yaml', 'Environment-specific overrides (dev.yaml, prod.yaml)', '↓'],
                ['4', '.env file', 'Environment variables from .env file (if env_file provided)', '↓'],
                ['5', 'OS env vars (AQ_*)', 'Environment variables with AQ_ prefix from the shell', '↓'],
                ['6', 'Manual overrides', 'Dict passed to ConfigLoader.load(overrides={...})', 'Highest'],
              ].map(([step, source, desc, prec], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono font-bold ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{step}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{source}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                  <td className={`px-4 py-3 font-semibold ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{prec}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" title="Merge Pipeline in Practice">
{`# Step 1: Workspace structure (aquilia.py detected automatically)
# ConfigLoader finds aquilia.py, imports it, calls workspace.to_dict()

# Step 2: Base config (shared defaults)
# If config/base.yaml exists, deep-merged into config_data

# Step 3: Environment config
# mode is read from runtime.mode (default "dev")
# If config/dev.yaml exists, deep-merged into config_data

# Step 4: .env file
# Lines with AQ_ prefix are parsed and nested
# AQ_RUNTIME__PORT=9000 → config_data["runtime"]["port"] = 9000

# Step 5: OS environment variables
# Same AQ_ prefix, same nesting via double-underscore

# Step 6: Manual overrides
loader = ConfigLoader.load(
    overrides={"runtime": {"port": 3000}}  # Highest precedence
)`}
        </CodeBlock>
      </section>

      {/* Auto-Detection */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Auto-Detection Logic
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When no explicit paths are provided, <code>ConfigLoader.load()</code> auto-detects
          the config format:
        </p>

        <CodeBlock language="python" title="Auto-detection (from config.py)">
{`# Auto-detect workspace config file
if not paths:
    if Path("aquilia.py").exists():
        paths = ["aquilia.py"]        # Python takes precedence
    elif Path("aquilia.yaml").exists():
        paths = ["aquilia.yaml"]      # YAML fallback`}
        </CodeBlock>

        <p className={`mt-4 mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          For Python config files, the loader imports the module and looks for a <code>workspace</code>
          variable of type <code>Workspace</code>. It then calls <code>workspace.to_dict()</code>
          to convert the fluent builder to a config dictionary:
        </p>

        <CodeBlock language="python" title="Python Config Loading">
{`def _load_python_config(self, path: str):
    """Load config from Python file (aquilia.py)."""
    spec = importlib.util.spec_from_file_location("aquilia_config", config_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get workspace object
        if hasattr(module, 'workspace'):
            workspace = module.workspace
            config_dict = workspace.to_dict()
            self._merge_dict(self.config_data, config_dict)`}
        </CodeBlock>
      </section>

      {/* Environment Variables */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Environment Variables
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Environment variables are loaded from both <code>.env</code> files and the OS environment.
          The prefix is configurable (default <code>AQ_</code>). Double-underscores denote nesting.
        </p>

        <CodeBlock language="bash" title="Environment Variable Nesting">
{`# AQ_SECTION__SUBSECTION__KEY=value → config["section"]["subsection"]["key"] = value

export AQ_RUNTIME__PORT=9000              # → runtime.port = 9000
export AQ_RUNTIME__MODE=prod              # → runtime.mode = "prod"
export AQ_DATABASE__URL=postgresql://...   # → database.url = "postgresql://..."
export AQ_AUTH__TOKENS__SECRET_KEY=abc123  # → auth.tokens.secret_key = "abc123"
export AQ_CACHE__BACKEND=redis            # → cache.backend = "redis"`}
        </CodeBlock>

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Automatic Type Parsing
        </h3>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          String values from environment variables are automatically coerced:
        </p>

        <div className={`overflow-x-auto mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Input String</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parsed As</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Python Type</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['"true", "yes", "1"', 'True', 'bool'],
                ['"false", "no", "0"', 'False', 'bool'],
                ['"42"', '42', 'int'],
                ['"3.14"', '3.14', 'float'],
                ['\'{"key": "val"}\'', "{'key': 'val'}", 'dict (JSON)'],
                ['\'["a", "b"]\'', "['a', 'b']", 'list (JSON)'],
                ['"anything_else"', '"anything_else"', 'str'],
              ].map(([input, parsed, type_], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{input}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{parsed}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{type_}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" title="_parse_value() (from config.py)">
{`def _parse_value(self, value: str) -> Any:
    """Parse string value to appropriate type."""
    # Boolean
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    
    # Number
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    
    # JSON (objects and arrays)
    if value.startswith(("{", "[")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    
    return value`}
        </CodeBlock>
      </section>

      {/* NestedNamespace */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          NestedNamespace
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>NestedNamespace</code> wraps dictionaries to enable dot-notation attribute access.
          The <code>ConfigLoader.apps</code> attribute uses this to provide <code>config.apps.auth.secret_key</code> syntax.
        </p>

        <CodeBlock language="python" title="NestedNamespace (from config.py)">
{`class NestedNamespace:
    """
    A namespace that supports nested attribute access for app configs.
    Enables syntax like: config.apps.auth.secret_key
    """
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data = data or {}
    
    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        
        if name not in self._data:
            raise AttributeError(
                f"'NestedNamespace' object has no attribute '{name}'"
            )
        
        value = self._data.get(name)
        if isinstance(value, dict):
            return NestedNamespace(value)  # Recursive wrapping
        return value
    
    def __getitem__(self, key: str) -> Any:
        return self._data[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def to_dict(self) -> dict:
        return self._data
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`# After ConfigLoader.load():
loader = ConfigLoader.load()

# Dot-notation access (via NestedNamespace):
secret = loader.apps.auth.secret_key

# Dict-style path access:
secret = loader.get("apps.auth.secret_key")

# Direct data access:
raw = loader.config_data["apps"]["auth"]["secret_key"]`}
        </CodeBlock>
      </section>

      {/* Typed Config */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Typed Config &amp; Validation
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>Config</code> base class and <code>get_app_config()</code> method support dataclass-based
          typed configuration with automatic validation. When a config class is a <code>@dataclass</code>,
          fields are validated against type hints and missing required fields raise <code>ConfigError</code>.
        </p>

        <CodeBlock language="python" title="Typed Config Example">
{`from dataclasses import dataclass
from typing import Optional
from aquilia.config import Config, ConfigError

@dataclass
class AuthAppConfig(Config):
    secret_key: str              # Required — no default
    algorithm: str = "HS256"
    issuer: str = "aquilia"
    access_token_ttl_minutes: int = 60
    refresh_token_ttl_days: int = 30
    require_auth_by_default: bool = False

# Usage:
loader = ConfigLoader.load()
auth_config = loader.get_app_config("auth", AuthAppConfig)
# Raises ConfigError if 'secret_key' is missing
# Raises ConfigError if type mismatch (e.g., string where int expected)`}
        </CodeBlock>

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Type Checking Rules
        </h3>

        <ul className={`list-disc list-inside space-y-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <li><code>Optional[T]</code> — allows <code>None</code> values, otherwise validates against <code>T</code></li>
          <li>Generic types (<code>List[str]</code>, <code>Dict[str, Any]</code>) — validates against the origin type (<code>list</code>, <code>dict</code>)</li>
          <li>Direct types (<code>str</code>, <code>int</code>, <code>bool</code>) — standard <code>isinstance</code> check</li>
          <li>Complex types — validation is skipped to avoid false positives</li>
        </ul>
      </section>

      {/* Subsystem Config Accessors */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Database className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Subsystem Config Accessors
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          <code>ConfigLoader</code> provides dedicated accessor methods for each subsystem. These
          methods merge user-provided config with sensible defaults and normalize inconsistent
          formats (e.g., a store config can be a string or dict).
        </p>

        <div className={`overflow-x-auto mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Config Paths Checked</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['get_session_config()', 'sessions → integrations.sessions', 'Session policy, store, transport config'],
                ['get_auth_config()', 'auth → integrations.auth', 'Auth tokens, store, security config'],
                ['get_template_config()', 'templates → integrations.templates', 'Template search paths, cache, sandbox'],
                ['get_security_config()', 'security', 'CORS, CSRF, helmet, rate-limit flags'],
                ['get_static_config()', 'integrations.static_files → static_files', 'Static file directories, cache, compression'],
                ['get_cache_config()', 'cache → integrations.cache', 'Backend, TTL, eviction, Redis config'],
                ['get_mail_config()', 'mail → integrations.mail', 'Providers, retry, rate-limit, DKIM'],
              ].map(([method, paths, returns], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{method}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{paths}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{returns}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Each accessor checks multiple config paths for compatibility. For example, <code>get_session_config()</code>
          first checks <code>config_data["sessions"]</code>, then falls back to <code>config_data["integrations"]["sessions"]</code>.
          It also normalizes inconsistent formats — a <code>store</code> value of <code>"memory"</code> (string)
          is converted to <code>{`{"type": "memory", "max_sessions": 10000}`}</code> (dict).
        </p>

        <CodeBlock language="python" title="Example: get_session_config() Normalization">
{`# YAML input:
# sessions:
#   store: memory     ← string

# After get_session_config():
{
    "enabled": True,
    "policy": {
        "name": "user_default",
        "ttl_days": 7,
        "idle_timeout_minutes": 30,
        "rotate_on_privilege_change": True,
        "max_sessions_per_principal": 5,
    },
    "store": {
        "type": "memory",          # ← normalized to dict
        "max_sessions": 10000,
    },
    "transport": {
        "adapter": "cookie",
        "cookie_name": "aquilia_session",
        "cookie_httponly": True,
        "cookie_secure": True,
        "cookie_samesite": "lax",
        "header_name": "X-Session-ID",
    },
}`}
        </CodeBlock>
      </section>

      {/* Deep Merge */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Deep Merge Strategy
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The merge algorithm is recursive and leaf-level. If both source and target have a dict
          at the same key, the dicts are merged recursively. Otherwise the source value replaces
          the target value entirely.
        </p>

        <CodeBlock language="python" title="_merge_dict() (from config.py)">
{`def _merge_dict(self, target: dict, source: dict):
    """Deep merge source into target."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            self._merge_dict(target[key], value)  # Recursive merge
        else:
            target[key] = value  # Leaf replacement`}
        </CodeBlock>

        <CodeBlock language="python" title="Merge Behavior Example">
{`# base.yaml:
database:
  url: sqlite:///app.db
  pool_size: 5
  echo: false

# prod.yaml (merged on top):
database:
  url: postgresql://prod-host/app   # Overrides url
  pool_size: 20                     # Overrides pool_size
  # echo is NOT mentioned → keeps false from base.yaml

# Final result:
{
    "database": {
        "url": "postgresql://prod-host/app",
        "pool_size": 20,
        "echo": False,   # Preserved from base
    }
}`}
        </CodeBlock>
      </section>

      {/* Multi-Environment */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Multi-Environment Setup
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The recommended project structure for multi-environment deployments uses a <code>config/</code>
          directory with environment-specific YAML files:
        </p>

        <CodeBlock language="text" title="Recommended Layout">
{`myproject/
├── aquilia.py              # Workspace definition (modules, integrations)
├── config/
│   ├── base.yaml           # Shared defaults (step 2)
│   ├── dev.yaml            # Development overrides (step 3)
│   ├── prod.yaml           # Production overrides (step 3)
│   └── test.yaml           # Test overrides (step 3)
├── .env                    # Local secrets (never commit)
└── apps/
    ├── users/
    └── blog/`}
        </CodeBlock>

        <CodeBlock language="yaml" title="config/prod.yaml">
{`runtime:
  mode: prod
  host: 0.0.0.0
  port: 80
  reload: false
  workers: 4

database:
  url: postgresql://db-host:5432/myapp
  pool_size: 20
  echo: false

cache:
  backend: redis
  redis_url: redis://cache-host:6379/0`}
        </CodeBlock>

        <div className={`p-4 rounded-lg border mt-4 ${isDark ? 'bg-yellow-500/5 border-yellow-500/20' : 'bg-yellow-50 border-yellow-200'}`}>
          <p className={`text-sm ${isDark ? 'text-yellow-300' : 'text-yellow-800'}`}>
            <AlertCircle className="w-4 h-4 inline mr-1" />
            <strong>Environment selection:</strong> The mode is read from <code>runtime.mode</code> in the
            workspace config. If <code>aquilia.py</code> sets <code>.runtime(mode="prod")</code>,
            then <code>config/prod.yaml</code> is loaded. You can override this with <code>AQ_RUNTIME__MODE=staging</code>
            to load <code>config/staging.yaml</code> instead — but note that env vars are processed <em>after</em>
            the config file selection, so for dynamic environment switching, set the mode in the workspace config
            or use CLI arguments.
          </p>
        </div>
      </section>

      {/* ConfigLoader Public API */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          ConfigLoader API Reference
        </h2>

        <div className={`overflow-x-auto mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method / Property</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Signature</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['load()', '@classmethod (paths, env_prefix, env_file, overrides) → ConfigLoader', 'Factory method — runs full 6-step pipeline'],
                ['get()', '(path: str, default) → Any', 'Get value by dot-separated path (e.g., "runtime.port")'],
                ['get_app_config()', '(app_name: str, config_class: Type[Config]) → Config', 'Instantiate & validate typed config for an app'],
                ['to_dict()', '() → dict', 'Export all config as a dictionary copy'],
                ['config_data', 'Dict[str, Any]', 'Raw configuration dictionary'],
                ['apps', 'NestedNamespace', 'Dot-access namespace for app configs'],
                ['env_prefix', 'str', 'Prefix for env var detection (default "AQ_")'],
              ].map(([method, sig, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{method}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{sig}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Navigation */}
      <div className={`mt-12 pt-6 border-t flex justify-between ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
        <Link
          to="/docs/server/lifecycle"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          ← Server Lifecycle
        </Link>
        <Link
          to="/docs/config/workspace"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          Workspace Builder <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
