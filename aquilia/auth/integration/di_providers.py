"""
AquilAuth - DI Providers

Dependency injection providers for all auth components.
Enables proper lifecycle management and dependency resolution.

This module provides:
- Providers for all auth components
- Factory functions for common configurations
- Integration with Aquilia DI system
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from aquilia.di import Container
from aquilia.di.decorators import service, factory
from aquilia.di.lifecycle import Lifecycle
# Scope imports removed - using string literals
from aquilia.sessions import (
    MemoryStore as SessionMemoryStore,
    SessionEngine,
    SessionPolicy,
)

from ..core import Identity
from ..hashing import PasswordHasher
from ..manager import AuthManager, RateLimiter
from ..mfa import MFAManager, TOTPProvider
from ..oauth import OAuth2Manager
from ..authz import AuthzEngine, RBACEngine, ABACEngine
from ..stores import (
    MemoryIdentityStore,
    MemoryCredentialStore,
    MemoryOAuthClientStore,
    MemoryTokenStore,
    MemoryAuthorizationCodeStore,
    MemoryDeviceCodeStore,
)
from ..tokens import KeyRing, TokenManager
from .aquila_sessions import (
    SessionAuthBridge,
    user_session_policy,
    api_session_policy,
)

if TYPE_CHECKING:
    from aquilia.faults import FaultEngine


# ============================================================================
# Core Auth Providers
# ============================================================================


@service(scope="app")
class PasswordHasherProvider:
    """Provider for PasswordHasher."""
    
    def provide(self) -> PasswordHasher:
        """Provide PasswordHasher instance."""
        return PasswordHasher()


@service(scope="app")
class KeyRingProvider:
    """Provider for KeyRing."""
    
    def provide(self) -> KeyRing:
        """Provide KeyRing with default keys."""
        keyring = KeyRing()
        # Generate default key on startup
        keyring.generate_key(
            key_id="default",
            algorithm="RS256",
            make_primary=True,
        )
        return keyring


@service(scope="app")
class TokenManagerProvider:
    """Provider for TokenManager."""
    
    def __init__(self, keyring: KeyRing):
        self.keyring = keyring
    
    def provide(self) -> TokenManager:
        """Provide TokenManager instance."""
        return TokenManager(keyring=self.keyring)


@service(scope="app")
class RateLimiterProvider:
    """Provider for RateLimiter."""
    
    def provide(
        self,
        max_attempts: int = 5,
        window_seconds: int = 900,
        lockout_duration: int = 3600,
    ) -> RateLimiter:
        """Provide RateLimiter instance."""
        return RateLimiter(
            max_attempts=max_attempts,
            window_seconds=window_seconds,
            lockout_duration=lockout_duration,
        )


# ============================================================================
# Store Providers
# ============================================================================


@service(scope="app")
class IdentityStoreProvider:
    """Provider for IdentityStore."""
    
    def provide(self) -> MemoryIdentityStore:
        """Provide memory-based identity store."""
        return MemoryIdentityStore()


@service(scope="app")
class CredentialStoreProvider:
    """Provider for CredentialStore."""
    
    def provide(self) -> MemoryCredentialStore:
        """Provide memory-based credential store."""
        return MemoryCredentialStore()


@service(scope="app")
class TokenStoreProvider:
    """Provider for TokenStore."""
    
    def provide(self) -> MemoryTokenStore:
        """Provide memory-based token store."""
        return MemoryTokenStore()


@service(scope="app")
class OAuthClientStoreProvider:
    """Provider for OAuthClientStore."""
    
    def provide(self) -> MemoryOAuthClientStore:
        """Provide memory-based OAuth client store."""
        return MemoryOAuthClientStore()


@service(scope="app")
class AuthorizationCodeStoreProvider:
    """Provider for AuthorizationCodeStore."""
    
    def provide(self) -> MemoryAuthorizationCodeStore:
        """Provide memory-based authorization code store."""
        return MemoryAuthorizationCodeStore()


@service(scope="app")
class DeviceCodeStoreProvider:
    """Provider for DeviceCodeStore."""
    
    def provide(self) -> MemoryDeviceCodeStore:
        """Provide memory-based device code store."""
        return MemoryDeviceCodeStore()


# ============================================================================
# Manager Providers
# ============================================================================


@service(scope="app")
class AuthManagerProvider:
    """Provider for AuthManager."""
    
    def __init__(
        self,
        identity_store: MemoryIdentityStore,
        credential_store: MemoryCredentialStore,
        token_store: MemoryTokenStore,
        token_manager: TokenManager,
        password_hasher: PasswordHasher,
        rate_limiter: RateLimiter,
    ):
        self.identity_store = identity_store
        self.credential_store = credential_store
        self.token_store = token_store
        self.token_manager = token_manager
        self.password_hasher = password_hasher
        self.rate_limiter = rate_limiter
    
    def provide(self) -> AuthManager:
        """Provide AuthManager instance."""
        return AuthManager(
            identity_store=self.identity_store,
            credential_store=self.credential_store,
            token_store=self.token_store,
            token_manager=self.token_manager,
            password_hasher=self.password_hasher,
            rate_limiter=self.rate_limiter,
        )


@service(scope="app")
class MFAManagerProvider:
    """Provider for MFAManager."""
    
    def __init__(self, credential_store: MemoryCredentialStore):
        self.credential_store = credential_store
    
    def provide(self) -> MFAManager:
        """Provide MFAManager instance."""
        return MFAManager(
            credential_store=self.credential_store,
            totp_provider=TOTPProvider(),
        )


@service(scope="app")
class OAuth2ManagerProvider:
    """Provider for OAuth2Manager."""
    
    def __init__(
        self,
        client_store: MemoryOAuthClientStore,
        auth_code_store: MemoryAuthorizationCodeStore,
        device_code_store: MemoryDeviceCodeStore,
        token_manager: TokenManager,
        identity_store: MemoryIdentityStore,
    ):
        self.client_store = client_store
        self.auth_code_store = auth_code_store
        self.device_code_store = device_code_store
        self.token_manager = token_manager
        self.identity_store = identity_store
    
    def provide(self) -> OAuth2Manager:
        """Provide OAuth2Manager instance."""
        return OAuth2Manager(
            client_store=self.client_store,
            auth_code_store=self.auth_code_store,
            device_code_store=self.device_code_store,
            token_manager=self.token_manager,
            identity_store=self.identity_store,
        )


@service(scope="app")
class AuthzEngineProvider:
    """Provider for AuthzEngine."""
    
    def provide(self) -> AuthzEngine:
        """Provide AuthzEngine instance."""
        rbac = RBACEngine()
        abac = ABACEngine()
        return AuthzEngine(rbac=rbac, abac=abac)


# ============================================================================
# Session Providers
# ============================================================================


@service(scope="app")
class SessionEngineProvider:
    """Provider for SessionEngine."""
    
    def provide(
        self,
        policy: SessionPolicy | None = None,
        logger: logging.Logger | None = None,
    ) -> SessionEngine:
        """Provide SessionEngine instance."""
        if policy is None:
            policy = user_session_policy()
        
        return SessionEngine(
            policy=policy,
            store=SessionMemoryStore(),
            transport=policy.transport,
            logger=logger,
        )


@service(scope="app")
class SessionAuthBridgeProvider:
    """Provider for SessionAuthBridge."""
    
    def __init__(self, session_engine: SessionEngine):
        self.session_engine = session_engine
    
    def provide(self) -> SessionAuthBridge:
        """Provide SessionAuthBridge instance."""
        return SessionAuthBridge(session_engine=self.session_engine)


# ============================================================================
# Container Registration Helper
# ============================================================================


def register_auth_providers(
    container: Container,
    config: dict[str, Any] | None = None,
) -> None:
    """
    Register all auth providers in DI container.
    
    Args:
        container: DI container
        config: Optional configuration dict
    """
    config = config or {}
    
    # Core components
    container.register_provider(PasswordHasherProvider)
    container.register_provider(KeyRingProvider)
    container.register_provider(TokenManagerProvider)
    container.register_provider(RateLimiterProvider)
    
    # Stores
    container.register_provider(IdentityStoreProvider)
    container.register_provider(CredentialStoreProvider)
    container.register_provider(TokenStoreProvider)
    container.register_provider(OAuthClientStoreProvider)
    container.register_provider(AuthorizationCodeStoreProvider)
    container.register_provider(DeviceCodeStoreProvider)
    
    # Managers
    container.register_provider(AuthManagerProvider)
    container.register_provider(MFAManagerProvider)
    container.register_provider(OAuth2ManagerProvider)
    container.register_provider(AuthzEngineProvider)
    
    # Sessions
    container.register_provider(SessionEngineProvider)
    container.register_provider(SessionAuthBridgeProvider)


def create_auth_container(
    config: dict[str, Any] | None = None,
    parent: Container | None = None,
) -> Container:
    """
    Create DI container with all auth providers registered.
    
    Args:
        config: Optional configuration dict
        parent: Optional parent container
        
    Returns:
        Configured container
    """
    container = Container(scope="app", parent=parent)
    register_auth_providers(container, config)
    return container


# ============================================================================
# Configuration Builders
# ============================================================================


class AuthConfig:
    """
    Authentication configuration builder.
    
    Provides fluent interface for configuring auth system.
    """
    
    def __init__(self):
        self._config: dict[str, Any] = {
            "rate_limit": {
                "max_attempts": 5,
                "window_seconds": 900,
                "lockout_duration": 3600,
            },
            "session": {
                "policy": "user",
                "ttl_days": 7,
                "idle_timeout_hours": 1,
                "max_sessions": 5,
            },
            "tokens": {
                "access_ttl_minutes": 15,
                "refresh_ttl_days": 30,
            },
            "mfa": {
                "enabled": False,
                "required": False,
            },
            "oauth": {
                "enabled": False,
            },
        }
    
    def rate_limit(
        self,
        max_attempts: int = 5,
        window_seconds: int = 900,
        lockout_duration: int = 3600,
    ) -> AuthConfig:
        """Configure rate limiting."""
        self._config["rate_limit"] = {
            "max_attempts": max_attempts,
            "window_seconds": window_seconds,
            "lockout_duration": lockout_duration,
        }
        return self
    
    def sessions(
        self,
        policy: str = "user",
        ttl_days: int = 7,
        idle_timeout_hours: int = 1,
        max_sessions: int = 5,
    ) -> AuthConfig:
        """Configure session management."""
        self._config["session"] = {
            "policy": policy,
            "ttl_days": ttl_days,
            "idle_timeout_hours": idle_timeout_hours,
            "max_sessions": max_sessions,
        }
        return self
    
    def tokens(
        self,
        access_ttl_minutes: int = 15,
        refresh_ttl_days: int = 30,
    ) -> AuthConfig:
        """Configure token lifetimes."""
        self._config["tokens"] = {
            "access_ttl_minutes": access_ttl_minutes,
            "refresh_ttl_days": refresh_ttl_days,
        }
        return self
    
    def mfa(
        self,
        enabled: bool = True,
        required: bool = False,
    ) -> AuthConfig:
        """Configure MFA."""
        self._config["mfa"] = {
            "enabled": enabled,
            "required": required,
        }
        return self
    
    def oauth(self, enabled: bool = True) -> AuthConfig:
        """Enable OAuth2/OIDC."""
        self._config["oauth"] = {"enabled": enabled}
        return self
    
    def build(self) -> dict[str, Any]:
        """Build configuration dict."""
        return self._config


# ============================================================================
# Exports
# ============================================================================


__all__ = [
    # Providers
    "PasswordHasherProvider",
    "KeyRingProvider",
    "TokenManagerProvider",
    "RateLimiterProvider",
    "IdentityStoreProvider",
    "CredentialStoreProvider",
    "TokenStoreProvider",
    "OAuthClientStoreProvider",
    "AuthorizationCodeStoreProvider",
    "DeviceCodeStoreProvider",
    "AuthManagerProvider",
    "MFAManagerProvider",
    "OAuth2ManagerProvider",
    "AuthzEngineProvider",
    "SessionEngineProvider",
    "SessionAuthBridgeProvider",
    # Helpers
    "register_auth_providers",
    "create_auth_container",
    "AuthConfig",
]
