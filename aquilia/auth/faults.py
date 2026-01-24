"""
AquilAuth - Authentication/Authorization Faults

Structured error types for auth failures integrated with AquilaFaults.
"""

from aquilia.faults import Fault, FaultDomain, Severity


# ============================================================================
# Authentication Faults
# ============================================================================

class AUTH_INVALID_CREDENTIALS(Fault):
    """Invalid username or password."""
    domain = FaultDomain.SECURITY
    code = "AUTH_001"
    severity = Severity.WARN
    message = "Invalid credentials"
    public_message = "Invalid username or password"
    retryable = False
    
    def __init__(self, username: str | None = None, **context):
        super().__init__(**context)
        if username:
            self.context["username_hash"] = self._hash_identifier(username)


class AUTH_TOKEN_INVALID(Fault):
    """Invalid or malformed token."""
    domain = FaultDomain.SECURITY
    code = "AUTH_002"
    severity = Severity.WARN
    message = "Invalid token"
    public_message = "Invalid authentication token"
    retryable = False


class AUTH_TOKEN_EXPIRED(Fault):
    """Access token has expired."""
    domain = FaultDomain.SECURITY
    code = "AUTH_003"
    severity = Severity.WARN
    message = "Token expired"
    public_message = "Your session has expired. Please log in again."
    retryable = False


class AUTH_TOKEN_REVOKED(Fault):
    """Token has been revoked."""
    domain = FaultDomain.SECURITY
    code = "AUTH_004"
    severity = Severity.WARN
    message = "Token revoked"
    public_message = "This token has been revoked"
    retryable = False


class AUTH_MFA_REQUIRED(Fault):
    """Multi-factor authentication required."""
    domain = FaultDomain.SECURITY
    code = "AUTH_005"
    severity = Severity.WARN
    message = "MFA required"
    public_message = "Please enter your MFA code"
    retryable = True


class AUTH_MFA_INVALID(Fault):
    """Invalid MFA code."""
    domain = FaultDomain.SECURITY
    code = "AUTH_006"
    severity = Severity.WARN
    message = "Invalid MFA code"
    public_message = "Invalid MFA code"
    retryable = True


class AUTH_ACCOUNT_SUSPENDED(Fault):
    """Account is suspended."""
    domain = FaultDomain.SECURITY
    code = "AUTH_007"
    severity = Severity.ERROR
    message = "Account suspended"
    public_message = "Your account has been suspended. Please contact support."
    retryable = False


class AUTH_ACCOUNT_LOCKED(Fault):
    """Account is locked due to failed login attempts."""
    domain = FaultDomain.SECURITY
    code = "AUTH_008"
    severity = Severity.WARN
    message = "Account locked"
    public_message = "Account locked due to multiple failed login attempts"
    retryable = True
    retry_after = 900  # 15 minutes


class AUTH_RATE_LIMITED(Fault):
    """Too many authentication attempts."""
    domain = FaultDomain.SECURITY
    code = "AUTH_009"
    severity = Severity.WARN
    message = "Rate limit exceeded"
    public_message = "Too many attempts. Please try again later."
    retryable = True
    retry_after = 900  # 15 minutes


class AUTH_REQUIRED(Fault):
    """Authentication required but not provided."""
    domain = FaultDomain.SECURITY
    code = "AUTH_010"
    severity = Severity.WARN
    message = "Authentication required"
    public_message = "Please log in to access this resource"
    retryable = False


class AUTH_CLIENT_INVALID(Fault):
    """Invalid OAuth client credentials."""
    domain = FaultDomain.SECURITY
    code = "AUTH_011"
    severity = Severity.WARN
    message = "Invalid client"
    public_message = "Invalid client credentials"
    retryable = False


class AUTH_GRANT_INVALID(Fault):
    """Invalid OAuth grant (code, refresh token, etc.)."""
    domain = FaultDomain.SECURITY
    code = "AUTH_012"
    severity = Severity.WARN
    message = "Invalid grant"
    public_message = "Invalid or expired authorization code"
    retryable = False


class AUTH_REDIRECT_URI_MISMATCH(Fault):
    """OAuth redirect URI doesn't match registered URI."""
    domain = FaultDomain.SECURITY
    code = "AUTH_013"
    severity = Severity.WARN
    message = "Redirect URI mismatch"
    public_message = "Invalid redirect URI"
    retryable = False


