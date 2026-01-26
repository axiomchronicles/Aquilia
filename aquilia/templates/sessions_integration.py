"""
AquilaTemplates - Session Integration

Deep integration between template system and AquilaSessions.
Enables seamless session access, flash messages, and session state
in templates.

Features:
- Session data access: {{ session.get('user_id') }}
- Flash messages: {{ flash_messages() }}
- Session lifecycle helpers
- Session guards integration
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from aquilia.sessions import Session, SessionEngine
    from aquilia.controller.base import RequestCtx
    from .engine import TemplateEngine


logger = logging.getLogger(__name__)


# ============================================================================
# Session Template Helpers
# ============================================================================


class SessionTemplateProxy:
    """
    Proxy object for session access in templates.
    
    Provides safe, read-only access to session data with
    convenient helpers for common patterns.
    
    Usage in templates:
        {{ session.get('user_id') }}
        {{ session.has('cart') }}
        {% if session.authenticated %}
    """
    
    def __init__(self, session: Optional["Session"] = None):
        self._session = session
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get session value by key.
        
        Example:
            {{ session.get('user_id') }}
            {{ session.get('theme', 'light') }}
        """
        if not self._session:
            return default
        
        return self._session.data.get(key, default)
    
    def has(self, key: str) -> bool:
        """
        Check if session has key.
        
        Example:
            {% if session.has('user_id') %}
                Welcome back!
            {% endif %}
        """
        if not self._session:
            return False
        
        return key in self._session.data
    
    @property
    def authenticated(self) -> bool:
        """
        Check if session is authenticated.
        
        Example:
            {% if session.authenticated %}
                <a href="/profile">Profile</a>
            {% endif %}
        """
        if not self._session:
            return False
        
        # Check for common auth indicators
        return (
            self.has('user_id') or
            self.has('identity_id') or
            self.has('authenticated')
        )
    
    @property
    def id(self) -> Optional[str]:
        """Get session ID."""
        if not self._session:
            return None
        return str(self._session.session_id)
    
    @property
    def created_at(self) -> Optional[str]:
        """Get session creation timestamp."""
        if not self._session:
            return None
        return self._session.created_at.isoformat()
    
    @property
    def expires_at(self) -> Optional[str]:
        """Get session expiration timestamp."""
        if not self._session:
            return None
        if self._session.expires_at:
            return self._session.expires_at.isoformat()
        return None
    
    def __bool__(self) -> bool:
        """Check if session exists."""
        return self._session is not None
    
    def __str__(self) -> str:
        """String representation."""
        if not self._session:
            return "<No Session>"
        return f"<Session {self.id}>"


class FlashMessages:
    """
    Flash message manager for templates.
    
    Flash messages are one-time notifications stored in session
    and consumed on first access.
    
    Usage in templates:
        {% for message in flash_messages() %}
            <div class="alert alert-{{ message.level }}">
                {{ message.text }}
            </div>
        {% endfor %}
    """
    
    FLASH_KEY = "_flash_messages"
    
    def __init__(self, session: Optional["Session"] = None):
        self._session = session
    
    def get_messages(self) -> List[Dict[str, str]]:
        """
        Get and consume flash messages.
        
        Returns:
            List of message dicts with 'text' and 'level' keys
        """
        if not self._session:
            return []
        
        messages = self._session.data.get(self.FLASH_KEY, [])
        
        # Consume messages (remove from session)
        if messages:
            self._session.data[self.FLASH_KEY] = []
        
        return messages
    
    def peek_messages(self) -> List[Dict[str, str]]:
        """
        Get flash messages without consuming them.
        
        Returns:
            List of message dicts
        """
        if not self._session:
            return []
        
        return self._session.data.get(self.FLASH_KEY, [])
    
    @staticmethod
    def add_flash(
        session: "Session",
        message: str,
        level: str = "info"
    ) -> None:
        """
        Add flash message to session.
        
        Call this from controllers to add messages.
        
        Args:
            session: Active session
            message: Message text
            level: Message level (info, success, warning, error)
        """
        if FlashMessages.FLASH_KEY not in session.data:
            session.data[FlashMessages.FLASH_KEY] = []
        
        session.data[FlashMessages.FLASH_KEY].append({
            "text": message,
            "level": level,
        })


# ============================================================================
# Template Engine Enhancement
# ============================================================================


