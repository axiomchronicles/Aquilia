import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Shield } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function AuthCredentials() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Shield className="w-4 h-4" />
          Auth / Credentials & Hashers
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Credentials & Hashers
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Credential verification, password hashing with pluggable algorithms, and token generation (JWT, opaque, API keys).
        </p>
      </div>

      {/* Password Hashers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Password Hashers</h2>
        <CodeBlock language="python" filename="hashers.py">{`from aquilia.auth import PasswordHasher, Argon2Hasher, BCryptHasher, PBKDF2Hasher

# Default: Argon2id (recommended)
hasher = Argon2Hasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
)

# BCrypt
hasher = BCryptHasher(rounds=12)

# PBKDF2 (fallback)
hasher = PBKDF2Hasher(iterations=600_000, algorithm="sha256")

# Hash and verify
hashed = hasher.hash("my_password")
is_valid = hasher.verify("my_password", hashed)  # True

# Check if rehash needed (params changed)
needs_update = hasher.needs_rehash(hashed)  # True/False`}</CodeBlock>
      </section>

      {/* Token Providers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Token Providers</h2>
        <CodeBlock language="python" filename="tokens.py">{`from aquilia.auth import JWTProvider, OpaqueTokenProvider, APIKeyProvider

# JWT
jwt = JWTProvider(
    secret="your-secret-key",
    algorithm="HS256",
    access_ttl=900,        # 15 minutes
    refresh_ttl=604800,    # 7 days
    issuer="myapp",
)

token = jwt.create_access_token(user_id=42, roles=["admin"])
payload = jwt.verify(token)  # {"user_id": 42, "roles": [...], "exp": ...}

# Opaque tokens (database-backed)
opaque = OpaqueTokenProvider(store=token_store)
token = await opaque.create(user_id=42, ttl=3600)
payload = await opaque.verify(token)
await opaque.revoke(token)

# API Keys
api_key = APIKeyProvider(prefix="aq_")
key = api_key.generate()  # "aq_a1b2c3d4e5f6..."
is_valid = await api_key.validate(key)`}</CodeBlock>
      </section>

      {/* CredentialManager */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CredentialManager</h2>
        <CodeBlock language="python" filename="manager.py">{`from aquilia.auth import CredentialManager

manager = CredentialManager(
    hasher=Argon2Hasher(),
    token_provider=JWTProvider(secret="..."),
)

# Full auth flow
user = await manager.authenticate(username="asha", password="secret")
tokens = await manager.create_tokens(user)
# → {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

refreshed = await manager.refresh(tokens["refresh_token"])
await manager.logout(tokens["access_token"])`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}