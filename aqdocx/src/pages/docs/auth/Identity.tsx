import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Shield } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function AuthIdentity() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Shield className="w-4 h-4" />Security &amp; Auth</div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Identity &amp; Credentials
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Deep dive into the credential types — passwords (Argon2id), API keys (scoped, rate-limited), and how they map to the <code className="text-aquilia-500">Identity</code> model.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>PasswordCredential</h2>
        <CodeBlock language="python" filename="Password Auth">{`from aquilia.auth.core import PasswordCredential, CredentialStatus

cred = PasswordCredential(
    identity_id="user_42",
    password_hash="$argon2id$v=19$m=65536,t=3,p=4$...",
    algorithm="argon2id",
    must_change=False,
)

# Check rotation policy (default: 90 days)
if cred.should_rotate(max_age_days=90):
    # Prompt user to change password
    ...

# Touch on successful login
cred.touch()  # updates last_used_at

# Serialization
data = cred.to_dict()`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ApiKeyCredential</h2>
        <CodeBlock language="python" filename="API Key Auth">{`from aquilia.auth.core import ApiKeyCredential

# Key format: ak_<env>_<random>
# Example: ak_live_1234567890abcdef

key = ApiKeyCredential(
    identity_id="service_7",
    key_id="key_abc123",
    key_hash="sha256:...",          # SHA-256 of the raw key
    prefix="ak_live_",              # First 8 chars for identification
    scopes=["read:users", "write:orders"],
    rate_limit=100,                 # 100 requests per minute
    expires_at=None,                # Never expires (or set a datetime)
)

# Security checks
key.is_expired()     # False
key.has_scope("read:users")  # via Identity attributes

# Keys are hashed before storage — raw key only shown once at creation`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Identity Types</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { type: 'USER', desc: 'Human user with email, roles, and interactive sessions.' },
            { type: 'SERVICE', desc: 'Machine-to-machine identity for microservices and APIs.' },
            { type: 'DEVICE', desc: 'IoT or device identity for hardware-based authentication.' },
            { type: 'ANONYMOUS', desc: 'Unauthenticated principal with minimal permissions.' },
          ].map((item, i) => (
            <div key={i} className={`p-5 rounded-xl border ${isDark ? 'bg-[#111] border-white/10' : 'bg-white border-gray-200'}`}>
              <span className="text-aquilia-500 font-mono font-bold text-sm">{item.type}</span>
              <p className={`mt-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Credential Status</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500">Status</th>
              <th className="text-left py-3 text-aquilia-500">Meaning</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['ACTIVE', 'Credential is valid and can be used for authentication.'],
                ['SUSPENDED', 'Temporarily disabled — can be reactivated.'],
                ['REVOKED', 'Permanently invalidated — must create a new credential.'],
                ['EXPIRED', 'Passed expiration date — renewal required.'],
              ].map(([s, d], i) => (
                <tr key={i}>
                  <td className="py-2.5 pr-4 font-mono text-xs text-aquilia-400">{s}</td>
                  <td className={`py-2.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}