# AquilAuth - Authentication & Authorization System Design

**Version:** 1.0.0  
**Status:** Design Complete → Implementation In Progress  
**Authors:** Aquilia Core Team  
**Last Updated:** 24 January 2026

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Mission & Philosophy](#mission--philosophy)
3. [Architecture Overview](#architecture-overview)
4. [Core Components](#core-components)
5. [Authentication Flows](#authentication-flows)
6. [Authorization Model](#authorization-model)
7. [AquilaPolicy DSL](#aquilapolicy-dsl)
8. [Token Management](#token-management)
9. [Key Management & Rotation](#key-management--rotation)
10. [Security Model & Threat Analysis](#security-model--threat-analysis)
11. [Integration Architecture](#integration-architecture)
12. [Crous Artifacts](#crous-artifacts)
13. [Observability & Audit](#observability--audit)
14. [API Reference](#api-reference)
15. [CLI Tools](#cli-tools)
16. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

**AquilAuth** is Aquilia's native authentication and authorization subsystem. Unlike systems borrowed from Django, Flask, or FastAPI, AquilAuth is **built from first principles** for Aquilia's architecture:

- **Manifest-first**: Auth configuration declared in manifests, compiled to crous artifacts
- **Flow-integrated**: Guards are pipeline nodes, statically analyzable
- **DI-native**: Identity, tokens, and policies injected via DI container
- **Session-aware**: Deep integration with AquilaSessions for lifecycle
- **Fault-driven**: All auth errors are structured AquilaFaults
- **Secure-by-default**: Least privilege, typed policies, audited operations
- **Crous-backed**: Keys, policies, and audit trails stored as signed artifacts

### Key Features

| Feature | Implementation |
|---------|---------------|
| **AuthN Methods** | Password, API Key, OAuth2/OIDC, mTLS, Passwordless, Device Flow |
| **AuthZ Models** | RBAC, ABAC, Policy DSL, Scoped Delegation |
| **MFA** | TOTP, WebAuthn (FIDO2), SMS/Email OTP |
| **Token Types** | Access (JWT-like signed), Refresh (opaque), API Key (long-lived) |
| **Key Management** | Crous-backed key rings, rotation CLI, kid-based verification |
| **Policy Engine** | Custom DSL → AST → Bytecode evaluator |
| **Audit** | Crous audit artifacts, CLI inspection, compliance-ready |
| **Integration** | Sessions, DI, Flow, Faults, Patterns, Config |

---

## Mission & Philosophy

### Mission Statement

> **Build an original, production-grade authentication and authorization system that is secure-by-default, manifest-driven, and deeply integrated with Aquilia's architecture.**

### Non-Negotiable Principles

1. **Manifest-First Configuration**
   - Auth clients, policies, and keys declared in manifests
   - `aq compile` produces `auth_clients.crous`, `auth_keys.crous`, `auth_policy.crous`
   - Deploy-time verification of signatures and fingerprints

2. **Least Privilege by Default**
   - Default-deny for all protected resources
   - Explicit scope and role requirements
   - Policy decisions audited

3. **Typed & Explicit**
   - Identity, credentials, tokens are typed objects
   - No ambient authority (no thread-locals or implicit globals)
   - IDE-friendly with type hints

4. **Composable Guards**
   - Authentication and authorization are Flow pipeline nodes
   - Can be composed, reordered, and statically analyzed
   - `@Auth.guard()` and `@Authz.require_scope()` decorators

5. **Audited & Testable**
   - Every sensitive operation emits audit event (crous artifact)
   - Deterministic policy evaluation (property testable)
   - Security tests in CI

6. **Separation of Concerns**
   - Identity storage ≠ Session management ≠ Token lifecycle ≠ Policy enforcement
   - Each component has clear boundaries and protocols

7. **No Import-Time Side Effects**
   - Manifest parsing must be safe in CI
   - `aq validate` checks manifests without executing runtime code

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AquilAuth System                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  AuthN Layer  │       │  Token Layer  │       │  AuthZ Layer  │
├───────────────┤       ├───────────────┤       ├───────────────┤
│ • Password    │       │ • TokenMgr    │       │ • RBAC        │
│ • API Key     │       │ • KeyRing     │       │ • ABAC        │
│ • OAuth2/OIDC │       │ • JWT Sign    │       │ • Policy DSL  │
│ • Passwordless│       │ • Rotation    │       │ • PDP/PIP     │
│ • mTLS        │       │ • Revocation  │       │ • Guards      │
│ • Device Flow │       │               │       │               │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        │         ┌─────────────┴─────────────┐         │
        │         │                           │         │
        ▼         ▼                           ▼         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Integration Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  • DI Container (inject Identity, TokenClaims, AuthzContext)    │
│  • AquilaSessions (create session on auth, rotate on privilege) │
│  • AquilaFaults (AUTH_* fault codes)                            │
│  • Flow Engine (guards as pipeline nodes)                       │
│  • Crous Artifacts (keys, policies, audit)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow: Authentication

```
User Request
    │
    ▼
┌────────────────┐
│ Auth Middleware│ ← Extract credentials (header/cookie/body)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  AuthManager   │ ← authenticate_password/api_key/oauth_callback
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Authenticator  │ ← Verify credentials (hash check, OAuth exchange)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Identity Store │ ← Load identity attributes
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  TokenManager  │ ← Issue access + refresh tokens
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ SessionEngine  │ ← Create/rotate session (AquilaSessions)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Audit Emitter  │ ← Write auth_success.crous
└────────┬───────┘
         │
         ▼
    Response
```

### Data Flow: Authorization

```
Authenticated Request
    │
    ▼
┌────────────────┐
│  Auth Guard    │ ← Extract Identity from token/session
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  Authz Guard   │ ← Check required scopes/roles/policy
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  AuthzEngine   │ ← Evaluate policy (PDP)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  Policy Store  │ ← Load compiled policy from auth_policy.crous
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Attribute PIP  │ ← Fetch user/resource/context attributes (DI)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│   Evaluator    │ ← Execute policy bytecode → Decision
└────────┬───────┘
         │
         ├─ PERMIT ──→ Continue to handler
         │
         └─ DENY ────→ Emit AUTH_POLICY_DENIED fault
```

---

## Core Components

### 1. Identity Model

```python
class Identity(BaseModel):
    """
    Represents an authenticated principal (user or service).
    
    Immutable once created, stored in DI request scope.
    """
    id: str                          # Stable unique ID (e.g., "user_123")
    type: Literal["user", "service"] # Principal type
    attributes: dict[str, Any]       # Key-value attributes (email, name, roles, etc.)
    status: Literal["active", "suspended", "deleted"]
    tenant_id: str | None = None     # Multi-tenancy support
    created_at: datetime
    updated_at: datetime
```

**Design Rationale:**
- **Stable ID**: Never changes, safe to use as foreign key
- **Type discrimination**: Different policies for users vs services
- **Attributes**: Flexible key-value store for ABAC (email, dept, clearance level)
- **Status**: Soft delete and suspension support
- **Tenant ID**: Native multi-tenancy

### 2. Credential Types

```python
class Credential(Protocol):
    """Base protocol for all credential types."""
    identity_id: str
    created_at: datetime
    last_used_at: datetime | None
    status: Literal["active", "suspended", "revoked"]

class PasswordCredential(BaseModel):
    """Password-based credential."""
    identity_id: str
    password_hash: str  # Argon2id or PBKDF2-SHA256
    salt: bytes
    algorithm: Literal["argon2id", "pbkdf2_sha256"]
    iterations: int
    created_at: datetime
    last_changed_at: datetime
    must_change: bool = False  # Force password change on next login

class ApiKeyCredential(BaseModel):
    """API key credential (long-lived)."""
    identity_id: str
    key_id: str           # Public identifier (e.g., "ak_live_123")
    key_hash: str         # SHA256(secret)
    prefix: str           # First 8 chars of key for identification
    scopes: list[str]     # Scoped permissions
    rate_limit: int | None = None
    expires_at: datetime | None = None
    created_at: datetime
    last_used_at: datetime | None = None

class OAuthClient(BaseModel):
    """OAuth2/OIDC client."""
    client_id: str
    client_secret_hash: str | None  # None for public clients
    name: str
    grant_types: list[Literal["authorization_code", "client_credentials", "refresh_token", "device_code"]]
    redirect_uris: list[str]
    scopes: list[str]
    require_pkce: bool = True
    require_consent: bool = True
    token_endpoint_auth_method: Literal["client_secret_basic", "client_secret_post", "none"]
    created_at: datetime
    status: Literal["active", "suspended"]

class MFACredential(BaseModel):
    """Multi-factor authentication credential."""
    identity_id: str
    mfa_type: Literal["totp", "webauthn", "sms", "email"]
    mfa_secret: str | None    # TOTP shared secret
    backup_codes: list[str]   # Hashed backup codes
    webauthn_credentials: list[dict] | None  # WebAuthn public keys
    created_at: datetime
    verified_at: datetime | None
    last_used_at: datetime | None
```

### 3. AuthManager

```python
class AuthManager:
    """
    Central authentication coordinator.
    
    Responsibilities:
    - Coordinate authentication flows
    - Issue tokens after successful auth
    - Integrate with sessions
    - Emit audit events
    """
    
    def __init__(
        self,
        identity_store: IdentityStore,
        credential_store: CredentialStore,
        token_manager: TokenManager,
        session_engine: SessionEngine | None = None,
        audit_emitter: AuditEmitter | None = None,
    ):
        ...
    
    async def authenticate_password(
        self,
        username: str,
        password: str,
        mfa_code: str | None = None,
    ) -> AuthResult:
        """
        Authenticate with username/password.
        
        Raises:
            AUTH_INVALID_CREDENTIALS
            AUTH_MFA_REQUIRED
            AUTH_ACCOUNT_SUSPENDED
        """
        ...
    
    async def authenticate_api_key(self, key: str) -> AuthResult:
        """Authenticate with API key."""
        ...
    
    async def authenticate_oauth_callback(
        self,
        client_id: str,
        code: str,
        redirect_uri: str,
        pkce_verifier: str | None = None,
    ) -> AuthResult:
        """Complete OAuth2 authorization code flow."""
        ...
    
    async def authenticate_device_code(
        self,
        device_code: str,
        client_id: str,
    ) -> AuthResult:
        """Poll device code for authorization."""
        ...
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """Exchange refresh token for new access token."""
        ...
    
    async def revoke_token(self, token: str) -> None:
        """Revoke access or refresh token."""
        ...
    
    async def logout(self, identity_id: str, session_id: str | None = None) -> None:
        """Logout identity, destroying session and revoking tokens."""
        ...
```

### 4. TokenManager

```python
class TokenManager:
    """
    Manages token lifecycle: issuance, validation, revocation.
    
    Supports:
    - Access tokens: short-lived, signed (JWT-like)
    - Refresh tokens: long-lived, opaque, stored
    - API keys: long-lived, scoped, rate-limited
    """
    
    def __init__(
        self,
        key_ring: KeyRing,
        token_store: TokenStore,
        config: TokenConfig,
    ):
        ...
    
    async def issue_access_token(
        self,
        identity: Identity,
        scopes: list[str],
        session_id: str | None = None,
        ttl: int | None = None,
    ) -> str:
        """
        Issue signed access token.
        
        Format:
            header: {"alg": "RS256", "kid": "key_001", "typ": "JWT"}
            payload: {"iss": "aquilia", "sub": "user_123", "aud": "api",
                      "exp": 1234567890, "iat": 1234567890,
                      "scopes": ["read", "write"], "sid": "sess_abc"}
            signature: RS256(header + payload, private_key)
        """
        ...
    
    async def issue_refresh_token(
        self,
        identity: Identity,
        session_id: str | None = None,
    ) -> str:
        """Issue opaque refresh token, stored in token_store."""
        ...
    
    async def validate_token(self, token: str) -> TokenClaims:
        """
        Validate and decode access token.
        
        Checks:
        - Signature validity (using kid from header)
        - Expiration (exp claim)
        - Not revoked (check revocation list)
        
        Raises:
            AUTH_TOKEN_INVALID
            AUTH_TOKEN_EXPIRED
            AUTH_TOKEN_REVOKED
        """
        ...
    
    async def revoke_token(self, token_id: str) -> None:
        """Add token to revocation list."""
        ...
    
    async def rotate_refresh_token(self, old_token: str) -> str:
        """
        Rotate refresh token (security best practice).
        
        Invalidates old token, issues new one with same identity/scopes.
        """
        ...
```

### 5. KeyRing (Crous-Backed)

```python
class KeyRing:
    """
    Manages cryptographic keys for token signing/verification.
    
    Keys stored as crous artifact: auth_keys.<env>.crous
    """
    
    def __init__(self, keys: list[KeyDescriptor]):
        self.keys: dict[str, KeyDescriptor] = {k.kid: k for k in keys}
        self.current_key_id: str = keys[0].kid  # Most recent key
    
    def get_signing_key(self) -> KeyDescriptor:
        """Get current signing key."""
        return self.keys[self.current_key_id]
    
    def get_verification_key(self, kid: str) -> KeyDescriptor | None:
        """Get verification key by kid (key ID)."""
        return self.keys.get(kid)
    
    @classmethod
    def from_crous(cls, artifact_path: Path) -> "KeyRing":
        """Load key ring from signed crous artifact."""
        ...
    
    def to_crous(self, output_path: Path, signer_key: Path) -> None:
        """Export key ring as signed crous artifact."""
        ...

class KeyDescriptor(BaseModel):
    """Cryptographic key metadata."""
    kid: str                    # Key ID (e.g., "key_001")
    algorithm: Literal["RS256", "ES256", "EdDSA"]
    public_key: str             # PEM-encoded
    private_key: str | None     # PEM-encoded (only for signing keys)
    status: Literal["active", "rotating", "retired", "revoked"]
    created_at: datetime
    retire_after: datetime | None  # Soft retirement date
    revoked_at: datetime | None
```

### 6. AuthzEngine

```python
class AuthzEngine:
    """
    Authorization policy decision point (PDP).
    
    Evaluates:
    - RBAC: role-based rules
    - ABAC: attribute-based conditions
    - Policy DSL: compiled policy bytecode
    """
    
    def __init__(
        self,
        policy_store: PolicyStore,
        attribute_provider: AttributeProvider,
        config: AuthzConfig,
    ):
        ...
    
    def check(
        self,
        identity: Identity,
        resource: str,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> Decision:
        """
        Check if identity can perform action on resource.
        
        Returns Decision:
            - effect: "permit" | "deny"
            - policy_id: str | None
            - obligations: list[str]  # e.g., ["log:transfer", "notify:admin"]
            - advice: list[str]       # e.g., ["cache:1h"]
            - reason: str | None      # Denial reason code
        """
        ...
    
    def check_scope(self, identity: Identity, required_scopes: list[str]) -> bool:
        """Check if identity has all required scopes."""
        ...
    
    def check_role(self, identity: Identity, required_roles: list[str]) -> bool:
        """Check if identity has any of the required roles."""
        ...
    
    def list_permitted_actions(
        self,
        identity: Identity,
        resource: str,
    ) -> list[str]:
        """
        List all actions identity can perform on resource.
        
        Used by UIs to show/hide actions.
        """
        ...
```

---

## Authentication Flows

### 1. Username/Password + Session

```python
# Developer usage
@flow("/login").POST
async def login(request: Request, auth_manager: AuthManager):
    data = await request.json()
    
    result = await auth_manager.authenticate_password(
        username=data["username"],
        password=data["password"],
        mfa_code=data.get("mfa_code"),
    )
    
    # Session automatically created by middleware
    # Access token returned in response
    
    return Response.json({
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "expires_in": 3600,
    })
```

**Internal Flow:**
1. Extract username/password from request body
2. Load identity by username from `IdentityStore`
3. Load password credential from `CredentialStore`
4. Verify password hash (Argon2id comparison)
5. If MFA enabled, verify MFA code (TOTP/WebAuthn)
6. Issue access + refresh tokens via `TokenManager`
7. Create session via `SessionEngine` (integrated middleware)
8. Emit `auth_success` audit event (crous)
9. Return tokens in response

**Security:**
- Rate limit: 5 attempts per IP per 15 minutes
- Constant-time password comparison
- MFA required for privileged accounts
- Session rotated on privilege escalation

### 2. API Key Authentication

```python
@flow("/api/orders").GET
@Auth.guard(methods=["api_key"])
async def list_orders(identity: Identity):
    # identity injected from API key
    return Response.json({"orders": []})
```

**Request:**
```http
GET /api/orders HTTP/1.1
Authorization: Bearer ak_live_1234567890abcdef
```

**Internal Flow:**
1. Extract API key from `Authorization: Bearer <key>`
2. Parse key prefix to identify key type
3. Hash key and lookup in `CredentialStore`
4. Validate key status (not expired/revoked)
5. Check rate limit for this key
6. Load identity attributes
7. Inject `Identity` into DI request scope
8. Update `last_used_at` timestamp

**Security:**
- Keys hashed with SHA256 before storage
- Rate limits enforced per key
- Keys can be scoped to specific actions
- Revocation immediate (no caching)

### 3. OAuth2 Authorization Code + PKCE

```mermaid
sequenceDiagram
    participant User
    participant Client
    participant Aquilia
    participant AuthServer
    
    User->>Client: Click "Login with Aquilia"
    Client->>Client: Generate code_verifier, code_challenge
    Client->>Aquilia: GET /oauth/authorize?client_id=...&redirect_uri=...&code_challenge=...
    Aquilia->>User: Show consent screen
    User->>Aquilia: Approve
    Aquilia->>Client: Redirect with code
    Client->>Aquilia: POST /oauth/token (code + code_verifier)
    Aquilia->>Aquilia: Verify code_challenge matches code_verifier
    Aquilia->>Client: Return access_token + refresh_token
```

**Endpoints:**

```python
@flow("/oauth/authorize").GET
async def oauth_authorize(
    request: Request,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: Literal["S256", "plain"],
):
    """
    Authorization endpoint (user consent).
    
    1. Validate client_id and redirect_uri
    2. Render consent screen (if not already consented)
    3. Generate authorization code
    4. Store code with PKCE challenge
    5. Redirect to client with code
    """
    ...

@flow("/oauth/token").POST
async def oauth_token(
    request: Request,
    grant_type: str,
    code: str | None = None,
    redirect_uri: str | None = None,
    code_verifier: str | None = None,
    refresh_token: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
):
    """
    Token endpoint (exchange code for tokens).
    
    1. Authenticate client (secret or PKCE)
    2. Validate authorization code
    3. Verify PKCE code_verifier matches stored code_challenge
    4. Issue access + refresh tokens
    5. Revoke authorization code (one-time use)
    """
    ...
```

**Security:**
- PKCE required for public clients (SPAs, mobile)
- Authorization codes valid for 10 minutes only
- Redirect URI exact match required
- Consent stored per client per user
- Refresh token rotation on each use

### 4. Device Flow (for devices without browser)

```python
# Device initiates flow
POST /oauth/device/authorize
{
    "client_id": "device_app",
    "scope": "read write"
}

# Response:
{
    "device_code": "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS",
    "user_code": "WDJB-MJHT",
    "verification_uri": "https://aquilia.example.com/device",
    "verification_uri_complete": "https://aquilia.example.com/device?code=WDJB-MJHT",
    "expires_in": 900,
    "interval": 5
}

# Device displays: "Go to https://aquilia.example.com/device and enter code WDJB-MJHT"

# Device polls token endpoint
POST /oauth/device/token
{
    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    "device_code": "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS",
    "client_id": "device_app"
}

# While pending:
{
    "error": "authorization_pending"
}

# After user approves:
{
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600
}
```

### 5. Passwordless (Magic Link)

```python
@flow("/auth/magic-link").POST
async def request_magic_link(request: Request, auth_manager: AuthManager):
    data = await request.json()
    
    link = await auth_manager.issue_magic_link(
        email=data["email"],
        redirect_uri=data.get("redirect_uri"),
    )
    
    # Send email with magic link (email service integration)
    await send_email(data["email"], link)
    
    return Response.json({"message": "Check your email"})

@flow("/auth/magic-link/verify").GET
async def verify_magic_link(token: str, auth_manager: AuthManager):
    result = await auth_manager.verify_magic_link(token)
    
    # Create session and redirect
    return Response.redirect(result.redirect_uri)
```

**Security:**
- Magic links valid for 15 minutes
- One-time use (consumed on verification)
- Token: 32-byte random, URL-safe
- Rate limit: 3 requests per email per hour

### 6. Multi-Factor Authentication (MFA)

**TOTP (Time-Based One-Time Password):**

```python
# Setup TOTP
@flow("/auth/mfa/totp/setup").POST
async def setup_totp(identity: Identity, auth_manager: AuthManager):
    secret = await auth_manager.create_totp_secret(identity.id)
    
    # Generate QR code for authenticator app
    qr_code_url = totp_qr_code(secret, identity.attributes["email"])
    
    return Response.json({
        "secret": secret,
        "qr_code": qr_code_url,
        "backup_codes": [...],  # 10 single-use backup codes
    })

# Verify TOTP during login
result = await auth_manager.authenticate_password(
    username="user@example.com",
    password="password123",
    mfa_code="123456",  # 6-digit TOTP code
)
```

**WebAuthn (FIDO2):**

```python
# Register security key
@flow("/auth/mfa/webauthn/register").POST
async def register_webauthn(identity: Identity):
    options = await auth_manager.generate_webauthn_registration_options(identity.id)
    
    return Response.json(options)  # Challenge for client

@flow("/auth/mfa/webauthn/verify").POST
async def verify_webauthn_registration(identity: Identity, request: Request):
    data = await request.json()
    
    await auth_manager.verify_webauthn_registration(
        identity.id,
        credential=data["credential"],
        challenge=data["challenge"],
    )
    
    return Response.json({"message": "Security key registered"})
```

---

## Authorization Model

### RBAC (Role-Based Access Control)

**Role Definition:**

```python
class Role(BaseModel):
    """Role with permissions and inheritance."""
    id: str                    # e.g., "admin", "editor", "viewer"
    name: str
    description: str
    permissions: list[str]     # e.g., ["users.read", "users.write"]
    inherits_from: list[str]   # e.g., ["viewer"] (editor inherits viewer perms)
    created_at: datetime

# Example roles
ROLES = {
    "viewer": Role(
        id="viewer",
        name="Viewer",
        permissions=["orders.read", "products.read"],
    ),
    "editor": Role(
        id="editor",
        name="Editor",
        permissions=["orders.write", "products.write"],
        inherits_from=["viewer"],
    ),
    "admin": Role(
        id="admin",
        name="Administrator",
        permissions=["*"],  # Wildcard: all permissions
    ),
}
```

**Usage:**

```python
@flow("/orders").DELETE
@Auth.guard()
@Authz.require_role("admin", "editor")
async def delete_order(order_id: str, identity: Identity):
    # Only users with admin or editor role can access
    ...
```

### ABAC (Attribute-Based Access Control)

**Attribute Sources:**
1. **User attributes**: roles, department, clearance_level
2. **Resource attributes**: owner_id, sensitivity, tags
3. **Context attributes**: time, IP address, device_trust_score

**Example Policy:**

```yaml
id: users:delete_account
description: "Users can delete their own account, admins can delete any"
effect: permit
target:
  resource: "accounts:{account_id}"
  action: ["delete"]
condition:
  any:
    - attr:user.id == resource.owner_id
    - attr:user.role == "admin"
```

### Scoped Delegation

**OAuth2 Scopes:**

```python
# Issue token with limited scopes
token = await token_manager.issue_access_token(
    identity=service_identity,
    scopes=["orders.read", "orders.write"],
    session_id=None,
)

# Handler checks required scopes
@flow("/orders").POST
@Auth.guard()
@Authz.require_scope("orders.write")
async def create_order(identity: Identity):
    # Token must have orders.write scope
    ...
```

**Scope Hierarchy:**

```
orders.*         → orders.read, orders.write
orders.read      → orders.list, orders.get
orders.write     → orders.create, orders.update, orders.delete
```

---

## AquilaPolicy DSL

### Language Specification

**Grammar (YAML-based):**

```yaml
# Policy schema
id: string                    # Unique policy ID
description: string           # Human-readable description
version: int                  # Policy version (for updates)
effect: "permit" | "deny"     # Default effect
target:
  resource: string            # Resource pattern (glob or regex)
  action: string[] | "*"      # Actions this policy applies to
condition:
  # Boolean expressions
  all: condition[]            # AND
  any: condition[]            # OR
  not: condition              # NOT
  
  # Comparisons
  attr:<path>: <value>        # Equality
  attr:<path>.<op>: <value>   # Comparison operators
  
  # Operators: ==, !=, >, <, >=, <=, in, not_in, matches
obligations: string[]         # Actions to perform on permit
advice: string[]              # Suggestions (not enforced)
```

**Example Policies:**

```yaml
# Policy 1: Users can read their own orders
id: users:read_own_orders
version: 1
effect: permit
target:
  resource: "orders:{order_id}"
  action: ["read"]
condition:
  attr:user.id == resource.owner_id
obligations:
  - "log:event=order_viewed"

---

# Policy 2: Admins can perform any action
id: admins:full_access
version: 1
effect: permit
target:
  resource: "*"
  action: "*"
condition:
  attr:user.role == "admin"

---

# Policy 3: Block suspended accounts
id: security:block_suspended
version: 1
effect: deny
target:
  resource: "*"
  action: "*"
condition:
  attr:user.status == "suspended"
obligations:
  - "log:event=suspended_access_attempt"
  - "notify:security_team"

---

# Policy 4: Complex transfer policy
id: transfers:can_transfer_funds
version: 1
effect: permit
target:
  resource: "accounts:{account_id}/transfers"
  action: ["create"]
condition:
  all:
    - attr:user.kyc == "verified"
    - attr:user.account_balance >= input.amount
    - not:
        attr:user.suspended
    - any:
        - attr:input.amount < 10000
        - attr:user.transfer_limit_override == true
obligations:
  - "log:event=transfer_initiated"
  - "notify:user_email"
advice:
  - "cache:ttl=300"  # Cache decision for 5 minutes
```

### Policy Compilation

**Compilation Pipeline:**

```
YAML Policy → Parser → AST → Optimizer → Bytecode → Crous Artifact
```

**AST Structure:**

```python
class PolicyAST(BaseModel):
    """Abstract syntax tree for policy."""
    id: str
    version: int
    effect: Literal["permit", "deny"]
    target: TargetNode
    condition: ConditionNode
    obligations: list[str]
    advice: list[str]

class ConditionNode(BaseModel):
    """Condition node (recursive)."""
    type: Literal["all", "any", "not", "comparison"]
    children: list["ConditionNode"] | None
    operator: str | None  # ==, !=, >, <, >=, <=, in, not_in, matches
    left: AttributePath | None
    right: Any | None

class AttributePath(BaseModel):
    """Attribute reference (e.g., user.role, resource.owner_id)."""
    scope: Literal["user", "resource", "context", "input"]
    path: list[str]  # ["user", "role"] or ["resource", "owner_id"]
```

**Bytecode Format:**

```python
# Bytecode instructions (stack-based)
LOAD_ATTR = 0x01      # Push attribute value onto stack
LOAD_CONST = 0x02     # Push constant value onto stack
CMP_EQ = 0x10         # Pop 2 values, push equality result
CMP_GT = 0x11         # Pop 2 values, push greater-than result
AND = 0x20            # Pop 2 bools, push AND result
OR = 0x21             # Pop 2 bools, push OR result
NOT = 0x22            # Pop bool, push NOT result
JUMP_IF_FALSE = 0x30  # Conditional jump
RETURN = 0xFF         # Return top of stack

# Example bytecode for: user.role == "admin"
bytecode = [
    (LOAD_ATTR, ["user", "role"]),
    (LOAD_CONST, "admin"),
    (CMP_EQ,),
    (RETURN,),
]
```

### Policy Evaluator

```python
class PolicyEvaluator:
    """
    Evaluates compiled policy bytecode.
    
    Stack-based virtual machine for policy execution.
    """
    
    def __init__(self, policy: CompiledPolicy):
        self.policy = policy
        self.bytecode = policy.bytecode
    
    def evaluate(
        self,
        user_attrs: dict[str, Any],
        resource_attrs: dict[str, Any],
        context_attrs: dict[str, Any],
        input_attrs: dict[str, Any],
    ) -> bool:
        """
        Execute bytecode and return boolean result.
        
        Uses stack-based evaluation for efficiency.
        """
        stack: list[Any] = []
        pc = 0  # Program counter
        
        while pc < len(self.bytecode):
            instruction = self.bytecode[pc]
            opcode = instruction[0]
            
            if opcode == LOAD_ATTR:
                path = instruction[1]
                value = self._resolve_attribute(path, user_attrs, resource_attrs, context_attrs, input_attrs)
                stack.append(value)
            
            elif opcode == LOAD_CONST:
                stack.append(instruction[1])
            
            elif opcode == CMP_EQ:
                right = stack.pop()
                left = stack.pop()
                stack.append(left == right)
            
            elif opcode == AND:
                right = stack.pop()
                left = stack.pop()
                stack.append(left and right)
            
            # ... other opcodes
            
            elif opcode == RETURN:
                return stack.pop()
            
            pc += 1
        
        return False  # Default deny
    
    def _resolve_attribute(self, path: list[str], user, resource, context, input_data):
        """Resolve attribute from path (e.g., ["user", "role"])."""
        scope = path[0]
        attrs = {"user": user, "resource": resource, "context": context, "input": input_data}
        
        obj = attrs[scope]
        for key in path[1:]:
            obj = obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)
        
        return obj
```

### Policy Store & Loading

```python
class PolicyStore:
    """
    Stores and retrieves compiled policies.
    
    Loads from auth_policy.crous artifact.
    """
    
    def __init__(self, policies: dict[str, CompiledPolicy]):
        self.policies = policies
    
    def get_policy(self, policy_id: str) -> CompiledPolicy | None:
        """Get policy by ID."""
        return self.policies.get(policy_id)
    
    def get_policies_for_resource(self, resource: str, action: str) -> list[CompiledPolicy]:
        """Get all policies matching resource and action."""
        matching = []
        
        for policy in self.policies.values():
            if self._matches_target(policy.target, resource, action):
                matching.append(policy)
        
        return matching
    
    @classmethod
    def from_crous(cls, artifact_path: Path) -> "PolicyStore":
        """Load policies from signed crous artifact."""
        # 1. Load and verify crous signature
        # 2. Deserialize policy bundle
        # 3. Validate policy versions and IDs
        # 4. Create PolicyStore instance
        ...
```

---

## Token Management

### Token Types

| Token Type | Lifetime | Format | Storage | Use Case |
|------------|----------|--------|---------|----------|
| **Access Token** | 1 hour | Signed (JWT-like) | Stateless | API requests |
| **Refresh Token** | 30 days | Opaque | TokenStore | Token renewal |
| **API Key** | 1 year | Opaque | CredentialStore | Service auth |
| **Magic Link Token** | 15 min | Opaque | TokenStore | Passwordless |
| **OAuth Code** | 10 min | Opaque | TokenStore | OAuth exchange |
| **Device Code** | 15 min | Opaque | TokenStore | Device flow |

### Access Token Structure

```json
{
  "header": {
    "alg": "RS256",
    "kid": "key_001",
    "typ": "JWT"
  },
  "payload": {
    "iss": "https://auth.aquilia.example.com",
    "sub": "user_123",
    "aud": ["https://api.aquilia.example.com"],
    "exp": 1643723400,
    "iat": 1643719800,
    "nbf": 1643719800,
    "jti": "token_abc123",
    "scopes": ["orders.read", "orders.write"],
    "sid": "sess_xyz789",
    "roles": ["editor"],
    "tenant_id": "tenant_001"
  },
  "signature": "base64url(RS256(header + payload, private_key))"
}
```

### Token Validation Process

```python
async def validate_token(self, token: str) -> TokenClaims:
    """
    Validate access token.
    
    Checks (in order):
    1. Format: 3 parts (header.payload.signature)
    2. Header: Valid JSON, has alg and kid
    3. Signature: Verify using public key from KeyRing
    4. Expiration: exp > now
    5. Not Before: nbf <= now
    6. Issuer: iss matches expected issuer
    7. Audience: aud contains expected audience
    8. Revocation: jti not in revocation list
    """
    
    # Parse token
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        raise AUTH_TOKEN_INVALID("Malformed token")
    
    # Decode header
    header_data = json.loads(base64_decode(header))
    kid = header_data.get("kid")
    
    if not kid:
        raise AUTH_TOKEN_INVALID("Missing kid in header")
    
    # Get verification key
    key = self.key_ring.get_verification_key(kid)
    
    if not key:
        raise AUTH_TOKEN_INVALID(f"Unknown kid: {kid}")
    
    # Verify signature
    message = f"{header}.{payload}".encode()
    signature_bytes = base64_decode(signature)
    
    if not verify_signature(message, signature_bytes, key.public_key):
        raise AUTH_TOKEN_INVALID("Invalid signature")
    
    # Decode payload
    payload_data = json.loads(base64_decode(payload))
    
    # Check expiration
    now = time.time()
    exp = payload_data.get("exp")
    
    if not exp or exp < now:
        raise AUTH_TOKEN_EXPIRED()
    
    # Check not before
    nbf = payload_data.get("nbf", 0)
    if nbf > now:
        raise AUTH_TOKEN_INVALID("Token not yet valid")
    
    # Check revocation
    jti = payload_data.get("jti")
    if await self.is_revoked(jti):
        raise AUTH_TOKEN_REVOKED()
    
    return TokenClaims(**payload_data)
```

### Token Revocation

**Revocation List:**

```python
class TokenRevocationList:
    """
    Fast revocation check using bloom filter + Redis.
    
    Approach:
    1. Bloom filter for fast negative checks (99.9% of requests)
    2. Redis set for confirmed revocations
    3. TTL-based expiration (remove after token exp)
    """
    
    def __init__(self, redis: Redis):
        self.redis = redis
        self.bloom = BloomFilter(size=1000000, error_rate=0.001)
    
    async def revoke(self, token_id: str, expires_at: datetime) -> None:
        """Add token to revocation list."""
        self.bloom.add(token_id)
        
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        await self.redis.setex(f"revoked:{token_id}", ttl, "1")
    
    async def is_revoked(self, token_id: str) -> bool:
        """Check if token is revoked."""
        # Fast path: bloom filter
        if token_id not in self.bloom:
            return False
        
        # Slow path: Redis check
        return await self.redis.exists(f"revoked:{token_id}")
```

---

## Key Management & Rotation

### Key Lifecycle

```
1. GENERATE → 2. ACTIVATE → 3. ROTATE → 4. RETIRE → 5. REVOKE
```

**States:**
- **Active**: Current signing key, used for new tokens
- **Rotating**: Transitioning to new key, both keys valid for verification
- **Retired**: No longer used for signing, but still valid for verification
- **Revoked**: Invalid for all operations, tokens signed with this key are invalid

### Key Rotation Process

```bash
# Step 1: Generate new key
aq auth keys generate --algorithm RS256 --output keys/key_002.pem

# Step 2: Add new key to key ring (mark as rotating)
aq auth keys add --key-file keys/key_002.pem --kid key_002 --status rotating

# Step 3: Promote new key to active (retire old key)
aq auth keys promote --kid key_002

# Step 4: Wait for old tokens to expire (grace period)
# Monitor: aq auth keys usage --kid key_001

# Step 5: Revoke old key (when usage drops to zero)
aq auth keys revoke --kid key_001
```

### Crous Key Ring Artifact

**File:** `artifacts/auth_keys.<env>.crous`

```json
{
  "schema_version": "1.0",
  "artifact_type": "auth_keys",
  "environment": "production",
  "fingerprint": "sha256:abc123...",
  "created_at": "2026-01-24T10:30:00Z",
  "keys": [
    {
      "kid": "key_002",
      "algorithm": "RS256",
      "public_key": "-----BEGIN PUBLIC KEY-----\n...",
      "status": "active",
      "created_at": "2026-01-24T10:00:00Z"
    },
    {
      "kid": "key_001",
      "algorithm": "RS256",
      "public_key": "-----BEGIN PUBLIC KEY-----\n...",
      "status": "retired",
      "created_at": "2025-10-24T10:00:00Z",
      "retire_after": "2026-01-24T10:00:00Z"
    }
  ],
  "signature": {
    "algorithm": "EdDSA",
    "public_key": "...",
    "signature": "...",
    "signed_by": "deploy_key_prod"
  }
}
```

---

## Security Model & Threat Analysis

### Threats & Countermeasures

| Threat | Attack Vector | Countermeasure | Implementation |
|--------|---------------|----------------|----------------|
| **Credential Theft** | Phishing, keylogger | Strong hashing, MFA | Argon2id + TOTP/WebAuthn |
| **Token Replay** | Stolen token reuse | Token expiration, binding | 1h TTL, optional TLS binding |
| **Session Fixation** | Force user into attacker's session | Rotate on privilege change | SessionEngine rotation |
| **CSRF** | Cross-site request forgery | SameSite cookies, CSRF tokens | Cookie SameSite=Lax |
| **XSS** | Steal token from JavaScript | HttpOnly cookies | Cookie HttpOnly=True |
| **Brute Force** | Password guessing | Rate limiting, account lockout | 5 attempts/15min, exponential backoff |
| **Account Enumeration** | Timing attacks, error messages | Consistent responses | Same response time for valid/invalid users |
| **Token Forgery** | Create fake tokens | Digital signatures | RS256 signing with private key |
| **Privilege Escalation** | Exploit authZ bugs | Least privilege, policy tests | Default-deny, property tests |
| **Man-in-the-Middle** | Intercept credentials | TLS only, HSTS | Secure flag on cookies, HTTPS required |

### Password Security

**Algorithm:** Argon2id (memory-hard, GPU-resistant)

```python
import argon2

# Hash password
hasher = argon2.PasswordHasher(
    time_cost=2,        # Iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,      # Threads
    hash_len=32,        # Output length
    salt_len=16,        # Salt length
)

password_hash = hasher.hash("user_password_123")
# Result: $argon2id$v=19$m=65536,t=2,p=4$randomsalt$hashoutput

# Verify password
try:
    hasher.verify(password_hash, "user_password_123")
except argon2.exceptions.VerifyMismatchError:
    # Invalid password
    ...
```

**Password Policy:**
- Minimum length: 12 characters
- Require: uppercase, lowercase, digit, special char (optional, configurable)
- Check against breached password list (Have I Been Pwned API)
- Enforce password change every 90 days (configurable)
- Prevent reuse of last 5 passwords

### Rate Limiting

```python
class RateLimiter:
    """
    Token bucket rate limiter for auth endpoints.
    
    Limits:
    - Login attempts: 5 per IP per 15 minutes
    - Magic link requests: 3 per email per hour
    - Token refresh: 10 per session per minute
    - API key requests: per-key configured limit
    """
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
        """
        Check if request is within rate limit.
        
        Uses Redis with sliding window.
        """
        now = time.time()
        window_start = now - window
        
        # Remove old entries
        await self.redis.zremrangebyscore(f"ratelimit:{key}", 0, window_start)
        
        # Count requests in window
        count = await self.redis.zcard(f"ratelimit:{key}")
        
        if count >= limit:
            return False
        
        # Add current request
        await self.redis.zadd(f"ratelimit:{key}", {str(now): now})
        await self.redis.expire(f"ratelimit:{key}", window)
        
        return True
```

### Audit & Compliance

**Audit Events:**

All sensitive operations emit audit events stored as crous artifacts:

```python
class AuditEvent(BaseModel):
    """Audit event structure."""
    event_id: str
    event_type: Literal[
        "auth_success", "auth_failure", "token_issued", "token_revoked",
        "mfa_enabled", "mfa_disabled", "password_changed", "account_suspended",
        "client_created", "client_deleted", "key_rotated", "policy_updated",
    ]
    identity_id: str | None
    client_id: str | None
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool
    error_code: str | None
    metadata: dict[str, Any]

# Example audit event
{
  "event_id": "evt_abc123",
  "event_type": "auth_success",
  "identity_id": "user_123",
  "client_id": None,
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2026-01-24T10:30:00Z",
  "success": true,
  "metadata": {
    "method": "password",
    "mfa_used": true,
    "session_id": "sess_xyz789"
  }
}
```

**Storage:**
- `artifacts/auth/audit/<date>/<event_id>.crous`
- Signed with audit signing key
- Immutable (append-only)
- Queryable via CLI: `aq auth audit --since 2026-01-01 --type auth_failure`

---

## Integration Architecture

### DI Integration

```python
# Register auth services in DI container

from aquilia.di import Container, service

# App-scoped services
@service(scope="app", name="AuthManager")
class AuthManager:
    ...

@service(scope="app", name="TokenManager")
class TokenManager:
    ...

@service(scope="app", name="AuthzEngine")
class AuthzEngine:
    ...

# Request-scoped services
@service(scope="request", name="Identity")
async def provide_identity(
    request: Request,
    token_manager: TokenManager,
) -> Identity | None:
    """
    Extract and validate identity from request.
    
    Checks (in order):
    1. Authorization header (Bearer token)
    2. Session cookie (via SessionEngine)
    3. API key header
    """
    # Try bearer token
    auth_header = request.header("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        claims = await token_manager.validate_token(token)
        return await load_identity(claims.sub)
    
    # Try session
    session = request.state.get("session")
    if session and session.is_authenticated:
        return await load_identity(session.principal.id)
    
    # Try API key
    api_key = request.header("x-api-key")
    if api_key:
        credential = await load_api_key(api_key)
        return await load_identity(credential.identity_id)
    
    return None
```

### Flow Integration

```python
from aquilia.auth import Auth, Authz

# Simple authentication guard
@flow("/api/orders").GET
@Auth.guard()  # Require authentication
async def list_orders(identity: Identity):
    # identity injected if authenticated
    return Response.json({"orders": []})

# Require specific scope
@flow("/api/orders").POST
@Auth.guard()
@Authz.require_scope("orders.write")
async def create_order(identity: Identity, request: Request):
    ...

# Require role
@flow("/admin/users").GET
@Auth.guard()
@Authz.require_role("admin")
async def list_users(identity: Identity):
    ...

# Complex policy
@flow("/accounts/{account_id}/transfer").POST
@Auth.guard()
@Authz.require_policy("transfers:can_transfer_funds")
async def transfer_funds(account_id: str, identity: Identity, request: Request):
    ...

# Optional authentication
@flow("/products").GET
async def list_products(identity: Identity | None = None):
    # Show different products based on authentication
    if identity:
        return Response.json({"products": get_premium_products()})
    else:
        return Response.json({"products": get_public_products()})
```

### Guard Implementation

```python
class AuthGuard:
    """
    Flow guard for authentication.
    
    Can be used as decorator or pipeline node.
    """
    
    def __init__(
        self,
        required: bool = True,
        methods: list[str] | None = None,  # ["password", "api_key", "oauth"]
    ):
        self.required = required
        self.methods = methods
    
    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        # Extract identity
        identity = await self._extract_identity(request, ctx)
        
        # Check if required
        if self.required and not identity:
            raise AUTH_REQUIRED()
        
        # Check method
        if self.methods and identity.attributes.get("auth_method") not in self.methods:
            raise AUTH_METHOD_NOT_ALLOWED()
        
        # Inject into context
        ctx.identity = identity
        
        # Register in DI
        if ctx.di_container:
            await ctx.di_container.register_instance(Identity, identity, scope="request")
        
        return await next(request, ctx)

class AuthzGuard:
    """Flow guard for authorization."""
    
    def __init__(
        self,
        scopes: list[str] | None = None,
        roles: list[str] | None = None,
        policy: str | None = None,
    ):
        self.scopes = scopes
        self.roles = roles
        self.policy = policy
    
    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        identity = ctx.identity
        
        if not identity:
            raise AUTH_REQUIRED()
        
        # Check scopes
        if self.scopes:
            if not self._has_scopes(identity, self.scopes):
                raise AUTH_INSUFFICIENT_SCOPE(required=self.scopes)
        
        # Check roles
        if self.roles:
            if not self._has_role(identity, self.roles):
                raise AUTH_INSUFFICIENT_ROLE(required=self.roles)
        
        # Check policy
        if self.policy:
            decision = await self._check_policy(identity, request, self.policy)
            if decision.effect == "deny":
                raise AUTH_POLICY_DENIED(policy_id=self.policy, reason=decision.reason)
        
        return await next(request, ctx)
```

### Session Integration

```python
class AuthSessionMiddleware:
    """
    Integrate auth with sessions.
    
    - Create session on successful authentication
    - Rotate session on privilege change
    - Destroy session on logout
    """
    
    def __init__(
        self,
        auth_manager: AuthManager,
        session_engine: SessionEngine,
    ):
        self.auth_manager = auth_manager
        self.session_engine = session_engine
    
    async def __call__(self, request: Request, ctx: RequestCtx, next: Handler) -> Response:
        # Resolve session
        session = await self.session_engine.resolve(request, ctx.di_container)
        
        # Check if login request
        if request.path == "/login" and request.method == "POST":
            # Authenticate
            data = await request.json()
            result = await self.auth_manager.authenticate_password(
                username=data["username"],
                password=data["password"],
            )
            
            # Mark session as authenticated
            principal = SessionPrincipal(
                kind="user",
                id=result.identity.id,
                attributes=result.identity.attributes,
            )
            session.mark_authenticated(principal)
            
            # Store token in session
            session.data["access_token"] = result.access_token
            session.data["refresh_token"] = result.refresh_token
        
        # Process request
        privilege_before = session.is_authenticated
        response = await next(request, ctx)
        privilege_after = session.is_authenticated
        
        # Commit session (rotate if privilege changed)
        await self.session_engine.commit(
            session,
            response,
            privilege_changed=(privilege_before != privilege_after),
        )
        
        return response
```

### Fault Integration

```python
# Auth-specific faults (aquilia/faults/domains/auth.py)

from aquilia.faults import Fault, FaultDomain, FaultSeverity

class AUTH_INVALID_CREDENTIALS(Fault):
    """Invalid username or password."""
    domain = FaultDomain.SECURITY
    code = "AUTH_001"
    severity = FaultSeverity.WARN
    message = "Invalid credentials"
    public_message = "Invalid username or password"
    retryable = False

class AUTH_TOKEN_EXPIRED(Fault):
    """Access token has expired."""
    domain = FaultDomain.SECURITY
    code = "AUTH_002"
    severity = FaultSeverity.WARN
    message = "Token expired"
    public_message = "Your session has expired. Please log in again."
    retryable = False

class AUTH_TOKEN_REVOKED(Fault):
    """Token has been revoked."""
    domain = FaultDomain.SECURITY
    code = "AUTH_003"
    severity = FaultSeverity.WARN
    message = "Token revoked"
    retryable = False

class AUTH_MFA_REQUIRED(Fault):
    """MFA verification required."""
    domain = FaultDomain.SECURITY
    code = "AUTH_004"
    severity = FaultSeverity.WARN
    message = "MFA required"
    public_message = "Please enter your MFA code"
    retryable = True

class AUTH_ACCOUNT_SUSPENDED(Fault):
    """Account is suspended."""
    domain = FaultDomain.SECURITY
    code = "AUTH_005"
    severity = FaultSeverity.ERROR
    message = "Account suspended"
    public_message = "Your account has been suspended. Please contact support."
    retryable = False

class AUTH_RATE_LIMITED(Fault):
    """Too many authentication attempts."""
    domain = FaultDomain.SECURITY
    code = "AUTH_006"
    severity = FaultSeverity.WARN
    message = "Rate limit exceeded"
    public_message = "Too many attempts. Please try again later."
    retryable = True
    retry_after = 900  # 15 minutes

class AUTH_POLICY_DENIED(Fault):
    """Authorization policy denied access."""
    domain = FaultDomain.SECURITY
    code = "AUTH_007"
    severity = FaultSeverity.WARN
    message = "Access denied by policy"
    public_message = "You do not have permission to perform this action"
    retryable = False
```

---

## Crous Artifacts

### 1. Auth Keys Artifact

**File:** `artifacts/auth_keys.<env>.crous`

```json
{
  "schema_version": "1.0",
  "artifact_type": "auth_keys",
  "environment": "production",
  "fingerprint": "sha256:abc123...",
  "created_at": "2026-01-24T10:30:00Z",
  "keys": [
    {
      "kid": "key_002",
      "algorithm": "RS256",
      "public_key": "-----BEGIN PUBLIC KEY-----\n...",
      "status": "active",
      "created_at": "2026-01-24T10:00:00Z"
    }
  ],
  "signature": {
    "algorithm": "EdDSA",
    "signed_by": "deploy_key_prod",
    "signature": "..."
  }
}
```

### 2. Auth Policy Artifact

**File:** `artifacts/auth_policy.<env>.crous`

```json
{
  "schema_version": "1.0",
  "artifact_type": "auth_policy",
  "environment": "production",
  "fingerprint": "sha256:def456...",
  "created_at": "2026-01-24T10:30:00Z",
  "policies": [
    {
      "id": "users:read_own_orders",
      "version": 1,
      "bytecode": [...],
      "compiled_at": "2026-01-24T10:00:00Z"
    }
  ],
  "signature": {
    "algorithm": "EdDSA",
    "signed_by": "deploy_key_prod",
    "signature": "..."
  }
}
```

### 3. Auth Clients Artifact

**File:** `artifacts/auth_clients.<env>.crous`

```json
{
  "schema_version": "1.0",
  "artifact_type": "auth_clients",
  "environment": "production",
  "fingerprint": "sha256:ghi789...",
  "created_at": "2026-01-24T10:30:00Z",
  "clients": [
    {
      "client_id": "app_web_001",
      "name": "Web Application",
      "grant_types": ["authorization_code", "refresh_token"],
      "redirect_uris": ["https://app.example.com/callback"],
      "scopes": ["orders.read", "orders.write"],
      "require_pkce": true
    }
  ],
  "signature": {
    "algorithm": "EdDSA",
    "signed_by": "deploy_key_prod",
    "signature": "..."
  }
}
```

### 4. Audit Event Artifact

**File:** `artifacts/auth/audit/2026-01-24/evt_abc123.crous`

```json
{
  "schema_version": "1.0",
  "artifact_type": "audit_event",
  "event_id": "evt_abc123",
  "event_type": "auth_success",
  "identity_id": "user_123",
  "timestamp": "2026-01-24T10:30:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "metadata": {
    "method": "password",
    "mfa_used": true
  },
  "signature": {
    "algorithm": "EdDSA",
    "signed_by": "audit_key_prod",
    "signature": "..."
  }
}
```

---

## CLI Tools

### `aq auth client`

```bash
# Create OAuth client
aq auth client create \
  --name "My App" \
  --grant-types authorization_code,refresh_token \
  --redirect-uris https://app.example.com/callback \
  --scopes orders.read,orders.write \
  --require-pkce

# List clients
aq auth client list

# Get client details
aq auth client get --client-id app_web_001

# Update client
aq auth client update --client-id app_web_001 \
  --add-redirect-uri https://app.example.com/callback2

# Delete client
aq auth client delete --client-id app_web_001

# Rotate client secret
aq auth client rotate-secret --client-id app_web_001
```

### `aq auth keys`

```bash
# Generate new key
aq auth keys generate --algorithm RS256 --output keys/key_002.pem

# Add key to key ring
aq auth keys add --key-file keys/key_002.pem --kid key_002

# List keys
aq auth keys list

# Promote key to active
aq auth keys promote --kid key_002

# Check key usage
aq auth keys usage --kid key_001

# Retire key
aq auth keys retire --kid key_001

# Revoke key
aq auth keys revoke --kid key_001

# Export key ring as crous
aq auth keys export --env production --output artifacts/auth_keys.prod.crous
```

### `aq auth token`

```bash
# Inspect token
aq auth token inspect <token>

# Validate token
aq auth token validate <token>

# Revoke token
aq auth token revoke --token-id token_abc123

# Revoke all tokens for user
aq auth token revoke --identity-id user_123

# Revoke all tokens for session
aq auth token revoke --session-id sess_xyz789
```

### `aq auth policy`

```bash
# Validate policy file
aq auth policy validate --file policies/transfers.yaml

# Compile policy
aq auth policy compile --file policies/transfers.yaml --output policies/transfers.bytecode

# Apply policy (deploy to production)
aq auth policy apply --file artifacts/auth_policy.prod.crous

# List policies
aq auth policy list

# Test policy
aq auth policy test --policy-id transfers:can_transfer_funds \
  --user-id user_123 \
  --resource accounts/acc_001/transfers \
  --action create \
  --context '{"amount": 5000}'
```

### `aq auth audit`

```bash
# View audit log
aq auth audit --since 2026-01-01 --limit 100

# Filter by event type
aq auth audit --type auth_failure --since today

# Filter by identity
aq auth audit --identity-id user_123 --since 2026-01-01

# Export audit log
aq auth audit export --since 2026-01-01 --format json --output audit.json

# Stream audit events (real-time)
aq auth audit stream
```

### `aq auth migrate`

```bash
# Migrate users from legacy system
aq auth migrate users --from-file legacy_users.csv --hash-algorithm bcrypt

# Migrate OAuth clients
aq auth migrate clients --from-file legacy_clients.json

# Verify migration
aq auth migrate verify --stats
```

---

## Implementation Roadmap

### Phase 1: Core Auth (Identity, Credentials, Tokens)
**Duration:** 3-4 days

**Tasks:**
1. Create `aquilia/auth/` package structure
2. Implement `Identity` model and `IdentityStore` protocol
3. Implement `Credential` types (password, API key)
4. Implement `PasswordHasher` (Argon2id)
5. Implement `TokenManager` with JWT signing
6. Implement `KeyRing` with crous loading
7. Create auth faults (AUTH_*)
8. Unit tests for crypto and token validation

**Deliverables:**
- `aquilia/auth/core.py` - Identity and credential types
- `aquilia/auth/tokens.py` - TokenManager and KeyRing
- `aquilia/auth/hashing.py` - Password hashing
- `aquilia/faults/domains/auth.py` - Auth faults

### Phase 2: AuthManager & Basic Flows
**Duration:** 3-4 days

**Tasks:**
1. Implement `AuthManager` core
2. Implement password authentication flow
3. Implement API key authentication
4. Implement token refresh
5. Implement token revocation
6. Create `CredentialStore` implementations (memory, Redis)
7. Integrate with rate limiter
8. Integration tests for auth flows

**Deliverables:**
- `aquilia/auth/manager.py` - AuthManager
- `aquilia/auth/stores.py` - Credential and token stores
- `aquilia/auth/rate_limit.py` - Rate limiter

### Phase 3: OAuth2/OIDC
**Duration:** 4-5 days

**Tasks:**
1. Implement OAuth2 authorization endpoint
2. Implement OAuth2 token endpoint
3. Implement PKCE verification
4. Implement device flow
5. Implement consent management
6. Create OAuth client store
7. Integration tests for OAuth flows

**Deliverables:**
- `aquilia/auth/oauth.py` - OAuth2 flows
- `aquilia/auth/pkce.py` - PKCE helper

### Phase 4: MFA & Passwordless
**Duration:** 3-4 days

**Tasks:**
1. Implement TOTP provider
2. Implement WebAuthn provider
3. Implement magic link generator
4. Implement SMS/Email OTP (hooks)
5. Create MFA credential store
6. Tests for MFA flows

**Deliverables:**
- `aquilia/auth/mfa.py` - MFA providers
- `aquilia/auth/passwordless.py` - Magic link, OTP

### Phase 5: Authorization (RBAC, ABAC)
**Duration:** 3-4 days

**Tasks:**
1. Implement `AuthzEngine` core
2. Implement RBAC (role checking)
3. Implement ABAC (attribute resolution)
4. Implement scope checking
5. Create `AttributeProvider` protocol
6. Unit tests for authz logic

**Deliverables:**
- `aquilia/auth/authz.py` - AuthzEngine
- `aquilia/auth/rbac.py` - RBAC helpers
- `aquilia/auth/abac.py` - ABAC helpers

### Phase 6: Policy DSL
**Duration:** 4-5 days

**Tasks:**
1. Design policy DSL grammar (YAML)
2. Implement policy parser (YAML → AST)
3. Implement policy compiler (AST → bytecode)
4. Implement policy evaluator (bytecode VM)
5. Create `PolicyStore` with crous loading
6. Property tests for policy evaluation

**Deliverables:**
- `aquilia/auth/policy/dsl.py` - DSL parser
- `aquilia/auth/policy/compiler.py` - Compiler
- `aquilia/auth/policy/evaluator.py` - Evaluator
- `aquilia/auth/policy/store.py` - PolicyStore

### Phase 7: Guards & Flow Integration
**Duration:** 2-3 days

**Tasks:**
1. Implement `AuthGuard` decorator
2. Implement `AuthzGuard` decorator
3. Integrate guards with Flow engine
4. Create DI providers for Identity
5. Integration tests with Flow

**Deliverables:**
- `aquilia/auth/guards.py` - Auth and Authz guards
- `aquilia/auth/integration/flow.py` - Flow integration

### Phase 8: Session Integration
**Duration:** 2-3 days

**Tasks:**
1. Create `AuthSessionMiddleware`
2. Integrate auth with SessionEngine
3. Implement session rotation on auth
4. Tests for session integration

**Deliverables:**
- `aquilia/auth/integration/sessions.py` - Session integration

### Phase 9: Crous Artifacts
**Duration:** 2-3 days

**Tasks:**
1. Define crous schemas for keys, policies, clients, audit
2. Implement crous serialization
3. Implement crous signature verification
4. Create artifact loaders
5. Tests for artifact integrity

**Deliverables:**
- `aquilia/auth/crous.py` - Crous helpers
- `schemas/auth_keys.json` - Key ring schema
- `schemas/auth_policy.json` - Policy bundle schema

### Phase 10: CLI Tools
**Duration:** 3-4 days

**Tasks:**
1. Implement `aq auth client` commands
2. Implement `aq auth keys` commands
3. Implement `aq auth token` commands
4. Implement `aq auth policy` commands
5. Implement `aq auth audit` commands
6. Implement `aq auth migrate` commands
7. CLI tests

**Deliverables:**
- `aquilia/cli/commands/auth/` - All CLI commands

### Phase 11: Tests & Documentation
**Duration:** 3-4 days

**Tasks:**
1. Comprehensive unit tests (coverage >90%)
2. Integration tests for all flows
3. Property tests for policy evaluation
4. Security tests (fuzzing, timing attacks)
5. Performance benchmarks
6. Complete API documentation
7. Security checklist
8. Operational runbook
9. Migration guides

**Deliverables:**
- `tests/auth/` - Complete test suite
- `docs/AQUILAUTH_API.md` - API reference
- `docs/AQUILAUTH_SECURITY.md` - Security guide
- `docs/AQUILAUTH_OPERATIONS.md` - Ops runbook

---

## Acceptance Criteria

✅ **Authentication:**
- [ ] Password authentication with Argon2id hashing
- [ ] API key authentication with scoped permissions
- [ ] OAuth2 authorization code flow with PKCE
- [ ] OAuth2 device flow
- [ ] Magic link passwordless authentication
- [ ] TOTP MFA provider
- [ ] WebAuthn MFA provider

✅ **Authorization:**
- [ ] RBAC with role inheritance
- [ ] ABAC with attribute resolution
- [ ] Policy DSL parser and compiler
- [ ] Policy evaluator with bytecode VM
- [ ] Scope-based delegation
- [ ] Entitlement API (list permitted actions)

✅ **Tokens:**
- [ ] Access tokens (signed, 1h TTL)
- [ ] Refresh tokens (opaque, rotating)
- [ ] Token validation with signature verification
- [ ] Token revocation with bloom filter
- [ ] Key ring with rotation support

✅ **Integration:**
- [ ] DI providers for Identity and AuthzContext
- [ ] Flow guards (@Auth.guard(), @Authz.require_scope())
- [ ] Session integration (create on auth, rotate on privilege)
- [ ] Fault integration (all auth errors map to AquilaFaults)

✅ **Crous:**
- [ ] auth_keys.crous artifact with signatures
- [ ] auth_policy.crous artifact with compiled policies
- [ ] auth_clients.crous artifact
- [ ] Audit events as crous artifacts

✅ **CLI:**
- [ ] `aq auth client` commands
- [ ] `aq auth keys` commands (generate, rotate, revoke)
- [ ] `aq auth token` commands (inspect, revoke)
- [ ] `aq auth policy` commands (validate, compile, test)
- [ ] `aq auth audit` commands (view, export, stream)

✅ **Security:**
- [ ] Rate limiting on auth endpoints
- [ ] Account lockout after failed attempts
- [ ] Constant-time password comparison
- [ ] CSRF protection (SameSite cookies)
- [ ] XSS protection (HttpOnly cookies)
- [ ] Token binding (optional TLS fingerprint)
- [ ] Audit trail for all sensitive operations

✅ **Tests:**
- [ ] Unit tests (>90% coverage)
- [ ] Integration tests (all flows end-to-end)
- [ ] Property tests (policy evaluation determinism)
- [ ] Security tests (fuzzing, timing attacks)
- [ ] Performance benchmarks (<300µs token validation)

---

## Summary

AquilAuth is a **comprehensive, original authentication and authorization system** designed specifically for Aquilia's architecture. It provides:

- **7 authentication methods**: password, API key, OAuth2, device flow, passwordless, mTLS, MFA
- **3 authorization models**: RBAC, ABAC, custom policy DSL
- **Secure token management**: signed access tokens, rotating refresh tokens, key rotation
- **Deep integration**: DI, Flow, Sessions, Faults, Crous artifacts
- **Production-ready security**: rate limiting, MFA, audit trails, secure defaults
- **Developer-friendly API**: guards, decorators, typed objects, IDE support

**Status:** Design complete, ready for implementation.

**Next Steps:** Begin Phase 1 implementation (Core Auth).
