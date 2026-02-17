import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Shield } from 'lucide-react'

export function AuthAdvanced() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Shield className="w-4 h-4" />
          Auth / Advanced
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Credentials, AuthManager, OAuth2 & MFA
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Deep dive into AquilAuth's credential system, authentication manager, OAuth2/OIDC provider, and multi-factor authentication engine.
        </p>
      </div>

      {/* Credentials */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Credential System</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Credentials are typed, status-tracked authenticators attached to an Identity. Aquilia supports multiple credential types per identity.
        </p>
        <CodeBlock language="python" filename="credentials.py">{`from aquilia.auth import (
    PasswordCredential,
    ApiKeyCredential,
    OAuthClient,
    MFACredential,
    CredentialStatus,
)

# Password credential with policy enforcement
password = PasswordCredential(
    identity_id="user_123",
    hash=hash_password("S3cur3Pa$$word!"),
    status=CredentialStatus.ACTIVE,
)

# API key credential
api_key = ApiKeyCredential(
    identity_id="user_123",
    key_hash=hash_key("ak_live_xxxxxxxxxxxx"),
    prefix="ak_live_",
    name="Production API Key",
    scopes=["read:articles", "write:articles"],
    expires_at=datetime(2025, 12, 31),
    status=CredentialStatus.ACTIVE,
)

# MFA credential (TOTP)
mfa = MFACredential(
    identity_id="user_123",
    method="totp",
    secret=generate_totp_secret(),
    backup_codes=generate_backup_codes(count=10),
    status=CredentialStatus.ACTIVE,
)`}</CodeBlock>
      </section>

      {/* Password Hashing */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Password Hashing & Policy</h2>
        <CodeBlock language="python" filename="password.py">{`from aquilia.auth import (
    PasswordHasher,
    PasswordPolicy,
    hash_password,
    verify_password,
    validate_password,
)

# Hash & verify
hashed = hash_password("MyP@ssw0rd!")
is_valid = verify_password("MyP@ssw0rd!", hashed)  # → True

# Custom hasher
hasher = PasswordHasher(
    algorithm="argon2id",
    memory_cost=65536,
    time_cost=3,
    parallelism=4,
)

# Password policy
policy = PasswordPolicy(
    min_length=12,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=True,
    max_repeated_chars=3,
    check_breached=True,       # Check against breach database
    prevent_reuse=5,           # Remember last 5 passwords
)

result = validate_password("weak", policy)
# result.valid → False
# result.errors → ["Too short (min 12)", "Missing uppercase", ...]`}</CodeBlock>
      </section>

      {/* AuthManager */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>AuthManager</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">AuthManager</code> orchestrates the full authentication flow: credential verification, token issuance, rate limiting, and audit events.
        </p>
        <CodeBlock language="python" filename="auth_manager.py">{`from aquilia.auth import AuthManager, RateLimiter

auth = AuthManager(
    identity_store=db_identity_store,
    credential_store=db_credential_store,
    token_manager=token_mgr,
    rate_limiter=RateLimiter(
        max_attempts=5,
        window_seconds=300,       # 5 attempts per 5 minutes
        lockout_seconds=900,      # 15-minute lockout
    ),
)

# Authenticate with password
result = await auth.authenticate_password(
    email="user@example.com",
    password="MyP@ssw0rd!",
)

if result.success:
    access_token = result.tokens.access_token
    refresh_token = result.tokens.refresh_token
    identity = result.identity
elif result.mfa_required:
    # MFA challenge
    challenge = result.mfa_challenge
    # → send challenge to client
elif result.locked:
    # Account locked due to too many attempts
    retry_after = result.retry_after  # seconds

# Authenticate with API key
result = await auth.authenticate_api_key("ak_live_xxxxxxxxxxxx")

# Refresh tokens
new_tokens = await auth.refresh(refresh_token)

# Revoke tokens
await auth.revoke(access_token)`}</CodeBlock>
      </section>

      {/* Token Management */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Token Management</h2>
        <CodeBlock language="python" filename="tokens.py">{`from aquilia.auth import TokenManager, TokenConfig, KeyRing, KeyAlgorithm

# Configure token manager
token_mgr = TokenManager(
    config=TokenConfig(
        access_token_ttl=3600,       # 1 hour
        refresh_token_ttl=2592000,   # 30 days
        issuer="https://api.example.com",
        audience="example-app",
    ),
    key_ring=KeyRing(
        algorithm=KeyAlgorithm.ES256,
        rotation_interval=86400 * 30,  # Rotate every 30 days
    ),
)

# Issue tokens
claims = TokenClaims(
    sub="user_123",
    roles=["admin"],
    scopes=["read", "write"],
)
tokens = await token_mgr.issue(claims)

# Verify token
verified = await token_mgr.verify(tokens.access_token)
# verified.sub → "user_123"
# verified.roles → ["admin"]

# Key rotation (seamless — old keys remain valid)
await token_mgr.rotate_keys()`}</CodeBlock>
      </section>

      {/* OAuth2 */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>OAuth2 / OIDC</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Full OAuth 2.0 Authorization Server with PKCE, device flow, and OpenID Connect support.
        </p>
        <CodeBlock language="python" filename="oauth2.py">{`from aquilia.auth import OAuth2Manager, OAuthClient

oauth = OAuth2Manager(
    auth_manager=auth,
    token_manager=token_mgr,
    consent_store=consent_store,
)

# Register OAuth client
client = OAuthClient(
    client_id="app_123",
    client_secret_hash=hash_secret("cs_xxxx"),
    name="My App",
    redirect_uris=["https://app.example.com/callback"],
    grant_types=["authorization_code", "refresh_token"],
    scopes=["openid", "profile", "email"],
    pkce_required=True,
)

# Authorization code flow
auth_url = oauth.authorize_url(
    client_id="app_123",
    redirect_uri="https://app.example.com/callback",
    scope="openid profile email",
    state=generate_state(),
    code_challenge=code_challenge,
    code_challenge_method="S256",
)

# Token exchange
tokens = await oauth.exchange_code(
    code=authorization_code,
    client_id="app_123",
    client_secret="cs_xxxx",
    redirect_uri="https://app.example.com/callback",
    code_verifier=code_verifier,
)`}</CodeBlock>
      </section>

      {/* MFA */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Multi-Factor Authentication</h2>
        <CodeBlock language="python" filename="mfa.py">{`from aquilia.auth import MFAManager

mfa = MFAManager(credential_store=db_credential_store)

# Enroll TOTP
enrollment = await mfa.enroll_totp(identity_id="user_123")
# enrollment.secret → "JBSWY3DPEHPK3PXP"
# enrollment.qr_uri → "otpauth://totp/Aquilia:user@..."
# enrollment.backup_codes → ["12345678", "87654321", ...]

# Verify TOTP code (during login)
is_valid = await mfa.verify_totp(
    identity_id="user_123",
    code="123456",
)

# Use backup code
is_valid = await mfa.use_backup_code(
    identity_id="user_123",
    code="12345678",
)

# Check enrollment status
enrolled = await mfa.is_enrolled(identity_id="user_123")
methods = await mfa.enrolled_methods(identity_id="user_123")
# → ["totp"]`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/auth/guards" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Guards
        </Link>
        <Link to="/docs/authz" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          Authorization <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
