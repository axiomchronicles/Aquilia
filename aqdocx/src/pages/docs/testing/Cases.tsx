import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { NextSteps } from '../../../components/NextSteps'
import { FlaskConical } from 'lucide-react'

export function TestingCases() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <FlaskConical className="w-4 h-4" />
          Testing / Test Cases
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Test Case Classes
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides specialized test case base classes with different levels of infrastructure setup — from simple unit tests to full live-server integration tests.
        </p>
      </div>

      {/* Test Case Hierarchy */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Test Case Hierarchy</h2>
        <div className="space-y-4">
          {[
            { name: 'SimpleTestCase', setup: 'None', desc: 'Pure unit tests. No database, no DI container, no server. Fastest execution.', color: 'green' },
            { name: 'AquiliaTestCase', setup: 'DI + DB', desc: 'Sets up DI container and database. Each test runs in a transaction that rolls back. Standard choice for most tests.', color: 'blue' },
            { name: 'TransactionTestCase', setup: 'DI + DB (real commits)', desc: 'Like AquiliaTestCase but allows real commits. Needed when testing code that uses transactions internally.', color: 'yellow' },
            { name: 'LiveServerTestCase', setup: 'Full server', desc: 'Starts a real HTTP server on a random port. For end-to-end and integration tests.', color: 'orange' },
          ].map((tc, i) => (
            <div key={i} className={box}>
              <div className="flex items-center gap-3 mb-2">
                <h3 className={`font-mono font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{tc.name}</h3>
                <span className={`text-xs font-mono px-2 py-0.5 rounded ${tc.color === 'green' ? 'bg-green-500/20 text-green-400' :
                  tc.color === 'blue' ? 'bg-blue-500/20 text-blue-400' :
                    tc.color === 'yellow' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-orange-500/20 text-orange-400'
                  }`}>{tc.setup}</span>
              </div>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{tc.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* SimpleTestCase */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SimpleTestCase</h2>
        <CodeBlock language="python" filename="test_utils.py">{`from aquilia.testing import SimpleTestCase

class TestPasswordHasher(SimpleTestCase):
    def test_hash_password(self):
        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed)
    
    def test_invalid_password(self):
        hashed = hash_password("secret123")
        assert not verify_password("wrong", hashed)`}</CodeBlock>
      </section>

      {/* AquiliaTestCase */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>AquiliaTestCase</h2>
        <CodeBlock language="python" filename="test_users.py">{`from aquilia.testing import AquiliaTestCase

class TestUserCRUD(AquiliaTestCase):
    # Fixtures loaded before each test
    fixtures = ["users.json", "profiles.json"]
    
    async def test_create_user(self):
        user = await User.objects.create(
            name="Asha", email="asha@test.com"
        )
        assert user.id is not None
        # Transaction rolls back after test — DB is clean
    
    async def test_list_users(self):
        users = await User.objects.all()
        assert len(users) == 3  # From fixtures`}</CodeBlock>
      </section>

      {/* LiveServerTestCase */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>LiveServerTestCase</h2>
        <CodeBlock language="python" filename="test_e2e.py">{`from aquilia.testing import LiveServerTestCase
import httpx

class TestAPIEndToEnd(LiveServerTestCase):
    async def test_full_flow(self):
        # self.live_server_url is set automatically
        async with httpx.AsyncClient(base_url=self.live_server_url) as client:
            # Create
            resp = await client.post("/api/users/", json={
                "name": "Asha", "email": "asha@test.com"
            })
            assert resp.status_code == 201
            user_id = resp.json()["id"]
            
            # Read
            resp = await client.get(f"/api/users/{user_id}")
            assert resp.json()["name"] == "Asha"
            
            # Delete
            resp = await client.delete(f"/api/users/{user_id}")
            assert resp.status_code == 204`}</CodeBlock>
      </section>

      <NextSteps />
    </div>
  )
}