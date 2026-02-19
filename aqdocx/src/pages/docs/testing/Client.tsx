import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { FlaskConical } from 'lucide-react'

export function TestingClient() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <FlaskConical className="w-4 h-4" />
          Testing / TestClient
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            TestClient
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">TestClient</code> provides an in-process HTTP client for testing Aquilia applications without starting a server. Supports HTTP, WebSocket, and streaming requests.
        </p>
      </div>

      {/* Basic Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
        <CodeBlock language="python" filename="test_api.py">{`from aquilia.testing import TestClient

async def test_list_users():
    async with TestClient(app) as client:
        response = await client.get("/api/users/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

async def test_create_user():
    async with TestClient(app) as client:
        response = await client.post("/api/users/", json={
            "name": "Asha",
            "email": "asha@test.com",
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Asha"`}</CodeBlock>
      </section>

      {/* HTTP Methods */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>HTTP Methods</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Method</th>
                <th className="py-3 px-4 text-left font-semibold">Signature</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['GET', 'client.get(path, params=None, headers=None)'],
                ['POST', 'client.post(path, json=None, data=None, files=None)'],
                ['PUT', 'client.put(path, json=None, data=None)'],
                ['PATCH', 'client.patch(path, json=None, data=None)'],
                ['DELETE', 'client.delete(path, headers=None)'],
                ['HEAD', 'client.head(path, headers=None)'],
                ['OPTIONS', 'client.options(path, headers=None)'],
              ].map(([method, sig], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className={`py-2.5 px-4 font-mono text-xs font-bold ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{method}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{sig}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Authentication */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Authentication</h2>
        <CodeBlock language="python" filename="auth.py">{`async def test_protected_endpoint():
    async with TestClient(app) as client:
        # Login and get token
        auth_response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "secret",
        })
        token = auth_response.json()["token"]
        
        # Use token in subsequent requests
        client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get("/api/admin/dashboard")
        assert response.status_code == 200

        # Or use force_authenticate for testing
        client.force_authenticate(user=admin_user)
        response = await client.get("/api/admin/dashboard")
        assert response.status_code == 200`}</CodeBlock>
      </section>

      {/* WebSocket Testing */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>WebSocket Testing</h2>
        <CodeBlock language="python" filename="websocket.py">{`from aquilia.testing import WebSocketTestClient

async def test_chat():
    async with TestClient(app) as client:
        ws = await client.websocket("/ws/chat/room1")
        
        await ws.send_json({"message": "Hello!"})
        response = await ws.receive_json()
        assert response["type"] == "message"
        assert response["data"]["text"] == "Hello!"
        
        await ws.close()`}</CodeBlock>
      </section>

      {/* Response Object */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TestResponse</h2>
        <CodeBlock language="python" filename="response.py">{`response = await client.get("/api/users/1")

response.status_code     # 200
response.json()          # Parsed JSON body
response.text            # Raw text body
response.content         # Raw bytes
response.headers         # Response headers dict
response.cookies         # Response cookies
response.elapsed         # Request duration`}</CodeBlock>
      </section>
    </div>
  )
}
