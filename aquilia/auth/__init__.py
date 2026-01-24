"""
AquilAuth - Authentication & Authorization System

Production-grade, Aquilia-native auth system with:
- Multiple authentication methods (password, API key, OAuth2, MFA, passwordless)
- Authorization engine (RBAC, ABAC, policy DSL)
- Token management with key rotation
- Deep integration with Sessions, DI, Flow, Faults

Design Philosophy:
1. Manifest-first: Auth config declared in manifests, compiled to crous
2. Least privilege: Default-deny for all protected resources
3. Typed & explicit: No ambient authority, everything injected
4. Composable guards: Auth/authz are Flow pipeline nodes
5. Audited & testable: All sensitive operations emit audit events
6. Separation of concerns: Clear boundaries between components

Status: Core implementation complete, ready for integration testing.
"""

# Core types
from .core import (
    Identity,
    IdentityType,
    IdentityStatus,
    IdentityStore,
    Credential,
    CredentialStatus,
    CredentialStore,
    PasswordCredential,
    ApiKeyCredential,
    OAuthClient,
    OAuthClientStore,
    MFACredential,
    TokenClaims,
    AuthResult,
)

# Password hashing
from .hashing import (
    PasswordHasher,
    PasswordPolicy,
    hash_password,
    verify_password,
    validate_password,
)

# Token management
from .tokens import (
    KeyDescriptor,
    KeyRing,
    KeyAlgorithm,
    KeyStatus,
    TokenManager,
    TokenConfig,
    TokenStore,
)

# Faults
from .faults import (
    # Authentication faults
    AUTH_INVALID_CREDENTIALS,
    AUTH_TOKEN_INVALID,
    AUTH_TOKEN_EXPIRED,
    AUTH_TOKEN_REVOKED,
    AUTH_MFA_REQUIRED,
    AUTH_MFA_INVALID,
    AUTH_ACCOUNT_SUSPENDED,
    AUTH_ACCOUNT_LOCKED,
    AUTH_RATE_LIMITED,
    AUTH_REQUIRED,
    AUTH_CLIENT_INVALID,
    AUTH_GRANT_INVALID,
    AUTH_REDIRECT_URI_MISMATCH,
    AUTH_SCOPE_INVALID,
    AUTH_PKCE_INVALID,
    # Authorization faults
    AUTHZ_POLICY_DENIED,
    AUTHZ_INSUFFICIENT_SCOPE,
    AUTHZ_INSUFFICIENT_ROLE,
    AUTHZ_RESOURCE_FORBIDDEN,
    AUTHZ_TENANT_MISMATCH,
    # Credential faults
    AUTH_PASSWORD_WEAK,
    AUTH_PASSWORD_BREACHED,
    AUTH_PASSWORD_REUSED,
    AUTH_KEY_EXPIRED,
    AUTH_KEY_REVOKED,
    # Session faults
    AUTH_SESSION_REQUIRED,
    AUTH_SESSION_INVALID,
    AUTH_SESSION_HIJACK_DETECTED,
    # OAuth faults
    AUTH_CONSENT_REQUIRED,
    AUTH_DEVICE_CODE_PENDING,
    AUTH_DEVICE_CODE_EXPIRED,
    AUTH_SLOW_DOWN,
    # MFA faults
    AUTH_MFA_NOT_ENROLLED,
    AUTH_MFA_ALREADY_ENROLLED,
    AUTH_WEBAUTHN_INVALID,
    AUTH_BACKUP_CODE_INVALID,
    AUTH_BACKUP_CODE_EXHAUSTED,
)


__all__ = [
    # Core types
    "Identity",
    "IdentityType",
    "IdentityStatus",
    "IdentityStore",
    "Credential",
    "CredentialStatus",
    "CredentialStore",
    "PasswordCredential",
    "ApiKeyCredential",
    "OAuthClient",
    "OAuthClientStore",
    "MFACredential",
    "TokenClaims",
    "AuthResult",
    # Password hashing
    "PasswordHasher",
    "PasswordPolicy",
    "hash_password",
    "verify_password",
    "validate_password",
    # Token management
    "KeyDescriptor",
    "KeyRing",
    "KeyAlgorithm",
    "KeyStatus",
    "TokenManager",
    "TokenConfig",
    "TokenStore",
    # Faults
    "AUTH_INVALID_CREDENTIALS",
    "AUTH_TOKEN_INVALID",
    "AUTH_TOKEN_EXPIRED",
    "AUTH_TOKEN_REVOKED",
    "AUTH_MFA_REQUIRED",
    "AUTH_MFA_INVALID",
    "AUTH_ACCOUNT_SUSPENDED",
    "AUTH_ACCOUNT_LOCKED",
    "AUTH_RATE_LIMITED",
    "AUTH_REQUIRED",
    "AUTH_CLIENT_INVALID",
    "AUTH_GRANT_INVALID",
    "AUTH_REDIRECT_URI_MISMATCH",
    "AUTH_SCOPE_INVALID",
    "AUTH_PKCE_INVALID",
    "AUTHZ_POLICY_DENIED",
    "AUTHZ_INSUFFICIENT_SCOPE",
    "AUTHZ_INSUFFICIENT_ROLE",
    "AUTHZ_RESOURCE_FORBIDDEN",
    "AUTHZ_TENANT_MISMATCH",
    "AUTH_PASSWORD_WEAK",
    "AUTH_PASSWORD_BREACHED",
    "AUTH_PASSWORD_REUSED",
    "AUTH_KEY_EXPIRED",
    "AUTH_KEY_REVOKED",
    "AUTH_SESSION_REQUIRED",
    "AUTH_SESSION_INVALID",
    "AUTH_SESSION_HIJACK_DETECTED",
    "AUTH_CONSENT_REQUIRED",
    "AUTH_DEVICE_CODE_PENDING",
    "AUTH_DEVICE_CODE_EXPIRED",
    "AUTH_SLOW_DOWN",
    "AUTH_MFA_NOT_ENROLLED",
    "AUTH_MFA_ALREADY_ENROLLED",
    "AUTH_WEBAUTHN_INVALID",
    "AUTH_BACKUP_CODE_INVALID",
    "AUTH_BACKUP_CODE_EXHAUSTED",
]


__version__ = "0.1.0"
