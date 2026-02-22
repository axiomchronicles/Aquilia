import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Box, ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../components/NextSteps'

export function SerializerDIIntegration() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-12">
                <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
                    <Box className="w-4 h-4" />Serializers
                </div>
                <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                        DI Integration
                        <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
                    </span>
                </h1>
                <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Aquilia's Serializers are deeply integrated with the Dependency Injection <code className="text-aquilia-500">RequestDAG</code>. Similar to FastAPI's Pydantic models, you can declare a <code className="text-aquilia-500">Serializer</code> subclass directly in a route handler signature, and Aquilia will automatically execute the validation pipeline and inject the instantiated serializer.
                </p>
            </div>

            {/* Core Concept: Native Injection */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Native Injection</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Whenever the <code className="text-aquilia-500">ControllerEngine</code> sees a handler parameter tipped with a <code className="text-aquilia-500">Serializer</code> subclass, it delegates instantiation entirely to the request context. This means the serializer reads from the ASGI scope (body, headers, query params) automatically.
                </p>

                <CodeBlock language="python" filename="Native Resolution">{`from aquilia.serializers import Serializer, CharField
from aquilia.controller import get

class LoginSerializer(Serializer):
    username = CharField(max_length=150)
    password = CharField()

@post("/login")
async def login_view(
    # Aquilia automatically parses the request body,
    # validates data against LoginSerializer,
    # and injects the resulting instance here.
    payload: LoginSerializer
):
    # payload.validated_data contains {"username": "...", "password": "..."}
    return {"token": "example"}`}</CodeBlock>

                <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-indigo-500/5 border-indigo-500/20' : 'bg-indigo-50 border-indigo-200'}`}>
                    <p className={`text-sm ${isDark ? 'text-indigo-400' : 'text-indigo-800'}`}>
                        <strong>Naming Convention:</strong> If the parameter name ends with <code className="text-aquilia-500">_serializer</code>, Aquilia injects the full `Serializer` instance. Otherwise, it injects the raw <code className="text-aquilia-500">.validated_data</code> dictionary automatically!
                    </p>
                </div>
            </section>

            {/* Extractors inside Serializers */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DI Extractors as Defaults</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Because Serializers sit inside the <code className="text-aquilia-500">RequestDAG</code> pipeline natively, you can assign DI extractors like <code className="text-aquilia-500">Header</code> and <code className="text-aquilia-500">Query</code> directly as field defaults.
                </p>

                <CodeBlock language="python" filename="Extractors Built In">{`from aquilia.serializers import Serializer, IntegerField, CharField
from aquilia.di import Header, Query

class PaginationSerializer(Serializer):
    # If absent from payload, tries to extract from '?page=...'
    # Implicitly coerces the string query string to an integer!
    page = IntegerField(default=Query("page", default=1))

    # Expects an x-client-id header
    client_id = CharField(default=Header("x-client-id", required=True))

@get("/items")
async def list_items(
    # Extracts ?page=2&client_id=... from the HTTP protocol
    # Validates it, coerces it, throws ValidationFault on failure,
    # injects it here natively.
    params: PaginationSerializer
):
    page_num = params.validated_data["page"] # Always an integer.
    return {"data": []}`}</CodeBlock>

                <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Coercion Pipeline</h3>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    When a field uses a DI extractor as a default, the extracted value does <strong>not</strong> bypass the serializer's validation pipeline. If you use <code className="text-aquilia-500">Query("page")</code> on an <code className="text-aquilia-500">IntegerField</code>, the raw string extracted from the query parameters is cleanly passed through <code className="text-aquilia-500">IntegerField.to_internal_value</code>, guaranteeing that your route handler always works with clean Python primitives.
                </p>
            </section>

            {/* Validations and Failures */}
            <section className="mb-16">
                <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Automatic Fault Ejection</h2>
                <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    If any field validation fails, or if a required DI extractor fails to locate its target (e.g. missing <code className="text-aquilia-500">Authorization</code> header assigned to a field), Aquilia traps the failure and immediately ejects a <code className="text-aquilia-500">ValidationFault</code> out to the Fault Engine.
                </p>

                <CodeBlock language="python" filename="Fault Example">{`from aquilia.serializers import CharField
from aquilia.di import Header

class ClientConfig(Serializer):
    api_version = CharField(default=Header("x-api-version", required=True))

@post("/process")
async def process(data: ClientConfig):
    pass

# curl -X POST /process
#
# HTTP/1.1 400 Bad Request
# {
#   "error": "validation_fault",
#   "details": {
#     "api_version": [
#       "Missing required header: x-api-version"
#     ]
#   }
# }`}</CodeBlock>
            </section>

            {/* Navigation */}
            <div className={`mt-16 pt-8 border-t flex justify-between ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
                <Link to="/docs/di/extractors" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
                    <ArrowLeft className="w-4 h-4" /> Extractors
                </Link>
                <Link to="/docs/database" className="flex items-center gap-2 text-aquilia-500 hover:underline font-medium">
                    Database <ArrowRight className="w-4 h-4" />
                </Link>
            </div>

            <NextSteps />
        </div>
    )
}