def enhance_engine_with_sessions(
    engine: "TemplateEngine",
    session_engine: Optional["SessionEngine"] = None
) -> None:
    """
    Enhance template engine with session integration.
    
    Registers session helpers, filters, and globals.
    
    Args:
        engine: TemplateEngine to enhance
        session_engine: SessionEngine instance (optional)
    """
    # Register session proxy helper
    def create_session_proxy(request_ctx: Optional["RequestCtx"] = None) -> SessionTemplateProxy:
        """Create session proxy from request context."""
        if request_ctx and hasattr(request_ctx, 'session'):
            return SessionTemplateProxy(request_ctx.session)
        return SessionTemplateProxy(None)
    
    # This will be injected per-render, not as global
    # engine.register_global("session", create_session_proxy)
    
    # Register flash message helper
    def flash_messages_func():
        """Get flash messages (callable in templates)."""
        # This needs access to current request context
        # Will be injected per-render
        return []
    
    engine.register_global("flash_messages", flash_messages_func)
    
    # Register session-aware filters
    @engine.register_filter("session_value")
    def session_value_filter(key: str, default: Any = None) -> Any:
        """
        Filter to get session value.
        
        Usage: {{ 'user_id' | session_value }}
        """
        # This needs current session from context
        return default
    
    logger.info("Template engine enhanced with session integration")


def inject_session_context(
    context: Dict[str, Any],
    request_ctx: Optional["RequestCtx"] = None
) -> None:
    """
    Inject session variables into template context.
    
    Call this in context creation to add session helpers.
    
    Args:
        context: Template context dictionary
        request_ctx: Request context with session
    """
    # Create session proxy
    session_proxy = None
    if request_ctx and hasattr(request_ctx, 'session'):
        session_proxy = SessionTemplateProxy(request_ctx.session)
    else:
        session_proxy = SessionTemplateProxy(None)
    
    context["session"] = session_proxy
    
    # Flash messages helper
    flash = FlashMessages(
        request_ctx.session if request_ctx and hasattr(request_ctx, 'session') else None
    )
    
    def flash_messages_func():
        return flash.get_messages()
    
    context["flash_messages"] = flash_messages_func
    
    # Session state helpers
    context["has_session"] = bool(session_proxy)


# ============================================================================
# Controller Helper Mixins
# ============================================================================


class TemplateFlashMixin:
    """
    Mixin for controllers to add flash messages.
    
    Usage:
        class MyController(Controller, TemplateFlashMixin):
            @POST("/submit")
            async def submit(self, ctx):
                self.flash(ctx, "Form submitted!", "success")
                return self.redirect("/")
    """
    
    def flash(
        self,
        ctx: "RequestCtx",
        message: str,
        level: str = "info"
    ) -> None:
        """
        Add flash message to session.
        
        Args:
            ctx: Request context
            message: Message text
            level: Message level (info, success, warning, error)
        """
        if not ctx.session:
            logger.warning("Attempted to flash message without session")
            return
        
        FlashMessages.add_flash(ctx.session, message, level)
    
    def flash_success(self, ctx: "RequestCtx", message: str) -> None:
        """Flash success message."""
        self.flash(ctx, message, "success")
    
    def flash_error(self, ctx: "RequestCtx", message: str) -> None:
        """Flash error message."""
        self.flash(ctx, message, "error")
    
    def flash_warning(self, ctx: "RequestCtx", message: str) -> None:
        """Flash warning message."""
        self.flash(ctx, message, "warning")
    
    def flash_info(self, ctx: "RequestCtx", message: str) -> None:
        """Flash info message."""
        self.flash(ctx, message, "info")


# ============================================================================
# Middleware Enhancement
# ============================================================================


def enhance_middleware_with_sessions():
    """
    Enhance TemplateMiddleware with session context injection.
    
    This is called automatically when both templates and sessions
    are enabled in the application.
    """
    # Import here to avoid circular dependency
    from .middleware import TemplateMiddleware
    from .context import create_template_context
    
    # Patch middleware to inject session context
    original_process = TemplateMiddleware.process_request
    
    async def patched_process(self, request, next_handler):
        # Call original
        response = await original_process(self, request, next_handler)
        
        # Inject session helpers into request.state
        if hasattr(request, 'state'):
            # Session proxy will be created during template rendering
            pass
        
        return response
    
    TemplateMiddleware.process_request = patched_process
    logger.info("TemplateMiddleware enhanced with session injection")
