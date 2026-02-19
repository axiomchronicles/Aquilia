import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Key } from 'lucide-react'

export function SessionsStores() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Key className="w-4 h-4" />
          Sessions / Stores & Transport
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Session Stores & Transport
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Session data is persisted via pluggable stores and transmitted via configurable transports (cookies, headers, or URL parameters).
        </p>
      </div>

      {/* Store Backends */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Store Backends</h2>
        <div className="space-y-4">
          {[
            { name: 'MemoryStore', desc: 'In-process dict. No persistence. Good for development and testing.', code: `from aquilia.sessions import MemoryStore\nstore = MemoryStore(max_sessions=10000)` },
            { name: 'FileStore', desc: 'File-system based. Each session is a JSON file. Good for single-server deployments.', code: `from aquilia.sessions import FileStore\nstore = FileStore(path="./sessions/", cleanup_interval=3600)` },
            { name: 'RedisStore', desc: 'Redis-backed. Supports TTL and distributed deployments.', code: `from aquilia.sessions import RedisStore\nstore = RedisStore(url="redis://localhost:6379", prefix="sess:")` },
            { name: 'DatabaseStore', desc: 'Database-backed via the ORM. Uses the Session model.', code: `from aquilia.sessions import DatabaseStore\nstore = DatabaseStore(engine=db_engine)` },
          ].map((s, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-sm mb-2 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{s.name}</h3>
              <p className={`text-xs mb-3 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{s.desc}</p>
              <CodeBlock language="python" filename="store.py">{s.code}</CodeBlock>
            </div>
          ))}
        </div>
      </section>

      {/* Transport */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Session Transport</h2>
        <CodeBlock language="python" filename="transport.py">{`from aquilia.sessions import SessionTransport, CookieTransport, HeaderTransport

# Cookie transport (default)
transport = CookieTransport(
    cookie_name="session_id",
    httponly=True,
    secure=True,
    samesite="lax",
    max_age=86400,
    domain=None,    # Current domain
    path="/",
)

# Header transport (for APIs)
transport = HeaderTransport(
    header_name="X-Session-ID",
)

# Configure in session middleware
SessionMiddleware(store=store, transport=transport)`}</CodeBlock>
      </section>

      {/* SessionID */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SessionID & Principal</h2>
        <CodeBlock language="python" filename="session.py">{`from aquilia.sessions import SessionID, SessionPrincipal

# SessionID — unique identifier
sid = SessionID.generate()   # UUID-based
print(sid.value)             # "a1b2c3d4-..."
print(sid.created_at)        # datetime

# SessionPrincipal — the authenticated identity
principal = SessionPrincipal(
    user_id=42,
    username="asha",
    roles=["admin", "editor"],
    permissions=["users.read", "users.write"],
)

# Attach to session
request.session.principal = principal
print(request.session.principal.user_id)  # 42`}</CodeBlock>
      </section>

      {/* Session Scope & Flags */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Scope & Flags</h2>
        <CodeBlock language="python" filename="scope.py">{`from aquilia.sessions import SessionScope, SessionFlag

# SessionScope — limits what a session can access
scope = SessionScope(["api", "admin"])

# SessionFlag — marks session state
flags = SessionFlag.AUTHENTICATED | SessionFlag.MFA_VERIFIED

# Check flags
if flags & SessionFlag.MFA_VERIFIED:
    print("MFA verified")`}</CodeBlock>
      </section>
    </div>
  )
}
