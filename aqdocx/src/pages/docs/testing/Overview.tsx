import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, FlaskConical } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function TestingOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <FlaskConical className="w-4 h-4" />
          Tooling / Testing
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Testing Framework
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides a comprehensive, batteries-included testing module with TestClient, test case classes, DI overrides, mock providers, and testing mixins for every subsystem — auth, cache, mail, WebSockets, faults, and effects.
        </p>
      </div>

      {/* Test Cases */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Test Case Classes</h2>
        <div className="space-y-3">
          {[
            { name: 'AquiliaTestCase', desc: 'Base test case with automatic server lifecycle management (startup/shutdown), TestClient, and DI container access.' },
            { name: 'TransactionTestCase', desc: 'Wraps each test in a database transaction that rolls back after the test — no data leaks between tests.' },
            { name: 'LiveServerTestCase', desc: 'Starts a real ASGI server on a random port. Use for integration tests with real HTTP clients.' },
            { name: 'SimpleTestCase', desc: 'Lightweight test case without server lifecycle. Use for pure unit tests of services and utilities.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* TestClient */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TestClient</h2>
        <CodeBlock language="python" filename="test_api.py">{`from aquilia.testing import AquiliaTestCase


class TestUserAPI(AquiliaTestCase):
    settings = {"debug": True, "database": {"engine": "sqlite", "name": ":memory:"}}

    async def test_list_users(self):
        response = await self.client.get("/api/users/")
        self.assert_status(response, 200)
        data = response.json()
        assert isinstance(data["users"], list)

    async def test_create_user(self):
        response = await self.client.post("/api/users/", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "secure123",
        })
        self.assert_status(response, 201)
        data = response.json()
        assert data["user"]["username"] == "testuser"

    async def test_unauthorized_access(self):
        response = await self.client.get("/api/admin/dashboard")
        self.assert_status(response, 401)

    async def test_authenticated_request(self):
        # Login first
        login = await self.client.post("/auth/login", json={
            "email": "admin@example.com",
            "password": "admin",
        })
        token = login.json()["token"]

        # Use token for authenticated request
        response = await self.client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assert_status(response, 200)`}</CodeBlock>
      </section>

      {/* DI Overrides */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DI Overrides & Mocks</h2>
        <CodeBlock language="python" filename="test_with_mocks.py">{`from aquilia.testing import (
    AquiliaTestCase, TestContainer,
    mock_provider, override_provider, spy_provider,
)


class TestProductController(AquiliaTestCase):

    async def test_with_mock_service(self):
        # Replace a real service with a mock
        mock_product_service = mock_provider(ProductService, {
            "get_all": [{"id": 1, "name": "Test Product"}],
            "get_by_id": {"id": 1, "name": "Test Product"},
        })

        with override_provider(ProductService, mock_product_service):
            response = await self.client.get("/api/products/")
            self.assert_status(response, 200)
            assert len(response.json()["products"]) == 1

    async def test_with_spy(self):
        # Spy on a real service (calls through, but records calls)
        spy = spy_provider(EmailService)

        with override_provider(EmailService, spy):
            await self.client.post("/auth/register", json={
                "email": "new@example.com",
                "password": "secure123",
            })

            # Assert the spy was called
            assert spy.was_called("send")
            assert spy.call_args("send")[0]["to"] == "new@example.com"`}</CodeBlock>
      </section>

      {/* Testing Mixins */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Testing Mixins</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Mixin</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Provides</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'AuthTestMixin', p: 'login_as(), create_test_user(), assert_authenticated(), IdentityBuilder' },
                { m: 'CacheTestMixin', p: 'assert_cached(), assert_cache_miss(), clear_test_cache(), MockCacheBackend' },
                { m: 'MailTestMixin', p: 'assert_mail_sent(), get_sent_mail(), clear_outbox(), CapturedMail' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'} text-xs`}>{row.p}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* WebSocket Testing */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>WebSocket Testing</h2>
        <CodeBlock language="python" filename="test_websocket.py">{`from aquilia.testing import AquiliaTestCase, WebSocketTestClient


class TestChatWebSocket(AquiliaTestCase):

    async def test_chat_connection(self):
        async with WebSocketTestClient(self.app, "/ws/chat") as ws:
            # Receive welcome message
            message = await ws.receive_event()
            assert message["event"] == "welcome"

            # Send a chat message
            await ws.send_event("message", {
                "text": "Hello!",
                "room": "general",
            })

            # Receive broadcast
            broadcast = await ws.receive_event()
            assert broadcast["event"] == "message"
            assert broadcast["data"]["text"] == "Hello!"`}</CodeBlock>
      </section>

      {/* Config Overrides */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration Overrides</h2>
        <CodeBlock language="python" filename="test_config.py">{`from aquilia.testing import override_settings


class TestWithCustomConfig(AquiliaTestCase):

    @override_settings(debug=True, cache={"backend": "null"})
    async def test_debug_mode(self):
        response = await self.client.get("/debug/info")
        self.assert_status(response, 200)

    async def test_override_context_manager(self):
        with override_settings(rate_limit={"enabled": False}):
            # Rate limiting is disabled in this block
            for _ in range(100):
                response = await self.client.get("/api/data")
                self.assert_status(response, 200)`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/cli" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> CLI
        </Link>
        <Link to="/docs/trace" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Trace & Debug <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  )
}