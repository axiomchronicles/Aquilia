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
          Aquilia provides purpose-built data structures that underpin request parsing: <code className="text-aquilia-500">MultiDict</code> for multi-value dictionaries, <code className="text-aquilia-500">Headers</code> for case-insensitive header access, <code className="text-aquilia-500">URL</code> for URL parsing and building, and more.
        </p>
      </div>

      {/* MultiDict */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>MultiDict</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A dictionary that supports multiple values per key. Used for query parameters and form data where keys can repeat (e.g. <code className="text-aquilia-500">?tag=python&tag=async</code>).
        </p>
        <CodeBlock language="python" filename="multidict_usage.py">{`from aquilia._datastructures import MultiDict

# Initialize from list of tuples
params = MultiDict([
    ("tag", "python"),
    ("tag", "async"),
    ("page", "1"),
])

# Get first value
params.get("tag")          # → "python"
params.get("page")         # → "1"
params.get("missing", "0") # → "0"

# Get ALL values for a key
params.get_all("tag")      # → ["python", "async"]

# Add values
params.add("tag", "web")
params.get_all("tag")      # → ["python", "async", "web"]

# Set (replaces existing)
params["tag"] = "overwritten"
params.get_all("tag")      # → ["overwritten"]

# Flat list of all items
params.items_list()
# → [("tag", "overwritten"), ("page", "1")]

# Query string encoding
params.to_query_string()   # → "tag=overwritten&page=1"`}</CodeBlock>

        <div className={`mt-6 ${boxClass}`}>
          <h3 className={`text-sm font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>MultiDict API</h3>
          <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
                {[
                  { m: '.get(key, default)', r: 'str | None', d: 'First value for key' },
                  { m: '.get_all(key)', r: 'list[str]', d: 'All values for key' },
                  { m: '.add(key, value)', r: 'None', d: 'Append value to key' },
                  { m: '[key] = value', r: 'None', d: 'Replace all values for key' },
                  { m: '.items_list()', r: 'list[tuple]', d: 'Flat list of (key, value) pairs' },
                  { m: '.to_query_string()', r: 'str', d: 'URL-encoded query string' },
                  { m: 'len(md)', r: 'int', d: 'Number of distinct keys' },
                ].map((row, i) => (
                  <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                    <td className="py-2.5 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                    <td className={`py-2.5 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.r}</td>
                    <td className={`py-2.5 px-4 text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Headers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Headers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Case-insensitive header dictionary. Implements the <code className="text-aquilia-500">MutableMapping</code> protocol with case-folded key access.
        </p>
        <CodeBlock language="python" filename="headers.py">{`from aquilia._datastructures import Headers

headers = Headers([
    ("Content-Type", "application/json"),
    ("X-Request-ID", "abc-123"),
    ("Authorization", "Bearer tok_xxxx"),
])

# Case-insensitive access
headers["content-type"]     # → "application/json"
headers["CONTENT-TYPE"]     # → "application/json"
headers.get("x-request-id") # → "abc-123"

# Check existence
"authorization" in headers  # → True

# Iterate
for key, value in headers.items():
    print(f"{key}: {value}")

# Immutable raw access
headers.raw  # → [(b"Content-Type", b"application/json"), ...]`}</CodeBlock>
      </section>

      {/* URL */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>URL</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Parsed URL object with component access and builder methods.
        </p>
        <CodeBlock language="python" filename="url.py">{`from aquilia._datastructures import URL

url = URL("https://api.example.com:8443/v1/users?page=2&sort=name#top")

url.scheme    # → "https"
url.host      # → "api.example.com"
url.port      # → 8443
url.path      # → "/v1/users"
url.query     # → "page=2&sort=name"
url.fragment  # → "top"
url.netloc    # → "api.example.com:8443"
url.is_secure # → True

# Build new URL from existing
new_url = url.replace(path="/v2/posts", query="page=1")
str(new_url)  # → "https://api.example.com:8443/v2/posts?page=1#top"

# Query parameter access
url.query_params          # → MultiDict({"page": ["2"], "sort": ["name"]})
url.query_params.get("page") # → "2"`}</CodeBlock>
      </section>

      {/* ParsedContentType */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ParsedContentType</h2>
        <CodeBlock language="python" filename="content_type.py">{`from aquilia._datastructures import ParsedContentType

ct = ParsedContentType("application/json; charset=utf-8")

ct.media_type  # → "application/json"
ct.type        # → "application"
ct.subtype     # → "json"
ct.charset     # → "utf-8"
ct.params      # → {"charset": "utf-8"}
ct.is_json     # → True
ct.is_form     # → False
ct.is_multipart # → False`}</CodeBlock>
      </section>

      {/* Range */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Range</h2>
        <CodeBlock language="python" filename="range.py">{`from aquilia._datastructures import Range

# Parse Range header
r = Range.parse("bytes=0-499")
r.unit   # → "bytes"
r.start  # → 0
r.end    # → 499
r.length # → 500

# Multi-range
ranges = Range.parse_multi("bytes=0-499, 1000-1499")
# → [Range(0, 499), Range(1000, 1499)]`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/request-response/response" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Response
        </Link>
        <Link to="/docs/request-response/uploads" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          File Uploads <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
