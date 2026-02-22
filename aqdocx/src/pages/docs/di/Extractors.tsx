import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../components/NextSteps'

export function DIExtractors() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-12">
                <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
                    <Box className="w-4 h-4" />Dependency Injection
                </div>
                <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                        HTTP Extractors
                        <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
                    </span>
                </h1>
                <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Aquilia's DI system natively understands HTTP requests. Using the <code className="text-aquilia-500">Header</code>, <code className="text-aquilia-500">Query</code>, and <code className="text-aquilia-500">Body</code> extractors within <code className="text-aquilia-500">Dep()</code> callables or <code className="text-aquilia-500">Serializer</code> definitions allows you to pull data directly from the ASGI scope or payload effortlessly.
                </p>
            </div>

            {/* Overview */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How Extractors Work</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    When the <code className="text-aquilia-500">RequestDAG</code> resolves dependencies, it checks if any parameter is annotated with an extractor dataclass. If it is, the DAG intercepts the resolution and reads the value straight from the <code className="text-aquilia-500">RequestCtx</code>.
                </p>

                <CodeBlock language="python" filename="Extractor Usage">{`from typing import Annotated
from aquilia.di import Header, Query, Dep

# A dependency that extracts the User-Agent header and a 'q' query param
async def search_telemetry(
    user_agent: Annotated[str, Header("User-Agent")],
    search_query: Annotated[str, Query("q", default="")]
):
    print(f"Tracking search: {search_query} from {user_agent}")
    return search_query

# The handler depends on the tracking logic
@get("/search")
async def search_view(
    query: Annotated[str, Dep(search_telemetry)]
):
    return {"status": "ok", "q": query}`}</CodeBlock>
            </section>

            {/* Header */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Header</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Extracts a specific HTTP header. Note that ASGI headers are typically lowercase; the <code className="text-aquilia-500">Header</code> class automatically handles case-insensitivity mapping under the hood.
                </p>

                <CodeBlock language="python" filename="Header Attributes">{`from aquilia.di import Header

@dataclass
class Header:
    name: str                   # The header name (e.g., "Authorization")
    alias: Optional[str] = None # Internal aliasing if mapping to a diff kwarg
    required: bool = True       # If True, throws ValidationFault when missing
    default: Any = None         # Fallback if required=False and header is missing`}</CodeBlock>

                <CodeBlock language="python" filename="Examples">{`# Required header
token: Annotated[str, Header("x-api-key")]

# Optional header with default
trace_id: Annotated[str, Header("x-trace-id", required=False, default="unknown")]`}</CodeBlock>
            </section>

            {/* Query */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Query</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Extracts parameters from the HTTP query string (<code className="text-aquilia-500">?key=value</code>). The extracted values are fundamentally strings, but if injected directly into a <code className="text-aquilia-500">Serializer</code> field, they automatically undergo coercion (e.g., string to integer).
                </p>

                <CodeBlock language="python" filename="Query Attributes">{`from aquilia.di import Query

@dataclass
class Query:
    name: str                   # Query parameter key (e.g., "page")
    default: Any = None         # Fallback value if missing
    required: bool = False      # If True, throws ValidationFault when missing`}</CodeBlock>

                <CodeBlock language="python" filename="Examples">{`# Optional query param
page: Annotated[str, Query("page", default="1")]

# Required query param
user_id: Annotated[str, Query("user_id", required=True)]`}</CodeBlock>
            </section>

            {/* Body */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Body</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Directly injects the parsed HTTP body. Usually, bodies are parsed via <code className="text-aquilia-500">Serializer</code> classes, but if you need raw dictionary access inside a <code className="text-aquilia-500">Dep()</code> callable, <code className="text-aquilia-500">Body()</code> provides it.
                </p>

                <CodeBlock language="python" filename="Body Attributes">{`from aquilia.di import Body

@dataclass
class Body:
    media_type: str = "application/json"   # Expected media type
    embed: bool = False                    # Reserved for future usage`}</CodeBlock>

                <CodeBlock language="python" filename="Example">{`async def audit_log_factory(
    payload: Annotated[dict, Body()]
):
    print("Raw body:", payload)
    return payload`}</CodeBlock>
            </section>

            {/* Errors */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Error Handling</h2>
                <div className={`mb-4 p-4 rounded-xl border ${isDark ? 'bg-red-500/5 border-red-500/20' : 'bg-red-50 border-red-200'}`}>
                    <p className={`text-sm ${isDark ? 'text-red-400' : 'text-red-800'}`}>
                        If an extractor is marked as <code className="text-aquilia-500">required=True</code> and the value doesn't exist in the HTTP request, Aquilia raises a <strong>ValidationFault</strong>. This automatically maps to an HTTP 400 Bad Request if it escapes to the top-level Fault Engine, returning structured JSON indicating the missing data.
                    </p>
                </div>
            </section>

            {/* Navigation */}
            <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
                <Link to="/docs/di/request-dag" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
                    <ArrowLeft className="w-4 h-4" /> RequestDAG
                </Link>
                <Link to="/docs/serializers/di-integration" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
                    Serializer DI Integration <ArrowRight className="w-4 h-4" />
                </Link>
            </div>

            <NextSteps />
        </div>
    )
}
