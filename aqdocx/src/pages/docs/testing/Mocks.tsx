import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { FlaskConical } from 'lucide-react'

export function TestingMocks() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <FlaskConical className="w-4 h-4" />
          Testing / Mocks & Mixins
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Mocks & Test Mixins
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides pre-built mock objects and test mixins for common subsystems — fault engine, effects, DI, cache, auth, and mail.
        </p>
      </div>

      {/* MockFaultEngine */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>MockFaultEngine</h2>
        <CodeBlock language="python" filename="faults.py">{`from aquilia.testing import MockFaultEngine

engine = MockFaultEngine()

# Simulate a fault
engine.should_raise("MODEL_NOT_FOUND")

# In your test
try:
    await service.get_user(999)
except:
    pass

# Assert fault was handled
engine.assert_fault_raised("MODEL_NOT_FOUND")
engine.assert_fault_count(1)`}</CodeBlock>
      </section>

      {/* MockEffectRegistry */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>MockEffectRegistry</h2>
        <CodeBlock language="python" filename="effects.py">{`from aquilia.testing import MockEffectRegistry

registry = MockEffectRegistry()

# Register mock effects
registry.mock_effect("DBTx", mode="write")
registry.mock_effect("Cache", mode="users")

# Effects return mock handles that record operations
handle = await registry.acquire("Cache", mode="users")
await handle.set("key", "value")

# Assert operations
registry.assert_acquired("Cache")
registry.assert_operation("Cache", "set", key="key")`}</CodeBlock>
      </section>

      {/* Test Mixins */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Test Mixins</h2>
        <div className="space-y-6">
          {[
            {
              name: 'CacheTestMixin',
              code: `from aquilia.testing import AquiliaTestCase, CacheTestMixin

class TestCachedView(CacheTestMixin, AquiliaTestCase):
    async def test_cache_hit(self):
        # Pre-populate cache
        self.cache_set("users:42", {"name": "Asha"})
        
        response = await self.client.get("/api/users/42")
        assert response.status_code == 200
        
        # Assert cache was used
        self.assert_cache_hit("users:42")`
            },
            {
              name: 'AuthTestMixin',
              code: `from aquilia.testing import AquiliaTestCase, AuthTestMixin

class TestProtectedAPI(AuthTestMixin, AquiliaTestCase):
    async def test_requires_auth(self):
        # Unauthenticated request
        resp = await self.client.get("/api/admin/")
        assert resp.status_code == 401
        
        # Authenticate as admin
        self.login(username="admin", role="admin")
        resp = await self.client.get("/api/admin/")
        assert resp.status_code == 200
        
        self.logout()`
            },
            {
              name: 'MailTestMixin',
              code: `from aquilia.testing import AquiliaTestCase, MailTestMixin

class TestWelcomeEmail(MailTestMixin, AquiliaTestCase):
    async def test_sends_welcome(self):
        await register_user("asha@test.com")
        
        # Assert email was "sent" (captured by test backend)
        self.assert_mail_sent(count=1)
        self.assert_mail_to("asha@test.com")
        self.assert_mail_subject_contains("Welcome")`
            },
          ].map((m, i) => (
            <div key={i}>
              <h3 className={`font-mono font-bold text-sm mb-3 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{m.name}</h3>
              <CodeBlock language="python" filename="test.py">{m.code}</CodeBlock>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