class AUTH_SCOPE_INVALID(Fault):
    """Requested scope is invalid or not allowed."""
    domain = FaultDomain.SECURITY
    code = "AUTH_014"
    severity = Severity.WARN
    message = "Invalid scope"
    public_message = "Requested scope is not available"
    retryable = False


class AUTH_PKCE_INVALID(Fault):
    """PKCE code verifier doesn't match challenge."""
    domain = FaultDomain.SECURITY
    code = "AUTH_015"
    severity = Severity.ERROR
    message = "PKCE verification failed"
    public_message = "Authorization failed"
    retryable = False


# ============================================================================
# Authorization Faults
# ============================================================================

class AUTHZ_POLICY_DENIED(Fault):
    """Authorization policy denied access."""
    domain = FaultDomain.SECURITY
    code = "AUTHZ_001"
    severity = Severity.WARN
    message = "Access denied by policy"
    public_message = "You do not have permission to perform this action"
    retryable = False
    
    def __init__(self, policy_id: str | None = None, reason: str | None = None, **context):
        super().__init__(**context)
        if policy_id:
            self.context["policy_id"] = policy_id
        if reason:
            self.context["denial_reason"] = reason


class AUTHZ_INSUFFICIENT_SCOPE(Fault):
    """Token missing required scopes."""
    domain = FaultDomain.SECURITY
    code = "AUTHZ_002"
    severity = Severity.WARN
    message = "Insufficient scope"
    public_message = "Insufficient permissions"
    retryable = False
    
    def __init__(self, required: list[str] | None = None, **context):
        super().__init__(**context)
        if required:
            self.context["required_scopes"] = required


class AUTHZ_INSUFFICIENT_ROLE(Fault):
    """Identity missing required role."""
    domain = FaultDomain.SECURITY
    code = "AUTHZ_003"
    severity = Severity.WARN
    message = "Insufficient role"
    public_message = "Insufficient permissions"
    retryable = False
    
    def __init__(self, required: list[str] | None = None, **context):
        super().__init__(**context)
        if required:
            self.context["required_roles"] = required


class AUTHZ_RESOURCE_FORBIDDEN(Fault):
    """Access to resource is forbidden."""
    domain = FaultDomain.SECURITY
    code = "AUTHZ_004"
    severity = Severity.WARN
    message = "Resource forbidden"
    public_message = "Access to this resource is forbidden"
    retryable = False


class AUTHZ_TENANT_MISMATCH(Fault):
    """Identity tenant doesn't match resource tenant."""
    domain = FaultDomain.SECURITY
    code = "AUTHZ_005"
    severity = Severity.ERROR
    message = "Tenant mismatch"
    public_message = "Access denied"
    retryable = False


# ============================================================================
# Credential Management Faults
# ============================================================================

class AUTH_PASSWORD_WEAK(Fault):
    """Password doesn't meet policy requirements."""
    domain = FaultDomain.SECURITY
    code = "AUTH_101"
    severity = Severity.WARN
    message = "Weak password"
    public_message = "Password doesn't meet security requirements"
    retryable = True
    
    def __init__(self, errors: list[str] | None = None, **context):
        super().__init__(**context)
        if errors:
            self.context["validation_errors"] = errors


class AUTH_PASSWORD_BREACHED(Fault):
    """Password found in breach database."""
    domain = FaultDomain.SECURITY
    code = "AUTH_102"
    severity = Severity.WARN
    message = "Breached password"
    public_message = "This password has been found in data breaches. Please choose a different password."
    retryable = True


class AUTH_PASSWORD_REUSED(Fault):
    """Password was recently used."""
    domain = FaultDomain.SECURITY
    code = "AUTH_103"
    severity = Severity.WARN
    message = "Password reused"
    public_message = "This password was recently used. Please choose a different password."
    retryable = True


class AUTH_KEY_EXPIRED(Fault):
    """API key has expired."""
    domain = FaultDomain.SECURITY
    code = "AUTH_104"
    severity = Severity.WARN
    message = "API key expired"
    public_message = "API key has expired"
    retryable = False


class AUTH_KEY_REVOKED(Fault):
    """API key has been revoked."""
    domain = FaultDomain.SECURITY
    code = "AUTH_105"
    severity = Severity.WARN
    message = "API key revoked"
    public_message = "API key has been revoked"
    retryable = False


