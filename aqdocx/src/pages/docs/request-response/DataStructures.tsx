import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Database } from 'lucide-react'

export function DataStructuresPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Database className="w-4 h-4" />
          Request / Data Structures
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Data Structures
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides purpose-built data structures in <code className="text-aquilia-500">aquilia._datastructures</code> that underpin request parsing:
          <code className="text-aquilia-500"> MultiDict</code> for multi-value dictionaries, <code className="text-aquilia-500">Headers</code> for case-insensitive header access,
          <code className="text-aquilia-500"> URL</code> for URL parsing and building, <code className="text-aquilia-500">ParsedContentType</code> for Content-Type parsing,
          <code className="text-aquilia-500"> Range</code> for byte-range requests, and utility functions for date and authorization header parsing.
        </p>
      </div>

      {/* ================================================================ */}
      {/* MultiDict */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>MultiDict</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A dictionary that supports multiple values per key. Implements <code className="text-aquilia-500">MutableMapping</code> so it works like a regular dict,
          but provides additional methods for multi-value access. Used internally for query parameters and form data where keys can repeat
          (e.g. <code className="text-aquilia-500">?tag=python&tag=async</code>).
        </p>
        <CodeBlock language="python" filename="multidict.py">{`from aquilia._datastructures import MultiDict

# Initialize from list of tuples
params = MultiDict([
    ("tag", "python"),
    ("tag", "async"),
    ("page", "1"),
])

# Standard dict access (returns FIRST value for key)
params["tag"]                  # → "python"
params.get("tag")              # → "python"
params.get("missing", "0")    # → "0"

# Multi-value access
params.get_all("tag")          # → ["python", "async"]
params.get_all("missing")     # → []

# Add values (doesn't replace)
params.add("tag", "web")
params.get_all("tag")          # → ["python", "async", "web"]

# Standard dict operations
"tag" in params                # → True
len(params)                    # → 3 (count of unique keys)
del params["page"]

# Iteration (yields unique keys)
list(params.keys())            # → ["tag", "page"]

# All items as flat list (includes duplicates)
params.items_list()            # → [("tag","python"), ("tag","async"), ("page","1")]

# Convert to plain dict (first value per key)
params.to_dict()               # → {"tag": "python", "page": "1"}

# Set value (replaces ALL values for key)
params["tag"] = "rust"
params.get_all("tag")          # → ["rust"]`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>API Reference</h3>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: '__getitem__(key)', t: 'V', d: 'First value for key. Raises KeyError if missing.' },
                { m: '__setitem__(key, val)', t: 'None', d: 'Replaces ALL values for key with single value.' },
                { m: '__delitem__(key)', t: 'None', d: 'Removes all values for key.' },
                { m: '__contains__(key)', t: 'bool', d: 'Check if key exists.' },
                { m: '__len__()', t: 'int', d: 'Number of unique keys.' },
                { m: '__iter__()', t: 'Iterator[K]', d: 'Iterate over unique keys.' },
                { m: 'get(key, default)', t: 'V | default', d: 'First value or default.' },
                { m: 'get_all(key)', t: 'List[V]', d: 'All values for key (empty list if missing).' },
                { m: 'add(key, value)', t: 'None', d: 'Append value (does not replace existing).' },
                { m: 'items_list()', t: 'List[Tuple[K,V]]', d: 'All (key, value) pairs including duplicates.' },
                { m: 'to_dict()', t: 'Dict[K,V]', d: 'Plain dict with first value per key.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={`${boxClass} mt-6`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>Implementation note:</strong> MultiDict stores data internally as <code className="text-aquilia-500">Dict[K, List[V]]</code>.
            The <code className="text-aquilia-500">__getitem__</code> and <code className="text-aquilia-500">get</code> methods return <code className="text-aquilia-500">values[0]</code>
            for compatibility with code that expects a regular dict.
          </p>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Headers */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Headers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A case-insensitive header container built as a <code className="text-aquilia-500">@dataclass</code>. Constructed from the ASGI scope's raw header
          bytes (<code className="text-aquilia-500">List[Tuple[bytes, bytes]]</code>) and builds a case-insensitive <code className="text-aquilia-500">_index</code> dict in
          <code className="text-aquilia-500"> __post_init__</code> for O(1) lookups.
        </p>
        <CodeBlock language="python" filename="headers.py">{`from aquilia._datastructures import Headers

# Constructed automatically by Request from ASGI scope["headers"]
# Manual construction:
headers = Headers(raw=[
    (b"content-type", b"application/json"),
    (b"Authorization", b"Bearer abc123"),
    (b"X-Custom", b"value1"),
    (b"x-custom", b"value2"),  # Multiple values for same header
])

# Case-insensitive get (returns first value)
headers.get("Content-Type")     # → "application/json"
headers.get("content-type")     # → "application/json" (same)
headers.get("CONTENT-TYPE")     # → "application/json" (same)
headers.get("missing", "none")  # → "none"

# Get all values for a header
headers.get_all("x-custom")     # → ["value1", "value2"]

# Check existence
headers.has("authorization")    # → True
headers.has("x-missing")        # → False

# Iterate
for name, value in headers.items():
    print(f"{name}: {value}")

# All header names
headers.keys()    # → ["content-type", "authorization", "x-custom"]

# All header values
headers.values()  # → ["application/json", "Bearer abc123", "value1"]`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>API Reference</h3>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'get(name, default=None)', t: 'str | None', d: 'First value for header (case-insensitive). Returns default if missing.' },
                { m: 'get_all(name)', t: 'List[str]', d: 'All values for header. Empty list if missing.' },
                { m: 'has(name)', t: 'bool', d: 'Check if header exists (case-insensitive).' },
                { m: 'items()', t: 'List[Tuple[str,str]]', d: 'All (name, value) pairs. Includes duplicate names.' },
                { m: 'keys()', t: 'List[str]', d: 'All unique header names (lowercased).' },
                { m: 'values()', t: 'List[str]', d: 'All header values (first value per name).' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={`${boxClass} mt-6`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>Implementation:</strong> The <code className="text-aquilia-500">raw</code> field stores the original
            <code className="text-aquilia-500"> List[Tuple[bytes, bytes]]</code> from ASGI. The <code className="text-aquilia-500">__post_init__</code> method builds
            <code className="text-aquilia-500"> _index: Dict[str, List[str]]</code> where keys are lowercased header names and values are decoded strings.
            This preserves raw bytes for proxying while providing fast case-insensitive lookups.
          </p>
        </div>
      </section>

      {/* ================================================================ */}
      {/* URL */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>URL</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-500">@dataclass</code> for URL parsing, building, and manipulation. Provides immutable URL objects with
          <code className="text-aquilia-500"> replace()</code> for creating modified copies.
        </p>
        <CodeBlock language="python" filename="url.py">{`from aquilia._datastructures import URL

# Parse a URL string
url = URL.parse("https://api.example.com:8443/users?page=2&sort=name#section")

# Access components
url.scheme     # → "https"
url.host       # → "api.example.com"
url.port       # → 8443
url.path       # → "/users"
url.query      # → "page=2&sort=name"
url.fragment   # → "section"

# Computed properties
url.netloc     # → "api.example.com:8443"
str(url)       # → "https://api.example.com:8443/users?page=2&sort=name#section"

# Create modified copies (immutable pattern)
url2 = url.replace(path="/articles", query="")
str(url2)      # → "https://api.example.com:8443/articles"

url3 = url.replace(scheme="http", port=80)

# Build query string from dict
url4 = url.with_query(page="3", sort="date", order="desc")
str(url4)      # → "https://api.example.com:8443/users?page=3&sort=date&order=desc"`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>API Reference</h3>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field / Method</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'scheme', t: 'str', d: 'URL scheme (http, https)' },
                { m: 'host', t: 'str', d: 'Hostname' },
                { m: 'port', t: 'int | None', d: 'Port number (None if default for scheme)' },
                { m: 'path', t: 'str', d: 'URL path' },
                { m: 'query', t: 'str', d: 'Query string (without leading ?)' },
                { m: 'fragment', t: 'str', d: 'URL fragment (without leading #)' },
                { m: 'netloc', t: 'str (property)', d: '"host:port" — omits port if standard (80/443)' },
                { m: 'parse(url_str)', t: 'URL (classmethod)', d: 'Parse URL string into URL object' },
                { m: 'replace(**kwargs)', t: 'URL', d: 'Create copy with specified fields replaced' },
                { m: 'with_query(**params)', t: 'URL', d: 'Create copy with query built from kwargs' },
                { m: '__str__()', t: 'str', d: 'Reconstruct full URL string' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* ParsedContentType */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ParsedContentType</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-500">@dataclass</code> that parses a Content-Type header into its components. Used internally by Request
          for form/multipart content type detection.
        </p>
        <CodeBlock language="python" filename="parsed_content_type.py">{`from aquilia._datastructures import ParsedContentType

# Parse Content-Type header
ct = ParsedContentType.parse("application/json; charset=utf-8")
ct.media_type   # → "application/json"
ct.params       # → {"charset": "utf-8"}
ct.charset      # → "utf-8" (property, defaults to "utf-8")

# Multipart boundary extraction
ct = ParsedContentType.parse("multipart/form-data; boundary=----WebKitFormBoundary")
ct.media_type   # → "multipart/form-data"
ct.boundary     # → "----WebKitFormBoundary" (property)

# Returns None for empty/invalid input
ParsedContentType.parse(None)   # → None
ParsedContentType.parse("")     # → None`}</CodeBlock>

        <div className={`overflow-hidden rounded-xl border mt-6 ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field / Property</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { f: 'media_type', t: 'str', d: 'Media type (lowercased, e.g. "application/json")' },
                { f: 'params', t: 'Dict[str, str]', d: 'Parameters dict (keys lowercased, values unquoted)' },
                { f: 'charset', t: 'str (property)', d: 'charset parameter, defaults to "utf-8"' },
                { f: 'boundary', t: 'str | None (property)', d: 'boundary parameter (for multipart)' },
                { f: 'parse(header)', t: 'ParsedContentType | None', d: 'Parse header string. Returns None if empty.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.f}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Range */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Range</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-500">@dataclass</code> representing a parsed HTTP <code className="text-aquilia-500">Range</code> header for byte-range requests.
          Used internally by <code className="text-aquilia-500">Response.file()</code> for partial content delivery.
        </p>
        <CodeBlock language="python" filename="range.py">{`from aquilia._datastructures import Range

# Parse Range header
r = Range.parse("bytes=0-499")
r.unit      # → "bytes"
r.ranges    # → [(0, 499)]

# Multiple ranges
r = Range.parse("bytes=0-499, 1000-1999")
r.ranges    # → [(0, 499), (1000, 1999)]

# Suffix range (last N bytes)
r = Range.parse("bytes=-500")
r.ranges    # → [(None, 500)]

# Open-ended range (from byte N to end)
r = Range.parse("bytes=500-")
r.ranges    # → [(500, None)]

# Reconstruct header string
str(r)      # → "bytes=500-"

# Invalid input
Range.parse(None)            # → None
Range.parse("invalid")       # → None`}</CodeBlock>

        <div className={`overflow-hidden rounded-xl border mt-6 ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field / Method</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { f: 'unit', t: 'str', d: 'Range unit (default: "bytes")' },
                { f: 'ranges', t: 'List[Tuple[int|None, int|None]]', d: 'List of (start, end) tuples. None indicates open-ended.' },
                { f: 'parse(header)', t: 'Range | None (classmethod)', d: 'Parse Range header string. Returns None if invalid.' },
                { f: '__str__()', t: 'str', d: 'Reconstruct Range header string.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.f}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Utility Functions */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Utility Functions</h2>

        <h3 className={`text-lg font-semibold mt-4 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>parse_authorization_header()</h3>
        <CodeBlock language="python" filename="parse_auth.py">{`from aquilia._datastructures import parse_authorization_header

# Parse "Scheme Credentials" format
result = parse_authorization_header("Bearer eyJhbGciOiJIUz...")
# → ("Bearer", "eyJhbGciOiJIUz...")

result = parse_authorization_header("Basic dXNlcjpwYXNz")
# → ("Basic", "dXNlcjpwYXNz")

# Invalid/missing
parse_authorization_header(None)      # → None
parse_authorization_header("")        # → None
parse_authorization_header("Invalid") # → None (no space separator)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>parse_date_header()</h3>
        <CodeBlock language="python" filename="parse_date.py">{`from aquilia._datastructures import parse_date_header

# Parse HTTP date header (RFC 7231)
dt = parse_date_header("Wed, 15 Jan 2025 12:00:00 GMT")
# → datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

# Uses email.utils.parsedate_to_datetime internally
# Returns None for invalid/missing values
parse_date_header(None)              # → None
parse_date_header("not a date")      # → None`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Usage in Request */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How Request Uses These Structures</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Understanding the relationship between Request and these data structures:
        </p>
        <CodeBlock language="python" filename="integration.py">{`# Request.query_params → MultiDict
# Lazily parsed from scope["query_string"] via parse_qsl
params = request.query_params  # MultiDict instance

# Request.headers → Headers
# Lazily built from scope["headers"] (raw bytes)
headers = request.headers  # Headers instance

# Request.content_type() → uses ParsedContentType internally
ct = request.content_type()  # string
# Internally: ParsedContentType.parse(ct) for charset/boundary

# Request.url() → uses URL dataclass
url_str = request.url()  # Full URL string built from scope

# Request.range_header → string, parsed by Response via Range.parse()

# Request.auth_header → parsed via parse_authorization_header()
# Request.bearer_token → extracts token from "Bearer <token>"

# Request.if_modified_since → parsed via parse_date_header()`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-gray-200 dark:border-white/10">
        <Link to="/docs/request-response/response" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Response</span>
        </Link>
        <Link to="/docs/request-response/uploads" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <span>File Uploads</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