# ============================================================================
# Session Integration Faults
# ============================================================================

class AUTH_SESSION_REQUIRED(Fault):
    """Session required but not found."""
    domain = FaultDomain.SECURITY
    code = "AUTH_201"
    severity = Severity.WARN
    message = "Session required"
    public_message = "Please log in"
    retryable = False


class AUTH_SESSION_INVALID(Fault):
    """Session is invalid or corrupted."""
    domain = FaultDomain.SECURITY
    code = "AUTH_202"
    severity = Severity.WARN
    message = "Invalid session"
    public_message = "Your session is invalid. Please log in again."
    retryable = False


class AUTH_SESSION_HIJACK_DETECTED(Fault):
    """Potential session hijacking detected."""
    domain = FaultDomain.SECURITY
    code = "AUTH_203"
    severity = Severity.ERROR
    message = "Session hijack detected"
    public_message = "Security issue detected. Please log in again."
    retryable = False


# ============================================================================
# OAuth/OIDC Specific Faults
# ============================================================================

class AUTH_CONSENT_REQUIRED(Fault):
    """User consent required for OAuth flow."""
    domain = FaultDomain.SECURITY
    code = "AUTH_301"
    severity = Severity.INFO
    message = "Consent required"
    public_message = "Please authorize this application"
    retryable = True


class AUTH_DEVICE_CODE_PENDING(Fault):
    """Device code authorization pending."""
    domain = FaultDomain.SECURITY
    code = "AUTH_302"
    severity = Severity.INFO
    message = "Authorization pending"
    public_message = "Waiting for user authorization"
    retryable = True


class AUTH_DEVICE_CODE_EXPIRED(Fault):
    """Device code has expired."""
    domain = FaultDomain.SECURITY
    code = "AUTH_303"
    severity = Severity.WARN
    message = "Device code expired"
    public_message = "Authorization code expired. Please try again."
    retryable = False


class AUTH_SLOW_DOWN(Fault):
    """Device flow polling too fast."""
    domain = FaultDomain.SECURITY
    code = "AUTH_304"
    severity = Severity.WARN
    message = "Slow down"
    public_message = "Polling too frequently"
    retryable = True
    retry_after = 5


# ============================================================================
# MFA Faults
# ============================================================================

class AUTH_MFA_NOT_ENROLLED(Fault):
    """MFA not enrolled for user."""
    domain = FaultDomain.SECURITY
    code = "AUTH_401"
    severity = Severity.WARN
    message = "MFA not enrolled"
    public_message = "Multi-factor authentication is not set up"
    retryable = True


class AUTH_MFA_ALREADY_ENROLLED(Fault):
    """MFA already enrolled."""
    domain = FaultDomain.SECURITY
    code = "AUTH_402"
    severity = Severity.WARN
    message = "MFA already enrolled"
    public_message = "Multi-factor authentication is already set up"
    retryable = False


class AUTH_WEBAUTHN_INVALID(Fault):
    """WebAuthn credential invalid."""
    domain = FaultDomain.SECURITY
    code = "AUTH_403"
    severity = Severity.WARN
    message = "WebAuthn invalid"
    public_message = "Security key verification failed"
    retryable = True


class AUTH_BACKUP_CODE_INVALID(Fault):
    """Invalid backup code."""
    domain = FaultDomain.SECURITY
    code = "AUTH_404"
    severity = Severity.WARN
    message = "Invalid backup code"
    public_message = "Invalid backup code"
    retryable = True


class AUTH_BACKUP_CODE_EXHAUSTED(Fault):
    """All backup codes used."""
    domain = FaultDomain.SECURITY
    code = "AUTH_405"
    severity = Severity.WARN
    message = "Backup codes exhausted"
    public_message = "All backup codes have been used. Please generate new codes."
    retryable = False


# ============================================================================
# Utility Functions
# ============================================================================

def raise_auth_fault(fault_class: type[Fault], **kwargs):
    """
    Raise an auth fault with context.
    
    Example:
        raise_auth_fault(AUTH_INVALID_CREDENTIALS, username="user@example.com")
    """
    raise fault_class(**kwargs)


def is_auth_fault(exception: Exception) -> bool:
    """Check if exception is an auth fault."""
    return isinstance(exception, Fault) and exception.domain == FaultDomain.SECURITY
